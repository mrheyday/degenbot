//! Uniswap V3 tick-aware sqrt-price math.
//!
//! Concentrated-liquidity amount-out: integrates active liquidity across
//! tick boundaries until either the input is exhausted or a price-limit
//! tick is hit. Reference: <https://uniswap.org/whitepaper-v3.pdf> §6.
//!
//! The per-step arithmetic (`computeSwapStep`, `SqrtPriceMath`, `TickMath`,
//! `TickBitmap`) is delegated to the vendored [`super::uniswap_v3_math`]
//! primitives. This file contains only the swap loop — the control flow of
//! the on-chain `UniswapV3Pool.swap`.

use std::collections::HashMap;

use alloy::primitives::{I256, U256};
use eyre::{eyre, Result};
use serde::{Deserialize, Serialize};

use super::uniswap_v3_math::liquidity_math::add_delta;
use super::uniswap_v3_math::swap_math::compute_swap_step;
use super::uniswap_v3_math::tick_bitmap::next_initialized_tick_within_one_word;
use super::uniswap_v3_math::tick_math::{
    get_sqrt_ratio_at_tick, get_tick_at_sqrt_ratio, MAX_SQRT_RATIO, MAX_TICK, MIN_SQRT_RATIO,
    MIN_TICK,
};
use super::uniswap_v3_math::tick_provider::TickProvider;

/// Compact V3 pool state needed for simulation. Mirrors the relevant
/// `Reserves::V3` fields plus the active-tick liquidity ladder.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct V3Snapshot {
    pub sqrt_price_x96: U256,
    pub liquidity: u128,
    pub tick: i32,
    /// LP fee in basis points (`30` = 0.30 %). Converted to the 1e6-scaled
    /// `fee_pips` the V3 core math expects.
    pub fee_bps: u32,
    /// Pool `tickSpacing` (1 / 10 / 60 / 200 for the canonical fee tiers).
    pub tick_spacing: i32,
    /// On-chain `tickBitmap` mapping: word position -> 256-bit word. Walked
    /// by `next_initialized_tick_within_one_word` to find the next boundary.
    /// May be sparse — only words spanned by the simulated swap are needed.
    pub tick_bitmap: HashMap<i16, U256>,
    /// `liquidityNet` per initialized tick, applied when the swap loop
    /// crosses a tick boundary.
    pub tick_net_liquidity: HashMap<i32, i128>,
}

impl TickProvider for V3Snapshot {
    fn get_tick(&self, word_pos: i16) -> eyre::Result<U256> {
        Ok(self
            .tick_bitmap
            .get(&word_pos)
            .copied()
            .unwrap_or(U256::ZERO))
    }
}

/// Compute amount_out and final state for `amount_in` in direction `zero_for_one`.
pub fn amount_out_with_state(
    pool: &V3Snapshot,
    amount_in: U256,
    zero_for_one: bool,
) -> Result<(U256, V3Snapshot)> {
    if amount_in.is_zero() {
        return Ok((U256::ZERO, pool.clone()));
    }
    if pool.fee_bps >= 10_000 {
        return Err(eyre!("v3::amount_out: fee_bps must be < 10000"));
    }
    if pool.tick_spacing <= 0 {
        return Err(eyre!("v3::amount_out: tick_spacing must be positive"));
    }
    let fee_pips = pool
        .fee_bps
        .checked_mul(100)
        .ok_or_else(|| eyre!("v3::amount_out: fee_bps overflow"))?;

    let sqrt_price_limit = if zero_for_one {
        MIN_SQRT_RATIO + U256::from(1u64)
    } else {
        MAX_SQRT_RATIO - U256::from(1u64)
    };

    let amount_specified = I256::try_from(amount_in)
        .map_err(|_| eyre!("v3::amount_out: amount_in exceeds I256 range"))?;

    let mut sqrt_price = pool.sqrt_price_x96;
    let mut tick = pool.tick;
    let mut liquidity = pool.liquidity;
    let mut amount_remaining = amount_specified;
    let mut amount_calculated = I256::ZERO;

    while !amount_remaining.is_zero() && sqrt_price != sqrt_price_limit {
        let sqrt_price_start = sqrt_price;

        let (tick_next_unclamped, initialized) =
            next_initialized_tick_within_one_word(pool, tick, pool.tick_spacing, zero_for_one)?;
        let tick_next = tick_next_unclamped.clamp(MIN_TICK, MAX_TICK);
        let sqrt_price_next = get_sqrt_ratio_at_tick(tick_next)?;

        let sqrt_price_target = if zero_for_one {
            sqrt_price_next.max(sqrt_price_limit)
        } else {
            sqrt_price_next.min(sqrt_price_limit)
        };

        let (next_price, step_amount_in, step_amount_out, step_fee) = compute_swap_step(
            sqrt_price,
            sqrt_price_target,
            liquidity,
            amount_remaining,
            fee_pips,
        )?;
        sqrt_price = next_price;

        let consumed = step_amount_in
            .checked_add(step_fee)
            .ok_or_else(|| eyre!("v3::amount_out: step input overflow"))?;
        amount_remaining = amount_remaining
            .checked_sub(
                I256::try_from(consumed)
                    .map_err(|_| eyre!("v3::amount_out: step input exceeds I256"))?,
            )
            .ok_or_else(|| eyre!("v3::amount_out: amount_remaining underflow"))?;
        amount_calculated = amount_calculated
            .checked_sub(
                I256::try_from(step_amount_out)
                    .map_err(|_| eyre!("v3::amount_out: step output exceeds I256"))?,
            )
            .ok_or_else(|| eyre!("v3::amount_out: amount_calculated underflow"))?;

        if sqrt_price == sqrt_price_next {
            if initialized {
                let mut liquidity_net = pool
                    .tick_net_liquidity
                    .get(&tick_next)
                    .copied()
                    .unwrap_or(0);
                if zero_for_one {
                    liquidity_net = -liquidity_net;
                }
                liquidity = add_delta(liquidity, liquidity_net)?;
            }
            tick = if zero_for_one {
                tick_next - 1
            } else {
                tick_next
            };
        } else if sqrt_price != sqrt_price_start {
            tick = get_tick_at_sqrt_ratio(sqrt_price)?;
        }
    }

    let mut next_pool = pool.clone();
    next_pool.sqrt_price_x96 = sqrt_price;
    next_pool.tick = tick;
    next_pool.liquidity = liquidity;

    Ok(((-amount_calculated).into_raw(), next_pool))
}

/// Compute amount_out for `amount_in` in direction `zero_for_one`.
///
/// `zero_for_one == true` swaps token0 -> token1 (price decreasing);
/// `false` swaps token1 -> token0 (price increasing). Exact-input only.
pub fn amount_out(pool: &V3Snapshot, amount_in: U256, zero_for_one: bool) -> Result<U256> {
    if amount_in.is_zero() {
        return Err(eyre!("v3::amount_out: amount_in is zero"));
    }
    if pool.fee_bps >= 10_000 {
        return Err(eyre!("v3::amount_out: fee_bps must be < 10000"));
    }
    if pool.tick_spacing <= 0 {
        return Err(eyre!("v3::amount_out: tick_spacing must be positive"));
    }
    let fee_pips = pool
        .fee_bps
        .checked_mul(100)
        .ok_or_else(|| eyre!("v3::amount_out: fee_bps overflow"))?;

    // Unbounded swap: clamp the price to one tick inside the V3 range so the
    // loop always terminates even if the snapshot's tick ladder is sparse.
    let sqrt_price_limit = if zero_for_one {
        MIN_SQRT_RATIO + U256::from(1u64)
    } else {
        MAX_SQRT_RATIO - U256::from(1u64)
    };

    let amount_specified = I256::try_from(amount_in)
        .map_err(|_| eyre!("v3::amount_out: amount_in exceeds I256 range"))?;

    let mut sqrt_price = pool.sqrt_price_x96;
    let mut tick = pool.tick;
    let mut liquidity = pool.liquidity;
    let mut amount_remaining = amount_specified;
    let mut amount_calculated = I256::ZERO;

    while !amount_remaining.is_zero() && sqrt_price != sqrt_price_limit {
        let sqrt_price_start = sqrt_price;

        let (tick_next_unclamped, initialized) =
            next_initialized_tick_within_one_word(pool, tick, pool.tick_spacing, zero_for_one)?;
        let tick_next = tick_next_unclamped.clamp(MIN_TICK, MAX_TICK);
        let sqrt_price_next = get_sqrt_ratio_at_tick(tick_next)?;

        // The compute-swap-step target never crosses the price limit.
        let sqrt_price_target = if zero_for_one {
            sqrt_price_next.max(sqrt_price_limit)
        } else {
            sqrt_price_next.min(sqrt_price_limit)
        };

        let (next_price, step_amount_in, step_amount_out, step_fee) = compute_swap_step(
            sqrt_price,
            sqrt_price_target,
            liquidity,
            amount_remaining,
            fee_pips,
        )?;
        sqrt_price = next_price;

        let consumed = step_amount_in
            .checked_add(step_fee)
            .ok_or_else(|| eyre!("v3::amount_out: step input overflow"))?;
        amount_remaining = amount_remaining
            .checked_sub(
                I256::try_from(consumed)
                    .map_err(|_| eyre!("v3::amount_out: step input exceeds I256"))?,
            )
            .ok_or_else(|| eyre!("v3::amount_out: amount_remaining underflow"))?;
        amount_calculated = amount_calculated
            .checked_sub(
                I256::try_from(step_amount_out)
                    .map_err(|_| eyre!("v3::amount_out: step output exceeds I256"))?,
            )
            .ok_or_else(|| eyre!("v3::amount_out: amount_calculated underflow"))?;

        if sqrt_price == sqrt_price_next {
            // Crossed a tick boundary: apply liquidityNet if initialized.
            if initialized {
                let mut liquidity_net = pool
                    .tick_net_liquidity
                    .get(&tick_next)
                    .copied()
                    .unwrap_or(0);
                if zero_for_one {
                    liquidity_net = -liquidity_net;
                }
                liquidity = add_delta(liquidity, liquidity_net)?;
            }
            tick = if zero_for_one {
                tick_next - 1
            } else {
                tick_next
            };
        } else if sqrt_price != sqrt_price_start {
            tick = get_tick_at_sqrt_ratio(sqrt_price)?;
        }
    }

    // For an exact-input swap `amount_calculated` accrues the (negative)
    // output-token delta; the magnitude is the amount out.
    Ok((-amount_calculated).into_raw())
}

#[cfg(test)]
mod tests {
    use super::*;

    /// `sqrtPriceX96` for price 1.0 is exactly `2^96` (tick 0).
    fn price_one_x96() -> U256 {
        U256::from(1u64) << 96
    }

    /// Pool at price 1.0, deep liquidity, no initialized ticks within reach —
    /// a swap small relative to liquidity stays in a single constant-`L` band.
    fn deep_pool() -> V3Snapshot {
        V3Snapshot {
            sqrt_price_x96: price_one_x96(),
            liquidity: 1_000_000_000_000_000_000u128, // 1e18
            tick: 0,
            fee_bps: 30, // 0.30 % tier
            tick_spacing: 60,
            tick_bitmap: HashMap::new(),
            tick_net_liquidity: HashMap::new(),
        }
    }

    #[test]
    fn rejects_zero_input() {
        assert!(amount_out(&deep_pool(), U256::ZERO, true).is_err());
    }

    #[test]
    fn rejects_fee_at_or_above_100_percent() {
        let mut pool = deep_pool();
        pool.fee_bps = 10_000;
        assert!(amount_out(&pool, U256::from(1_000u64), true).is_err());
    }

    #[test]
    fn small_swap_in_single_band_approximates_price_one_minus_fee() {
        // 1e15 in against 1e18 liquidity at price 1.0: output ≈ input·(1-fee)
        // with sub-percent slippage. Holds for both swap directions.
        let pool = deep_pool();
        let amount_in = U256::from(1_000_000_000_000_000u64); // 1e15
        for zero_for_one in [true, false] {
            let out = amount_out(&pool, amount_in, zero_for_one).unwrap();
            // Lower bound: fee (0.30 %) + a generous 0.5 % slippage allowance.
            let lower = U256::from(990_000_000_000_000u64); // 0.99e15
            assert!(out > lower, "out={out} below lower bound ({zero_for_one})");
            // Upper bound: can never exceed the post-fee input at price 1.0.
            assert!(
                out < amount_in,
                "out={out} not below input ({zero_for_one})"
            );
        }
    }

    #[test]
    fn output_is_deterministic() {
        let pool = deep_pool();
        let amount_in = U256::from(500_000_000_000_000u64);
        let a = amount_out(&pool, amount_in, true).unwrap();
        let b = amount_out(&pool, amount_in, true).unwrap();
        assert_eq!(a, b);
    }

    #[test]
    fn higher_fee_yields_less_output() {
        let amount_in = U256::from(1_000_000_000_000_000u64);
        let mut low_fee = deep_pool();
        low_fee.fee_bps = 5; // 0.05 % tier
        let mut high_fee = deep_pool();
        high_fee.fee_bps = 100; // 1.00 % tier
        let out_low = amount_out(&low_fee, amount_in, true).unwrap();
        let out_high = amount_out(&high_fee, amount_in, true).unwrap();
        assert!(out_low > out_high, "expected lower fee to beat higher fee");
    }

    #[test]
    fn swap_crosses_initialized_tick_and_applies_liquidity_net() {
        // Tick 60 carries positive liquidityNet; a one_for_zero swap large
        // enough to reach it must cross without error and still produce a
        // sane (positive, sub-input) output.
        let mut pool = deep_pool();
        pool.liquidity = 100_000_000_000_000u128; // 1e14 — thin enough to move
        let mut bitmap_word = U256::ZERO;
        // tick 60, spacing 60 -> compressed 1 -> word 0, bit 1.
        bitmap_word |= U256::from(1u64) << 1;
        pool.tick_bitmap.insert(0, bitmap_word);
        pool.tick_net_liquidity.insert(60, 50_000_000_000_000i128);

        let amount_in = U256::from(1_000_000_000_000_000u64); // 1e15
        let out = amount_out(&pool, amount_in, false).unwrap();
        assert!(out > U256::ZERO);
        assert!(out < amount_in);
    }
}
