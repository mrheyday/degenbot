//! Analytical optimization for Uniswap V2 2-pool cycles.
//!
//! Formula derived from the constant-product invariant (x*y=k) for two
//! pools in a cycle. Reference: Degen Code "Numerical Optimization" Part V.

use alloy::primitives::{U256, U512};
use eyre::{eyre, Result};

use crate::utils::u256::{isqrt, isqrt_u512, narrow_u512};

/// Calculate the optimal input amount for a 2-pool Uniswap V2 arbitrage cycle.
pub fn optimal_input_2pool(
    r_a1: U256,
    r_b1: U256,
    fee_bps1: u32,
    r_b2: U256,
    r_a2: U256,
    fee_bps2: u32,
) -> Result<U256> {
    if r_a1.is_zero() || r_b1.is_zero() || r_b2.is_zero() || r_a2.is_zero() {
        return Err(eyre!("v2_optimize: reserves must be non-zero"));
    }

    let g1_num = U512::from(10_000u64 - u64::from(fee_bps1));
    let g2_num = U512::from(10_000u64 - u64::from(fee_bps2));
    let d = U512::from(10_000u64);

    let k =
        U512::from(r_a1) * U512::from(r_b1) * U512::from(r_b2) * U512::from(r_a2) * g1_num * g2_num;
    let sqrt_k = isqrt_u512(k);

    let term1 = sqrt_k / d;
    let term2 = U512::from(r_a1) * U512::from(r_b2);

    if term1 <= term2 {
        return Ok(U256::ZERO);
    }

    let numerator = term1 - term2;
    let denom_scaled = U512::from(r_b2) * d + U512::from(r_b1) * g1_num;
    let result = (numerator * d) / denom_scaled;

    narrow_u512(result, "v2_optimize: optimal input overflows U256")
}

/// Calculate the optimal frontrun amount for a sandwich attack.
pub fn optimal_v2_frontrun_amount(
    victim_amount_in: U256,
    victim_min_out: U256,
    reserve_in: U256,
    reserve_out: U256,
    fee_bps: u32,
    margin_bps: u32,
) -> Result<U256> {
    if fee_bps >= 10_000 || margin_bps >= 10_000 {
        return Ok(U256::ZERO);
    }
    if reserve_in.is_zero()
        || reserve_out.is_zero()
        || victim_amount_in.is_zero()
        || victim_min_out.is_zero()
    {
        return Ok(U256::ZERO);
    }

    let g_bps = U256::from(10_000 - fee_bps);
    let bps_u256 = U256::from(10_000u64);

    let victim_fee = victim_amount_in
        .checked_mul(g_bps)
        .ok_or_else(|| eyre!("overflow in optimal_v2_frontrun_amount victim_fee"))?;
    let num = victim_fee
        .checked_mul(reserve_out)
        .ok_or_else(|| eyre!("overflow in optimal_v2_frontrun_amount numerator"))?;
    let den = reserve_in
        .checked_mul(bps_u256)
        .ok_or_else(|| eyre!("overflow in optimal_v2_frontrun_amount denominator reserve"))?
        .checked_add(victim_fee)
        .ok_or_else(|| eyre!("overflow in optimal_v2_frontrun_amount denominator add"))?;

    let baseline_out = num / den;
    if baseline_out <= victim_min_out {
        return Ok(U256::ZERO);
    }

    let inner = reserve_in
        .checked_mul(bps_u256)
        .ok_or_else(|| eyre!("overflow in optimal_v2_frontrun_amount c1 inner reserve"))?
        .checked_add(victim_fee)
        .ok_or_else(|| eyre!("overflow in optimal_v2_frontrun_amount c1 inner add"))?;
    let c1_pos = reserve_in
        .checked_mul(inner)
        .ok_or_else(|| eyre!("overflow in optimal_v2_frontrun_amount c1_pos"))?
        / g_bps;
    let c1_neg = victim_amount_in
        .checked_mul(reserve_in)
        .ok_or_else(|| eyre!("overflow in optimal_v2_frontrun_amount c1_neg reserve"))?
        .checked_mul(reserve_out)
        .ok_or_else(|| eyre!("overflow in optimal_v2_frontrun_amount c1_neg out"))?
        / victim_min_out;

    if c1_neg <= c1_pos {
        return Ok(U256::ZERO);
    }
    let abs_c1 = c1_neg - c1_pos;

    let bps_plus_gamma = bps_u256
        .checked_add(g_bps)
        .ok_or_else(|| eyre!("overflow in optimal_v2_frontrun_amount bps_plus_gamma"))?;
    let b1_lhs = reserve_in
        .checked_mul(bps_plus_gamma)
        .ok_or_else(|| eyre!("overflow in optimal_v2_frontrun_amount b1_lhs"))?
        / g_bps;
    let b1_rhs = g_bps
        .checked_mul(victim_amount_in)
        .ok_or_else(|| eyre!("overflow in optimal_v2_frontrun_amount b1_rhs"))?
        / bps_u256;
    let b1 = b1_lhs
        .checked_add(b1_rhs)
        .ok_or_else(|| eyre!("overflow in optimal_v2_frontrun_amount b1"))?;

    let half_b = b1 / U256::from(2);
    let disc = half_b
        .checked_mul(half_b)
        .ok_or_else(|| eyre!("overflow in optimal_v2_frontrun_amount half_b_sq"))?
        .checked_add(abs_c1)
        .ok_or_else(|| eyre!("overflow in optimal_v2_frontrun_amount discriminant"))?;

    let sqrt_disc = isqrt(disc);
    if sqrt_disc <= half_b {
        return Ok(U256::ZERO);
    }

    let mut frontrun_amount = sqrt_disc - half_b;
    if margin_bps > 0 {
        let margin_factor = bps_u256
            .checked_sub(U256::from(margin_bps))
            .ok_or_else(|| eyre!("underflow in optimal_v2_frontrun_amount margin"))?;
        frontrun_amount = frontrun_amount
            .checked_mul(margin_factor)
            .ok_or_else(|| eyre!("overflow in optimal_v2_frontrun_amount margin mul"))?
            / bps_u256;
    }

    Ok(frontrun_amount)
}

/// Calculate the mid-price in Q64.96 for a V2 pool.
pub fn v2_mid_price_x96(reserve_in: U256, reserve_out: U256) -> U256 {
    if reserve_in.is_zero() {
        return U256::ZERO;
    }
    (reserve_out << 96) / reserve_in
}

/// Apply the gap to a price (basis points; positive moves price up).
pub fn apply_gap_to_price_x96(price_x96: U256, gap_bps: i32) -> U256 {
    if gap_bps == 0 {
        return price_x96;
    }
    let factor = 10_000i32.saturating_add(gap_bps);
    if factor <= 0 {
        return U256::ZERO;
    }
    let scaled = price_x96
        .checked_mul(U256::from(factor as u64))
        .unwrap_or(U256::MAX);
    scaled / U256::from(10_000u64)
}

/// Synthetic victim swap size — gap magnitude scaled against pool depth.
pub fn synthetic_victim_amount_in(gap_bps: i32, reserve_in: U256) -> U256 {
    let mag = u64::from(gap_bps.unsigned_abs());
    if mag == 0 {
        return U256::ZERO;
    }
    let fraction = U256::from(mag.min(5_000));
    (reserve_in * fraction) / U256::from(10_000u64)
}

/// Largest frontrun size `a` such that the victim's post-distortion fill is exactly `victim_min_out`.
pub fn v2_sandwich_max_size(
    victim_amount_in: U256,
    victim_min_out: U256,
    reserve_in: U256,
    reserve_out: U256,
    fee_bps: u32,
) -> Result<U256> {
    if fee_bps >= 10_000 {
        return Ok(U256::ZERO);
    }
    if reserve_in.is_zero() || reserve_out.is_zero() || victim_amount_in.is_zero() {
        return Ok(U256::ZERO);
    }
    let f = U256::from(10_000 - fee_bps);
    let d = U256::from(10_000u64);

    let baseline_out =
        (reserve_out * victim_amount_in * f) / (reserve_in * d + victim_amount_in * f);
    if baseline_out <= victim_min_out {
        return Ok(U256::ZERO);
    }

    let x0d = reserve_in * d;
    let vf = victim_amount_in * f;
    let l = victim_min_out;

    let a_coeff = l * f * d;
    let b_coeff = l * (x0d * (d + f) + victim_amount_in * f * f);
    let c_pos = l * x0d * (x0d + vf);
    let c_neg = reserve_out * x0d * vf;

    if c_neg <= c_pos {
        return Ok(U256::ZERO);
    }
    let neg_c = c_neg - c_pos;

    let a512 = U512::from(a_coeff);
    let b512 = U512::from(b_coeff);
    let c512 = U512::from(neg_c);

    let disc = b512
        .checked_mul(b512)
        .ok_or_else(|| eyre!("b_coeff^2 overflow"))?
        .checked_add(U512::from(4u64) * a512 * c512)
        .ok_or_else(|| eyre!("disc overflow"))?;

    let sqrt_disc = isqrt_u512(disc);
    if sqrt_disc <= b512 {
        return Ok(U256::ZERO);
    }

    let res = (sqrt_disc - b512) / (U512::from(2u64) * a512);
    narrow_u512(res, "v2_optimize: sandwich max size overflows U256")
}

/// Find the unconstrained optimal frontrun size using golden-section search.
pub fn v2_optimal_sandwich_size(
    victim_amount_in: U256,
    reserve_in: U256,
    reserve_out: U256,
    fee_bps: u32,
    a_max: U256,
) -> Result<U256> {
    if a_max.is_zero() {
        return Ok(U256::ZERO);
    }

    let mut lo = U256::ZERO;
    let mut hi = a_max;

    let profit_at = |a: U256| -> U256 {
        if a.is_zero() {
            return U256::ZERO;
        }
        let f = 10_000 - fee_bps;
        let d = 10_000;
        let fr_out =
            (reserve_out * a * U256::from(f)) / (reserve_in * U256::from(d) + a * U256::from(f));
        let x1 = reserve_in + a;
        let y1 = reserve_out - fr_out;
        let v_out = (y1 * victim_amount_in * U256::from(f))
            / (x1 * U256::from(d) + victim_amount_in * U256::from(f));
        let x2 = x1 + victim_amount_in;
        let y2 = y1 - v_out;
        let br_out = (x2 * fr_out * U256::from(f)) / (y2 * U256::from(d) + fr_out * U256::from(f));
        if br_out > a {
            br_out - a
        } else {
            U256::ZERO
        }
    };

    for _ in 0..64 {
        if hi - lo <= U256::from(100u64) {
            break;
        }
        let span = hi - lo;
        let c = lo + (span * U256::from(382u64)) / U256::from(1000u64);
        let d = lo + (span * U256::from(618u64)) / U256::from(1000u64);
        if profit_at(c) >= profit_at(d) {
            hi = d;
        } else {
            lo = c;
        }
    }

    Ok(if profit_at(lo) >= profit_at(hi) {
        lo
    } else {
        hi
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_optimal_input_profitable() {
        let result = optimal_input_2pool(
            U256::from(1000u64),
            U256::from(2000u64),
            30,
            U256::from(1000u64),
            U256::from(1000u64),
            30,
        )
        .unwrap();
        assert!(result > U256::ZERO);
    }
}
