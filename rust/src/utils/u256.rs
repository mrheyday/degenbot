//! U256 helpers for hot-path math.
//!
//! No `f64` on profit paths (per CLAUDE.md). Each helper returns
//! `eyre::Result` rather than panicking on overflow / division-by-zero so
//! callers can attach opportunity-id context.

use alloy::primitives::{U256, U512};
use eyre::{eyre, Result};

/// `(a * b) / denom` with no intermediate overflow on values that fit in
/// U512. Used by V2 / V3 amount-out math.
pub fn mul_div(a: U256, b: U256, denom: U256) -> Result<U256> {
    if denom.is_zero() {
        return Err(eyre!("u256::mul_div: denominator is zero"));
    }
    let wide = U512::from(a) * U512::from(b);
    let q = wide / U512::from(denom);
    narrow_u512(q, "u256::mul_div: quotient overflows U256")
}

/// `(a * b + denom - 1) / denom` — ceiling division of mul_div. Used for
/// amount-in inverse helpers.
pub fn mul_div_ceil(a: U256, b: U256, denom: U256) -> Result<U256> {
    if denom.is_zero() {
        return Err(eyre!("u256::mul_div_ceil: denominator is zero"));
    }
    let wide = U512::from(a) * U512::from(b);
    let denom_wide = U512::from(denom);
    let q = wide / denom_wide;
    let r = wide % denom_wide;
    let rounded = if r.is_zero() {
        q
    } else {
        q.checked_add(U512::ONE)
            .ok_or_else(|| eyre!("u256::mul_div_ceil: rounded quotient overflows U512"))?
    };
    narrow_u512(rounded, "u256::mul_div_ceil: quotient overflows U256")
}

pub(crate) fn narrow_u512(value: U512, error: &'static str) -> Result<U256> {
    U256::checked_from_limbs_slice(value.as_limbs()).ok_or_else(|| eyre!(error))
}

/// Convert a Uniswap V3 `sqrtPriceX96` to a WAD-scaled price.
/// `price_wad = (sqrtPriceX96 * sqrtPriceX96 * 1e18) / 2^192`.
///
/// Computed in U512 to avoid intermediate overflow — `sqrtPriceX96` is up
/// to ~2^160, so the square is up to ~2^320.
pub fn sqrt_price_x96_to_price_wad(sqrt_price_x96: U256) -> Result<U256> {
    let p = U512::from(sqrt_price_x96);
    let squared = p
        .checked_mul(p)
        .ok_or_else(|| eyre!("u256::sqrt_price_x96_to_price_wad: sqrtP^2 overflows U512"))?;
    let scaled = squared
        .checked_mul(U512::from(1_000_000_000_000_000_000u64))
        .ok_or_else(|| eyre!("u256::sqrt_price_x96_to_price_wad: WAD scaling overflows U512"))?;
    narrow_u512(
        scaled >> 192,
        "u256::sqrt_price_x96_to_price_wad: price overflows U256",
    )
}

/// Integer square root (floor) via Newton's method on U256. Used for
/// golden-section bounds + cycle-bound estimation.
pub fn isqrt(n: U256) -> U256 {
    if n.is_zero() {
        return U256::ZERO;
    }
    // Initial guess `n/2 + 1` is >= floor(sqrt(n)) for all n >= 1 and never
    // overflows; Newton then descends monotonically to the floor root.
    let mut x = (n >> 1) + U256::ONE;
    let mut y = (x + n / x) >> 1;
    while y < x {
        x = y;
        y = (x + n / x) >> 1;
    }
    x
}

/// Integer square root (floor) of a `U512`, via Newton's method. Same
/// algorithm as [`isqrt`], widened: the closed-form two-pool optimizer
/// needs `√(E·F)` where the radicand reaches ~2^503 — past U256 range,
/// though the root itself (~2^251) still fits U256.
pub fn isqrt_u512(n: U512) -> U512 {
    if n.is_zero() {
        return U512::ZERO;
    }
    let mut x = (n >> 1) + U512::ONE;
    let mut y = (x + n / x) >> 1;
    while y < x {
        x = y;
        y = (x + n / x) >> 1;
    }
    x
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn mul_div_floor_and_ceil_round_trip() {
        assert_eq!(
            mul_div(U256::from(7u64), U256::from(10u64), U256::from(6u64)).unwrap(),
            U256::from(11u64),
        );
        assert_eq!(
            mul_div_ceil(U256::from(7u64), U256::from(10u64), U256::from(6u64)).unwrap(),
            U256::from(12u64),
        );
    }

    #[test]
    fn mul_div_supports_512_bit_intermediate() {
        let a = U256::from(1u64) << 200;
        let b = U256::from(1u64) << 100;
        let denom = U256::from(1u64) << 60;
        assert_eq!(mul_div(a, b, denom).unwrap(), U256::from(1u64) << 240);
    }

    #[test]
    fn mul_div_rejects_zero_denominator() {
        assert!(mul_div(U256::ONE, U256::ONE, U256::ZERO).is_err());
        assert!(mul_div_ceil(U256::ONE, U256::ONE, U256::ZERO).is_err());
    }

    #[test]
    fn isqrt_handles_small_values_and_perfect_squares() {
        assert_eq!(isqrt(U256::ZERO), U256::ZERO);
        assert_eq!(isqrt(U256::from(1u64)), U256::from(1u64));
        assert_eq!(isqrt(U256::from(3u64)), U256::from(1u64));
        assert_eq!(isqrt(U256::from(4u64)), U256::from(2u64));
        assert_eq!(isqrt(U256::from(15u64)), U256::from(3u64));
        assert_eq!(isqrt(U256::from(16u64)), U256::from(4u64));
        assert_eq!(isqrt(U256::from(17u64)), U256::from(4u64));
    }

    #[test]
    fn isqrt_handles_large_perfect_square() {
        let root = U256::from(1u64) << 64;
        assert_eq!(isqrt(root * root), root);
    }

    #[test]
    fn isqrt_satisfies_floor_root_invariant() {
        for n in [
            U256::from(2u64),
            U256::from(99u64),
            U256::from(1_000_003u64),
            (U256::from(1u64) << 200) + U256::from(7u64),
        ] {
            let r = isqrt(n);
            assert!(r * r <= n, "r^2 must not exceed n");
            assert!(
                (r + U256::ONE) * (r + U256::ONE) > n,
                "(r+1)^2 must exceed n"
            );
        }
    }

    #[test]
    fn isqrt_u512_handles_small_values_and_perfect_squares() {
        assert_eq!(isqrt_u512(U512::ZERO), U512::ZERO);
        assert_eq!(isqrt_u512(U512::from(1u64)), U512::from(1u64));
        assert_eq!(isqrt_u512(U512::from(3u64)), U512::from(1u64));
        assert_eq!(isqrt_u512(U512::from(4u64)), U512::from(2u64));
        assert_eq!(isqrt_u512(U512::from(15u64)), U512::from(3u64));
        assert_eq!(isqrt_u512(U512::from(16u64)), U512::from(4u64));
    }

    #[test]
    fn isqrt_u512_handles_radicands_beyond_u256() {
        // `E·F` in the two-pool optimizer reaches ~2^503: the radicand
        // overflows U256 while its root (~2^251) does not.
        let root = U512::from(1u64) << 251;
        assert_eq!(isqrt_u512(root * root), root);
    }

    #[test]
    fn isqrt_u512_satisfies_floor_root_invariant() {
        for n in [
            U512::from(2u64),
            U512::from(1_000_003u64),
            (U512::from(1u64) << 256) + U512::from(7u64),
            (U512::from(1u64) << 502) + U512::from(123u64),
        ] {
            let r = isqrt_u512(n);
            assert!(r * r <= n, "r^2 must not exceed n");
            assert!(
                (r + U512::ONE) * (r + U512::ONE) > n,
                "(r+1)^2 must exceed n"
            );
        }
    }

    #[test]
    fn sqrt_price_wad_is_one_at_price_one() {
        // sqrtPriceX96 == 2^96 encodes price 1.0 -> price_wad == 1e18.
        let one_x96 = U256::from(1u64) << 96;
        assert_eq!(
            sqrt_price_x96_to_price_wad(one_x96).unwrap(),
            U256::from(1_000_000_000_000_000_000u64),
        );
    }

    #[test]
    fn sqrt_price_wad_is_four_at_price_four() {
        // sqrtPriceX96 == 2^97 encodes price 4.0 -> price_wad == 4e18.
        let two_x96 = U256::from(1u64) << 97;
        assert_eq!(
            sqrt_price_x96_to_price_wad(two_x96).unwrap(),
            U256::from(4_000_000_000_000_000_000u64),
        );
    }
}
