//! REVM `CacheDB<AlloyDB>` warm cache.
//!
//! The cache owns the REVM database used by hot-path simulation. It is backed
//! by an Alloy HTTP provider, preloads watched pool accounts on construction,
//! stores the latest observed `PoolState` per pool, and exposes per-pool epoch
//! counters for stale-read detection.
//!
//! This module deliberately does not infer protocol storage slots. Pool-specific
//! reserve/tick storage writes require explicit slot manifests per adapter; until
//! those exist, monitor updates are recorded as versioned snapshots and REVM
//! account/storage misses fall back to the pinned AlloyDB provider.

use alloy::primitives::{Address, Bytes, U256};
use alloy_network::Ethereum;
use alloy_provider::{DynProvider, Provider, ProviderBuilder};
use dashmap::DashMap;
use eyre::{eyre, ContextCompat, Result, WrapErr};
use parking_lot::RwLock;
use revm::{
    context::result::{ExecutionResult, Output},
    database::{AlloyDB, BlockId, CacheDB, WrapDatabaseAsync},
    primitives::TxKind,
    Context, ExecuteEvm, MainBuilder, MainContext,
};

use crate::monitor::PoolState;

/// Type-erased Alloy provider used by the REVM database backend.
pub type RevmProvider = DynProvider<Ethereum>;

/// Concrete REVM warm-cache shape for the currently pinned `revm` / `alloy`.
pub type RevmCacheDb = CacheDB<WrapDatabaseAsync<AlloyDB<Ethereum, RevmProvider>>>;

/// Warm-cache wrapper around REVM's `CacheDB<AlloyDB>`.
pub struct RevmDb {
    inner: RwLock<RevmCacheDb>,
    epochs: DashMap<Address, u64>,
    pool_states: DashMap<Address, PoolState>,
}

impl RevmDb {
    /// Construct a fresh DB backed by the supplied HTTP RPC endpoint.
    ///
    /// `seed_pools` is the initial pool set to load into the REVM cache. Each
    /// pool gets epoch `0`; monitor updates advance the epoch through
    /// [`Self::apply_pool_state`].
    pub async fn new(arb_rpc_http: &str, seed_pools: &[Address]) -> Result<Self> {
        let provider = ProviderBuilder::new()
            .connect_http(
                arb_rpc_http
                    .parse()
                    .wrap_err("invalid Arbitrum RPC HTTP URL")?,
            )
            .erased();
        Self::from_provider_at_block(provider, BlockId::default(), seed_pools).await
    }

    /// Construct a DB from an already-built Alloy provider and explicit block.
    ///
    /// This is the pinned-block entry point for future REVM-vs-`eth_call`
    /// validators; passing a numeric `BlockId` keeps AlloyDB reads deterministic.
    pub async fn from_provider_at_block(
        provider: RevmProvider,
        block: BlockId,
        seed_pools: &[Address],
    ) -> Result<Self> {
        let alloy_db = AlloyDB::new(provider, block);
        let wrapped = WrapDatabaseAsync::new(alloy_db).wrap_err("failed to wrap AlloyDB")?;
        let mut cache = CacheDB::new(wrapped);
        let epochs = DashMap::new();

        for pool in seed_pools {
            cache
                .load_account(*pool)
                .wrap_err_with(|| format!("failed to preload pool account {pool:?}"))?;
            epochs.insert(*pool, 0);
        }

        Ok(Self {
            inner: RwLock::new(cache),
            epochs,
            pool_states: DashMap::new(),
        })
    }

    /// Execute an eth-call-style REVM call against the warm cache.
    ///
    /// Cache misses lazily hit the AlloyDB provider configured at construction.
    /// The write lock is intentional: REVM may populate the cache while handling
    /// account, code, and storage misses.
    pub fn call(&self, from: Address, to: Address, calldata: Bytes) -> Result<Bytes> {
        self.call_with_value(from, to, calldata, U256::ZERO)
    }

    /// Execute an eth-call-style REVM call with an explicit `msg.value`.
    pub fn call_with_value(
        &self,
        from: Address,
        to: Address,
        calldata: Bytes,
        value: U256,
    ) -> Result<Bytes> {
        let mut db = self.inner.write();
        let mut evm = Context::mainnet()
            .with_db(&mut *db)
            .modify_tx_chained(|tx| {
                tx.caller = from;
                tx.kind = TxKind::Call(to);
                tx.data = calldata;
                tx.value = value;
            })
            .build_mainnet();

        let result = evm.replay().wrap_err("REVM replay failed")?.result;
        match result {
            ExecutionResult::Success {
                output: Output::Call(value),
                ..
            } => Ok(value),
            ExecutionResult::Success { output, .. } => {
                Err(eyre!("unexpected non-call REVM output: {output:?}"))
            }
            ExecutionResult::Revert { output, .. } => Err(eyre!("REVM call reverted: {output:?}")),
            ExecutionResult::Halt { reason, gas, .. } => {
                Err(eyre!("REVM call halted: {reason:?}, gas={gas:?}"))
            }
        }
    }

    /// Apply a fresh on-chain state to the local epoch map.
    ///
    /// This does not mutate protocol storage. Storage writes will be added only
    /// from audited per-protocol slot manifests; for now, the state cache is the
    /// deterministic freshness witness consumed by strategy logic.
    pub fn apply_pool_state(&self, state: &PoolState) -> Result<()> {
        self.pool_states.insert(state.address, state.clone());
        self.epochs
            .entry(state.address)
            .and_modify(|epoch| *epoch = epoch.saturating_add(1))
            .or_insert(1);
        Ok(())
    }

    /// Return the latest observed pool state, if the monitor has supplied one.
    pub fn pool_state(&self, pool: Address) -> Option<PoolState> {
        self.pool_states.get(&pool).map(|state| state.clone())
    }

    /// Read the current epoch counter for `pool`.
    ///
    /// Simulations record this value and the submit path compares it before
    /// dispatch; any intervening monitor update invalidates the quote.
    pub fn epoch(&self, pool: Address) -> u64 {
        self.epochs.get(&pool).map_or(0, |epoch| *epoch)
    }

    #[cfg(test)]
    pub(crate) fn test_instance() -> Self {
        let provider = ProviderBuilder::new()
            .connect_http("http://127.0.0.1:1".parse().expect("valid test URL"))
            .erased();
        let alloy_db = AlloyDB::new(provider, BlockId::default());
        let wrapped = WrapDatabaseAsync::new(alloy_db).expect("test AlloyDB wrapper");
        Self {
            inner: RwLock::new(CacheDB::new(wrapped)),
            epochs: DashMap::new(),
            pool_states: DashMap::new(),
        }
    }
}

#[cfg(test)]
mod tests {
    use std::{env, str::FromStr};

    use alloy::primitives::{address, hex};
    use alloy_rpc_types_eth::{TransactionInput, TransactionRequest};

    use super::*;
    use crate::Reserves;

    #[tokio::test(flavor = "multi_thread")]
    async fn pool_state_updates_increment_epoch() -> Result<()> {
        let db = RevmDb::test_instance();
        let pool = address!("0000000000000000000000000000000000000001");
        let first_state = PoolState {
            address: pool,
            block_number: 10,
            reserves: Reserves::V2 {
                reserve0: U256::from(100),
                reserve1: U256::from(200),
            },
        };
        let second_state = PoolState {
            block_number: 11,
            ..first_state.clone()
        };

        assert_eq!(db.epoch(pool), 0);
        db.apply_pool_state(&first_state)?;
        assert_eq!(db.epoch(pool), 1);
        assert_eq!(db.pool_state(pool).expect("pool state").block_number, 10);

        db.apply_pool_state(&second_state)?;
        assert_eq!(db.epoch(pool), 2);
        assert_eq!(db.pool_state(pool).expect("pool state").block_number, 11);

        Ok(())
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn opt_in_revm_call_matches_eth_call_at_pinned_block() -> Result<()> {
        let Some(fixture) = PinnedCallFixture::from_env()? else {
            return Ok(());
        };

        let provider = ProviderBuilder::new()
            .connect_http(
                fixture
                    .rpc_url
                    .parse()
                    .wrap_err("invalid ARB_RPC_HTTP URL")?,
            )
            .erased();
        let block = BlockId::number(fixture.block);
        let db = RevmDb::from_provider_at_block(provider.clone(), block, &[fixture.to]).await?;

        let revm_output = db.call_with_value(
            fixture.from,
            fixture.to,
            fixture.calldata.clone(),
            fixture.value,
        )?;

        let tx = TransactionRequest::default()
            .from(fixture.from)
            .to(fixture.to)
            .value(fixture.value)
            .input(TransactionInput::both(fixture.calldata));
        let eth_call_output = provider
            .call(tx)
            .block(block)
            .await
            .wrap_err("pinned-block eth_call failed")?;

        assert_eq!(revm_output, eth_call_output);
        Ok(())
    }

    struct PinnedCallFixture {
        rpc_url: String,
        block: u64,
        from: Address,
        to: Address,
        calldata: Bytes,
        value: U256,
    }

    impl PinnedCallFixture {
        fn from_env() -> Result<Option<Self>> {
            let Some(rpc_url) = optional_env("ARB_RPC_HTTP")? else {
                return Ok(None);
            };
            let Some(block) = optional_env("REVM_VALIDATION_BLOCK")? else {
                return Ok(None);
            };
            let Some(to) = optional_env("REVM_VALIDATION_TO")? else {
                return Ok(None);
            };
            let Some(calldata) = optional_env("REVM_VALIDATION_CALLDATA")? else {
                return Ok(None);
            };

            let from = optional_env("REVM_VALIDATION_FROM")?
                .map(|value| Address::from_str(&value))
                .transpose()
                .wrap_err("invalid REVM_VALIDATION_FROM")?
                .unwrap_or(Address::ZERO);
            let value = optional_env("REVM_VALIDATION_VALUE_WEI")?
                .map(|value| U256::from_str(&value))
                .transpose()
                .wrap_err("invalid REVM_VALIDATION_VALUE_WEI")?
                .unwrap_or(U256::ZERO);

            Ok(Some(Self {
                rpc_url,
                block: block
                    .parse::<u64>()
                    .wrap_err("invalid REVM_VALIDATION_BLOCK")?,
                from,
                to: Address::from_str(&to).wrap_err("invalid REVM_VALIDATION_TO")?,
                calldata: decode_hex_bytes("REVM_VALIDATION_CALLDATA", &calldata)?,
                value,
            }))
        }
    }

    fn optional_env(name: &str) -> Result<Option<String>> {
        match env::var(name) {
            Ok(value) if value.trim().is_empty() => Ok(None),
            Ok(value) => Ok(Some(value)),
            Err(env::VarError::NotPresent) => Ok(None),
            Err(error) => Err(error).wrap_err_with(|| format!("invalid {name}")),
        }
    }

    fn decode_hex_bytes(name: &str, value: &str) -> Result<Bytes> {
        let encoded = value
            .strip_prefix("0x")
            .or_else(|| value.strip_prefix("0X"))
            .unwrap_or(value);
        let decoded = hex::decode(encoded).wrap_err_with(|| format!("invalid {name} hex"))?;
        Ok(Bytes::from(decoded))
    }
}
