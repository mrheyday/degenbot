//! Uniswap V4 simulation — singleton `PoolManager` + hooks.
//!
//! V4 differs from V3 by routing all swaps through a singleton
//! `PoolManager` keyed by `PoolKey` and by allowing user-supplied hook
//! contracts to mutate state at well-defined callback points
//! (`beforeSwap` / `afterSwap` / `beforeAddLiquidity` / etc).
//!
//! For static cycles where the hook is empty (or cannot run at a
//! swap-affecting callback), reusing the V3 sqrt-price math is correct. For
//! cycles whose hook can intercept the swap, we MUST step into REVM to
//! faithfully execute the hook code — those cycles do not survive the
//! warm-cache fast path.

use alloy::primitives::{Address, B256, U256};
use eyre::{eyre, Result};

use super::v3::{self, V3Snapshot};

/// V4-specific pool descriptor keyed by `PoolKey` hash.
#[derive(Debug, Clone)]
pub struct V4Snapshot {
    pub key: B256,
    pub hooks: Address,
    /// V4 reduces to V3-style sqrt-price math iff the hook cannot intercept
    /// the swap (see [`requires_revm_step`]).
    pub inner: V3Snapshot,
}

// V4 hook-permission flags (`v4-core` `Hooks.sol`) are encoded in the low
// 14 bits of the hook address. These four let a hook intercept or rewrite
// swap execution; if any is set the V3 closed form is unfaithful.
const HOOK_BEFORE_SWAP: u16 = 1 << 7;
const HOOK_AFTER_SWAP: u16 = 1 << 6;
const HOOK_BEFORE_SWAP_RETURNS_DELTA: u16 = 1 << 3;
const HOOK_AFTER_SWAP_RETURNS_DELTA: u16 = 1 << 2;
const SWAP_AFFECTING_HOOK_MASK: u16 = HOOK_BEFORE_SWAP
    | HOOK_AFTER_SWAP
    | HOOK_BEFORE_SWAP_RETURNS_DELTA
    | HOOK_AFTER_SWAP_RETURNS_DELTA;

/// Does this pool's `hooks` address mutate swap state in a way that breaks
/// the V3 math approximation?
///
/// The zero address is a no-op hook. Otherwise the hook's callback
/// permissions are read directly from the low bits of its address (the V4
/// hook-address mining invariant): if it can run at `beforeSwap` /
/// `afterSwap` or return a swap delta, the fast path is unsafe.
pub fn requires_revm_step(pool: &V4Snapshot) -> bool {
    if pool.hooks.is_zero() {
        return false;
    }
    let bytes = pool.hooks.as_slice();
    let low_bits = u16::from_be_bytes([bytes[18], bytes[19]]);
    low_bits & SWAP_AFFECTING_HOOK_MASK != 0
}

/// Compute amount_out for a V4 pool. Delegates to the V3 sqrt-price math
/// when the hook is swap-transparent; otherwise errors so the caller routes
/// the cycle through REVM.
pub fn amount_out(pool: &V4Snapshot, amount_in: U256, zero_for_one: bool) -> Result<U256> {
    if requires_revm_step(pool) {
        return Err(eyre!(
            "v4::amount_out: pool hooks can intercept the swap; route through REVM"
        ));
    }
    v3::amount_out(&pool.inner, amount_in, zero_for_one)
}

#[cfg(test)]
mod tests {
    use std::collections::HashMap;

    use super::*;

    fn deep_v3_pool() -> V3Snapshot {
        V3Snapshot {
            sqrt_price_x96: U256::from(1u64) << 96,
            liquidity: 1_000_000_000_000_000_000u128,
            tick: 0,
            fee_bps: 30,
            tick_spacing: 60,
            tick_bitmap: HashMap::new(),
            tick_net_liquidity: HashMap::new(),
        }
    }

    fn snapshot_with_hook(hook_low_bits: u16) -> V4Snapshot {
        let mut bytes = [0u8; 20];
        let [hi, lo] = hook_low_bits.to_be_bytes();
        bytes[18] = hi;
        bytes[19] = lo;
        V4Snapshot {
            key: B256::ZERO,
            hooks: Address::from(bytes),
            inner: deep_v3_pool(),
        }
    }

    #[test]
    fn zero_hook_is_transparent() {
        let pool = V4Snapshot {
            key: B256::ZERO,
            hooks: Address::ZERO,
            inner: deep_v3_pool(),
        };
        assert!(!requires_revm_step(&pool));
    }

    #[test]
    fn non_swap_hook_is_transparent() {
        // 1 << 11 = beforeAddLiquidity — does not touch swap execution.
        let pool = snapshot_with_hook(1 << 11);
        assert!(!requires_revm_step(&pool));
    }

    #[test]
    fn before_swap_hook_requires_revm() {
        let pool = snapshot_with_hook(HOOK_BEFORE_SWAP);
        assert!(requires_revm_step(&pool));
    }

    #[test]
    fn after_swap_returns_delta_hook_requires_revm() {
        let pool = snapshot_with_hook(HOOK_AFTER_SWAP_RETURNS_DELTA);
        assert!(requires_revm_step(&pool));
    }

    #[test]
    fn transparent_pool_delegates_to_v3_math() {
        let pool = V4Snapshot {
            key: B256::ZERO,
            hooks: Address::ZERO,
            inner: deep_v3_pool(),
        };
        let amount_in = U256::from(1_000_000_000_000_000u64);
        let v4_out = amount_out(&pool, amount_in, true).unwrap();
        let v3_out = v3::amount_out(&pool.inner, amount_in, true).unwrap();
        assert_eq!(v4_out, v3_out);
        assert!(v4_out > U256::ZERO);
    }

    #[test]
    fn opaque_pool_errors_instead_of_quoting() {
        let pool = snapshot_with_hook(HOOK_BEFORE_SWAP);
        let res = amount_out(&pool, U256::from(1_000_000_000_000_000u64), true);
        assert!(res.is_err());
    }
}
