use alloy::sol_types::SolCall;
use degenbot_rs::contract_bindings;
use degenbot_rs::types::executor::{
    composeFourLegCall, executeNativeArbCall, matchInternalCall, transferToSettlementCall,
    triggerCoWFlashLoanRouterCall,
};

#[test]
fn generated_executor_bindings_are_wired_into_degenbot_rs() {
    use contract_bindings::executor::Executor;

    assert_eq!(
        Executor::executeNativeArbCall::SELECTOR,
        executeNativeArbCall::SELECTOR,
    );
    assert_eq!(
        Executor::matchInternalCall::SELECTOR,
        matchInternalCall::SELECTOR,
    );
    assert_eq!(
        Executor::composeFourLegCall::SELECTOR,
        composeFourLegCall::SELECTOR,
    );
    assert_eq!(
        Executor::triggerCoWFlashLoanRouterCall::SELECTOR,
        triggerCoWFlashLoanRouterCall::SELECTOR,
    );
    assert_eq!(
        Executor::transferToSettlementCall::SELECTOR,
        transferToSettlementCall::SELECTOR,
    );
}

#[test]
fn generated_selected_binding_set_exposes_hot_path_modules() {
    assert_eq!(25, contract_bindings::SELECTED_CONTRACT_BINDING_COUNT);
    assert_eq!(
        [0x98, 0xb6, 0xd7, 0xda],
        contract_bindings::multi_hop_caller::MultiHopCaller::swapWithAutoSlippageCall::SELECTOR,
    );
    assert_eq!(
        [0x80, 0x8c, 0x50, 0xc4],
        <contract_bindings::router_registry::RouterRegistry::UnknownRouterKind as alloy::sol_types::SolError>::SELECTOR,
    );
}
