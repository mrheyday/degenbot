//! Piecewise optimization for Uniswap V3 / V4 concentrated liquidity.
//!
//! Uses a hybrid binary/Newton search across tick boundaries to find the
//! optimal input amount for a 2-pool cycle involving at least one V3/V4 pool.

use alloy::primitives::{I256, U256};
use eyre::{eyre, Result};

use crate::simulation::v2::amount_out as v2_amount_out;
use crate::simulation::v3::{amount_out as v3_amount_out, amount_out_with_state, V3Snapshot};

/// Find the optimal input amount for a 2-pool cycle.
pub fn optimal_input_2pool_v3(
    pool1_v3: &V3Snapshot,
    pool1_zero_for_one: bool,
    pool2_v3: Option<&V3Snapshot>,
    pool2_v2: Option<(U256, U256, u32)>,
) -> Result<U256> {
    let mut low = U256::ZERO;
    let mut high = if let Some(v2) = pool2_v2 {
        v2.0
    } else {
        U256::from(pool1_v3.liquidity) * U256::from(100u64)
    };

    if high.is_zero() {
        return Ok(U256::ZERO);
    }

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

    let out2_i256 = I256::try_from(out2).map_err(|_| eyre!("v3 profit output overflows I256"))?;
    let amount_in_i256 =
        I256::try_from(amount_in).map_err(|_| eyre!("v3 profit input overflows I256"))?;
    Ok(out2_i256 - amount_in_i256)
}

/// Find the largest frontrun size `a` for a V3 sandwich such that the
/// victim does not revert (output >= min_out).
pub fn v3_sandwich_max_size(
    pool: &V3Snapshot,
    victim_amount_in: U256,
    victim_min_out: U256,
    zero_for_one: bool,
) -> Result<U256> {
    let baseline = v3_amount_out(pool, victim_amount_in, zero_for_one)?;
    if baseline <= victim_min_out {
        return Ok(U256::ZERO);
    }

    let mut hi = victim_amount_in;
    for _ in 0..32 {
        let (_, next_pool) = amount_out_with_state(pool, hi, zero_for_one)?;
        let vic_out = v3_amount_out(&next_pool, victim_amount_in, zero_for_one)?;
        if vic_out <= victim_min_out {
            break;
        }
        hi <<= 1;
    }

    let mut lo = U256::ZERO;
    for _ in 0..64 {
        if hi - lo <= U256::from(1u64) {
            break;
        }
        let mid = (lo + hi) >> 1;
        let (_, next_pool) = amount_out_with_state(pool, mid, zero_for_one)?;
        let vic_out = v3_amount_out(&next_pool, victim_amount_in, zero_for_one)?;
        if vic_out >= victim_min_out {
            lo = mid;
        } else {
            hi = mid;
        }
    }
    Ok(lo)
}

/// Find the optimal frontrun size for a V3 sandwich using golden-section search.
pub fn v3_optimal_sandwich_size(
    pool: &V3Snapshot,
    victim_amount_in: U256,
    zero_for_one: bool,
    a_max: U256,
) -> Result<U256> {
    if a_max.is_zero() {
        return Ok(U256::ZERO);
    }

    let profit_at = |a: U256| -> Result<I256> {
        if a.is_zero() {
            return Ok(I256::ZERO);
        }
        let (fr_out, pool_after_fr) = amount_out_with_state(pool, a, zero_for_one)?;
        let (_, pool_after_vic) =
            amount_out_with_state(&pool_after_fr, victim_amount_in, zero_for_one)?;
        let br_out = v3_amount_out(&pool_after_vic, fr_out, !zero_for_one)?;

        let br_out_i256 = I256::try_from(br_out).map_err(|_| eyre!("v3 br_out overflow"))?;
        let a_i256 = I256::try_from(a).map_err(|_| eyre!("v3 a overflow"))?;
        Ok(br_out_i256 - a_i256)
    };

    let mut lo = U256::ZERO;
    let mut hi = a_max;

    for _ in 0..64 {
        if hi - lo <= U256::from(100u64) {
            break;
        }
        let span = hi - lo;
        let c = lo + (span * U256::from(382u64)) / U256::from(1000u64);
        let d = lo + (span * U256::from(618u64)) / U256::from(1000u64);

        if profit_at(c)? >= profit_at(d)? {
            hi = d;
        } else {
            lo = c;
        }
    }

    Ok(if profit_at(lo)? >= profit_at(hi)? {
        lo
    } else {
        hi
    })
}
