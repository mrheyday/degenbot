use alloy::primitives::U256;
use crate::monitor::MatchCandidate;

pub const SCALE: U256 = U256::from_limbs([1_000_000_000_000_000_000, 0, 0, 0]); // 1e18

pub fn outbound_min_price(o: &MatchCandidate) -> U256 {
    if o.amount_sell.is_zero() {
        return U256::ZERO;
    }
    (o.amount_buy_min * SCALE) / o.amount_sell
}

pub fn counter_max_price(c: &MatchCandidate) -> U256 {
    if c.amount_buy_min.is_zero() {
        return U256::ZERO;
    }
    (c.amount_sell * SCALE) / c.amount_buy_min
}

pub fn is_opposing_pair(o: &MatchCandidate, c: &MatchCandidate) -> bool {
    o.pair_sell == c.pair_buy && o.pair_buy == c.pair_sell
}

pub fn is_price_compatible(o: &MatchCandidate, c: &MatchCandidate) -> bool {
    if !is_opposing_pair(o, c) {
        return false;
    }
    outbound_min_price(o) <= counter_max_price(c)
}

pub fn clearing_price(o: &MatchCandidate, c: &MatchCandidate) -> U256 {
    let lo = outbound_min_price(o);
    let hi = counter_max_price(c);
    (lo + hi) / U256::from(2)
}

pub fn fill_amount(o: &MatchCandidate, c: &MatchCandidate) -> U256 {
    let c_max = counter_max_price(c);
    let c_budget_in_o_sell = (c.amount_buy_min * c_max) / SCALE;
    std::cmp::min(o.amount_sell, c_budget_in_o_sell)
}
