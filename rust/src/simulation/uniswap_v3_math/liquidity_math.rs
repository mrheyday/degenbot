use crate::simulation::uniswap_v3_math::error::UniswapV3MathError;
use crate::simulation::uniswap_v3_math::full_math::mul_div;
use crate::simulation::uniswap_v3_math::sqrt_price_math::Q96;
use alloy::primitives::{U128, U256};
use eyre::eyre;

// returns (uint128 z)
pub fn add_delta(x: u128, y: i128) -> Result<u128, UniswapV3MathError> {
    if y < 0 {
        let z = x.overflowing_sub(-y as u128);

        if z.1 {
            Err(UniswapV3MathError::LiquiditySub)
        } else {
            Ok(z.0)
        }
    } else {
        let z = x.overflowing_add(y as u128);
        if z.0 < x {
            Err(UniswapV3MathError::LiquidityAdd)
        } else {
            Ok(z.0)
        }
    }
}

pub fn get_liquidity_for_amount0(
    sqrt_ratio_a_x_96: U256,
    sqrt_ratio_b_x_96: U256,
    amount0: U256,
) -> eyre::Result<u128> {
    let (sqrt_ratio_a_x_96, sqrt_ratio_b_x_96) = if sqrt_ratio_a_x_96 > sqrt_ratio_b_x_96 {
        (sqrt_ratio_b_x_96, sqrt_ratio_a_x_96)
    } else {
        (sqrt_ratio_a_x_96, sqrt_ratio_b_x_96)
    };

    //let mut denominator = Q96;
    let intermediate = mul_div(sqrt_ratio_a_x_96, sqrt_ratio_b_x_96, Q96)?;
    let ret = mul_div(amount0, intermediate, sqrt_ratio_b_x_96 - sqrt_ratio_a_x_96)?;
    if ret > U256::from(U128::MAX) {
        Err(eyre!("LIQUIDITY_OVERFLOWN"))
    } else {
        Ok(ret.to())
    }
}

pub fn get_liquidity_for_amount1(
    sqrt_ratio_a_x_96: U256,
    sqrt_ratio_b_x_96: U256,
    amount1: U256,
) -> eyre::Result<u128> {
    let (sqrt_ratio_a_x_96, sqrt_ratio_b_x_96) = if sqrt_ratio_a_x_96 > sqrt_ratio_b_x_96 {
        (sqrt_ratio_b_x_96, sqrt_ratio_a_x_96)
    } else {
        (sqrt_ratio_a_x_96, sqrt_ratio_b_x_96)
    };
    let ret = mul_div(amount1, Q96, sqrt_ratio_b_x_96 - sqrt_ratio_a_x_96)?;
    if ret > U256::from(U128::MAX) {
        Err(eyre!("LIQUIDITY_OVERFLOWN"))
    } else {
        Ok(ret.to())
    }
}

pub fn get_liquidity_for_amounts(
    sqrt_ratio_x_96: U256,
    sqrt_ratio_a_x_96: U256,
    sqrt_ratio_b_x_96: U256,
    amount0: U256,
    amount1: U256,
) -> eyre::Result<u128> {
    let (sqrt_ratio_a_x_96, sqrt_ratio_b_x_96) = if sqrt_ratio_a_x_96 > sqrt_ratio_b_x_96 {
        (sqrt_ratio_b_x_96, sqrt_ratio_a_x_96)
    } else {
        (sqrt_ratio_a_x_96, sqrt_ratio_b_x_96)
    };
    let liquidity = if sqrt_ratio_x_96 <= sqrt_ratio_a_x_96 {
        get_liquidity_for_amount0(sqrt_ratio_a_x_96, sqrt_ratio_b_x_96, amount0)?
    } else if sqrt_ratio_x_96 < sqrt_ratio_b_x_96 {
        let liquidity0 = get_liquidity_for_amount0(sqrt_ratio_x_96, sqrt_ratio_b_x_96, amount0)?;
        let liquidity1 = get_liquidity_for_amount1(sqrt_ratio_a_x_96, sqrt_ratio_x_96, amount1)?;
        if liquidity0 < liquidity1 {
            liquidity0
        } else {
            liquidity1
        }
    } else {
        get_liquidity_for_amount1(sqrt_ratio_a_x_96, sqrt_ratio_b_x_96, amount1)?
    };
    Ok(liquidity)
}

#[cfg(test)]
mod test {

    use crate::simulation::uniswap_v3_math::liquidity_math::{
        add_delta, get_liquidity_for_amount0, get_liquidity_for_amount1, get_liquidity_for_amounts,
    };
    use crate::simulation::uniswap_v3_math::sqrt_price_math::Q96;
    use alloy::primitives::{U128, U256};

    /// `n * Q96` as a U256 — a sqrt-ratio at price `n^2`.
    fn q96(n: u64) -> U256 {
        Q96 * U256::from(n)
    }

    #[test]
    fn get_liquidity_for_amount0_applies_the_concentrated_liquidity_formula() {
        // a=Q96, b=2*Q96: intermediate = a*b/Q96 = 2*Q96; ret = amount0 * 2*Q96 / (b-a).
        let liq = get_liquidity_for_amount0(q96(1), q96(2), U256::from(1_000_000u64)).unwrap();
        assert_eq!(liq, 2_000_000);
        // Swapped a/b order is normalised to the same result.
        let swapped = get_liquidity_for_amount0(q96(2), q96(1), U256::from(1_000_000u64)).unwrap();
        assert_eq!(swapped, 2_000_000);
    }

    #[test]
    fn get_liquidity_for_amount0_rejects_a_u128_overflow() {
        let err = get_liquidity_for_amount0(q96(1), q96(2), U256::from(U128::MAX)).unwrap_err();
        assert!(err.to_string().contains("LIQUIDITY_OVERFLOWN"));
    }

    #[test]
    fn get_liquidity_for_amount1_divides_amount1_by_the_sqrt_ratio_span() {
        // ret = amount1 * Q96 / (b-a); with b-a = Q96 the result is amount1.
        let liq = get_liquidity_for_amount1(q96(1), q96(2), U256::from(777_000u64)).unwrap();
        assert_eq!(liq, 777_000);
    }

    #[test]
    fn get_liquidity_for_amount1_rejects_a_u128_overflow() {
        // ret == amount1 here (b-a == Q96); one past U128::MAX overflows u128.
        let amount1 = U256::from(U128::MAX) + U256::from(1u64);
        let err = get_liquidity_for_amount1(q96(1), q96(2), amount1).unwrap_err();
        assert!(err.to_string().contains("LIQUIDITY_OVERFLOWN"));
    }

    #[test]
    fn get_liquidity_for_amounts_picks_the_right_branch_per_price() {
        let a = q96(1);
        let b = q96(2);
        let amount = U256::from(1_000_000u64);

        // x <= a -> amount0-only branch.
        let below =
            get_liquidity_for_amounts(q96(1) - Q96 / U256::from(2), a, b, amount, amount).unwrap();
        assert_eq!(below, 2_000_000);

        // a < x < b -> min(liquidity0, liquidity1).
        let inside =
            get_liquidity_for_amounts(q96(1) + Q96 / U256::from(2), a, b, amount, amount).unwrap();
        assert!(inside > 0);

        // x >= b -> amount1-only branch.
        let above = get_liquidity_for_amounts(q96(3), a, b, amount, amount).unwrap();
        assert_eq!(above, 1_000_000);
    }

    #[test]
    fn test_add_delta() {
        // 1 + 0
        let result = add_delta(1, 0);
        assert_eq!(result.unwrap(), 1);

        // 1 + -1
        let result = add_delta(1, -1);
        assert_eq!(result.unwrap(), 0);

        // 1 + 1
        let result = add_delta(1, 1);
        assert_eq!(result.unwrap(), 2);

        // 2**128-15 + 15 overflows
        let result = add_delta(340282366920938463463374607431768211441, 15);
        assert_eq!(result.err().unwrap().to_string(), "Liquidity Add");

        // 0 + -1 underflows
        let result = add_delta(0, -1);
        assert_eq!(result.err().unwrap().to_string(), "Liquidity Sub");

        // 3 + -4 underflows
        let result = add_delta(3, -4);
        assert_eq!(result.err().unwrap().to_string(), "Liquidity Sub");
    }
}
