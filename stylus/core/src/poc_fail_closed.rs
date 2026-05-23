//! Stylus parity for Solidity research POC safety gates.
//!
//! Five of the six `contracts/src/poc` artifacts are intentionally fail-closed.
//! The Comet artifact is an owner-gated research primitive, so this module ports
//! its deterministic address and parameter guards while leaving token movement
//! behind the runtime migration gate.

use alloy_primitives::address;
use stylus_sdk::alloy_primitives::{Address, U256};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum PocKind {
    CometLiquidator = 0,
    CompoundSilo = 1,
    DolomiteGeneric = 2,
    EulerV2Evc = 3,
    PendleLimitOrderV4 = 4,
    PendlePySy = 5,
}

impl PocKind {
    pub fn from_u8(value: u8) -> Option<Self> {
        match value {
            0 => Some(Self::CometLiquidator),
            1 => Some(Self::CompoundSilo),
            2 => Some(Self::DolomiteGeneric),
            3 => Some(Self::EulerV2Evc),
            4 => Some(Self::PendleLimitOrderV4),
            5 => Some(Self::PendlePySy),
            _ => None,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CometValidationError {
    DeadlinePassed,
    UnsupportedComet,
    InvalidParams,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct PromotionEvidence {
    pub top_markets_fork_verified: bool,
    pub router_quote_reproduced: bool,
    pub raw_fair_value_proven: bool,
    pub swap_back_proven: bool,
    pub flash_settlement_proven: bool,
    pub net_profit_proven: bool,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct CometStaticPlan {
    pub now: U256,
    pub comet: Address,
    pub collateral: Address,
    pub base_amount: U256,
    pub borrower_count: U256,
    pub swap_path_len: U256,
    pub amount_out_minimum: U256,
    pub min_profit: U256,
    pub deadline: U256,
}

pub const ARBITRUM_ONE_CHAIN_ID: u64 = 42_161;

pub const COMET_BALANCER_V3_VAULT: Address = address!("bA1333333333a1BA1108E8412f11850A5C319bA9");
pub const COMET_UNIV3_ROUTER02: Address = address!("68b3465833fb72A70ecDF485E0e4C7bD8665Fc45");
pub const COMET_USDC: Address = address!("9c4ec768c28520B50860ea7a15bd7213a9fF58bf");
pub const COMET_WETH: Address = address!("6f7D514bbD4aFf3BcD1140B7344b32f063dEe486");
pub const COMET_USDC_E: Address = address!("A5EDBDD9646f8dFF606d7448e414884C7d905dCA");
pub const COMET_USDT: Address = address!("d98Be00b5D27fc98112BdE293e487f8D4cA57d07");
pub const KAIROS_PAYMENT_RECIPIENT: Address = address!("60E6a31591392f926e627ED871e670C3e81f1AB8");

pub const USDC: Address = address!("af88d065e77c8cC2239327C5EDb3A432268e5831");
pub const WETH: Address = address!("82aF49447D8a07e3bd95BD0d56f35241523fBab1");
pub const WBTC: Address = address!("2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f");

pub const COMPOUND_SILO_SOURCE_COUNT: u64 = 7;
pub const COMPOUND_SILO_UNRESOLVED_GATE_COUNT: u64 = 8;

pub const EULER_EVC: Address = address!("6302ef0F34100CDDFb5489fbcB6eE1AA95CD1066");
pub const EULER_GOVERNED_PERSPECTIVE: Address =
    address!("c7693ceEf74Bc7c8Af703c5519F24bB5e6642643");
pub const EULER_EXTERNAL_VAULT_REGISTRY: Address =
    address!("FB13aa1d7CFe1C85826f9D5e571589B13b785A6e");
pub const EULER_SWAPPER: Address = address!("4AaA129FaD81a65Dab41b1fa7e964CBB9B30C848");
pub const EULER_SWAP_VERIFIER: Address = address!("cB4cbC3128b38d6Ca46b7676D2389fAfa6009c1f");

pub const EVC_BATCH_SELECTOR: [u8; 4] = [0xc1, 0x6a, 0xe7, 0xa4];
pub const EVC_ENABLE_CONTROLLER_SELECTOR: [u8; 4] = [0xc3, 0x68, 0x51, 0x6c];
pub const EVC_ENABLE_COLLATERAL_SELECTOR: [u8; 4] = [0xd4, 0x4f, 0xee, 0x5a];
pub const EVC_DISABLE_COLLATERAL_SELECTOR: [u8; 4] = [0xe9, 0x20, 0xe8, 0xe0];
pub const EVC_DISABLE_CONTROLLER_SELECTOR: [u8; 4] = [0xf4, 0xfc, 0x35, 0x70];
pub const EVAULT_CHECK_LIQUIDATION_SELECTOR: [u8; 4] = [0x88, 0xaa, 0x6f, 0x12];
pub const EVAULT_LIQUIDATE_SELECTOR: [u8; 4] = [0xc1, 0x34, 0x25, 0x74];
pub const EVAULT_REDEEM_SELECTOR: [u8; 4] = [0xba, 0x08, 0x76, 0x52];

pub const DOLOMITE_MARGIN: Address = address!("6Bd780E7fDf01D77e4d475c821f1e7AE05409072");
pub const DOLOMITE_EXPIRY_TRADER: Address = address!("DEc1ae3b570ac3c57871BBD7bFeacC807f973Bea");
pub const DOLOMITE_EXPIRY_PROXY: Address = address!("40899E265A7899968f0f153410321B9175730B00");
pub const DOLOMITE_GENERIC_TRADER_PROXY_V1: Address =
    address!("905F3adD52F01A9069218c8D1c11E240afF61D2B");
pub const DOLOMITE_LIQUIDATOR_PROXY_V4_WITH_GENERIC_TRADER: Address =
    address!("34975624E992bF5c094EF0CF3344660f7AaB9CB3");
pub const DOLOMITE_MISSING_GATE_COUNT: u64 = 3;

pub const PENDLE_LIMIT_ROUTER: Address = address!("000000000000c9B3E2C3Ec88B1B4c0cD853f4321");
pub const PENDLE_ROUTER: Address = address!("888888888889758F76e7103c6CbF23ABbF58F946");
pub const PENDLE_ROUTER_STATIC: Address = address!("AdB09F65bd90d19e3148D9ccb693F3161C6DB3E8");
pub const UNISWAP_V4_POOL_MANAGER: Address = address!("360E68faCcca8cA495c1B759Fd9EEe466db9FB32");
pub const UNISWAP_UNIVERSAL_ROUTER: Address = address!("A51afAFe0263b40EdaEf0Df8781eA9aa03E381a3");
pub const PERMIT2: Address = address!("000000000022D473030F116dDEE9F6B43aC78BA3");

pub const BEFORE_SWAP_FLAG: u16 = 1 << 7;
pub const AFTER_SWAP_FLAG: u16 = 1 << 6;
pub const BEFORE_SWAP_RETURNS_DELTA_FLAG: u16 = 1 << 3;
pub const AFTER_SWAP_RETURNS_DELTA_FLAG: u16 = 1 << 2;
pub const SWAP_AFFECTING_HOOK_MASK: u16 = BEFORE_SWAP_FLAG
    | AFTER_SWAP_FLAG
    | BEFORE_SWAP_RETURNS_DELTA_FLAG
    | AFTER_SWAP_RETURNS_DELTA_FLAG;

pub const SELECTOR_MINT_PY_FROM_SY: [u8; 4] = [0x1a, 0x86, 0x31, 0xb2];
pub const SELECTOR_REDEEM_PY_TO_SY: [u8; 4] = [0x33, 0x97, 0x48, 0xcb];
pub const SELECTOR_SWAP_EXACT_SY_FOR_PT: [u8; 4] = [0xec, 0x2c, 0x0f, 0x5e];
pub const SELECTOR_SWAP_EXACT_SY_FOR_YT: [u8; 4] = [0x67, 0xa1, 0x7d, 0xdd];
pub const SELECTOR_SWAP_EXACT_PT_FOR_SY: [u8; 4] = [0x62, 0x8d, 0x71, 0xe1];
pub const SELECTOR_SWAP_EXACT_YT_FOR_SY: [u8; 4] = [0x16, 0xce, 0x7d, 0x6c];

pub const GATE_TOP_MARKETS_FORK_VERIFIED: u64 = 1 << 0;
pub const GATE_ROUTER_QUOTE_REPRODUCED: u64 = 1 << 1;
pub const GATE_RAW_FAIR_VALUE_PROVEN: u64 = 1 << 2;
pub const GATE_SWAP_BACK_PROVEN: u64 = 1 << 3;
pub const GATE_FLASH_SETTLEMENT_PROVEN: u64 = 1 << 4;
pub const GATE_NET_PROFIT_PROVEN: u64 = 1 << 5;
pub const PENDLE_PY_SY_MISSING_GATES: u64 = GATE_TOP_MARKETS_FORK_VERIFIED
    | GATE_ROUTER_QUOTE_REPRODUCED
    | GATE_RAW_FAIR_VALUE_PROVEN
    | GATE_SWAP_BACK_PROVEN
    | GATE_FLASH_SETTLEMENT_PROVEN
    | GATE_NET_PROFIT_PROVEN;

pub const STRATEGY_CONFIRMED_SELECTOR: [u8; 4] = [0x89, 0x4e, 0xe8, 0x3d];
pub const EXECUTE_BYTES_SELECTOR: [u8; 4] = [0x09, 0xc5, 0xea, 0xbe];
pub const COMPOUND_SILO_EXECUTE_COMPOUND_SELECTOR: [u8; 4] = [0x4f, 0xce, 0xf0, 0xf1];
pub const COMPOUND_SILO_EXECUTE_SILO_SELECTOR: [u8; 4] = [0xf8, 0xd2, 0x82, 0x3e];
pub const EULER_RECEIVE_FLASH_LOAN_SELECTOR: [u8; 4] = [0x95, 0x8f, 0xa2, 0x80];
pub const PENDLE_LIMIT_CALLBACK_SELECTOR: [u8; 4] = [0xeb, 0x3a, 0x7d, 0x47];
pub const PENDLE_VALIDATE_PROMOTION_EVIDENCE_SELECTOR: [u8; 4] = [0xff, 0x14, 0x04, 0x85];

#[must_use]
pub fn is_fail_closed(kind: PocKind) -> bool {
    !matches!(kind, PocKind::CometLiquidator)
}

#[must_use]
pub fn strategy_confirmed(kind: PocKind) -> bool {
    match kind {
        PocKind::CometLiquidator => false,
        PocKind::CompoundSilo
        | PocKind::DolomiteGeneric
        | PocKind::EulerV2Evc
        | PocKind::PendleLimitOrderV4
        | PocKind::PendlePySy => false,
    }
}

#[must_use]
pub fn missing_gate_count(kind: PocKind) -> U256 {
    let count = match kind {
        PocKind::CometLiquidator => 0,
        PocKind::CompoundSilo => COMPOUND_SILO_UNRESOLVED_GATE_COUNT,
        PocKind::DolomiteGeneric => DOLOMITE_MISSING_GATE_COUNT,
        PocKind::EulerV2Evc => 5,
        PocKind::PendleLimitOrderV4 => 4,
        PocKind::PendlePySy => 6,
    };
    U256::from(count)
}

#[must_use]
pub fn requires_hook_classification(hook: Address) -> bool {
    let low_bits = u16::from_be_bytes([hook.as_slice()[18], hook.as_slice()[19]]);
    (low_bits & SWAP_AFFECTING_HOOK_MASK) != 0
}

#[must_use]
pub fn pendle_py_sy_missing_gates(evidence: PromotionEvidence) -> U256 {
    let mut missing = 0u64;
    if !evidence.top_markets_fork_verified {
        missing |= GATE_TOP_MARKETS_FORK_VERIFIED;
    }
    if !evidence.router_quote_reproduced {
        missing |= GATE_ROUTER_QUOTE_REPRODUCED;
    }
    if !evidence.raw_fair_value_proven {
        missing |= GATE_RAW_FAIR_VALUE_PROVEN;
    }
    if !evidence.swap_back_proven {
        missing |= GATE_SWAP_BACK_PROVEN;
    }
    if !evidence.flash_settlement_proven {
        missing |= GATE_FLASH_SETTLEMENT_PROVEN;
    }
    if !evidence.net_profit_proven {
        missing |= GATE_NET_PROFIT_PROVEN;
    }
    U256::from(missing)
}

#[must_use]
pub fn is_supported_comet(comet: Address) -> bool {
    comet == COMET_USDC || comet == COMET_WETH || comet == COMET_USDC_E || comet == COMET_USDT
}

pub fn validate_comet_static_plan(plan: CometStaticPlan) -> Result<(), CometValidationError> {
    if plan.now > plan.deadline {
        return Err(CometValidationError::DeadlinePassed);
    }
    if !is_supported_comet(plan.comet) {
        return Err(CometValidationError::UnsupportedComet);
    }
    let Some(required_output) = plan.base_amount.checked_add(plan.min_profit) else {
        return Err(CometValidationError::InvalidParams);
    };
    if plan.collateral == Address::ZERO
        || plan.base_amount == U256::ZERO
        || plan.borrower_count == U256::ZERO
        || plan.swap_path_len < U256::from(43)
        || plan.min_profit == U256::ZERO
        || plan.amount_out_minimum < required_output
    {
        return Err(CometValidationError::InvalidParams);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn poc_kind_ordinals_are_stable() {
        assert_eq!(Some(PocKind::CometLiquidator), PocKind::from_u8(0));
        assert_eq!(Some(PocKind::PendlePySy), PocKind::from_u8(5));
        assert_eq!(None, PocKind::from_u8(6));
    }

    #[test]
    fn fail_closed_strategy_status_matches_solidity_pocs() {
        for kind in [
            PocKind::CompoundSilo,
            PocKind::DolomiteGeneric,
            PocKind::EulerV2Evc,
            PocKind::PendleLimitOrderV4,
            PocKind::PendlePySy,
        ] {
            assert!(is_fail_closed(kind));
            assert!(!strategy_confirmed(kind));
            assert!(missing_gate_count(kind) > U256::ZERO);
        }
        assert!(!is_fail_closed(PocKind::CometLiquidator));
    }

    #[test]
    fn poc_selectors_match_solidity_artifacts() {
        assert_eq!([0x89, 0x4e, 0xe8, 0x3d], STRATEGY_CONFIRMED_SELECTOR);
        assert_eq!([0x09, 0xc5, 0xea, 0xbe], EXECUTE_BYTES_SELECTOR);
        assert_eq!(
            [0x4f, 0xce, 0xf0, 0xf1],
            COMPOUND_SILO_EXECUTE_COMPOUND_SELECTOR
        );
        assert_eq!(
            [0xf8, 0xd2, 0x82, 0x3e],
            COMPOUND_SILO_EXECUTE_SILO_SELECTOR
        );
        assert_eq!([0x95, 0x8f, 0xa2, 0x80], EULER_RECEIVE_FLASH_LOAN_SELECTOR);
        assert_eq!([0xeb, 0x3a, 0x7d, 0x47], PENDLE_LIMIT_CALLBACK_SELECTOR);
        assert_eq!(
            [0xff, 0x14, 0x04, 0x85],
            PENDLE_VALIDATE_PROMOTION_EVIDENCE_SELECTOR
        );
    }

    #[test]
    fn pendle_hook_classification_matches_v4_low_bit_model() {
        assert!(!requires_hook_classification(address!(
            "0000000000000000000000000000000000000000"
        )));
        assert!(requires_hook_classification(address!(
            "0000000000000000000000000000000000000080"
        )));
        assert!(requires_hook_classification(address!(
            "0000000000000000000000000000000000000040"
        )));
        assert!(requires_hook_classification(address!(
            "0000000000000000000000000000000000000008"
        )));
        assert!(requires_hook_classification(address!(
            "0000000000000000000000000000000000000004"
        )));
        assert!(!requires_hook_classification(address!(
            "0000000000000000000000000000000000000002"
        )));
    }

    #[test]
    fn pendle_py_sy_evidence_bitmask_matches_solidity() {
        let missing = pendle_py_sy_missing_gates(PromotionEvidence {
            top_markets_fork_verified: false,
            router_quote_reproduced: false,
            raw_fair_value_proven: false,
            swap_back_proven: false,
            flash_settlement_proven: false,
            net_profit_proven: false,
        });
        assert_eq!(U256::from(PENDLE_PY_SY_MISSING_GATES), missing);

        let complete = pendle_py_sy_missing_gates(PromotionEvidence {
            top_markets_fork_verified: true,
            router_quote_reproduced: true,
            raw_fair_value_proven: true,
            swap_back_proven: true,
            flash_settlement_proven: true,
            net_profit_proven: true,
        });
        assert_eq!(U256::ZERO, complete);
    }

    #[test]
    fn comet_static_validation_matches_solidity_pre_external_guards() {
        assert!(is_supported_comet(COMET_USDC));
        assert!(is_supported_comet(COMET_WETH));
        assert!(is_supported_comet(COMET_USDC_E));
        assert!(is_supported_comet(COMET_USDT));
        assert!(!is_supported_comet(address!(
            "1111111111111111111111111111111111111111"
        )));

        let valid = validate_comet_static_plan(CometStaticPlan {
            now: U256::from(100),
            comet: COMET_USDC,
            collateral: WETH,
            base_amount: U256::from(1_000),
            borrower_count: U256::from(1),
            swap_path_len: U256::from(43),
            amount_out_minimum: U256::from(1_100),
            min_profit: U256::from(100),
            deadline: U256::from(101),
        });
        assert_eq!(Ok(()), valid);

        assert_eq!(
            Err(CometValidationError::DeadlinePassed),
            validate_comet_static_plan(CometStaticPlan {
                now: U256::from(102),
                comet: COMET_USDC,
                collateral: WETH,
                base_amount: U256::from(1_000),
                borrower_count: U256::from(1),
                swap_path_len: U256::from(43),
                amount_out_minimum: U256::from(1_100),
                min_profit: U256::from(100),
                deadline: U256::from(101),
            })
        );
        assert_eq!(
            Err(CometValidationError::UnsupportedComet),
            validate_comet_static_plan(CometStaticPlan {
                now: U256::from(100),
                comet: address!("1111111111111111111111111111111111111111"),
                collateral: WETH,
                base_amount: U256::from(1_000),
                borrower_count: U256::from(1),
                swap_path_len: U256::from(43),
                amount_out_minimum: U256::from(1_100),
                min_profit: U256::from(100),
                deadline: U256::from(101),
            })
        );
        assert_eq!(
            Err(CometValidationError::InvalidParams),
            validate_comet_static_plan(CometStaticPlan {
                now: U256::from(100),
                comet: COMET_USDC,
                collateral: WETH,
                base_amount: U256::from(1_000),
                borrower_count: U256::from(1),
                swap_path_len: U256::from(42),
                amount_out_minimum: U256::from(1_100),
                min_profit: U256::from(100),
                deadline: U256::from(101),
            })
        );
    }
}
