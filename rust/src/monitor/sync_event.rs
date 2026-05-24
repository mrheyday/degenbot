//! Per-DEX log decoder.
//!
//! Translates raw `alloy_rpc_types::eth::Log` items into `PoolState` deltas
//! that the simulation layer can apply to its REVM `CacheDB` and that the
//! IPC layer can forward to the coordinator as `Message::PoolUpdate`.
//!
//! Decodes the events that carry the post-trade pool state directly:
//! UniV2 `Sync`, UniV3 `Swap`, UniV4 `Swap` (singleton PoolManager). Curve
//! `TokenExchange` carries trade amounts, not balances, so it cannot be
//! turned into a `Reserves::Curve` from the log alone — those logs return
//! `Ok(None)` and the balances are refreshed by a separate read.
//!
//! Latency target (per `09-LATENCY-BUDGET.md` §2.1): ABI decode p99 ≤ 3 ms.

use alloy::primitives::aliases::{U112, U160};
use alloy::primitives::{B256, U256};
use alloy::rpc::types::eth::Log;
use alloy::sol_types::SolEvent;
use eyre::Result;

use crate::monitor::{PoolState, Reserves};

// The V4 `Swap` event carries 8 fields; the sol!-generated constructor
// trips `too_many_arguments` on generated code we don't control, so the
// macro is wrapped in a module that scopes the allow to it.
#[allow(clippy::too_many_arguments)]
mod events {
    use alloy::sol;

    sol! {
        interface IUniV2 {
            event Sync(uint112 reserve0, uint112 reserve1);
        }
        interface IUniV3 {
            event Swap(
                address indexed sender,
                address indexed recipient,
                int256 amount0,
                int256 amount1,
                uint160 sqrtPriceX96,
                uint128 liquidity,
                int24 tick
            );
        }
        interface IUniV4 {
            event Swap(
                bytes32 indexed id,
                address indexed sender,
                int128 amount0,
                int128 amount1,
                uint160 sqrtPriceX96,
                uint128 liquidity,
                int24 tick,
                uint24 fee
            );
        }
    }
}

use events::{IUniV2, IUniV3, IUniV4};

/// Topic0 signature hashes of the pool-state events `decode_log` handles.
/// Exposed so `monitor::ws` can narrow the WS subscription server-side to
/// only state-bearing logs instead of streaming every log from the pools.
pub const WATCHED_EVENT_SIGNATURES: [B256; 3] = [
    IUniV2::Sync::SIGNATURE_HASH,
    IUniV3::Swap::SIGNATURE_HASH,
    IUniV4::Swap::SIGNATURE_HASH,
];

/// Result of decoding one log against the registered pool table. `None`
/// indicates the log was for a pool we don't track (filtered cheaply
/// upstream by `monitor::ws::LogFilter`, but defensively re-checked here).
#[derive(Debug, Clone)]
pub enum DecodedEvent {
    /// New pool state — replaces the cached entry for `pool`.
    State(PoolState),
    /// Log was recognized but not state-bearing (e.g., a non-Sync emit on a
    /// V2 pair). The block number is still useful for tip tracking.
    Tip { block_number: u64 },
}

/// Decode a single log. Dispatches by topic0 against the per-DEX event
/// signature hashes; unrecognized logs return `Ok(None)`.
pub fn decode_log(log: &Log) -> Result<Option<DecodedEvent>> {
    let topics = log.topics();
    let Some(topic0) = topics.first().copied() else {
        return Ok(None);
    };
    let pool = log.inner.address;
    let block_number = log.block_number.unwrap_or_default();
    let data: &[u8] = &log.inner.data.data;

    if topic0 == IUniV2::Sync::SIGNATURE_HASH {
        let ev = IUniV2::Sync::decode_raw_log(topics, data)?;
        return Ok(Some(DecodedEvent::State(PoolState {
            address: pool,
            block_number,
            reserves: Reserves::V2 {
                reserve0: u112_to_u256(&ev.reserve0),
                reserve1: u112_to_u256(&ev.reserve1),
            },
        })));
    }

    if topic0 == IUniV3::Swap::SIGNATURE_HASH {
        let ev = IUniV3::Swap::decode_raw_log(topics, data)?;
        return Ok(Some(DecodedEvent::State(PoolState {
            address: pool,
            block_number,
            reserves: Reserves::V3 {
                sqrt_price_x96: u160_to_u256(&ev.sqrtPriceX96),
                liquidity: ev.liquidity,
                tick: i32::try_from(ev.tick).unwrap_or_default(),
            },
        })));
    }

    if topic0 == IUniV4::Swap::SIGNATURE_HASH {
        let ev = IUniV4::Swap::decode_raw_log(topics, data)?;
        return Ok(Some(DecodedEvent::State(PoolState {
            address: pool,
            block_number,
            reserves: Reserves::V4 {
                key: ev.id,
                sqrt_price_x96: u160_to_u256(&ev.sqrtPriceX96),
                liquidity: ev.liquidity,
                tick: i32::try_from(ev.tick).unwrap_or_default(),
            },
        })));
    }

    Ok(None)
}

fn u112_to_u256(x: &U112) -> U256 {
    let l = x.as_limbs();
    U256::from_limbs([l[0], l[1], 0, 0])
}

fn u160_to_u256(x: &U160) -> U256 {
    let l = x.as_limbs();
    U256::from_limbs([l[0], l[1], l[2], 0])
}

#[cfg(test)]
mod tests {
    use alloy::primitives::{address, Address, Bytes, LogData, B256};

    use super::*;

    /// Build an `alloy::rpc::types::eth::Log` from raw topics + data.
    fn raw_log(address: Address, topics: Vec<B256>, data: Vec<u8>) -> Log {
        let inner = alloy::primitives::Log {
            address,
            data: LogData::new_unchecked(topics, Bytes::from(data)),
        };
        Log {
            inner,
            block_number: Some(123),
            ..Default::default()
        }
    }

    #[test]
    fn unrecognized_topic_decodes_to_none() {
        let log = raw_log(Address::ZERO, vec![B256::ZERO], vec![]);
        assert!(decode_log(&log).unwrap().is_none());
    }

    #[test]
    fn empty_topics_decode_to_none() {
        let log = raw_log(Address::ZERO, vec![], vec![]);
        assert!(decode_log(&log).unwrap().is_none());
    }

    #[test]
    fn decodes_a_univ2_sync_event() {
        // Sync(uint112,uint112): both reserves non-indexed, two 32-byte words.
        let pool = address!("00000000000000000000000000000000000000a1");
        let mut data = vec![0u8; 64];
        data[31] = 0x64; // reserve0 = 100
        data[63] = 0xc8; // reserve1 = 200
        let log = raw_log(pool, vec![IUniV2::Sync::SIGNATURE_HASH], data);

        let decoded = decode_log(&log).unwrap().expect("recognized");
        match decoded {
            DecodedEvent::State(state) => {
                assert_eq!(state.address, pool);
                assert_eq!(state.block_number, 123);
                match state.reserves {
                    Reserves::V2 { reserve0, reserve1 } => {
                        assert_eq!(reserve0, U256::from(100u64));
                        assert_eq!(reserve1, U256::from(200u64));
                    }
                    other => panic!("expected V2 reserves, got {other:?}"),
                }
            }
            other => panic!("expected State, got {other:?}"),
        }
    }
}
