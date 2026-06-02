//! Pre-flight simulation gate (ADR-026 hybrid model).
//!
//! Phase 1d implementation: REVM `CacheDB` over a custom alloy-2.0 backed
//! database. We measure the actual `profit_token.balanceOf(signer)` delta
//! that running `plan.calldata` against `plan.target` produces, by transacting
//! three txs against an in-memory journal:
//!
//!   1. `transact(balanceOf(signer))` against `plan.profit_token` — pre-balance
//!   2. `transact_commit(plan.calldata)` against `plan.target` — apply the plan
//!   3. `transact(balanceOf(signer))` again — post-balance
//!
//! The on-chain `Executor.sol::_runSwapChain` post-swap assertion remains the
//! ultimate safety gate; this preflight catches guaranteed-revert paths and
//! sub-floor profit before paying gas to discover them.
//!
//! ## Why a custom DB instead of revm's bundled `AlloyDB`?
//!
//! `revm-database 13.0.1` is pinned to `alloy 1.8.x`, which clashes with our
//! workspace's `alloy 2.0` and produces "two versions of crate" type errors.
//! The custom [`Web3Db`] is ~80 LOC and uses only `alloy 2.0`'s `Provider<N>`
//! surface. revm's primitive types (`Address`, `U256`, `B256`) are re-exports
//! of `alloy_primitives 1.5.x` (the single resolved version), so the
//! `Database` trait boundary is type-clean.
//!
//! ## Native-currency special case
//!
//! When `plan.profit_token == address(0)` the plan is a pure-ETH path. We
//! read the signer account balance directly from the REVM DB before and
//! after the committed plan transaction, so native paths get the same
//! measured-delta treatment as ERC-20 paths.
//!
//! ## Threading
//!
//! Each cold storage read inside the EVM blocks on the underlying provider
//! RPC. The engine's `tokio::main` is multi-thread by default. We run the
//! entire EVM transaction sequence inside `spawn_blocking` so the executor's
//! main async loop isn't stalled on RPC latency.

use std::sync::Arc;

use alloy::eips::BlockId;
use alloy::network::Ethereum;
use alloy::primitives::{Address, Bytes, I256, U256};
use alloy::providers::Provider;
use alloy::sol;
use alloy::sol_types::SolCall;

use revm::context::result::{ExecResultAndState, ExecutionResult};
use revm::context::{ContextTr, TxEnv};
use revm::database::CacheDB;
use revm::database_interface::{DBErrorMarker, Database, DatabaseRef};
use revm::primitives::{StorageKey, StorageValue, TxKind, B256, KECCAK_EMPTY};
use revm::state::{AccountInfo, Bytecode};
use revm::{handler::EvmTr, Context, ExecuteCommitEvm, ExecuteEvm, MainBuilder, MainContext};
use tokio::runtime::Handle;

use super::PreflightError;
use crate::monitor::Plan;

sol! {
    #[allow(missing_docs)]
    interface IERC20Min {
        function balanceOf(address owner) external view returns (uint256);
    }
}

const NATIVE_TOKEN: Address = Address::ZERO;
/// Generous gas for ERC-20 `balanceOf` reads inside the simulated journal.
const BALANCE_OF_GAS_LIMIT: u64 = 100_000;

/// Run the REVM preflight for `plan` from `from_address` over a fork of the
/// latest block on `provider`.
///
/// Returns the simulated balance delta on `plan.profit_token`. Errors with
/// [`PreflightError::SimulationReverted`] when the plan tx reverts, with
/// [`PreflightError::ForkFailed`] when the EVM/db construction fails, and
/// with [`PreflightError::Unavailable`] when the RPC layer is unreachable.
pub async fn check<P>(
    provider: &P,
    plan: &Plan,
    from_address: Address,
) -> Result<I256, PreflightError>
where
    P: Provider<Ethereum> + Clone + Send + Sync + 'static,
{
    let provider = provider.clone();
    let plan = Arc::new(plan.clone());

    // EVM execution is sync (Database trait is sync). Run on a blocking
    // thread so we don't stall the executor's main async loop while the
    // CacheDB cold-faults storage from the live RPC.
    let plan_for_task = Arc::clone(&plan);
    tokio::task::spawn_blocking(move || {
        run_preflight_blocking(provider, &plan_for_task, from_address)
    })
    .await
    .map_err(|e| PreflightError::ForkFailed(format!("spawn_blocking: {e}")))?
}

fn run_preflight_blocking<P>(
    provider: P,
    plan: &Plan,
    from_address: Address,
) -> Result<I256, PreflightError>
where
    P: Provider<Ethereum> + Clone + Send + Sync + 'static,
{
    let db = Web3Db::new(provider, BlockId::latest()).ok_or_else(|| {
        PreflightError::Unavailable(
            "tokio runtime handle unavailable in preflight thread".to_string(),
        )
    })?;
    let mut cache_db = CacheDB::new(db);
    apply_eip7702_delegation_overlay(&mut cache_db, plan, from_address)?;

    // Three sequential txs from the same caller without explicit nonce
    // bookkeeping — disable the nonce check so the journal doesn't reject
    // the post-balance read after the plan tx bumps the caller's nonce.
    // The on-chain Executor reverifies every prerequisite; the journal
    // only mirrors live state for sim accuracy.
    let mut evm = Context::mainnet()
        .modify_cfg_chained(|cfg| {
            cfg.disable_nonce_check = true;
        })
        .with_db(cache_db)
        .build_mainnet();

    if plan.profit_token == NATIVE_TOKEN {
        let pre_balance =
            read_native_balance(&mut evm, from_address).map_err(map_balance_err("pre"))?;
        execute_plan_tx(&mut evm, plan, from_address)?;
        let post_balance =
            read_native_balance(&mut evm, from_address).map_err(map_balance_err("post"))?;
        return Ok(u256_diff_to_i256(post_balance, pre_balance));
    }

    let pre_balance = read_erc20_balance(&mut evm, plan.profit_token, from_address)
        .map_err(map_balance_err("pre"))?;

    execute_plan_tx(&mut evm, plan, from_address)?;

    let post_balance = read_erc20_balance(&mut evm, plan.profit_token, from_address)
        .map_err(map_balance_err("post"))?;

    Ok(u256_diff_to_i256(post_balance, pre_balance))
}

fn apply_eip7702_delegation_overlay<DB>(
    cache_db: &mut CacheDB<DB>,
    plan: &Plan,
    from_address: Address,
) -> Result<(), PreflightError>
where
    DB: DatabaseRef,
    <DB as DatabaseRef>::Error: std::fmt::Debug,
{
    let Some(delegation) = &plan.eip7702 else {
        return Ok(());
    };
    if delegation.authority != from_address {
        return Err(PreflightError::SimulationReverted(
            "eip7702 authority must equal preflight signer".to_string(),
        ));
    }
    if plan.target != delegation.authority {
        return Err(PreflightError::SimulationReverted(
            "eip7702 plan target must equal authority".to_string(),
        ));
    }

    let delegate_info = cache_db
        .basic(delegation.delegate_address)
        .map_err(|e| PreflightError::Unavailable(format!("eip7702 delegate account: {e:?}")))?
        .ok_or_else(|| {
            PreflightError::SimulationReverted(format!(
                "eip7702 delegate {} has no account",
                delegation.delegate_address
            ))
        })?;
    let delegate_code = match delegate_info.code.clone() {
        Some(code) => code,
        None => cache_db
            .code_by_hash(delegate_info.code_hash)
            .map_err(|e| PreflightError::Unavailable(format!("eip7702 delegate code: {e:?}")))?,
    };
    if delegate_code.is_empty() {
        return Err(PreflightError::SimulationReverted(format!(
            "eip7702 delegate {} has empty code",
            delegation.delegate_address
        )));
    }

    let mut authority_info = cache_db
        .basic(delegation.authority)
        .map_err(|e| PreflightError::Unavailable(format!("eip7702 authority account: {e:?}")))?
        .unwrap_or_else(|| AccountInfo::new(U256::ZERO, 0, KECCAK_EMPTY, Bytecode::new()));
    // EIP-7702 code is a delegation designator, not the delegate bytecode
    // itself. REVM follows the designator and executes the delegate code in
    // the authority account's context; keeping that shape avoids EIP-3607
    // caller-with-code rejection and mirrors a type-4 transaction.
    let designator = Bytecode::new_eip7702(delegation.delegate_address);
    authority_info.code_hash = designator.hash_slow();
    authority_info.code = Some(designator);
    cache_db.insert_account_info(delegation.authority, authority_info);
    Ok(())
}

fn map_balance_err(stage: &'static str) -> impl FnOnce(BalanceReadError) -> PreflightError {
    move |err| match err {
        BalanceReadError::Reverted(s) => {
            PreflightError::SimulationReverted(format!("{stage} balanceOf: {s}"))
        }
        BalanceReadError::Decode(s) => {
            PreflightError::SimulationReverted(format!("{stage} balanceOf decode: {s}"))
        }
        BalanceReadError::Evm(s) => {
            PreflightError::Unavailable(format!("{stage} balanceOf evm: {s}"))
        }
    }
}

/// Build the plan TxEnv and `transact_commit` it against the EVM.
fn execute_plan_tx<DB>(
    evm: &mut PreflightEvm<DB>,
    plan: &Plan,
    from_address: Address,
) -> Result<(), PreflightError>
where
    DB: Database + revm::database_interface::DatabaseCommit,
    <DB as Database>::Error: std::fmt::Debug,
{
    let tx = TxEnv::builder()
        .caller(from_address)
        .kind(TxKind::Call(plan.target))
        .data(plan.calldata.clone())
        .value(plan.value)
        .gas_limit(plan.gas_limit)
        // Keep gas-pricing trivially valid inside the journal — the live
        // gas-envelope is enforced at submission time, not preflight.
        .gas_price(0)
        .gas_priority_fee(Some(0))
        .build()
        .map_err(|e| PreflightError::SimulationReverted(format!("plan tx env: {e:?}")))?;

    let result = evm
        .transact_commit(tx)
        .map_err(|e| PreflightError::SimulationReverted(format!("plan exec: {e:?}")))?;

    match result {
        ExecutionResult::Success { .. } => Ok(()),
        ExecutionResult::Revert { output, .. } => Err(PreflightError::SimulationReverted(
            format_revert_reason(&output),
        )),
        ExecutionResult::Halt { reason, .. } => Err(PreflightError::SimulationReverted(format!(
            "halt: {reason:?}"
        ))),
    }
}

#[derive(Debug)]
enum BalanceReadError {
    Reverted(String),
    Decode(String),
    Evm(String),
}

/// Read `IERC20.balanceOf(owner)` against `token` inside `evm`. Uses
/// `transact` (non-committing) so the journal stays clean for the next
/// stage.
fn read_erc20_balance<DB>(
    evm: &mut PreflightEvm<DB>,
    token: Address,
    owner: Address,
) -> Result<U256, BalanceReadError>
where
    DB: Database,
    <DB as Database>::Error: std::fmt::Debug,
{
    let calldata = IERC20Min::balanceOfCall { owner }.abi_encode();

    let tx = TxEnv::builder()
        .caller(owner)
        .kind(TxKind::Call(token))
        .data(Bytes::from(calldata))
        .gas_limit(BALANCE_OF_GAS_LIMIT)
        .gas_price(0)
        .gas_priority_fee(Some(0))
        .build()
        .map_err(|e| BalanceReadError::Evm(format!("balanceOf tx env: {e:?}")))?;

    let ExecResultAndState { result, .. } = evm
        .transact(tx)
        .map_err(|e| BalanceReadError::Evm(format!("balanceOf transact: {e:?}")))?;

    match result {
        ExecutionResult::Success { output, .. } => {
            let bytes = output.into_data();
            <IERC20Min::balanceOfCall as SolCall>::abi_decode_returns(&bytes)
                .map_err(|e| BalanceReadError::Decode(format!("{e}")))
        }
        ExecutionResult::Revert { output, .. } => {
            Err(BalanceReadError::Reverted(format_revert_reason(&output)))
        }
        ExecutionResult::Halt { reason, .. } => {
            Err(BalanceReadError::Reverted(format!("halt: {reason:?}")))
        }
    }
}

/// Read native balance directly from the EVM DB/journal.
fn read_native_balance<DB>(
    evm: &mut PreflightEvm<DB>,
    owner: Address,
) -> Result<U256, BalanceReadError>
where
    DB: Database,
    <DB as Database>::Error: std::fmt::Debug,
{
    evm.ctx()
        .db_mut()
        .basic(owner)
        .map(|account| account.map_or(U256::ZERO, |info| info.balance))
        .map_err(|e| BalanceReadError::Evm(format!("native balance: {e:?}")))
}

/// Compute `post - pre` as an `I256`. On magnitudes outside the I256 range
/// we saturate — the on-chain Executor enforces the real floor; the
/// preflight's job is to surface the sign + magnitude for logs.
fn u256_diff_to_i256(post: U256, pre: U256) -> I256 {
    if post >= pre {
        let abs = post - pre;
        I256::try_from(abs).unwrap_or(I256::MAX)
    } else {
        let abs = pre - post;
        let signed = I256::try_from(abs).unwrap_or(I256::MAX);
        signed.checked_neg().unwrap_or(I256::MIN + I256::ONE)
    }
}

/// Best-effort readable revert. Solidity revert-reason strings are encoded
/// as `Error(string)` — selector `0x08c379a0` followed by an ABI-encoded
/// string. For other shapes we fall through to a hex preview.
fn format_revert_reason(data: &Bytes) -> String {
    if data.len() >= 4 && data[..4] == [0x08, 0xc3, 0x79, 0xa0] {
        if let Ok(s) = <String as alloy::sol_types::SolValue>::abi_decode(&data[4..]) {
            return format!("revert: {s}");
        }
    }
    if data.is_empty() {
        return "revert: <empty>".to_string();
    }
    format!("revert: 0x{}", alloy::hex::encode(data))
}

// ---------------------------------------------------------------------------
// Web3Db — alloy 2.0 backed REVM `Database` impl
// ---------------------------------------------------------------------------

/// REVM `Database` adapter that reads account/storage state from a live
/// alloy 2.0 `Provider<Ethereum>`. Created fresh per preflight invocation;
/// CacheDB on top memoises hits, so each storage slot pays one RPC round
/// trip per simulation.
///
/// Block_on uses the captured tokio handle. Caller MUST be inside
/// `spawn_blocking` (or another non-current-thread context) — see the
/// `try_current` check in [`Web3Db::new`].
pub struct Web3Db<P> {
    provider: P,
    block_id: BlockId,
    handle: Handle,
}

impl<P> Web3Db<P>
where
    P: Provider<Ethereum> + Clone + Send + Sync + 'static,
{
    /// Construct a new adapter or `None` if no tokio runtime handle is
    /// available in the current thread context.
    pub fn new(provider: P, block_id: BlockId) -> Option<Self> {
        let handle = Handle::try_current().ok()?;
        Some(Self {
            provider,
            block_id,
            handle,
        })
    }
}

#[derive(Debug)]
pub struct Web3DbError(pub String);
impl DBErrorMarker for Web3DbError {}
impl std::fmt::Display for Web3DbError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "Web3Db: {}", self.0)
    }
}
impl std::error::Error for Web3DbError {}

impl<P> DatabaseRef for Web3Db<P>
where
    P: Provider<Ethereum> + Clone + Send + Sync + 'static,
{
    type Error = Web3DbError;

    fn basic_ref(&self, address: Address) -> Result<Option<AccountInfo>, Self::Error> {
        let provider = self.provider.clone();
        let block_id = self.block_id;
        let (nonce, balance, code) = self.handle.block_on(async move {
            tokio::join!(
                provider.get_transaction_count(address).block_id(block_id),
                provider.get_balance(address).block_id(block_id),
                provider.get_code_at(address).block_id(block_id),
            )
        });
        let nonce = nonce.map_err(|e| Web3DbError(format!("nonce {address}: {e}")))?;
        let balance = balance.map_err(|e| Web3DbError(format!("balance {address}: {e}")))?;
        let code_bytes = code.map_err(|e| Web3DbError(format!("code {address}: {e}")))?;

        let bytecode = if code_bytes.is_empty() {
            Bytecode::new()
        } else {
            Bytecode::new_raw(code_bytes)
        };
        let code_hash = if bytecode.is_empty() {
            KECCAK_EMPTY
        } else {
            bytecode.hash_slow()
        };

        Ok(Some(AccountInfo::new(balance, nonce, code_hash, bytecode)))
    }

    fn code_by_hash_ref(&self, _code_hash: B256) -> Result<Bytecode, Self::Error> {
        // `basic_ref()` always loads code inline, so the EVM never reaches
        // here on first-fault paths. Returning empty is safe — the EVM will
        // see code already cached on the AccountInfo.
        Ok(Bytecode::new())
    }

    fn storage_ref(
        &self,
        address: Address,
        index: StorageKey,
    ) -> Result<StorageValue, Self::Error> {
        let provider = self.provider.clone();
        let block_id = self.block_id;
        let val = self
            .handle
            .block_on(async move {
                provider
                    .get_storage_at(address, index)
                    .block_id(block_id)
                    .await
            })
            .map_err(|e| Web3DbError(format!("storage {address}[{index}]: {e}")))?;
        Ok(val)
    }

    fn block_hash_ref(&self, number: u64) -> Result<B256, Self::Error> {
        let provider = self.provider.clone();
        let block = self
            .handle
            .block_on(async move { provider.get_block_by_number(number.into()).await })
            .map_err(|e| Web3DbError(format!("block {number}: {e}")))?;
        match block {
            Some(b) => Ok(b.header.hash),
            None => Err(Web3DbError(format!("block {number} not found"))),
        }
    }
}

// Type alias for the concrete EVM the preflight builds. We don't surface this
// to callers because the inner DB type is generic.
type PreflightEvm<DB> = revm::handler::MainnetEvm<
    revm::Context<
        revm::context::BlockEnv,
        revm::context::TxEnv,
        revm::context::CfgEnv,
        DB,
        revm::Journal<DB>,
        (),
    >,
>;

#[cfg(test)]
mod tests {
    use super::*;
    use crate::Eip7702Delegation;
    use alloy::primitives::address;
    use revm::database::EmptyDB;
    use revm::primitives::U256 as RU256;

    /// Minimal EVM stub bytecode — RETURN abi.encode(uint256(0)) for any
    /// call. 11 bytes. Sufficient for `balanceOf` reads in the offline tests.
    const STUB_RETURN_ZERO: &[u8] = &[
        0x60, 0x00, // PUSH1 0x00
        0x60, 0x00, // PUSH1 0x00
        0x52, // MSTORE
        0x60, 0x20, // PUSH1 0x20
        0x60, 0x00, // PUSH1 0x00
        0xf3, // RETURN
    ];

    /// Build an EVM whose CacheDB sits over an EmptyDB and pre-loads a
    /// stub ERC-20 + a funded EOA. Used by the unit tests below — does not
    /// touch the network.
    fn build_offline_evm(
        caller: Address,
        token: Address,
        token_code: &[u8],
    ) -> PreflightEvm<CacheDB<EmptyDB>> {
        let mut cache_db = CacheDB::new(EmptyDB::new());

        let caller_info = AccountInfo::new(
            RU256::from(10_u128.pow(20)),
            0,
            KECCAK_EMPTY,
            Bytecode::new(),
        );
        cache_db.insert_account_info(caller, caller_info);

        let bytecode = Bytecode::new_raw(token_code.to_vec().into());
        let code_hash = bytecode.hash_slow();
        let token_info = AccountInfo::new(RU256::ZERO, 1, code_hash, bytecode);
        cache_db.insert_account_info(token, token_info);

        Context::mainnet()
            .modify_cfg_chained(|cfg| {
                cfg.disable_nonce_check = true;
            })
            .with_db(cache_db)
            .build_mainnet()
    }

    fn dummy_plan(target: Address, profit_token: Address) -> Plan {
        use crate::{GasEnvelope, Lane, PlanKind};
        use alloy::primitives::b256;
        Plan {
            trace_id: "preflight-test-01".to_string(),
            opportunity_id: "preflight-test-01".to_string(),
            admission_hash: Some(b256!(
                "ad00000000000000000000000000000000000000000000000000000000000001"
            )),
            kind: PlanKind::Liquidation,
            target,
            calldata: Bytes::new(),
            value: U256::ZERO,
            gas_limit: 100_000,
            gas_envelope: GasEnvelope {
                max_fee_per_gas_wei: U256::from(1_000_000_000_u64),
                max_priority_fee_per_gas_wei: U256::from(0_u64),
            },
            deadline_ms: u64::MAX,
            require_preflight: true,
            expected_balance_delta_floor: I256::ZERO,
            profit_token,
            submission_lane: Lane::Default,
            timeboost_bid_wei: None,
            dry_run: false,
            eip7702: None,
        }
    }

    #[test]
    fn read_erc20_balance_returns_zero_from_stub_token() {
        let caller = address!("00000000000000000000000000000000000000a1");
        let token = address!("000000000000000000000000000000000000beef");
        let mut evm = build_offline_evm(caller, token, STUB_RETURN_ZERO);

        let bal = read_erc20_balance(&mut evm, token, caller).expect("balanceOf returns");
        assert_eq!(bal, U256::ZERO);
    }

    #[test]
    fn execute_plan_tx_succeeds_on_no_op_target() {
        // Target is a stub that always returns 32 zero bytes — no revert.
        let caller = address!("00000000000000000000000000000000000000a2");
        let target = address!("000000000000000000000000000000000000c0de");
        let mut evm = build_offline_evm(caller, target, STUB_RETURN_ZERO);

        let plan = dummy_plan(target, address!("000000000000000000000000000000000000beef"));
        execute_plan_tx(&mut evm, &plan, caller).expect("plan tx is no-op success");
    }

    #[test]
    fn native_balance_delta_reflects_value_sent_by_plan() {
        let caller = address!("00000000000000000000000000000000000000a3");
        let target = address!("000000000000000000000000000000000000c0de");
        let mut evm = build_offline_evm(caller, target, STUB_RETURN_ZERO);
        let mut plan = dummy_plan(target, NATIVE_TOKEN);
        plan.value = U256::from(7_u64);

        let pre = read_native_balance(&mut evm, caller).expect("pre native balance");
        execute_plan_tx(&mut evm, &plan, caller).expect("plan sends native value");
        let post = read_native_balance(&mut evm, caller).expect("post native balance");

        assert_eq!(
            u256_diff_to_i256(post, pre),
            I256::try_from(-7_i64).unwrap()
        );
    }

    #[test]
    fn eip7702_overlay_materializes_delegate_code_at_authority() {
        let authority = address!("0000000000000000000000000000000000007702");
        let delegate = address!("000000000000000000000000000000000000b0b0");
        let mut cache_db = CacheDB::new(EmptyDB::new());

        cache_db.insert_account_info(
            authority,
            AccountInfo::new(
                RU256::from(10_u128.pow(20)),
                0,
                KECCAK_EMPTY,
                Bytecode::new(),
            ),
        );
        let delegate_code = Bytecode::new_raw(STUB_RETURN_ZERO.to_vec().into());
        let delegate_code_hash = delegate_code.hash_slow();
        cache_db.insert_account_info(
            delegate,
            AccountInfo::new(RU256::ZERO, 1, delegate_code_hash, delegate_code),
        );

        let mut plan = dummy_plan(
            authority,
            address!("000000000000000000000000000000000000beef"),
        );
        plan.eip7702 = Some(Eip7702Delegation {
            authority,
            delegate_address: delegate,
        });

        apply_eip7702_delegation_overlay(&mut cache_db, &plan, authority).expect("overlay applies");
        let authority_info = cache_db
            .basic(authority)
            .expect("cache basic succeeds")
            .expect("authority exists");
        assert!(
            authority_info
                .code
                .as_ref()
                .is_some_and(Bytecode::is_eip7702),
            "authority must carry an EIP-7702 designator for REVM"
        );

        let mut evm = Context::mainnet()
            .modify_cfg_chained(|cfg| {
                cfg.disable_nonce_check = true;
            })
            .with_db(cache_db)
            .build_mainnet();
        execute_plan_tx(&mut evm, &plan, authority).expect("delegated plan executes");
    }

    #[test]
    fn execute_plan_tx_propagates_revert_reason_string() {
        // Target bytecode: REVERT(0, len) with `Error("nope")` payload.
        // Layout:
        //   selector 0x08c379a0 padded to 32-byte word, offset=0x20,
        //   length=4, "nope" right-padded to 32. Total 4+32+32+32 = 100,
        //   so we lay out the data right after a tiny CODECOPY+REVERT
        //   loader and reference it by offset.
        // Solidity's `revert("nope")` packs to:
        //   selector 0x08c379a0       (4 bytes, NO leading padding)
        //   string offset 0x20        (32 bytes)
        //   string length 4           (32 bytes)
        //   string data "nope"+pad    (32 bytes)
        // Total: 100 bytes.
        let revert_bytecode: Vec<u8> = {
            let mut data = Vec::with_capacity(100);
            data.extend_from_slice(&[0x08, 0xc3, 0x79, 0xa0]);
            data.extend_from_slice(&{
                let mut buf = [0u8; 32];
                buf[31] = 0x20;
                buf
            });
            data.extend_from_slice(&{
                let mut buf = [0u8; 32];
                buf[31] = 0x04;
                buf
            });
            let mut s = Vec::with_capacity(32);
            s.extend_from_slice(b"nope");
            s.extend(std::iter::repeat_n(0u8, 28));
            data.extend_from_slice(&s);
            assert_eq!(data.len(), 100);

            let len = data.len() as u8;
            let loader_len = 12;
            let offset = loader_len as u8;
            let code: Vec<u8> = vec![
                0x60, len, // PUSH1 len
                0x60, offset, // PUSH1 offset (data starts immediately after loader)
                0x60, 0x00, // PUSH1 0
                0x39, // CODECOPY
                0x60, len, // PUSH1 len
                0x60, 0x00, // PUSH1 0
                0xfd, // REVERT
            ];
            assert_eq!(code.len(), loader_len);
            let mut full = code;
            full.extend_from_slice(&data);
            full
        };

        let caller = address!("00000000000000000000000000000000000000a3");
        let target = address!("00000000000000000000000000000000ba1ba1ba");
        let mut evm = build_offline_evm(caller, target, &revert_bytecode);

        let plan = dummy_plan(target, address!("000000000000000000000000000000000000beef"));
        let err = execute_plan_tx(&mut evm, &plan, caller).expect_err("plan reverts");
        let msg = err.to_string();
        assert!(
            msg.contains("nope"),
            "revert reason should propagate, got: {msg}"
        );
    }

    #[test]
    fn u256_diff_to_i256_handles_positive_and_negative() {
        assert_eq!(
            u256_diff_to_i256(U256::from(100u64), U256::from(40u64)),
            I256::try_from(60).unwrap()
        );
        assert_eq!(
            u256_diff_to_i256(U256::from(40u64), U256::from(100u64)),
            I256::try_from(-60).unwrap()
        );
        assert_eq!(u256_diff_to_i256(U256::ZERO, U256::ZERO), I256::ZERO);
    }

    /// Integration test: spawn anvil, drive the full
    /// [`LiveBackend::preflight`] pipeline against a Plan that points at a
    /// stub `balanceOf` contract installed via `anvil_setCode`. Validates:
    ///
    ///   * `Web3Db::basic_ref` fetches code from a live RPC
    ///   * `Web3Db::storage_ref` would resolve cold storage if the EVM
    ///     accessed any (the stub doesn't, but the path is exercised by
    ///     CacheDB's miss handling)
    ///   * `read_erc20_balance` round-trips through the live transport
    ///   * `execute_plan_tx` commits against the CacheDB
    ///
    /// `#[ignore]` because it spawns the `anvil` binary; run with
    /// `cargo test --package mev-engine -- --ignored anvil_revm_preflight`.
    #[tokio::test]
    #[ignore]
    async fn anvil_revm_preflight_balanceof_stub_returns_zero_delta() {
        use crate::executor::{lane, signer, ExecutorBackend, LiveBackend};
        use crate::{GasEnvelope, Lane, PlanKind};
        use alloy::network::AnyNetwork;
        use alloy::node_bindings::Anvil;
        use alloy::primitives::Bytes;
        use alloy::providers::ext::AnvilApi;
        use alloy::providers::ProviderBuilder;

        const KEY: &str = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80";
        let stub_token = address!("000000000000000000000000000000000000beef");

        let anvil = Anvil::new().chain_id(31337_u64).spawn();

        // Install the stub balanceOf bytecode at `stub_token` via anvil's
        // setCode cheat. Use a separate provider for the cheat call so we
        // don't disturb the LiveBackend's wallet stack.
        let cheat_provider = ProviderBuilder::new()
            .network::<AnyNetwork>()
            .connect(&anvil.endpoint())
            .await
            .expect("anvil provider connects");
        cheat_provider
            .anvil_set_code(stub_token, Bytes::from_static(STUB_RETURN_ZERO))
            .await
            .expect("anvil_setCode succeeds");

        // Build the LiveBackend pointing at anvil with a pre-funded signer.
        let lane_endpoints = lane::LaneEndpoints {
            default_http: anvil.endpoint(),
            ..Default::default()
        };
        let signer = signer::ExecutorSigner::from_hex(KEY).expect("anvil key parses");
        let signer_addr = signer.address();
        let backend = LiveBackend::with_signer(signer, lane_endpoints)
            .await
            .expect("backend constructs");

        let plan = Plan {
            trace_id: "anvil-revm-pf-01".to_string(),
            opportunity_id: "anvil-revm-pf-01".to_string(),
            admission_hash: Some(alloy::primitives::b256!(
                "ad00000000000000000000000000000000000000000000000000000000000002"
            )),
            kind: PlanKind::Liquidation,
            target: stub_token,
            // Empty calldata — the stub bytecode ignores selector and
            // returns 32 zero bytes. The plan tx commits cleanly.
            calldata: Bytes::new(),
            value: U256::ZERO,
            gas_limit: 100_000,
            gas_envelope: GasEnvelope {
                max_fee_per_gas_wei: U256::from(10_000_000_000_u64),
                max_priority_fee_per_gas_wei: U256::from(0_u64),
            },
            deadline_ms: u64::MAX,
            require_preflight: true,
            expected_balance_delta_floor: I256::ZERO,
            profit_token: stub_token,
            submission_lane: Lane::Default,
            timeboost_bid_wei: None,
            dry_run: false,
            eip7702: None,
        };

        let delta = backend.preflight(&plan).await.expect("preflight succeeds");
        assert_eq!(
            delta,
            I256::ZERO,
            "stub balanceOf returns 0 pre and post, so delta is 0"
        );

        // Sanity: Web3Db basic_ref against the signer reports a non-zero
        // balance (anvil pre-funds 10000 ETH). Build the DB directly and
        // call into it from a spawn_blocking task to mirror the real path.
        let provider = backend.provider().clone();
        let basic = tokio::task::spawn_blocking(move || {
            let db = Web3Db::new(provider, BlockId::latest()).expect("handle present");
            db.basic_ref(signer_addr)
        })
        .await
        .unwrap()
        .expect("basic_ref ok");
        let info = basic.expect("account exists on anvil");
        assert!(
            info.balance > U256::ZERO,
            "anvil pre-funds the test signer; got {:?}",
            info.balance
        );

        drop(anvil);
    }
}
