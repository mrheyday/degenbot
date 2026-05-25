//! Curve simulation: stable pools (StableSwap invariant).
//!
//! Stable: `An^n · Σx + D = AD·n^n + D^(n+1)/(n^n · Π x)`. The pool
//! invariant `D` is solved by Newton iteration; the out-token balance `y`
//! is then solved against the post-trade in-token balance — a faithful
//! port of Curve's `StableSwap.vy` `get_D` / `get_y` / `get_dy`.
//!
//! Cryptopools (CryptoSwap invariant — `gamma`, `price_scale`, on-the-fly
//! `A`) are NOT covered: [`CurveSnapshot`] carries only StableSwap state,
//! so cold cryptopool cycles must route through REVM.

use alloy::primitives::U256;
use serde::{Deserialize, Serialize};
use eyre::{eyre, Result};

use crate::utils::u256::mul_div;

#[allow(non_snake_case)]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CurveSnapshot {
    pub balances: Vec<U256>,
    /// Amplification coefficient. Field name follows whitepaper convention.
    pub A: U256,
    pub fee_bps: u32,
    pub is_meta: bool,
}

/// `get_dy` equivalent: out-amount of token `j` for `amount_in` of token `i`.
pub fn amount_out(pool: &CurveSnapshot, i: usize, j: usize, amount_in: U256) -> Result<U256> {
    let n = pool.balances.len();
    if n < 2 {
        return Err(eyre!("curve::amount_out: pool needs >= 2 coins"));
    }
    if i >= n || j >= n {
        return Err(eyre!("curve::amount_out: token index out of range"));
    }
    if i == j {
        return Err(eyre!("curve::amount_out: i and j must differ"));
    }
    if amount_in.is_zero() {
        return Err(eyre!("curve::amount_out: amount_in is zero"));
    }
    if pool.fee_bps >= 10_000 {
        return Err(eyre!("curve::amount_out: fee_bps must be < 10000"));
    }
    if pool.A.is_zero() {
        return Err(eyre!("curve::amount_out: amplification A must be > 0"));
    }
    if pool.balances.iter().any(U256::is_zero) {
        return Err(eyre!("curve::amount_out: pool has an empty balance"));
    }

    let x = pool.balances[i]
        .checked_add(amount_in)
        .ok_or_else(|| eyre!("curve::amount_out: balance + amount_in overflow"))?;
    let y = get_y(i, j, x, &pool.balances, pool.A)?;

    // dy = balances[j] - y - 1; the -1 is Curve's rounding margin.
    let dy = pool.balances[j]
        .checked_sub(y)
        .and_then(|d| d.checked_sub(U256::ONE))
        .ok_or_else(|| eyre!("curve::amount_out: non-positive output"))?;
    let fee = mul_div(dy, U256::from(pool.fee_bps), U256::from(10_000u64))?;
    dy.checked_sub(fee)
        .ok_or_else(|| eyre!("curve::amount_out: fee exceeds output"))
}

/// Solve the StableSwap invariant `D` for the supplied balances by Newton
/// iteration (Curve `StableSwap.vy::get_D`).
fn get_d(xp: &[U256], amp: U256) -> Result<U256> {
    let n = U256::from(xp.len());
    let mut sum = U256::ZERO;
    for &x in xp {
        sum = sum
            .checked_add(x)
            .ok_or_else(|| eyre!("curve::get_d: balance sum overflow"))?;
    }
    if sum.is_zero() {
        return Ok(U256::ZERO);
    }
    let ann = amp
        .checked_mul(n)
        .ok_or_else(|| eyre!("curve::get_d: A*n overflow"))?;

    let mut d = sum;
    for _ in 0..255 {
        // d_p = d * Π(d / (x_k * n))
        let mut d_p = d;
        for &x in xp {
            let denom = x
                .checked_mul(n)
                .ok_or_else(|| eyre!("curve::get_d: x*n overflow"))?;
            d_p = mul_div(d_p, d, denom)?;
        }
        let d_prev = d;
        // d = (ann*sum + d_p*n) * d / ((ann-1)*d + (n+1)*d_p)
        let numerator_lhs = ann
            .checked_mul(sum)
            .ok_or_else(|| eyre!("curve::get_d: ann*sum overflow"))?
            .checked_add(
                d_p.checked_mul(n)
                    .ok_or_else(|| eyre!("curve::get_d: d_p*n overflow"))?,
            )
            .ok_or_else(|| eyre!("curve::get_d: numerator overflow"))?;
        let denominator = ann
            .checked_sub(U256::ONE)
            .ok_or_else(|| eyre!("curve::get_d: ann < 1"))?
            .checked_mul(d)
            .ok_or_else(|| eyre!("curve::get_d: (ann-1)*d overflow"))?
            .checked_add(
                n.checked_add(U256::ONE)
                    .ok_or_else(|| eyre!("curve::get_d: n+1 overflow"))?
                    .checked_mul(d_p)
                    .ok_or_else(|| eyre!("curve::get_d: (n+1)*d_p overflow"))?,
            )
            .ok_or_else(|| eyre!("curve::get_d: denominator overflow"))?;
        d = mul_div(numerator_lhs, d, denominator)?;
        if abs_diff(d, d_prev) <= U256::ONE {
            return Ok(d);
        }
    }
    Err(eyre!("curve::get_d: Newton iteration did not converge"))
}

/// Solve for the new balance of token `j` given a new balance `x` of token
/// `i` (Curve `StableSwap.vy::get_y`).
fn get_y(i: usize, j: usize, x: U256, xp: &[U256], amp: U256) -> Result<U256> {
    let n = U256::from(xp.len());
    let d = get_d(xp, amp)?;
    let ann = amp
        .checked_mul(n)
        .ok_or_else(|| eyre!("curve::get_y: A*n overflow"))?;

    // c = d^(n+1) / (n^n · Π x_k≠j); s = Σ x_k≠j.
    let mut c = d;
    let mut s = U256::ZERO;
    for (k, &xp_k) in xp.iter().enumerate() {
        let x_k = if k == i {
            x
        } else if k != j {
            xp_k
        } else {
            continue;
        };
        s = s
            .checked_add(x_k)
            .ok_or_else(|| eyre!("curve::get_y: balance sum overflow"))?;
        let denom = x_k
            .checked_mul(n)
            .ok_or_else(|| eyre!("curve::get_y: x*n overflow"))?;
        c = mul_div(c, d, denom)?;
    }
    let ann_n = ann
        .checked_mul(n)
        .ok_or_else(|| eyre!("curve::get_y: ann*n overflow"))?;
    c = mul_div(c, d, ann_n)?;
    // ann is non-zero (A > 0, n >= 2), so the division is safe.
    let b = s
        .checked_add(d / ann)
        .ok_or_else(|| eyre!("curve::get_y: b overflow"))?;

    let mut y = d;
    for _ in 0..255 {
        let y_prev = y;
        // y = (y*y + c) / (2*y + b - d)
        let numerator = y
            .checked_mul(y)
            .ok_or_else(|| eyre!("curve::get_y: y*y overflow"))?
            .checked_add(c)
            .ok_or_else(|| eyre!("curve::get_y: numerator overflow"))?;
        let denominator = y
            .checked_mul(U256::from(2u64))
            .ok_or_else(|| eyre!("curve::get_y: 2*y overflow"))?
            .checked_add(b)
            .and_then(|v| v.checked_sub(d))
            .ok_or_else(|| eyre!("curve::get_y: denominator underflow"))?;
        if denominator.is_zero() {
            return Err(eyre!("curve::get_y: zero denominator"));
        }
        y = numerator / denominator;
        if abs_diff(y, y_prev) <= U256::ONE {
            return Ok(y);
        }
    }
    Err(eyre!("curve::get_y: Newton iteration did not converge"))
}

fn abs_diff(a: U256, b: U256) -> U256 {
    if a > b {
        a - b
    } else {
        b - a
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// 3-coin pool, all balances equal — StableSwap marginal price is
    /// exactly 1.0 here, so a small swap returns ~`amount_in·(1-fee)`.
    fn balanced_pool() -> CurveSnapshot {
        let coin = U256::from(1_000_000_000_000_000_000_000_000u128); // 1e24
        CurveSnapshot {
            balances: vec![coin, coin, coin],
            A: U256::from(100u64),
            fee_bps: 4, // 0.04 %
            is_meta: false,
        }
    }

    #[test]
    fn small_swap_in_balanced_pool_approximates_input_minus_fee() {
        let pool = balanced_pool();
        let amount_in = U256::from(1_000_000_000_000_000_000_000u128); // 1e21
        let dy = amount_out(&pool, 0, 1, amount_in).unwrap();
        // Lower bound: fee (0.04 %) + generous slippage allowance.
        assert!(dy > U256::from(990_000_000_000_000_000_000u128), "dy={dy}");
        // Output can never reach the gross input.
        assert!(dy < amount_in, "dy={dy}");
    }

    #[test]
    fn output_is_symmetric_across_coin_pairs() {
        let pool = balanced_pool();
        let amount_in = U256::from(1_000_000_000_000_000_000_000u128);
        let dy_01 = amount_out(&pool, 0, 1, amount_in).unwrap();
        let dy_12 = amount_out(&pool, 1, 2, amount_in).unwrap();
        // A symmetric pool quotes every coin pair identically.
        assert_eq!(dy_01, dy_12);
    }

    #[test]
    fn large_swap_incurs_slippage() {
        let pool = balanced_pool();
        let amount_in = U256::from(500_000_000_000_000_000_000_000u128); // 5e23
        let dy = amount_out(&pool, 0, 1, amount_in).unwrap();
        assert!(dy < amount_in, "dy={dy}");
        // A high-A StableSwap stays close to peg even for a large trade.
        assert!(dy > amount_in / U256::from(2u64), "dy={dy}");
    }

    #[test]
    fn output_is_deterministic() {
        let pool = balanced_pool();
        let amount_in = U256::from(2_000_000_000_000_000_000_000u128);
        let a = amount_out(&pool, 0, 2, amount_in).unwrap();
        let b = amount_out(&pool, 0, 2, amount_in).unwrap();
        assert_eq!(a, b);
    }

    #[test]
    fn rejects_invalid_inputs() {
        let pool = balanced_pool();
        let amt = U256::from(1_000u64);
        assert!(amount_out(&pool, 0, 0, amt).is_err(), "i == j");
        assert!(amount_out(&pool, 0, 9, amt).is_err(), "j out of range");
        assert!(amount_out(&pool, 0, 1, U256::ZERO).is_err(), "zero input");

        let mut bad_fee = balanced_pool();
        bad_fee.fee_bps = 10_000;
        assert!(amount_out(&bad_fee, 0, 1, amt).is_err(), "fee >= 100%");

        let mut zero_a = balanced_pool();
        zero_a.A = U256::ZERO;
        assert!(amount_out(&zero_a, 0, 1, amt).is_err(), "A == 0");

        let mut empty_balance = balanced_pool();
        empty_balance.balances[1] = U256::ZERO;
        assert!(
            amount_out(&empty_balance, 0, 1, amt).is_err(),
            "empty balance"
        );
    }
}
