//! Uniswap V2 / Sushi / Camelot V2 constant-product math.
//!
//! Pure-Rust amount-out helpers. No I/O, no async. Used both by the
//! strategy layer for fast cycle pricing and as oracle assertions for the
//! REVM execution path.

use alloy::primitives::{U256, U512};
use eyre::{eyre, Result};

use crate::utils::u256::{mul_div, narrow_u512};

/// `getAmountOut` per UniswapV2 Library: `out = (in * fee_num * R_out) /
/// (R_in * fee_denom + in * fee_num)`. `fee_bps` is the LP fee in bps; for
/// canonical V2 use `30` (= 0.30 %).
pub fn amount_out(
    amount_in: U256,
    reserve_in: U256,
    reserve_out: U256,
    fee_bps: u32,
) -> Result<U256> {
    validate_reserves(reserve_in, reserve_out)?;
    validate_fee_bps(fee_bps)?;
    if amount_in.is_zero() {
        return Err(eyre!("v2::amount_out: amount_in is zero"));
    }

    let fee_denom = U256::from(10_000u64);
    let fee_num = U256::from(10_000u64 - u64::from(fee_bps));
    let amount_in_with_fee = amount_in
        .checked_mul(fee_num)
        .ok_or_else(|| eyre!("v2::amount_out: amount_in * fee_num overflow"))?;
    let denominator = reserve_in
        .checked_mul(fee_denom)
        .and_then(|base| base.checked_add(amount_in_with_fee))
        .ok_or_else(|| eyre!("v2::amount_out: denominator overflow"))?;
    mul_div(amount_in_with_fee, reserve_out, denominator)
}

/// Inverse of `amount_out`: given a desired `amount_out`, what `amount_in`
/// is required? Used by golden-section search bounds.
pub fn amount_in_for_out(
    amount_out: U256,
    reserve_in: U256,
    reserve_out: U256,
    fee_bps: u32,
) -> Result<U256> {
    validate_reserves(reserve_in, reserve_out)?;
    validate_fee_bps(fee_bps)?;
    if amount_out.is_zero() {
        return Err(eyre!("v2::amount_in_for_out: amount_out is zero"));
    }
    if amount_out >= reserve_out {
        return Err(eyre!(
            "v2::amount_in_for_out: amount_out exceeds reserve_out"
        ));
    }

    let fee_denom = U256::from(10_000u64);
    let fee_num = U256::from(10_000u64 - u64::from(fee_bps));
    let numerator = U512::from(reserve_in) * U512::from(amount_out) * U512::from(fee_denom);
    let denominator = U512::from(reserve_out - amount_out) * U512::from(fee_num);
    if denominator.is_zero() {
        return Err(eyre!("v2::amount_in_for_out: denominator is zero"));
    }
    let rounded = (numerator / denominator)
        + if numerator % denominator == U512::ZERO {
            U512::ZERO
        } else {
            U512::ONE
        };
    narrow_u512(
        rounded,
        "v2::amount_in_for_out: required input overflows U256",
    )
}

fn validate_reserves(reserve_in: U256, reserve_out: U256) -> Result<()> {
    if reserve_in.is_zero() || reserve_out.is_zero() {
        return Err(eyre!("v2: reserves must be non-zero"));
    }
    Ok(())
}

fn validate_fee_bps(fee_bps: u32) -> Result<()> {
    if fee_bps >= 10_000 {
        return Err(eyre!("v2: fee_bps must be < 10000"));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn amount_out_matches_uniswap_v2_library_formula() {
        let out = amount_out(
            U256::from(1_000u64),
            U256::from(10_000u64),
            U256::from(20_000u64),
            30,
        )
        .unwrap();
        assert_eq!(out, U256::from(1_813u64));
    }

    #[test]
    fn amount_in_for_out_rounds_up_to_cover_desired_output() {
        let required = amount_in_for_out(
            U256::from(1_813u64),
            U256::from(10_000u64),
            U256::from(20_000u64),
            30,
        )
        .unwrap();
        assert_eq!(required, U256::from(1_000u64));
        let produced =
            amount_out(required, U256::from(10_000u64), U256::from(20_000u64), 30).unwrap();
        assert!(produced >= U256::from(1_813u64));
    }

    #[test]
    fn rejects_invalid_inputs() {
        assert!(amount_out(U256::ZERO, U256::ONE, U256::ONE, 30).is_err());
        assert!(amount_out(U256::ONE, U256::ZERO, U256::ONE, 30).is_err());
        assert!(amount_out(U256::ONE, U256::ONE, U256::ONE, 10_000).is_err());
        assert!(amount_in_for_out(U256::ONE, U256::ONE, U256::ONE, 30).is_err());
    }
}
