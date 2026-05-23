#![cfg_attr(
    not(any(test, feature = "export-abi", feature = "native-test")),
    no_main
)]
#![cfg_attr(feature = "contract-client-gen", allow(unused_imports))]

extern crate alloc;

pub mod bit_math;
pub mod frontrun_calldata;
pub mod interface_surfaces;
pub mod lib_uniswap;
pub mod lp_transfer_lib;
pub mod mega_mev_optimization;
pub mod router_registry;
pub mod singleton_arrays;
pub mod step_merging;
pub mod token_risk_filter;
pub mod token_standard_ids;
pub mod transient_slots;
pub mod upgrade_policy;

#[cfg(all(not(any(test, feature = "native-test")), not(target_arch = "wasm32")))]
mod native_hostio_shims {
    include!("../../test_hostio_shims.rs");
}

#[cfg(not(any(test, feature = "native-test")))]
use alloy_sol_types::sol;
#[cfg(any(test, not(feature = "native-test")))]
use stylus_sdk::alloy_primitives::FixedBytes;
#[cfg(not(any(test, feature = "native-test")))]
use stylus_sdk::{
    alloy_primitives::{Address, U256},
    prelude::*,
};

#[cfg(not(any(test, feature = "native-test")))]
sol_storage! {
    #[entrypoint]
    pub struct DegenbotStylusCore {}
}

#[cfg(not(any(test, feature = "native-test")))]
sol! {
    error BitMathZeroInput();
    error UnknownRouterKind(uint8 kind);
    error UnknownFlowKind(uint8 kind);
    error DivisionByZero();
    error PowerOfTwoOverflow();
    error MathOverflow();
    error FrontrunCalldataTooShort();
    error FrontrunInvalidReserves();
    error FrontrunInvalidFeeBps(uint256 feeBps);
    error FrontrunInvalidMarginBps(uint256 marginBps);
}

#[cfg(not(any(test, feature = "native-test")))]
#[derive(SolidityError)]
pub enum CoreError {
    BitMathZeroInput(BitMathZeroInput),
    UnknownRouterKind(UnknownRouterKind),
    UnknownFlowKind(UnknownFlowKind),
    DivisionByZero(DivisionByZero),
    PowerOfTwoOverflow(PowerOfTwoOverflow),
    MathOverflow(MathOverflow),
    FrontrunCalldataTooShort(FrontrunCalldataTooShort),
    FrontrunInvalidReserves(FrontrunInvalidReserves),
    FrontrunInvalidFeeBps(FrontrunInvalidFeeBps),
    FrontrunInvalidMarginBps(FrontrunInvalidMarginBps),
}

pub const SOURCE_CONTRACT_COUNT: u64 = 62;

#[cfg(not(any(test, feature = "native-test")))]
#[public]
impl DegenbotStylusCore {
    pub fn source_contract_count(&self) -> U256 {
        U256::from(SOURCE_CONTRACT_COUNT)
    }

    pub fn most_significant_bit(&self, x: U256) -> Result<u8, CoreError> {
        bit_math::most_significant_bit(x)
            .map_err(|_| CoreError::BitMathZeroInput(BitMathZeroInput {}))
    }

    pub fn leading_zeros(&self, x: U256) -> U256 {
        U256::from(bit_math::leading_zeros(x))
    }

    pub fn ierc165_id(&self) -> FixedBytes<4> {
        FixedBytes::from(token_standard_ids::IERC165_ID)
    }

    pub fn ierc1271_id(&self) -> FixedBytes<4> {
        FixedBytes::from(token_standard_ids::IERC1271_ID)
    }

    pub fn ierc721_receiver_id(&self) -> FixedBytes<4> {
        FixedBytes::from(token_standard_ids::IERC721_RECEIVER_ID)
    }

    pub fn ierc1155_receiver_id(&self) -> FixedBytes<4> {
        FixedBytes::from(token_standard_ids::IERC1155_RECEIVER_ID)
    }

    pub fn ierc1155_single_received_ret(&self) -> FixedBytes<4> {
        FixedBytes::from(token_standard_ids::IERC1155_SINGLE_RECEIVED_RET)
    }

    pub fn ierc1155_batch_received_ret(&self) -> FixedBytes<4> {
        FixedBytes::from(token_standard_ids::IERC1155_BATCH_RECEIVED_RET)
    }

    pub fn iaccount_validate_user_op(&self) -> FixedBytes<4> {
        FixedBytes::from(token_standard_ids::IACCOUNT_VALIDATE_USER_OP)
    }

    pub fn ierc3156_flash_borrower_id(&self) -> FixedBytes<4> {
        FixedBytes::from(token_standard_ids::IERC3156_FLASH_BORROWER_ID)
    }

    pub fn permission_id(&self, target: Address, selector: FixedBytes<4>) -> U256 {
        token_standard_ids::permission_id(target, selector)
    }

    pub fn strategy_id(&self, strategy_tag: FixedBytes<32>) -> U256 {
        token_standard_ids::strategy_id(strategy_tag)
    }

    pub fn paymaster_pool_id(&self, pool_tag: FixedBytes<32>) -> U256 {
        token_standard_ids::paymaster_pool_id(pool_tag)
    }

    pub fn inflight_id(&self, asset: Address) -> U256 {
        token_standard_ids::inflight_id(asset)
    }

    pub fn flash_protocol_aave_v3(&self) -> u8 {
        interface_surfaces::FlashProtocol::AaveV3 as u8
    }

    pub fn flash_protocol_morpho_blue(&self) -> u8 {
        interface_surfaces::FlashProtocol::MorphoBlue as u8
    }

    pub fn flash_protocol_erc3156(&self) -> u8 {
        interface_surfaces::FlashProtocol::Erc3156 as u8
    }

    pub fn flash_protocol_uniswap_v3(&self) -> u8 {
        interface_surfaces::FlashProtocol::UniswapV3 as u8
    }

    pub fn flash_protocol_uniswap_v2(&self) -> u8 {
        interface_surfaces::FlashProtocol::UniswapV2 as u8
    }

    pub fn flash_protocol_uniswap_v4(&self) -> u8 {
        interface_surfaces::FlashProtocol::UniswapV4 as u8
    }

    pub fn on_morpho_flash_loan_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(interface_surfaces::ON_MORPHO_FLASH_LOAN)
    }

    pub fn aave_execute_operation_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(interface_surfaces::AAVE_EXECUTE_OPERATION)
    }

    pub fn v3_flash_callback_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(interface_surfaces::V3_FLASH_CALLBACK)
    }

    pub fn v2_flash_callback_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(interface_surfaces::V2_FLASH_CALLBACK)
    }

    pub fn erc3156_on_flash_loan_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(interface_surfaces::ERC3156_ON_FLASH_LOAN)
    }

    pub fn cow_borrower_callback_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(interface_surfaces::COW_BORROWER_CALLBACK)
    }

    pub fn uniswapx_reactor_callback_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(interface_surfaces::UNISWAPX_REACTOR_CALLBACK)
    }

    pub fn permit2_approve_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(interface_surfaces::PERMIT2_APPROVE)
    }

    pub fn permit2_transfer_from_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(interface_surfaces::PERMIT2_TRANSFER_FROM)
    }

    pub fn uniswap_v4_hook_flags(&self, hook: Address) -> U256 {
        U256::from(interface_surfaces::v4_hook_flags(hook))
    }

    pub fn uniswap_v4_has_hook_flag(&self, hook: Address, flag: u16) -> bool {
        interface_surfaces::has_v4_hook_flag(hook, flag)
    }

    pub fn dex_kind_for(&self, kind: u8) -> u8 {
        interface_surfaces::dex_kind_for(kind)
    }

    pub fn pathfinder_solidly_executor_dex_kind(&self) -> u8 {
        interface_surfaces::PathFinderVenue::Solidly
            .executor_dex_kind()
            .map(|dex_kind| dex_kind as u8)
            .unwrap_or(u8::MAX)
    }

    pub fn pathfinder_balancer_executor_dex_kind(&self) -> u8 {
        interface_surfaces::PathFinderVenue::Balancer
            .executor_dex_kind()
            .map(|dex_kind| dex_kind as u8)
            .unwrap_or(u8::MAX)
    }

    pub fn execute_native_arb_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(interface_surfaces::EXECUTE_NATIVE_ARB)
    }

    pub fn match_internal_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(interface_surfaces::MATCH_INTERNAL)
    }

    pub fn compose_four_leg_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(interface_surfaces::COMPOSE_FOUR_LEG)
    }

    pub fn find_route_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(interface_surfaces::FIND_ROUTE)
    }

    pub fn find_route_with_hints_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(interface_surfaces::FIND_ROUTE_WITH_HINTS)
    }

    pub fn identity_registry(&self) -> Address {
        interface_surfaces::IDENTITY_REGISTRY
    }

    pub fn reputation_registry(&self) -> Address {
        interface_surfaces::REPUTATION_REGISTRY
    }

    pub fn identity_register_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(interface_surfaces::IDENTITY_REGISTER)
    }

    pub fn reputation_give_feedback_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(interface_surfaces::REPUTATION_GIVE_FEEDBACK)
    }

    pub fn router_for(&self, kind: u8) -> Result<Address, CoreError> {
        router_registry::RouterKind::from_u8(kind)
            .map(router_registry::router_for)
            .ok_or(CoreError::UnknownRouterKind(UnknownRouterKind { kind }))
    }

    pub fn is_known_router(&self, router: Address) -> bool {
        router_registry::is_known(router)
    }

    pub fn universal_router_command(&self, kind: u8) -> Result<u8, CoreError> {
        router_registry::commands::command_for(kind)
            .ok_or(CoreError::UnknownRouterKind(UnknownRouterKind { kind }))
    }

    pub fn compute_uniswap_v2_address(
        &self,
        factory: Address,
        token_a: Address,
        token_b: Address,
    ) -> Address {
        lib_uniswap::compute_v2_address(factory, token_a, token_b)
    }

    pub fn compute_uniswap_v3_address(
        &self,
        factory: Address,
        token_a: Address,
        token_b: Address,
        fee: u32,
    ) -> Address {
        lib_uniswap::compute_v3_address(factory, token_a, token_b, fee)
    }

    pub fn frontrun_v2_swap_exact_tokens_for_tokens_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(frontrun_calldata::V2_SWAP_EXACT_TOKENS_FOR_TOKENS)
    }

    pub fn frontrun_v3_exact_input_single_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(frontrun_calldata::V3_EXACT_INPUT_SINGLE)
    }

    pub fn frontrun_v3_exact_input_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(frontrun_calldata::V3_EXACT_INPUT)
    }

    pub fn frontrun_ur_execute_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(frontrun_calldata::UR_EXECUTE)
    }

    pub fn frontrun_aave_v3_liquidation_call_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(frontrun_calldata::AAVE_V3_LIQUIDATION_CALL)
    }

    pub fn is_frontrun_selector(&self, selector: FixedBytes<4>) -> bool {
        let mut bytes = [0u8; 4];
        bytes.copy_from_slice(selector.as_slice());
        frontrun_calldata::is_frontrun_selector(bytes)
    }

    pub fn frontrun_ur_command_kind(&self, raw: u8) -> u8 {
        frontrun_calldata::classify_ur_command(raw).kind as u8
    }

    pub fn frontrun_ur_command_allows_revert(&self, raw: u8) -> bool {
        frontrun_calldata::classify_ur_command(raw).allow_revert
    }

    pub fn frontrun_get_amount_out(
        &self,
        amount_in: U256,
        reserve_in: U256,
        reserve_out: U256,
        fee_bps: U256,
    ) -> Result<U256, CoreError> {
        frontrun_calldata::get_amount_out(amount_in, reserve_in, reserve_out, fee_bps)
            .map_err(frontrun_math_error)
    }

    pub fn frontrun_optimal_v2_amount(
        &self,
        victim_amount_in: U256,
        victim_min_out: U256,
        reserve_in: U256,
        reserve_out: U256,
        fee_bps: U256,
        margin_bps: U256,
    ) -> Result<U256, CoreError> {
        frontrun_calldata::optimal_v2_frontrun_amount(
            victim_amount_in,
            victim_min_out,
            reserve_in,
            reserve_out,
            fee_bps,
            margin_bps,
        )
        .map_err(frontrun_math_error)
    }

    pub fn lp_kind_v2_erc20(&self) -> u8 {
        lp_transfer_lib::LpKind::V2Erc20 as u8
    }

    pub fn lp_kind_v3_nft(&self) -> u8 {
        lp_transfer_lib::LpKind::V3Nft as u8
    }

    pub fn lp_kind_v4_erc6909(&self) -> u8 {
        lp_transfer_lib::LpKind::V4Erc6909 as u8
    }

    pub fn lp_erc20_transfer_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(lp_transfer_lib::ERC20_TRANSFER)
    }

    pub fn lp_erc721_safe_transfer_from_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(lp_transfer_lib::ERC721_SAFE_TRANSFER_FROM)
    }

    pub fn lp_erc6909_transfer_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(lp_transfer_lib::ERC6909_TRANSFER)
    }

    pub fn lp_erc6909_set_operator_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(lp_transfer_lib::ERC6909_SET_OPERATOR)
    }

    pub fn transient_identity_slot(&self, kind: u8) -> Result<FixedBytes<32>, CoreError> {
        transient_slots::identity_slot(kind)
            .ok_or(CoreError::UnknownFlowKind(UnknownFlowKind { kind }))
    }

    pub fn transient_reentrancy_slot(&self, kind: u8) -> Result<FixedBytes<32>, CoreError> {
        transient_slots::FlowKind::from_u8(kind)
            .map(transient_slots::reentrancy_slot)
            .ok_or(CoreError::UnknownFlowKind(UnknownFlowKind { kind }))
    }

    pub fn simulate_merged_step_price_impact(&self, amount_in: U256, pool_liquidity: U256) -> U256 {
        step_merging::simulate_price_impact_u256(amount_in, pool_liquidity)
    }

    pub fn mega_ctz256(&self, x: U256) -> U256 {
        mega_mev_optimization::ctz256(x)
    }

    pub fn mega_bit_length(&self, x: U256) -> U256 {
        mega_mev_optimization::bit_length(x)
    }

    pub fn mega_floor_power_of_two(&self, x: U256) -> U256 {
        mega_mev_optimization::floor_power_of_two(x)
    }

    pub fn mega_lowest_bit(&self, x: U256) -> U256 {
        mega_mev_optimization::lowest_bit(x)
    }

    pub fn mega_next_power_of_two(&self, x: U256) -> Result<U256, CoreError> {
        mega_mev_optimization::next_power_of_two(x)
            .map_err(|_| CoreError::PowerOfTwoOverflow(PowerOfTwoOverflow {}))
    }

    pub fn mega_sqrt(&self, x: U256) -> U256 {
        mega_mev_optimization::sqrt(x)
    }

    pub fn mega_sqrt_up(&self, x: U256) -> U256 {
        mega_mev_optimization::sqrt_up(x)
    }

    pub fn mega_mul_div(&self, x: U256, y: U256, denominator: U256) -> Result<U256, CoreError> {
        mega_mev_optimization::mul_div(x, y, denominator).map_err(math_error)
    }

    pub fn mega_mul_div_up(&self, x: U256, y: U256, denominator: U256) -> Result<U256, CoreError> {
        mega_mev_optimization::mul_div_up(x, y, denominator).map_err(math_error)
    }

    pub fn reject_by_reserve_shape(
        &self,
        reserve_a: U256,
        reserve_b: U256,
        min_bit_length: U256,
        max_imbalance_bucket: U256,
    ) -> bool {
        mega_mev_optimization::reject_by_reserve_shape(
            reserve_a,
            reserve_b,
            min_bit_length,
            max_imbalance_bucket,
        )
    }

    pub fn token_risk_known_mask(&self) -> U256 {
        token_risk_filter::known_risk_mask()
    }

    pub fn token_risk_is_major(&self, token: Address) -> bool {
        token_risk_filter::is_major(token)
    }

    pub fn token_risk_is_safe_flags(&self, flags: U256) -> bool {
        token_risk_filter::is_safe_flags(flags)
    }

    pub fn token_risk_cache_ttl_seconds(&self) -> U256 {
        U256::from(token_risk_filter::CACHE_TTL_SECONDS)
    }

    pub fn token_risk_staticcall_gas(&self) -> U256 {
        U256::from(token_risk_filter::RISK_STATICCALL_GAS)
    }

    pub fn erc1967_implementation_slot(&self) -> FixedBytes<32> {
        upgrade_policy::erc1967_implementation_slot()
    }

    pub fn proxiable_uuid(&self) -> FixedBytes<32> {
        upgrade_policy::proxiable_uuid()
    }

    pub fn stylus_reactivation_period_seconds(&self) -> U256 {
        U256::from(upgrade_policy::REACTIVATION_PERIOD_SECONDS)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn source_contract_count_is_fixed_for_audit_surface() {
        assert_eq!(62, SOURCE_CONTRACT_COUNT);
    }

    #[test]
    fn upgrade_policy_surface_matches_library() {
        assert_eq!(
            upgrade_policy::erc1967_implementation_slot(),
            upgrade_policy::proxiable_uuid()
        );
        assert_eq!(
            365 * 24 * 60 * 60,
            upgrade_policy::REACTIVATION_PERIOD_SECONDS
        );
    }

    #[test]
    fn interface_surface_selectors_match_library() {
        assert_eq!(24, interface_surfaces::dex_kind_for(24));
        assert_eq!(u8::MAX, interface_surfaces::dex_kind_for(29));
        assert_eq!(
            Some(interface_surfaces::DexKind::UniswapV2),
            interface_surfaces::PathFinderVenue::Solidly.executor_dex_kind()
        );
        assert_eq!(
            FixedBytes::from([0xf6, 0xf6, 0xad, 0xd1]),
            FixedBytes::from(interface_surfaces::EXECUTE_NATIVE_ARB)
        );
        assert_eq!(
            FixedBytes::from([0xc0, 0x36, 0xc8, 0xea]),
            FixedBytes::from(interface_surfaces::FIND_ROUTE_WITH_HINTS)
        );
    }
}

#[cfg(test)]
mod port_parity_tests;

#[cfg(not(any(test, feature = "native-test")))]
fn math_error(error: mega_mev_optimization::MathError) -> CoreError {
    match error {
        mega_mev_optimization::MathError::DivisionByZero => {
            CoreError::DivisionByZero(DivisionByZero {})
        }
        mega_mev_optimization::MathError::Overflow => CoreError::MathOverflow(MathOverflow {}),
    }
}

#[cfg(not(any(test, feature = "native-test")))]
fn frontrun_math_error(error: frontrun_calldata::FrontrunMathError) -> CoreError {
    match error {
        frontrun_calldata::FrontrunMathError::InvalidReserves => {
            CoreError::FrontrunInvalidReserves(FrontrunInvalidReserves {})
        }
        frontrun_calldata::FrontrunMathError::InvalidFeeBps(fee_bps) => {
            CoreError::FrontrunInvalidFeeBps(FrontrunInvalidFeeBps { feeBps: fee_bps })
        }
        frontrun_calldata::FrontrunMathError::InvalidMarginBps(margin_bps) => {
            CoreError::FrontrunInvalidMarginBps(FrontrunInvalidMarginBps {
                marginBps: margin_bps,
            })
        }
        frontrun_calldata::FrontrunMathError::Overflow => CoreError::MathOverflow(MathOverflow {}),
    }
}
