use alloc::vec::Vec;
use stylus_sdk::alloy_primitives::{FixedBytes, U256, keccak256};

pub const SCALE: U256 = U256::from_limbs([1_000_000_000_000_000_000, 0, 0, 0]);
pub const FEE_BPS: u64 = 30;
pub const IMPACT_EXPONENT: u64 = 3;
pub const MIN_EFFECTIVE_RATE_FRACTION: u64 = 10;
pub const MERGED_GAS_NUMERATOR: u64 = 62;
pub const MERGED_GAS_DENOMINATOR: u64 = 100;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Hop {
    pub dex: FixedBytes<32>,
    pub from_token: FixedBytes<32>,
    pub to_token: FixedBytes<32>,
    pub amount_in: U256,
    pub amount_out: U256,
    pub gas: U256,
    pub pool_liquidity: U256,
}

#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct Route {
    pub hops: Vec<Hop>,
    pub total_output: U256,
    pub total_gas: U256,
}

#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct MergedGroup {
    pub signature_hash: FixedBytes<32>,
    pub merged_count: U256,
    pub merged_amount_at_intermediate: U256,
    pub merged_output: U256,
    pub original_best_output: U256,
    pub merged_gas: U256,
    pub original_total_gas: U256,
}

pub fn simulate_price_impact_u256(amount_in: U256, pool_liquidity: U256) -> U256 {
    if pool_liquidity == U256::ZERO {
        return U256::ZERO;
    }

    let denominator = pool_liquidity + amount_in;
    let impact_factor = mul_div(amount_in, SCALE, denominator);
    let fee_part = (U256::from(FEE_BPS) * SCALE) / U256::from(10_000);
    let impact_part = mul_div(impact_factor, U256::from(IMPACT_EXPONENT), U256::from(100));
    let penalty = fee_part + impact_part;
    let effective_rate = if SCALE > penalty {
        SCALE - penalty
    } else {
        U256::ZERO
    };
    let floor_rate = SCALE / U256::from(MIN_EFFECTIVE_RATE_FRACTION);
    if effective_rate > floor_rate {
        effective_rate
    } else {
        floor_rate
    }
}

pub fn make_route(hops: Vec<Hop>) -> Route {
    if hops.is_empty() {
        return Route::default();
    }
    let total_output = hops[hops.len() - 1].amount_out;
    let total_gas = hops.iter().fold(U256::ZERO, |sum, hop| sum + hop.gas);
    Route {
        hops,
        total_output,
        total_gas,
    }
}

pub fn intermediate_signature(hops: &[Hop]) -> FixedBytes<32> {
    if hops.len() < 2 {
        return FixedBytes::<32>::ZERO;
    }
    let mut packed = Vec::with_capacity((hops.len() - 1) * 32);
    for hop in &hops[..hops.len() - 1] {
        packed.extend_from_slice(hop.to_token.as_slice());
    }
    keccak256(packed)
}

pub fn merge_steps_by_intermediate(
    routes: &[Route],
    final_token: FixedBytes<32>,
) -> (Vec<Route>, Vec<MergedGroup>) {
    if routes.is_empty() {
        return (Vec::new(), Vec::new());
    }

    let sigs: Vec<_> = routes
        .iter()
        .map(|route| intermediate_signature(&route.hops))
        .collect();
    let mut used = vec![false; routes.len()];
    let mut optimised = Vec::new();
    let mut groups = Vec::new();

    for i in 0..routes.len() {
        if used[i] {
            continue;
        }
        used[i] = true;
        let sig = sigs[i];
        if sig == FixedBytes::<32>::ZERO {
            optimised.push(routes[i].clone());
            continue;
        }

        let mut indexes = vec![i];
        for j in i + 1..routes.len() {
            if !used[j] && sigs[j] == sig {
                used[j] = true;
                indexes.push(j);
            }
        }

        if indexes.len() == 1 {
            optimised.push(routes[i].clone());
        } else {
            let (route, group) = build_merged_route(routes, &indexes, sig, final_token);
            optimised.push(route);
            groups.push(group);
        }
    }

    (optimised, groups)
}

fn build_merged_route(
    routes: &[Route],
    indexes: &[usize],
    sig: FixedBytes<32>,
    final_token: FixedBytes<32>,
) -> (Route, MergedGroup) {
    let first_route = &routes[indexes[0]];
    let mut total_at_merge = U256::ZERO;
    let mut best_final = first_route.hops[first_route.hops.len() - 1].clone();
    let mut best_rate = mul_div(best_final.amount_out, SCALE, best_final.amount_in);

    for index in indexes {
        let route = &routes[*index];
        let hop_count = route.hops.len();
        let penultimate = &route.hops[hop_count - 2];
        let final_hop = &route.hops[hop_count - 1];
        total_at_merge += penultimate.amount_out;
        let rate = mul_div(final_hop.amount_out, SCALE, final_hop.amount_in);
        if rate > best_rate {
            best_rate = rate;
            best_final = final_hop.clone();
        }
    }

    let effective_rate = simulate_price_impact_u256(total_at_merge, best_final.pool_liquidity);
    let merged_amount_out = mul_div(total_at_merge, effective_rate, SCALE);
    let merged_gas =
        (best_final.gas * U256::from(MERGED_GAS_NUMERATOR)) / U256::from(MERGED_GAS_DENOMINATOR);
    let last_intermediate = first_route.hops[first_route.hops.len() - 2].to_token;

    let merged_final = Hop {
        dex: best_final.dex,
        from_token: last_intermediate,
        to_token: final_token,
        amount_in: total_at_merge,
        amount_out: merged_amount_out,
        gas: merged_gas,
        pool_liquidity: best_final.pool_liquidity,
    };

    let mut merged_hops = first_route.hops.clone();
    let last = merged_hops.len() - 1;
    merged_hops[last] = merged_final;
    let merged_route = make_route(merged_hops);

    let mut original_best_output = U256::ZERO;
    let mut original_total_gas = U256::ZERO;
    for index in indexes {
        let route = &routes[*index];
        if route.total_output > original_best_output {
            original_best_output = route.total_output;
        }
        original_total_gas += route.total_gas;
    }

    let group = MergedGroup {
        signature_hash: sig,
        merged_count: U256::from(indexes.len()),
        merged_amount_at_intermediate: total_at_merge,
        merged_output: merged_amount_out,
        original_best_output,
        merged_gas: merged_route.total_gas,
        original_total_gas,
    };

    (merged_route, group)
}

fn mul_div(x: U256, y: U256, denominator: U256) -> U256 {
    x.checked_mul(y)
        .expect("StepMerging multiplication overflow")
        / denominator
}
