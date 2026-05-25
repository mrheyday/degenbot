//! Piecewise optimization for Uniswap V3 / V4 concentrated liquidity.
//!
//! Uses a hybrid binary/Newton search across tick boundaries to find the 
//! optimal input amount for a 2-pool cycle involving at least one V3/V4 pool.

use alloy::primitives::{U256, I256};
use eyre::{Result};

use crate::simulation::v3::{V3Snapshot, amount_out as v3_amount_out};
use crate::simulation::v2::{amount_out as v2_amount_out};

/// Find the optimal input amount for a 2-pool cycle.
/// Supported combinations: V2-V3, V3-V3.
pub fn optimal_input_2pool_v3(
    pool1_v3: &V3Snapshot,
    pool1_zero_for_one: bool,
    pool2_v3: Option<&V3Snapshot>,
    pool2_v2: Option<(U256, U256, u32)>,
) -> Result<U256> {
    // Robust binary search across ticks as the baseline.
    // Concentrated liquidity profit curves are concave and piecewise-differentiable.
    
    let mut low = U256::ZERO;
    let mut high = if let Some(v2) = pool2_v2 {
        v2.0
    } else {
        // For V3-V3, we bound by a large multiple of liquidity or a fixed ceiling.
        U256::from(pool1_v3.liquidity) * U256::from(100u64)
    };

    if high.is_zero() {
        return Ok(U256::ZERO);
    }

    // 128 iterations of ternary search for high precision on U256.
    for _ in 0..128 {
        let diff = high - low;
        if diff <= U256::from(100u64) {
            break;
        }

        let m1 = low + diff / U256::from(3);
        let m2 = high - diff / U256::from(3);

        let p1 = calculate_profit(pool1_v3, pool1_zero_for_one, pool2_v3, pool2_v2, m1)?;
        let p2 = calculate_profit(pool1_v3, pool1_zero_for_one, pool2_v3, pool2_v2, m2)?;

        if p1 < p2 {
            low = m1;
        } else {
            high = m2;
        }
    }

    let final_x = (low + high) / U256::from(2);
    let final_profit = calculate_profit(pool1_v3, pool1_zero_for_one, pool2_v3, pool2_v2, final_x)?;
    
    if final_profit <= I256::ZERO {
        Ok(U256::ZERO)
    } else {
        Ok(final_x)
    }
}

fn calculate_profit(
    pool1_v3: &V3Snapshot,
    p1_zfo: bool,
    pool2_v3: Option<&V3Snapshot>,
    pool2_v2: Option<(U256, U256, u32)>,
    amount_in: U256,
) -> Result<I256> {
    if amount_in.is_zero() {
        return Ok(I256::ZERO);
    }

    let out1 = v3_amount_out(pool1_v3, amount_in, p1_zfo)?;
    if out1.is_zero() {
        return Ok(I256::MIN);
    }

    let out2 = if let Some(p2v3) = pool2_v3 {
        v3_amount_out(p2v3, out1, !p1_zfo)?
    } else if let Some(p2v2) = pool2_v2 {
        v2_amount_out(out1, p2v2.0, p2v2.1, p2v2.2)?
    } else {
        U256::ZERO
    };

    Ok(I256::try_from(out2).unwrap() - I256::try_from(amount_in).unwrap())
}
