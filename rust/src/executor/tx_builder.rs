//! Plan → EIP-1559 `TransactionRequest`.
//!
//! Honours `Plan.gas_envelope` as the upper bound; the engine MAY tighten
//! the priority fee toward observed prevailing tip (via
//! `super::gas::tighten`) but MUST NOT exceed the strategist's caps.
//! `Plan.gas_limit` is taken verbatim — pre-flight has already verified
//! simulated gas usage against this number.

use alloy::network::TransactionBuilder;
use alloy::rpc::types::TransactionRequest;

use crate::monitor::Plan;

/// Materialise a Plan into the alloy `TransactionRequest` shape. Pure
/// function; no I/O. Nonce + chainId are set separately by the caller after
/// querying the nonce cache and provider.
pub fn build_tx_request(plan: &Plan) -> TransactionRequest {
    TransactionRequest::default()
        .with_to(plan.target)
        .with_input(plan.calldata.clone())
        .with_value(plan.value)
        .with_gas_limit(plan.gas_limit)
        .with_max_fee_per_gas(plan.gas_envelope.max_fee_per_gas_wei.to::<u128>())
        .with_max_priority_fee_per_gas(plan.gas_envelope.max_priority_fee_per_gas_wei.to::<u128>())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{GasEnvelope, Lane, Plan, PlanKind};
    use alloy::primitives::{address, b256, bytes, I256, U256};

    fn sample_plan() -> Plan {
        Plan {
            trace_id: "x".to_string(),
            opportunity_id: "x".to_string(),
            admission_hash: Some(b256!(
                "ad00000000000000000000000000000000000000000000000000000000000001"
            )),
            kind: PlanKind::NativeArb,
            target: address!("794a61358D6845594F94dc1DB02A252b5b4814aD"),
            calldata: bytes!("a9059cbb"),
            value: U256::from(123_u64),
            gas_limit: 800_000,
            gas_envelope: GasEnvelope {
                max_fee_per_gas_wei: U256::from(2_000_000_000_u64),
                max_priority_fee_per_gas_wei: U256::from(100_000_000_u64),
            },
            deadline_ms: 1_715_500_000_000,
            require_preflight: true,
            expected_balance_delta_floor: I256::ZERO,
            profit_token: address!("82aF49447D8a07e3bd95BD0d56f35241523fBab1"),
            submission_lane: Lane::Default,
            timeboost_bid_wei: None,
            dry_run: false,
            eip7702: None,
        }
    }

    #[test]
    fn builds_tx_request_from_plan_fields() {
        let plan = sample_plan();
        let tx = build_tx_request(&plan);

        // Target maps to `to` field.
        assert_eq!(tx.to.unwrap().to().copied(), Some(plan.target));
        // Value transferred verbatim.
        assert_eq!(tx.value, Some(plan.value));
        // Gas limit transferred verbatim.
        assert_eq!(tx.gas, Some(plan.gas_limit));
        // EIP-1559 fee fields set from the envelope.
        assert_eq!(
            tx.max_fee_per_gas,
            Some(plan.gas_envelope.max_fee_per_gas_wei.to::<u128>())
        );
        assert_eq!(
            tx.max_priority_fee_per_gas,
            Some(plan.gas_envelope.max_priority_fee_per_gas_wei.to::<u128>())
        );
        // Calldata round-trips.
        assert_eq!(tx.input.input.as_ref(), Some(&plan.calldata));
    }
}
