#![cfg_attr(
    not(any(test, feature = "export-abi", feature = "native-test")),
    no_main
)]
#![cfg_attr(feature = "contract-client-gen", allow(unused_imports))]

extern crate alloc;

#[path = "../../core/src/runtime_adapter.rs"]
pub mod runtime_adapter;

#[cfg(all(not(any(test, feature = "native-test")), not(target_arch = "wasm32")))]
mod native_hostio_shims {
    include!("../../test_hostio_shims.rs");
}

#[cfg(not(any(test, feature = "native-test")))]
use stylus_sdk::{
    alloy_primitives::{Address, FixedBytes, U256},
    prelude::*,
};

#[cfg(not(any(test, feature = "native-test")))]
sol_storage! {
    #[entrypoint]
    pub struct RuntimeAdapterProof {}
}

#[cfg(not(any(test, feature = "native-test")))]
#[public]
impl RuntimeAdapterProof {
    pub fn runtime_lane_count(&self) -> u8 {
        9
    }

    pub fn runtime_adapter_domain_separator(&self) -> FixedBytes<32> {
        runtime_adapter::domain_separator()
    }

    pub fn runtime_callback_auth_code(
        &self,
        lane: u8,
        msg_sender: Address,
        expected_lender: Address,
        expected_v3_pool: Address,
        expected_reactor: Address,
        initiator: Address,
        executor: Address,
        canonical_sender: Address,
        active_plan_hash: FixedBytes<32>,
        expected_plan_hash: FixedBytes<32>,
        require_plan_hash: bool,
    ) -> u8 {
        runtime_adapter::error_code(runtime_adapter::validate_callback_auth(
            runtime_adapter::CallbackAuthProof {
                lane,
                msg_sender,
                expected_lender,
                expected_v3_pool,
                expected_reactor,
                initiator,
                executor,
                canonical_sender,
                active_plan_hash,
                expected_plan_hash,
                require_plan_hash,
            },
        ))
    }

    pub fn runtime_flash_settlement_code(
        &self,
        flash_token: Address,
        callback_token: Address,
        flash_amount: U256,
        callback_amount: U256,
        premium: U256,
        balance_on_callback: U256,
        balance_before_repay: U256,
        min_profit: U256,
        reject_idle_balance: bool,
    ) -> u8 {
        match runtime_adapter::validate_flash_settlement(runtime_adapter::FlashSettlementProof {
            flash_token,
            callback_token,
            flash_amount,
            callback_amount,
            premium,
            balance_on_callback,
            balance_before_repay,
            min_profit,
            reject_idle_balance,
        }) {
            Ok(_) => 0,
            Err(error) => error as u8,
        }
    }

    pub fn runtime_flash_settlement_profit_or_zero(
        &self,
        flash_token: Address,
        callback_token: Address,
        flash_amount: U256,
        callback_amount: U256,
        premium: U256,
        balance_on_callback: U256,
        balance_before_repay: U256,
        min_profit: U256,
        reject_idle_balance: bool,
    ) -> U256 {
        runtime_adapter::settlement_profit_or_zero(runtime_adapter::FlashSettlementProof {
            flash_token,
            callback_token,
            flash_amount,
            callback_amount,
            premium,
            balance_on_callback,
            balance_before_repay,
            min_profit,
            reject_idle_balance,
        })
    }

    pub fn runtime_approval_code(
        &self,
        token: Address,
        spender: Address,
        spender_allowed: bool,
    ) -> u8 {
        runtime_adapter::error_code(runtime_adapter::validate_runtime_approval(
            runtime_adapter::RuntimeApprovalProof {
                token,
                spender,
                spender_allowed,
            },
        ))
    }

    pub fn runtime_call_code(
        &self,
        target: Address,
        selector: FixedBytes<4>,
        target_allowed: bool,
        selector_allowed: bool,
        value: U256,
        native_value_limit: U256,
    ) -> u8 {
        let mut selector_bytes = [0_u8; 4];
        selector_bytes.copy_from_slice(selector.as_slice());
        runtime_adapter::error_code(runtime_adapter::validate_runtime_call(
            runtime_adapter::RuntimeCallProof {
                target,
                selector: selector_bytes,
                target_allowed,
                selector_allowed,
                value,
                native_value_limit,
            },
        ))
    }

    pub fn runtime_execution_receipt_digest(
        &self,
        lane: u8,
        flow_id: FixedBytes<32>,
        plan_hash: FixedBytes<32>,
        flash_token: Address,
        flash_amount: U256,
        premium: U256,
        min_profit: U256,
        profit: U256,
    ) -> FixedBytes<32> {
        runtime_adapter::execution_receipt_digest(runtime_adapter::ExecutionReceiptProof {
            lane,
            flow_id,
            plan_hash,
            flash_token,
            flash_amount,
            premium,
            min_profit,
            profit,
        })
    }
}
