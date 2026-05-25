use alloy::primitives::U256;
use serde::{Deserialize, Serialize};
use std::cmp::min;

use crate::monitor::{AggregatorQuote, Opportunity};

pub const SANDOOSCORE_SCALE: U256 = U256::from_limbs([1_000_000, 0, 0, 0]);
pub const GWEI_IN_WEI: U256 = U256::from_limbs([1_000_000_000, 0, 0, 0]);
pub const HUNDRED_PERCENT_BPS: U256 = U256::from_limbs([10_000, 0, 0, 0]);

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SandooIdeaComponents {
    pub estimated_profit_wei: U256,
    pub safe_size_wei: U256,
    pub quote_amount_out: U256,
    pub quote_amount_net_out: U256,
    pub route_gas_wei: U256,
    pub quote_fee_wei: U256,
    pub flash_loan_fee_wei: U256,
    pub net_profit_after_cost_wei: U256,
    pub size_vs_flash_ratio_bps: U256,
    pub quote_profit_gap_wei: U256,
    pub score_scale: U256,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SandooIdeaSignal {
    pub eligible: bool,
    pub score: U256,
    pub reasons: Vec<String>,
    pub components: SandooIdeaComponents,
}

pub fn evaluate_sandoo_idea(
    opp: &Opportunity,
    best_quote: Option<&AggregatorQuote>,
    max_gas_price_gwei: u64,
    flash_loan_fee_wei: U256,
) -> SandooIdeaSignal {
    let mut reasons = Vec::new();

    if opp.flash_amount.is_zero() {
        return build_negative_signal(
            opp,
            best_quote,
            U256::ZERO,
            "zero_flash_amount",
            max_gas_price_gwei,
            flash_loan_fee_wei,
            U256::ZERO,
        );
    }

    let safe_size_wei = min(opp.amount_in, opp.flash_amount);
    if safe_size_wei.is_zero() {
        return build_negative_signal(
            opp,
            best_quote,
            safe_size_wei,
            "safe_size_zero",
            max_gas_price_gwei,
            flash_loan_fee_wei,
            U256::ZERO,
        );
    }

    if opp.estimated_profit_wei.is_zero() {
        return build_negative_signal(
            opp,
            best_quote,
            safe_size_wei,
            "non_positive_estimated_profit",
            max_gas_price_gwei,
            flash_loan_fee_wei,
            U256::ZERO,
        );
    }

    let quote_amount_out = best_quote.map(|q| q.amount_out).unwrap_or(U256::ZERO);
    let quote_amount_net_out = if quote_amount_out > opp.amount_in {
        quote_amount_out - opp.amount_in
    } else {
        U256::ZERO
    };

    let max_gas_fee_wei = U256::from(max_gas_price_gwei) * GWEI_IN_WEI;
    let route_gas_wei = if let Some(q) = best_quote {
        U256::from(q.estimated_gas) * max_gas_fee_wei
    } else {
        U256::ZERO
    };

    let quote_fee_wei = if let Some(q) = best_quote {
        (opp.amount_in * U256::from(q.fee_bps)) / HUNDRED_PERCENT_BPS
    } else {
        U256::ZERO
    };

    let total_cost = route_gas_wei + quote_fee_wei + flash_loan_fee_wei;
    let net_profit_after_cost_wei = if opp.estimated_profit_wei > total_cost {
        opp.estimated_profit_wei - total_cost
    } else {
        U256::ZERO
    };

    if net_profit_after_cost_wei.is_zero() {
        return build_negative_signal(
            opp,
            best_quote,
            safe_size_wei,
            "cost_after_profit_not_positive",
            max_gas_price_gwei,
            flash_loan_fee_wei,
            net_profit_after_cost_wei,
        );
    }

    let size_vs_flash_ratio_bps = if opp.amount_in > U256::ZERO {
        (safe_size_wei * HUNDRED_PERCENT_BPS) / opp.amount_in
    } else {
        U256::ZERO
    };

    if size_vs_flash_ratio_bps < HUNDRED_PERCENT_BPS {
        reasons.push("flash_amount_caps_execution_size".to_string());
    }

    let quote_profit_gap_wei = if let Some(_) = best_quote {
        if opp.token_in == opp.token_out {
            if quote_amount_net_out > opp.estimated_profit_wei {
                quote_amount_net_out - opp.estimated_profit_wei
            } else {
                U256::ZERO
            }
        } else {
            U256::ZERO
        }
    } else {
        U256::ZERO
    };

    if !quote_profit_gap_wei.is_zero() {
        reasons.push("quote_outperforms_candidate_profit".to_string());
    }

    let score = (net_profit_after_cost_wei * SANDOOSCORE_SCALE) / safe_size_wei;
    if !size_vs_flash_ratio_bps.is_zero() && score.is_zero() {
        reasons.push("positive_profit_lost_to_size_rounding".to_string());
    } else if !score.is_zero() {
        reasons.push("candidate_has_positive_adj_profit".to_string());
    }

    SandooIdeaSignal {
        eligible: true,
        score,
        reasons,
        components: SandooIdeaComponents {
            estimated_profit_wei: opp.estimated_profit_wei,
            safe_size_wei,
            quote_amount_out,
            quote_amount_net_out,
            route_gas_wei,
            quote_fee_wei,
            flash_loan_fee_wei,
            net_profit_after_cost_wei,
            size_vs_flash_ratio_bps,
            quote_profit_gap_wei,
            score_scale: SANDOOSCORE_SCALE,
        },
    }
}

fn build_negative_signal(
    opp: &Opportunity,
    best_quote: Option<&AggregatorQuote>,
    safe_size_wei: U256,
    reason: &str,
    max_gas_price_gwei: u64,
    flash_loan_fee_wei: U256,
    net_profit_after_cost_wei: U256,
) -> SandooIdeaSignal {
    let max_gas_fee_wei = U256::from(max_gas_price_gwei) * GWEI_IN_WEI;
    let route_gas_wei = if let Some(q) = best_quote {
        U256::from(q.estimated_gas) * max_gas_fee_wei
    } else {
        U256::ZERO
    };

    let quote_fee_wei = if let Some(q) = best_quote {
        (opp.amount_in * U256::from(q.fee_bps)) / HUNDRED_PERCENT_BPS
    } else {
        U256::ZERO
    };

    let quote_amount_out = best_quote.map(|q| q.amount_out).unwrap_or(U256::ZERO);
    let quote_amount_net_out = if quote_amount_out > opp.amount_in {
        quote_amount_out - opp.amount_in
    } else {
        U256::ZERO
    };

    let size_vs_flash_ratio_bps = if opp.amount_in > U256::ZERO {
        (safe_size_wei * HUNDRED_PERCENT_BPS) / opp.amount_in
    } else {
        U256::ZERO
    };

    SandooIdeaSignal {
        eligible: false,
        score: U256::ZERO,
        reasons: vec![reason.to_string()],
        components: SandooIdeaComponents {
            estimated_profit_wei: opp.estimated_profit_wei,
            safe_size_wei,
            quote_amount_out,
            quote_amount_net_out,
            route_gas_wei,
            quote_fee_wei,
            flash_loan_fee_wei,
            net_profit_after_cost_wei,
            size_vs_flash_ratio_bps,
            quote_profit_gap_wei: U256::ZERO,
            score_scale: SANDOOSCORE_SCALE,
        },
    }
}
