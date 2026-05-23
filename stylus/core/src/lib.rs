#![cfg_attr(
    not(any(test, feature = "export-abi", feature = "native-test")),
    no_main
)]
#![cfg_attr(feature = "contract-client-gen", allow(unused_imports))]

extern crate alloc;

pub mod account_semantics;
pub mod auth_semantics;
pub mod bit_math;
pub mod contract_manifest;
pub mod executor_abi;
pub mod executor_semantics;
pub mod frontrun_calldata;
pub mod interface_surfaces;
pub mod lib_uniswap;
pub mod lp_transfer_lib;
pub mod mega_mev_optimization;
pub mod poc_fail_closed;
pub mod router_registry;
pub mod singleton_arrays;
pub mod step_merging;
pub mod swapper_semantics;
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
    error UnknownSourceCategory(uint8 category);
    error UnknownMigrationStatus(uint8 status);
    error UnknownPocKind(uint8 kind);
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
    UnknownSourceCategory(UnknownSourceCategory),
    UnknownMigrationStatus(UnknownMigrationStatus),
    UnknownPocKind(UnknownPocKind),
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

    pub fn source_manifest_count(&self) -> U256 {
        U256::from(contract_manifest::SOURCE_COUNT)
    }

    pub fn source_manifest_has_full_coverage(&self) -> bool {
        contract_manifest::has_full_source_coverage()
    }

    pub fn source_category_count(&self, category: u8) -> Result<U256, CoreError> {
        contract_manifest::SourceCategory::from_u8(category)
            .map(contract_manifest::category_count)
            .map(U256::from)
            .ok_or(CoreError::UnknownSourceCategory(UnknownSourceCategory {
                category,
            }))
    }

    pub fn migration_status_count(&self, status: u8) -> Result<U256, CoreError> {
        contract_manifest::MigrationStatus::from_u8(status)
            .map(contract_manifest::status_count)
            .map(U256::from)
            .ok_or(CoreError::UnknownMigrationStatus(UnknownMigrationStatus {
                status,
            }))
    }

    pub fn poc_is_fail_closed(&self, kind: u8) -> Result<bool, CoreError> {
        poc_fail_closed::PocKind::from_u8(kind)
            .map(poc_fail_closed::is_fail_closed)
            .ok_or(CoreError::UnknownPocKind(UnknownPocKind { kind }))
    }

    pub fn poc_strategy_confirmed(&self, kind: u8) -> Result<bool, CoreError> {
        poc_fail_closed::PocKind::from_u8(kind)
            .map(poc_fail_closed::strategy_confirmed)
            .ok_or(CoreError::UnknownPocKind(UnknownPocKind { kind }))
    }

    pub fn poc_missing_gate_count(&self, kind: u8) -> Result<U256, CoreError> {
        poc_fail_closed::PocKind::from_u8(kind)
            .map(poc_fail_closed::missing_gate_count)
            .ok_or(CoreError::UnknownPocKind(UnknownPocKind { kind }))
    }

    pub fn comet_balancer_v3_vault(&self) -> Address {
        poc_fail_closed::COMET_BALANCER_V3_VAULT
    }

    pub fn comet_univ3_router02(&self) -> Address {
        poc_fail_closed::COMET_UNIV3_ROUTER02
    }

    pub fn comet_is_supported(&self, comet: Address) -> bool {
        poc_fail_closed::is_supported_comet(comet)
    }

    pub fn comet_static_validation_code(
        &self,
        now: U256,
        comet: Address,
        collateral: Address,
        base_amount: U256,
        borrower_count: U256,
        swap_path_len: U256,
        amount_out_minimum: U256,
        min_profit: U256,
        deadline: U256,
    ) -> u8 {
        match poc_fail_closed::validate_comet_static_plan(poc_fail_closed::CometStaticPlan {
            now,
            comet,
            collateral,
            base_amount,
            borrower_count,
            swap_path_len,
            amount_out_minimum,
            min_profit,
            deadline,
        }) {
            Ok(()) => 0,
            Err(poc_fail_closed::CometValidationError::DeadlinePassed) => 1,
            Err(poc_fail_closed::CometValidationError::UnsupportedComet) => 2,
            Err(poc_fail_closed::CometValidationError::InvalidParams) => 3,
        }
    }

    pub fn euler_evc(&self) -> Address {
        poc_fail_closed::EULER_EVC
    }

    pub fn euler_batch_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(poc_fail_closed::EVC_BATCH_SELECTOR)
    }

    pub fn pendle_limit_router(&self) -> Address {
        poc_fail_closed::PENDLE_LIMIT_ROUTER
    }

    pub fn pendle_router(&self) -> Address {
        poc_fail_closed::PENDLE_ROUTER
    }

    pub fn pendle_requires_hook_classification(&self, hook: Address) -> bool {
        poc_fail_closed::requires_hook_classification(hook)
    }

    pub fn pendle_py_sy_missing_gates(
        &self,
        top_markets_fork_verified: bool,
        router_quote_reproduced: bool,
        raw_fair_value_proven: bool,
        swap_back_proven: bool,
        flash_settlement_proven: bool,
        net_profit_proven: bool,
    ) -> U256 {
        poc_fail_closed::pendle_py_sy_missing_gates(poc_fail_closed::PromotionEvidence {
            top_markets_fork_verified,
            router_quote_reproduced,
            raw_fair_value_proven,
            swap_back_proven,
            flash_settlement_proven,
            net_profit_proven,
        })
    }

    pub fn permission_grant_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(auth_semantics::PERMISSION_GRANT_SELECTOR)
    }

    pub fn permission_grant_batch_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(auth_semantics::PERMISSION_GRANT_BATCH_SELECTOR)
    }

    pub fn permission_revoke_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(auth_semantics::PERMISSION_REVOKE_SELECTOR)
    }

    pub fn permission_has_permission_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(auth_semantics::PERMISSION_HAS_PERMISSION_SELECTOR)
    }

    pub fn permission_token_decimals(&self) -> u8 {
        auth_semantics::PERMISSION_TOKEN_DECIMALS
    }

    pub fn permission_grant_params_valid(
        &self,
        account: Address,
        target: Address,
        selector: FixedBytes<4>,
    ) -> bool {
        auth_semantics::permission_grant_params_valid(account, target, selector)
    }

    pub fn strategy_set_executor_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(auth_semantics::STRATEGY_SET_EXECUTOR_SELECTOR)
    }

    pub fn strategy_record_profit_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(auth_semantics::STRATEGY_RECORD_PROFIT_SELECTOR)
    }

    pub fn strategy_ledger_decimals(&self) -> u8 {
        auth_semantics::STRATEGY_LEDGER_DECIMALS
    }

    pub fn strategy_profit_params_valid(
        &self,
        is_executor: bool,
        to: Address,
        amount: U256,
    ) -> bool {
        auth_semantics::strategy_profit_params_valid(is_executor, to, amount)
    }

    pub fn session_add_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(auth_semantics::SESSION_ADD_SELECTOR)
    }

    pub fn passkey_add_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(auth_semantics::PASSKEY_ADD_SELECTOR)
    }

    pub fn validator_validate_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(auth_semantics::VALIDATOR_VALIDATE_SELECTOR)
    }

    pub fn session_registration_code(&self, now: U256, signer: Address, expiry: U256) -> u8 {
        match auth_semantics::validate_session_registration(now, signer, expiry) {
            Ok(()) => 0,
            Err(auth_semantics::AuthParamError::InvalidParams) => 1,
            Err(auth_semantics::AuthParamError::InvalidExpiry) => 2,
            Err(auth_semantics::AuthParamError::InvalidPubkey) => 3,
            Err(auth_semantics::AuthParamError::InvalidValidatorData) => 4,
        }
    }

    pub fn pack_session_validation_data(&self, expiry: U256) -> U256 {
        auth_semantics::pack_session_validation_data(expiry)
    }

    pub fn passkey_pubkey_len_valid(&self, len: u64) -> bool {
        auth_semantics::passkey_pubkey_len_valid(len as usize)
    }

    pub fn passkey_validator_data_len_valid(&self, len: u64) -> bool {
        auth_semantics::passkey_validator_data_len_valid(len as usize)
    }

    pub fn account_entry_point_v06(&self) -> Address {
        account_semantics::ENTRY_POINT_V06
    }

    pub fn account_entry_point_v07(&self) -> Address {
        account_semantics::ENTRY_POINT_V07
    }

    pub fn account_entry_point_v08(&self) -> Address {
        account_semantics::ENTRY_POINT_V08
    }

    pub fn account_entry_point_v09(&self) -> Address {
        account_semantics::ENTRY_POINT_V09
    }

    pub fn account_is_entry_point(&self, addr: Address) -> bool {
        account_semantics::is_entry_point(addr)
    }

    pub fn account_erc1271_magic(&self) -> FixedBytes<4> {
        FixedBytes::from(account_semantics::ERC1271_MAGIC)
    }

    pub fn account_erc6909_set_operator_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(account_semantics::ERC6909_SET_OPERATOR_SELECTOR)
    }

    pub fn account_erc6909_approve_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(account_semantics::ERC6909_APPROVE_SELECTOR)
    }

    pub fn safe_execute_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(account_semantics::SAFE_EXECUTE_SELECTOR)
    }

    pub fn safe_execute_batch_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(account_semantics::SAFE_EXECUTE_BATCH_SELECTOR)
    }

    pub fn safe_execute_erc6909_batch_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(account_semantics::SAFE_EXECUTE_ERC6909_BATCH_SELECTOR)
    }

    pub fn bot_execute_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(account_semantics::BOT_EXECUTE_SELECTOR)
    }

    pub fn paymaster_v06_validate_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(account_semantics::PAYMASTER_V06_VALIDATE_SELECTOR)
    }

    pub fn paymaster_v07_validate_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(account_semantics::PAYMASTER_V07_VALIDATE_SELECTOR)
    }

    pub fn cowshed_execute_hooks_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(account_semantics::COWSHED_EXECUTE_HOOKS_SELECTOR)
    }

    pub fn account_threshold_code(&self, threshold: U256, signer_count: U256) -> u8 {
        account_semantics::error_code(account_semantics::validate_threshold(
            threshold,
            signer_count,
        ))
    }

    pub fn safe_execute_static_code(&self, target: Address, selector: FixedBytes<4>) -> u8 {
        let mut selector_bytes = [0_u8; 4];
        selector_bytes.copy_from_slice(selector.as_slice());
        account_semantics::error_code(account_semantics::validate_safe_execute(
            target,
            selector_bytes,
        ))
    }

    pub fn safe_erc6909_call_static_code(
        &self,
        op: u8,
        token: Address,
        counterparty: Address,
        id: U256,
        amount: U256,
        approved: bool,
    ) -> u8 {
        account_semantics::error_code(account_semantics::validate_erc6909_call(
            account_semantics::Erc6909CallStatic {
                op,
                token,
                counterparty,
                id,
                amount,
                approved,
            },
        ))
    }

    pub fn safe_finance_plan_static_code(
        &self,
        flash_lender: Address,
        flash_asset: Address,
        flash_amount: U256,
        aave_pool: Address,
    ) -> u8 {
        account_semantics::error_code(account_semantics::validate_safe_finance_plan(
            account_semantics::SafeFinancePlanStatic {
                flash_lender,
                flash_asset,
                flash_amount,
                aave_pool,
            },
        ))
    }

    pub fn safe_finance_v3_plan_static_code(
        &self,
        flash_asset: Address,
        flash_amount: U256,
        aave_pool: Address,
    ) -> u8 {
        account_semantics::error_code(account_semantics::validate_safe_finance_v3_plan(
            account_semantics::SafeFinancePlanStatic {
                flash_lender: Address::ZERO,
                flash_asset,
                flash_amount,
                aave_pool,
            },
        ))
    }

    pub fn account_signature_kind(&self, signature_len: u64) -> u8 {
        account_semantics::signature_kind(signature_len as usize)
    }

    pub fn paymaster_tuning_static_code(&self, max_wei_per_epoch: U256, epoch_length: u64) -> u8 {
        account_semantics::error_code(account_semantics::validate_paymaster_tuning(
            max_wei_per_epoch,
            epoch_length,
        ))
    }

    pub fn paymaster_erc20_config_static_code(
        &self,
        token: Address,
        token_oracle: Address,
        treasury: Address,
        max_staleness: u32,
        markup_bps: u16,
        oracle_decimals: u8,
    ) -> u8 {
        account_semantics::error_code(account_semantics::validate_paymaster_erc20_config(
            account_semantics::PaymasterErc20ConfigStatic {
                token,
                token_oracle,
                treasury,
                max_staleness,
                markup_bps,
                oracle_decimals,
            },
        ))
    }

    pub fn paymaster_data_mode_or_invalid(&self, len: u64, first_byte: u8) -> u8 {
        account_semantics::validate_paymaster_data_shape(len as usize, first_byte)
            .unwrap_or(u8::MAX)
    }

    pub fn paymaster_budget_reservation_code(
        &self,
        spent: U256,
        reservation: U256,
        max_wei_per_epoch: U256,
    ) -> u8 {
        account_semantics::error_code(account_semantics::validate_budget_reservation(
            spent,
            reservation,
            max_wei_per_epoch,
        ))
    }

    pub fn paymaster_pool_id_code(&self, pool_id: U256, allow_zero: bool) -> u8 {
        account_semantics::error_code(account_semantics::validate_pool_id(pool_id, allow_zero))
    }

    pub fn paymaster_pool_token_id(&self, pool_id: U256, token: Address) -> U256 {
        account_semantics::encode_pool_token_id(pool_id, token)
    }

    pub fn cowshed_initialize_static_code(&self, admin: Address, already_initialized: bool) -> u8 {
        account_semantics::error_code(account_semantics::validate_cowshed_initialize(
            admin,
            already_initialized,
        ))
    }

    pub fn cowshed_update_implementation_static_code(
        &self,
        implementation: Address,
        implementation_has_code: bool,
    ) -> u8 {
        account_semantics::error_code(account_semantics::validate_cowshed_update_implementation(
            implementation,
            implementation_has_code,
        ))
    }

    pub fn cowshed_execute_hooks_static_code(
        &self,
        call_count: u64,
        nonce_used: bool,
        signature_len: u64,
    ) -> u8 {
        account_semantics::error_code(account_semantics::validate_cowshed_execute_hooks(
            call_count as usize,
            nonce_used,
            signature_len as usize,
        ))
    }

    pub fn multihop_swap_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(swapper_semantics::SWAP_SELECTOR)
    }

    pub fn multihop_swap_with_auto_slippage_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(swapper_semantics::SWAP_WITH_AUTO_SLIPPAGE_SELECTOR)
    }

    pub fn multihop_swap_with_quoted_v4_input_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(swapper_semantics::SWAP_WITH_QUOTED_V4_INPUT_SELECTOR)
    }

    pub fn multihop_apply_slippage(&self, amount: U256, bps: U256) -> Result<U256, CoreError> {
        swapper_semantics::apply_slippage(amount, bps).map_err(|error| match error {
            swapper_semantics::MultiHopError::SlippageOutOfRange
            | swapper_semantics::MultiHopError::MathOverflow => {
                CoreError::MathOverflow(MathOverflow {})
            }
            swapper_semantics::MultiHopError::WrongValue
            | swapper_semantics::MultiHopError::Expired
            | swapper_semantics::MultiHopError::V4AmountInZero => {
                CoreError::MathOverflow(MathOverflow {})
            }
        })
    }

    pub fn multihop_static_swap_code(
        &self,
        now: U256,
        msg_value: U256,
        amount_in: U256,
        deadline: U256,
    ) -> u8 {
        match swapper_semantics::validate_swap_static(swapper_semantics::SwapStaticInput {
            now,
            msg_value,
            amount_in,
            deadline,
        }) {
            Ok(()) => 0,
            Err(swapper_semantics::MultiHopError::WrongValue) => 1,
            Err(swapper_semantics::MultiHopError::Expired) => 2,
            Err(swapper_semantics::MultiHopError::SlippageOutOfRange) => 3,
            Err(swapper_semantics::MultiHopError::V4AmountInZero) => 4,
            Err(swapper_semantics::MultiHopError::MathOverflow) => 5,
        }
    }

    pub fn multihop_depth_is_sufficient(
        &self,
        v2_weth_usdc_r0: u128,
        v2_arb_usdc_r1: u128,
        v3_weth_arb_liq: u128,
        v3_wsteth_weth_liq: u128,
        v4_wsteth_weth_liq: u128,
        v4_weth_arb_liq: u128,
    ) -> bool {
        swapper_semantics::depth_is_sufficient(swapper_semantics::DepthSnapshot {
            v2_weth_usdc_r0,
            v2_arb_usdc_r1,
            v3_weth_arb_liq,
            v3_wsteth_weth_liq,
            v4_wsteth_weth_liq,
            v4_weth_arb_liq,
        })
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

    pub fn execute_uniswapx_fill_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(interface_surfaces::EXECUTE_UNISWAPX_FILL)
    }

    pub fn trigger_cow_flash_loan_router_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(interface_surfaces::TRIGGER_COW_FLASH_LOAN_ROUTER)
    }

    pub fn executor_reactor_execute_batch_with_callback_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(executor_semantics::REACTOR_EXECUTE_BATCH_WITH_CALLBACK_SELECTOR)
    }

    pub fn executor_static_native_arb_code(
        &self,
        now: U256,
        flash_token: Address,
        flash_amount: U256,
        swap_count: u64,
        first_token_in: Address,
        last_token_out: Address,
        deadline: U256,
    ) -> u8 {
        executor_semantics::error_code(executor_semantics::validate_native_arb_shape(
            now,
            flash_token,
            flash_amount,
            swap_count as usize,
            first_token_in,
            last_token_out,
            deadline,
        ))
    }

    pub fn executor_static_match_internal_code(
        &self,
        now: U256,
        expected_token_inflows_len: u64,
        expected_token_inflow_min_len: u64,
        flash_amount: U256,
        deadline: U256,
    ) -> u8 {
        executor_semantics::error_code(executor_semantics::validate_match_internal_shape(
            now,
            expected_token_inflows_len as usize,
            expected_token_inflow_min_len as usize,
            flash_amount,
            deadline,
        ))
    }

    pub fn executor_static_compose_four_leg_code(
        &self,
        now: U256,
        flash_amount: U256,
        deadline: U256,
    ) -> u8 {
        executor_semantics::error_code(executor_semantics::validate_compose_four_leg_shape(
            now,
            flash_amount,
            deadline,
        ))
    }

    pub fn executor_static_uniswapx_fill_code(
        &self,
        reactor: Address,
        expected_reactor: Address,
        execute_calldata_len: u64,
        execute_selector: FixedBytes<4>,
        callback_data_len: u64,
    ) -> u8 {
        let mut selector = [0_u8; 4];
        selector.copy_from_slice(execute_selector.as_slice());
        executor_semantics::error_code(executor_semantics::validate_uniswapx_fill_static(
            executor_semantics::ExecutorUniswapXFillStatic {
                reactor,
                expected_reactor,
                execute_calldata_len: execute_calldata_len as usize,
                execute_selector: selector,
                callback_data_len: callback_data_len as usize,
            },
        ))
    }

    pub fn executor_static_cow_start_code(
        &self,
        now: U256,
        total_rounds: U256,
        deadline: U256,
    ) -> u8 {
        executor_semantics::error_code(executor_semantics::validate_cow_router_start_shape(
            now,
            total_rounds,
            deadline,
        ))
    }

    pub fn executor_static_cow_round_code(&self, round: U256, total_rounds: U256) -> u8 {
        executor_semantics::error_code(executor_semantics::validate_cow_round_shape(
            round,
            total_rounds,
        ))
    }

    pub fn executor_static_cow_final_strategy_code(&self, strategy_id: u8) -> u8 {
        executor_semantics::error_code(executor_semantics::validate_cow_final_strategy_id(
            strategy_id,
        ))
    }

    pub fn executor_static_swap_step_code(
        &self,
        dex_kind: u8,
        router_is_whitelisted: bool,
        amount_in: U256,
        carry: U256,
    ) -> u8 {
        executor_semantics::swap_step_static_error_code(
            executor_semantics::ExecutorSwapStepStatic {
                dex_kind,
                router_is_whitelisted,
                amount_in,
                carry,
            },
        )
    }

    pub fn atomic_execute_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(executor_semantics::ATOMIC_EXECUTE_SELECTOR)
    }

    pub fn atomic_execute_compressed_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(executor_semantics::ATOMIC_EXECUTE_COMPRESSED_SELECTOR)
    }

    pub fn atomic_unlock_callback_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(executor_semantics::ATOMIC_UNLOCK_CALLBACK_SELECTOR)
    }

    pub fn atomic_balancer_v3_unlock_callback_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(executor_semantics::ATOMIC_BALANCER_V3_UNLOCK_CALLBACK_SELECTOR)
    }

    pub fn atomic_receive_flash_loan_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(executor_semantics::ATOMIC_RECEIVE_FLASH_LOAN_SELECTOR)
    }

    pub fn atomic_aave_execute_operation_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(executor_semantics::ATOMIC_AAVE_EXECUTE_OPERATION_SELECTOR)
    }

    pub fn atomic_balancer_v3_vault(&self) -> Address {
        executor_semantics::ATOMIC_BALANCER_V3_VAULT
    }

    pub fn atomic_balancer_v2_vault(&self) -> Address {
        executor_semantics::ATOMIC_BALANCER_V2_VAULT
    }

    pub fn atomic_aave_v3_pool(&self) -> Address {
        executor_semantics::ATOMIC_AAVE_V3_POOL
    }

    pub fn atomic_univ3_router02(&self) -> Address {
        executor_semantics::ATOMIC_UNIV3_ROUTER02
    }

    pub fn atomic_static_exec_code(
        &self,
        now: U256,
        flash_token: Address,
        flash_token_has_code: bool,
        flash_amount: U256,
        strategy: u8,
        flash_source: u8,
        strategy_data_len: u64,
        deadline: U256,
    ) -> u8 {
        executor_semantics::error_code(executor_semantics::validate_atomic_exec_static(
            executor_semantics::AtomicExecStatic {
                now,
                flash_token,
                flash_token_has_code,
                flash_amount,
                strategy,
                flash_source,
                strategy_data_len: strategy_data_len as usize,
                deadline,
            },
        ))
    }

    pub fn atomic_static_compressed_code(
        &self,
        compressed_len: u64,
        strategy_data_len: u64,
        max_strategy_data_len: u64,
        strategy_data_hash_matches: bool,
    ) -> u8 {
        executor_semantics::error_code(executor_semantics::validate_atomic_compressed_static(
            executor_semantics::AtomicCompressedStatic {
                compressed_len: compressed_len as usize,
                strategy_data_len: strategy_data_len as usize,
                max_strategy_data_len: max_strategy_data_len as usize,
                strategy_data_hash_matches,
            },
        ))
    }

    pub fn atomic_static_aave_liquidation_code(
        &self,
        executor: Address,
        collateral_asset: Address,
        debt_asset: Address,
        borrower: Address,
        flash_token: Address,
        flash_amount: U256,
        debt_to_cover: U256,
        swap_path_len: u64,
        swap_path_token_in: Address,
        swap_path_token_out: Address,
        amount_out_minimum: U256,
    ) -> u8 {
        executor_semantics::error_code(executor_semantics::validate_atomic_aave_liquidation_static(
            executor_semantics::AaveLiquidationStatic {
                executor,
                collateral_asset,
                debt_asset,
                borrower,
                flash_token,
                flash_amount,
                debt_to_cover,
                swap_path_len: swap_path_len as usize,
                swap_path_token_in,
                swap_path_token_out,
                amount_out_minimum,
            },
        ))
    }

    pub fn liquidation_liquidate_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(executor_semantics::LIQUIDATION_LIQUIDATE_SELECTOR)
    }

    pub fn liquidation_liquidate_morpho_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(executor_semantics::LIQUIDATION_LIQUIDATE_MORPHO_SELECTOR)
    }

    pub fn liquidation_on_morpho_liquidate_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(executor_semantics::LIQUIDATION_ON_MORPHO_LIQUIDATE_SELECTOR)
    }

    pub fn liquidation_receive_flash_loan_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(executor_semantics::LIQUIDATION_RECEIVE_FLASH_LOAN_SELECTOR)
    }

    pub fn liquidation_morpho(&self) -> Address {
        executor_semantics::LIQUIDATION_MORPHO
    }

    pub fn liquidation_static_entry_code(
        &self,
        now: U256,
        executor: Address,
        collateral: Address,
        debt: Address,
        borrower: Address,
        debt_amount: U256,
        swap_path_len: u64,
        amount_out_minimum: U256,
        deadline: U256,
    ) -> u8 {
        executor_semantics::error_code(executor_semantics::validate_liquidation_entry_static(
            executor_semantics::LiquidationEntryStatic {
                now,
                executor,
                collateral,
                debt,
                borrower,
                debt_amount,
                swap_path_len: swap_path_len as usize,
                amount_out_minimum,
                deadline,
            },
        ))
    }

    pub fn liquidation_static_morpho_entry_code(
        &self,
        now: U256,
        executor: Address,
        loan_token: Address,
        collateral_token: Address,
        borrower: Address,
        seized_assets: U256,
        swap_path_len: u64,
        amount_out_minimum: U256,
        deadline: U256,
    ) -> u8 {
        executor_semantics::error_code(
            executor_semantics::validate_morpho_liquidation_entry_static(
                executor_semantics::MorphoLiquidationEntryStatic {
                    now,
                    executor,
                    loan_token,
                    collateral_token,
                    borrower,
                    seized_assets,
                    swap_path_len: swap_path_len as usize,
                    amount_out_minimum,
                    deadline,
                },
            ),
        )
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
        assert_eq!(62, contract_manifest::SOURCE_COUNT);
        assert!(contract_manifest::has_full_source_coverage());
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
