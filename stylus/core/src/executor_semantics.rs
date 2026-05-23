//! Static semantics for `executors/*.sol`.
//!
//! These helpers intentionally stop before live ERC-20 balances, external
//! calls, transient writes, and callback re-entry. They port the deterministic
//! executor-family ABI selectors, enum ordinals, deadline gates, path-shape
//! guards, flash-source gates, and liquidation plan guards that must hold before
//! the Solidity contracts touch external protocols.

use alloy_primitives::address;
use stylus_sdk::alloy_primitives::{Address, U256};

use crate::executor_abi::{
    CoWFlashLoanRouterStartParams, ComposeParams, MatchParams, NativeArbParams,
};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum ExecutorStaticError {
    DeadlineExpired = 1,
    InvalidPath = 2,
    InvalidFlashAmount = 3,
    FlashTokenMismatch = 4,
    ArrayLengthMismatch = 5,
    InvalidActionData = 6,
    UnexpectedReactor = 7,
    InvalidRound = 8,
    InvalidStrategyId = 9,
    DirectPoolManagerV4Disabled = 10,
    RouterNotWhitelisted = 11,
    InvalidParams = 12,
    InvalidStrategy = 13,
    InvalidFlashSource = 14,
    WrongFlashAsset = 15,
    CompressedDataTooLarge = 16,
    StrategyDataTooLarge = 17,
    PlanHashMismatch = 18,
    ZeroAddress = 19,
    ZeroAmountOutMinimum = 20,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum AtomicStrategy {
    AaveLiquidation = 0,
    SettlementArb = 1,
    OracleGap = 2,
    CyclicArb = 3,
}

impl AtomicStrategy {
    pub fn from_u8(value: u8) -> Option<Self> {
        match value {
            0 => Some(Self::AaveLiquidation),
            1 => Some(Self::SettlementArb),
            2 => Some(Self::OracleGap),
            3 => Some(Self::CyclicArb),
            _ => None,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum AtomicFlashSource {
    BalancerV3 = 0,
    BalancerV2 = 1,
    AaveV3Simple = 2,
}

impl AtomicFlashSource {
    pub fn from_u8(value: u8) -> Option<Self> {
        match value {
            0 => Some(Self::BalancerV3),
            1 => Some(Self::BalancerV2),
            2 => Some(Self::AaveV3Simple),
            _ => None,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ExecutorSwapStepStatic {
    pub dex_kind: u8,
    pub router_is_whitelisted: bool,
    pub amount_in: U256,
    pub carry: U256,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ExecutorUniswapXFillStatic {
    pub reactor: Address,
    pub expected_reactor: Address,
    pub execute_calldata_len: usize,
    pub execute_selector: [u8; 4],
    pub callback_data_len: usize,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct AtomicExecStatic {
    pub now: U256,
    pub flash_token: Address,
    pub flash_token_has_code: bool,
    pub flash_amount: U256,
    pub strategy: u8,
    pub flash_source: u8,
    pub strategy_data_len: usize,
    pub deadline: U256,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct AtomicCompressedStatic {
    pub compressed_len: usize,
    pub strategy_data_len: usize,
    pub max_strategy_data_len: usize,
    pub strategy_data_hash_matches: bool,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct AaveLiquidationStatic {
    pub executor: Address,
    pub collateral_asset: Address,
    pub debt_asset: Address,
    pub borrower: Address,
    pub flash_token: Address,
    pub flash_amount: U256,
    pub debt_to_cover: U256,
    pub swap_path_len: usize,
    pub swap_path_token_in: Address,
    pub swap_path_token_out: Address,
    pub amount_out_minimum: U256,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct LiquidationEntryStatic {
    pub now: U256,
    pub executor: Address,
    pub collateral: Address,
    pub debt: Address,
    pub borrower: Address,
    pub debt_amount: U256,
    pub swap_path_len: usize,
    pub amount_out_minimum: U256,
    pub deadline: U256,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct MorphoLiquidationEntryStatic {
    pub now: U256,
    pub executor: Address,
    pub loan_token: Address,
    pub collateral_token: Address,
    pub borrower: Address,
    pub seized_assets: U256,
    pub swap_path_len: usize,
    pub amount_out_minimum: U256,
    pub deadline: U256,
}

pub const REACTOR_EXECUTE_BATCH_WITH_CALLBACK_SELECTOR: [u8; 4] = [0x13, 0xfb, 0x72, 0xc7];

pub const ATOMIC_EXECUTE_SELECTOR: [u8; 4] = [0x68, 0xba, 0x2b, 0x3e];
pub const ATOMIC_EXECUTE_COMPRESSED_SELECTOR: [u8; 4] = [0xf0, 0xe4, 0x54, 0x0e];
pub const ATOMIC_UNLOCK_CALLBACK_SELECTOR: [u8; 4] = [0x91, 0xdd, 0x73, 0x46];
pub const ATOMIC_BALANCER_V3_UNLOCK_CALLBACK_SELECTOR: [u8; 4] = [0xc8, 0x77, 0xe1, 0x8b];
pub const ATOMIC_RECEIVE_FLASH_LOAN_SELECTOR: [u8; 4] = [0xf0, 0x4f, 0x27, 0x07];
pub const ATOMIC_AAVE_EXECUTE_OPERATION_SELECTOR: [u8; 4] = [0x1b, 0x11, 0xd0, 0xff];

pub const LIQUIDATION_LIQUIDATE_SELECTOR: [u8; 4] = [0x6f, 0x0c, 0xaa, 0xc9];
pub const LIQUIDATION_LIQUIDATE_MORPHO_SELECTOR: [u8; 4] = [0x49, 0x30, 0x4b, 0xd4];
pub const LIQUIDATION_ON_MORPHO_LIQUIDATE_SELECTOR: [u8; 4] = [0xcf, 0x7e, 0xa1, 0x96];
pub const LIQUIDATION_RECEIVE_FLASH_LOAN_SELECTOR: [u8; 4] = [0xf0, 0x4f, 0x27, 0x07];

pub const ATOMIC_BALANCER_V3_VAULT: Address = address!("bA1333333333a1BA1108E8412f11850A5C319bA9");
pub const ATOMIC_BALANCER_V2_VAULT: Address = address!("BA12222222228d8Ba445958a75a0704d566BF2C8");
pub const ATOMIC_AAVE_V3_POOL: Address = address!("794a61358D6845594F94dc1DB02A252b5b4814aD");
pub const ATOMIC_UNIV3_ROUTER02: Address = address!("68b3465833fb72A70ecDF485E0e4C7bD8665Fc45");
pub const LIQUIDATION_MORPHO: Address = address!("6c247b1F6182318877311737BaC0844bAa518F5e");

pub const MAX_COMPRESSED_STRATEGY_DATA_BYTES: usize = 16_384;
pub const MAX_DECOMPRESSED_STRATEGY_DATA_BYTES: usize = 24_576;
pub const MIN_V3_EXACT_INPUT_PATH_BYTES: usize = 43;
pub const V3_EXACT_INPUT_HOP_BYTES: usize = 23;

#[must_use]
pub fn error_code(result: Result<(), ExecutorStaticError>) -> u8 {
    match result {
        Ok(()) => 0,
        Err(error) => error as u8,
    }
}

pub fn validate_native_arb_entry(
    now: U256,
    params: &NativeArbParams,
) -> Result<(), ExecutorStaticError> {
    validate_native_arb_shape(
        now,
        params.flash_token,
        params.flash_amount,
        params.swaps.len(),
        params
            .swaps
            .first()
            .map(|step| step.token_in)
            .unwrap_or(Address::ZERO),
        params
            .swaps
            .last()
            .map(|step| step.token_out)
            .unwrap_or(Address::ZERO),
        params.deadline,
    )
}

pub fn validate_native_arb_shape(
    now: U256,
    flash_token: Address,
    flash_amount: U256,
    swap_count: usize,
    first_token_in: Address,
    last_token_out: Address,
    deadline: U256,
) -> Result<(), ExecutorStaticError> {
    if now > deadline {
        return Err(ExecutorStaticError::DeadlineExpired);
    }
    if swap_count == 0 {
        return Err(ExecutorStaticError::InvalidPath);
    }
    if flash_amount == U256::ZERO {
        return Err(ExecutorStaticError::InvalidFlashAmount);
    }
    if first_token_in != flash_token || last_token_out != flash_token {
        return Err(ExecutorStaticError::FlashTokenMismatch);
    }
    Ok(())
}

pub fn validate_match_internal_entry(
    now: U256,
    params: &MatchParams,
) -> Result<(), ExecutorStaticError> {
    validate_match_internal_shape(
        now,
        params.expected_token_inflows.len(),
        params.expected_token_inflow_min.len(),
        params.flash_amount,
        params.deadline,
    )
}

pub fn validate_match_internal_shape(
    now: U256,
    expected_token_inflows_len: usize,
    expected_token_inflow_min_len: usize,
    flash_amount: U256,
    deadline: U256,
) -> Result<(), ExecutorStaticError> {
    if now > deadline {
        return Err(ExecutorStaticError::DeadlineExpired);
    }
    if expected_token_inflows_len != expected_token_inflow_min_len {
        return Err(ExecutorStaticError::ArrayLengthMismatch);
    }
    if flash_amount == U256::ZERO {
        return Err(ExecutorStaticError::InvalidFlashAmount);
    }
    Ok(())
}

pub fn validate_compose_four_leg_entry(
    now: U256,
    params: &ComposeParams,
) -> Result<(), ExecutorStaticError> {
    validate_compose_four_leg_shape(now, params.flash_amount, params.deadline)
}

pub fn validate_compose_four_leg_shape(
    now: U256,
    flash_amount: U256,
    deadline: U256,
) -> Result<(), ExecutorStaticError> {
    if now > deadline {
        return Err(ExecutorStaticError::DeadlineExpired);
    }
    if flash_amount == U256::ZERO {
        return Err(ExecutorStaticError::InvalidFlashAmount);
    }
    Ok(())
}

pub fn validate_uniswapx_fill_static(
    input: ExecutorUniswapXFillStatic,
) -> Result<(), ExecutorStaticError> {
    if input.reactor != input.expected_reactor {
        return Err(ExecutorStaticError::UnexpectedReactor);
    }
    if input.execute_calldata_len < 4 || input.callback_data_len == 0 {
        return Err(ExecutorStaticError::InvalidActionData);
    }
    if input.execute_selector != REACTOR_EXECUTE_BATCH_WITH_CALLBACK_SELECTOR {
        return Err(ExecutorStaticError::InvalidActionData);
    }
    Ok(())
}

pub fn validate_cow_router_start_entry(
    now: U256,
    params: &CoWFlashLoanRouterStartParams,
) -> Result<(), ExecutorStaticError> {
    validate_cow_router_start_shape(now, params.total_rounds, params.deadline)
}

pub fn validate_cow_router_start_shape(
    now: U256,
    total_rounds: U256,
    deadline: U256,
) -> Result<(), ExecutorStaticError> {
    if now > deadline {
        return Err(ExecutorStaticError::DeadlineExpired);
    }
    if total_rounds == U256::ZERO {
        return Err(ExecutorStaticError::InvalidRound);
    }
    Ok(())
}

pub fn validate_cow_round_shape(
    round: U256,
    total_rounds: U256,
) -> Result<(), ExecutorStaticError> {
    if round == U256::ZERO || total_rounds == U256::ZERO || round > total_rounds {
        return Err(ExecutorStaticError::InvalidRound);
    }
    Ok(())
}

pub fn validate_cow_final_strategy_id(strategy_id: u8) -> Result<(), ExecutorStaticError> {
    if strategy_id == 1 || strategy_id == 2 {
        Ok(())
    } else {
        Err(ExecutorStaticError::InvalidStrategyId)
    }
}

pub fn validate_swap_step_static(
    input: ExecutorSwapStepStatic,
) -> Result<U256, ExecutorStaticError> {
    if input.dex_kind == 2 {
        return Err(ExecutorStaticError::DirectPoolManagerV4Disabled);
    }
    if input.dex_kind == 5 && !input.router_is_whitelisted {
        return Err(ExecutorStaticError::RouterNotWhitelisted);
    }

    let amount_in = if input.amount_in == U256::ZERO {
        input.carry
    } else {
        input.amount_in
    };
    if amount_in == U256::ZERO {
        return Err(ExecutorStaticError::InvalidPath);
    }
    Ok(amount_in)
}

#[must_use]
pub fn swap_step_static_error_code(input: ExecutorSwapStepStatic) -> u8 {
    match validate_swap_step_static(input) {
        Ok(_) => 0,
        Err(error) => error as u8,
    }
}

pub fn validate_atomic_exec_static(input: AtomicExecStatic) -> Result<(), ExecutorStaticError> {
    if input.flash_token == Address::ZERO
        || !input.flash_token_has_code
        || input.flash_amount == U256::ZERO
    {
        return Err(ExecutorStaticError::InvalidParams);
    }
    if input.now > input.deadline {
        return Err(ExecutorStaticError::DeadlineExpired);
    }
    if AtomicStrategy::from_u8(input.strategy).is_none() {
        return Err(ExecutorStaticError::InvalidStrategy);
    }
    if AtomicFlashSource::from_u8(input.flash_source).is_none() {
        return Err(ExecutorStaticError::InvalidFlashSource);
    }
    if input.strategy_data_len == 0 {
        return Err(ExecutorStaticError::InvalidParams);
    }
    Ok(())
}

pub fn validate_atomic_compressed_static(
    input: AtomicCompressedStatic,
) -> Result<(), ExecutorStaticError> {
    if input.compressed_len > MAX_COMPRESSED_STRATEGY_DATA_BYTES {
        return Err(ExecutorStaticError::CompressedDataTooLarge);
    }
    if input.strategy_data_len > input.max_strategy_data_len {
        return Err(ExecutorStaticError::StrategyDataTooLarge);
    }
    if input.strategy_data_len > MAX_DECOMPRESSED_STRATEGY_DATA_BYTES {
        return Err(ExecutorStaticError::StrategyDataTooLarge);
    }
    if !input.strategy_data_hash_matches {
        return Err(ExecutorStaticError::PlanHashMismatch);
    }
    Ok(())
}

pub fn validate_atomic_aave_liquidation_static(
    input: AaveLiquidationStatic,
) -> Result<(), ExecutorStaticError> {
    if input.collateral_asset == Address::ZERO
        || input.debt_asset == Address::ZERO
        || input.borrower == Address::ZERO
        || input.borrower == input.executor
        || input.collateral_asset == input.debt_asset
        || input.debt_asset != input.flash_token
        || input.debt_to_cover == U256::ZERO
        || input.debt_to_cover != input.flash_amount
        || !is_v3_exact_input_path_shape(
            input.swap_path_len,
            input.collateral_asset,
            input.debt_asset,
            input.swap_path_token_in,
            input.swap_path_token_out,
        )
        || input.amount_out_minimum == U256::ZERO
    {
        return Err(ExecutorStaticError::InvalidParams);
    }
    Ok(())
}

pub fn validate_liquidation_entry_static(
    input: LiquidationEntryStatic,
) -> Result<(), ExecutorStaticError> {
    if input.collateral == Address::ZERO
        || input.debt == Address::ZERO
        || input.borrower == Address::ZERO
        || input.borrower == input.executor
        || input.collateral == input.debt
        || input.debt_amount == U256::ZERO
        || input.swap_path_len < MIN_V3_EXACT_INPUT_PATH_BYTES
    {
        return Err(ExecutorStaticError::InvalidParams);
    }
    if input.amount_out_minimum == U256::ZERO {
        return Err(ExecutorStaticError::ZeroAmountOutMinimum);
    }
    if input.now > input.deadline {
        return Err(ExecutorStaticError::DeadlineExpired);
    }
    Ok(())
}

pub fn validate_morpho_liquidation_entry_static(
    input: MorphoLiquidationEntryStatic,
) -> Result<(), ExecutorStaticError> {
    if input.collateral_token == Address::ZERO
        || input.loan_token == Address::ZERO
        || input.borrower == Address::ZERO
        || input.borrower == input.executor
        || input.seized_assets == U256::ZERO
        || input.swap_path_len < MIN_V3_EXACT_INPUT_PATH_BYTES
    {
        return Err(ExecutorStaticError::InvalidParams);
    }
    if input.amount_out_minimum == U256::ZERO {
        return Err(ExecutorStaticError::ZeroAmountOutMinimum);
    }
    if input.now > input.deadline {
        return Err(ExecutorStaticError::DeadlineExpired);
    }
    Ok(())
}

#[must_use]
pub fn is_v3_exact_input_path_shape(
    path_len: usize,
    expected_token_in: Address,
    expected_token_out: Address,
    actual_token_in: Address,
    actual_token_out: Address,
) -> bool {
    path_len >= MIN_V3_EXACT_INPUT_PATH_BYTES
        && (path_len - 20).is_multiple_of(V3_EXACT_INPUT_HOP_BYTES)
        && actual_token_in == expected_token_in
        && actual_token_out == expected_token_out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::executor_abi;

    fn token(byte: u8) -> Address {
        Address::repeat_byte(byte)
    }

    fn valid_swap() -> executor_abi::SwapStep {
        executor_abi::SwapStep {
            dex_kind: 1,
            router: token(0x99),
            call_data: alloc::vec![0xde, 0xad, 0xbe, 0xef],
            token_in: token(0x11),
            token_out: token(0x11),
            amount_in: U256::from(1),
            amount_out_min: U256::from(1),
        }
    }

    #[test]
    fn executor_family_selectors_match_solidity_artifacts() {
        assert_eq!(
            [0x13, 0xfb, 0x72, 0xc7],
            REACTOR_EXECUTE_BATCH_WITH_CALLBACK_SELECTOR
        );
        assert_eq!([0x68, 0xba, 0x2b, 0x3e], ATOMIC_EXECUTE_SELECTOR);
        assert_eq!([0xf0, 0xe4, 0x54, 0x0e], ATOMIC_EXECUTE_COMPRESSED_SELECTOR);
        assert_eq!(
            [0xc8, 0x77, 0xe1, 0x8b],
            ATOMIC_BALANCER_V3_UNLOCK_CALLBACK_SELECTOR
        );
        assert_eq!([0xf0, 0x4f, 0x27, 0x07], ATOMIC_RECEIVE_FLASH_LOAN_SELECTOR);
        assert_eq!([0x6f, 0x0c, 0xaa, 0xc9], LIQUIDATION_LIQUIDATE_SELECTOR);
        assert_eq!(
            [0x49, 0x30, 0x4b, 0xd4],
            LIQUIDATION_LIQUIDATE_MORPHO_SELECTOR
        );
        assert_eq!(
            [0xcf, 0x7e, 0xa1, 0x96],
            LIQUIDATION_ON_MORPHO_LIQUIDATE_SELECTOR
        );
    }

    #[test]
    fn executor_entry_guards_match_solidity_shape() {
        let params = executor_abi::NativeArbParams {
            flash_lender: token(0xaa),
            flash_protocol: 0,
            flash_token: token(0x11),
            flash_amount: U256::from(100),
            swaps: alloc::vec![valid_swap()],
            min_profit: U256::from(1),
            deadline: U256::from(101),
        };
        assert_eq!(Ok(()), validate_native_arb_entry(U256::from(100), &params));

        let mut bad = params.clone();
        bad.swaps[0].token_out = token(0x22);
        assert_eq!(
            Err(ExecutorStaticError::FlashTokenMismatch),
            validate_native_arb_entry(U256::from(100), &bad)
        );

        assert_eq!(
            Err(ExecutorStaticError::DeadlineExpired),
            validate_compose_four_leg_shape(U256::from(102), U256::from(1), U256::from(101))
        );
        assert_eq!(
            Err(ExecutorStaticError::ArrayLengthMismatch),
            validate_match_internal_shape(U256::from(1), 1, 2, U256::from(1), U256::from(2))
        );
    }

    #[test]
    fn executor_callback_and_round_guards_match_solidity_shape() {
        assert_eq!(
            Ok(()),
            validate_uniswapx_fill_static(ExecutorUniswapXFillStatic {
                reactor: token(0x44),
                expected_reactor: token(0x44),
                execute_calldata_len: 4,
                execute_selector: REACTOR_EXECUTE_BATCH_WITH_CALLBACK_SELECTOR,
                callback_data_len: 32,
            })
        );
        assert_eq!(
            Err(ExecutorStaticError::InvalidActionData),
            validate_uniswapx_fill_static(ExecutorUniswapXFillStatic {
                execute_selector: [0, 0, 0, 0],
                ..ExecutorUniswapXFillStatic {
                    reactor: token(0x44),
                    expected_reactor: token(0x44),
                    execute_calldata_len: 4,
                    execute_selector: REACTOR_EXECUTE_BATCH_WITH_CALLBACK_SELECTOR,
                    callback_data_len: 32,
                }
            })
        );
        assert_eq!(
            Err(ExecutorStaticError::InvalidRound),
            validate_cow_round_shape(U256::from(3), U256::from(2))
        );
        assert_eq!(Ok(()), validate_cow_final_strategy_id(1));
        assert_eq!(
            Err(ExecutorStaticError::InvalidStrategyId),
            validate_cow_final_strategy_id(0)
        );
    }

    #[test]
    fn swap_step_static_guards_match_executor_runner() {
        assert_eq!(
            Ok(U256::from(7)),
            validate_swap_step_static(ExecutorSwapStepStatic {
                dex_kind: 1,
                router_is_whitelisted: false,
                amount_in: U256::ZERO,
                carry: U256::from(7),
            })
        );
        assert_eq!(
            Err(ExecutorStaticError::DirectPoolManagerV4Disabled),
            validate_swap_step_static(ExecutorSwapStepStatic {
                dex_kind: 2,
                router_is_whitelisted: true,
                amount_in: U256::from(1),
                carry: U256::ZERO,
            })
        );
        assert_eq!(
            Err(ExecutorStaticError::RouterNotWhitelisted),
            validate_swap_step_static(ExecutorSwapStepStatic {
                dex_kind: 5,
                router_is_whitelisted: false,
                amount_in: U256::from(1),
                carry: U256::ZERO,
            })
        );
    }

    #[test]
    fn atomic_static_guards_match_solidity_preconditions() {
        assert_eq!(
            Ok(()),
            validate_atomic_exec_static(AtomicExecStatic {
                now: U256::from(100),
                flash_token: token(0xaa),
                flash_token_has_code: true,
                flash_amount: U256::from(1),
                strategy: AtomicStrategy::SettlementArb as u8,
                flash_source: AtomicFlashSource::BalancerV3 as u8,
                strategy_data_len: 32,
                deadline: U256::from(101),
            })
        );
        assert_eq!(
            Err(ExecutorStaticError::InvalidFlashSource),
            validate_atomic_exec_static(AtomicExecStatic {
                flash_source: 3,
                ..AtomicExecStatic {
                    now: U256::from(100),
                    flash_token: token(0xaa),
                    flash_token_has_code: true,
                    flash_amount: U256::from(1),
                    strategy: 1,
                    flash_source: 0,
                    strategy_data_len: 32,
                    deadline: U256::from(101),
                }
            })
        );
        assert_eq!(
            Err(ExecutorStaticError::CompressedDataTooLarge),
            validate_atomic_compressed_static(AtomicCompressedStatic {
                compressed_len: MAX_COMPRESSED_STRATEGY_DATA_BYTES + 1,
                strategy_data_len: 1,
                max_strategy_data_len: 1,
                strategy_data_hash_matches: true,
            })
        );
    }

    #[test]
    fn liquidation_entry_guards_match_solidity_preconditions() {
        let input = LiquidationEntryStatic {
            now: U256::from(100),
            executor: token(0xee),
            collateral: token(0x01),
            debt: token(0x02),
            borrower: token(0x03),
            debt_amount: U256::from(1),
            swap_path_len: MIN_V3_EXACT_INPUT_PATH_BYTES,
            amount_out_minimum: U256::from(1),
            deadline: U256::from(101),
        };
        assert_eq!(Ok(()), validate_liquidation_entry_static(input));
        assert_eq!(
            Err(ExecutorStaticError::ZeroAmountOutMinimum),
            validate_liquidation_entry_static(LiquidationEntryStatic {
                amount_out_minimum: U256::ZERO,
                ..input
            })
        );
        assert_eq!(
            Err(ExecutorStaticError::InvalidParams),
            validate_morpho_liquidation_entry_static(MorphoLiquidationEntryStatic {
                now: U256::from(100),
                executor: token(0xee),
                loan_token: token(0x02),
                collateral_token: token(0x01),
                borrower: token(0xee),
                seized_assets: U256::from(1),
                swap_path_len: MIN_V3_EXACT_INPUT_PATH_BYTES,
                amount_out_minimum: U256::from(1),
                deadline: U256::from(101),
            })
        );
    }

    #[test]
    fn v3_exact_input_path_shape_matches_solidity_formula() {
        assert!(is_v3_exact_input_path_shape(
            43,
            token(0x01),
            token(0x02),
            token(0x01),
            token(0x02)
        ));
        assert!(is_v3_exact_input_path_shape(
            66,
            token(0x01),
            token(0x03),
            token(0x01),
            token(0x03)
        ));
        assert!(!is_v3_exact_input_path_shape(
            44,
            token(0x01),
            token(0x02),
            token(0x01),
            token(0x02)
        ));
    }
}
