//! Numerical optimization for Curve StableSwap pools.
//!
//! Uses iterative refinement (ternary search) to find the optimal input 
//! amount for cycles involving a Curve pool.

use alloy::primitives::{U256, I256};
use eyre::{Result};

use crate::simulation::curve::{amount_out as curve_amount_out, CurveSnapshot};

/// Find the optimal input amount for a 2-pool cycle with a Curve pool.
pub fn optimal_input_2pool_curve(
    pool_curve: &CurveSnapshot,
    i: usize,
    j: usize,
    pool2_v2: Option<(U256, U256, u32)>,
) -> Result<U256> {
    let mut low = U256::ZERO;
    let mut high = pool_curve.balances[i]; // Bound by the reserve of the input token

    if high.is_zero() {
        return Ok(U256::ZERO);
    }

    // Ternary search for the peak of the concave profit function.
    for _ in 0..128 {
        let diff = high - low;
        if diff <= U256::from(100u64) {
            break;
        }

        let m1 = low + diff / U256::from(3);
        let m2 = high - diff / U256::from(3);

        let p1 = calculate_curve_profit(pool_curve, i, j, pool2_v2, m1)?;
        let p2 = calculate_curve_profit(pool_curve, i, j, pool2_v2, m2)?;

        if p1 < p2 {
            low = m1;
        } else {
            high = m2;
        }
    }

    let final_x = (low + high) / U256::from(2);
    let final_profit = calculate_curve_profit(pool_curve, i, j, pool2_v2, final_x)?;
    
    if final_profit <= I256::ZERO {
        Ok(U256::ZERO)
    } else {
        Ok(final_x)
    }
}

fn calculate_curve_profit(
    pool_curve: &CurveSnapshot,
    i: usize,
    j: usize,
    pool2_v2: Option<(U256, U256, u32)>,
    amount_in: U256,
) -> Result<I256> {
    if amount_in.is_zero() {
        return Ok(I256::ZERO);
    }

    let out1 = curve_amount_out(pool_curve, i, j, amount_in)?;
    if out1.is_zero() {
        return Ok(I256::MIN);
    }

    let out2 = if let Some(v2) = pool2_v2 {
        crate::simulation::v2::amount_out(out1, v2.0, v2.1, v2.2)?
    } else {
        U256::ZERO
    };

    Ok(I256::try_from(out2).unwrap() - I256::try_from(amount_in).unwrap())
}
