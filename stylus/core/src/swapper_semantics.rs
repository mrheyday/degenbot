//! Static semantics for `swappers/MultiHopCaller.sol`.
//!
//! The runtime Universal Router execution is still a contract migration item.
//! This module ports the deterministic address constants, selectors, depth
//! floors, slippage math, and pre-external-call guards.

use alloy_primitives::address;
use stylus_sdk::alloy_primitives::{Address, U256};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum MultiHopError {
    WrongValue,
    Expired,
    SlippageOutOfRange,
    V4AmountInZero,
    MathOverflow,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct SwapStaticInput {
    pub now: U256,
    pub msg_value: U256,
    pub amount_in: U256,
    pub deadline: U256,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct DepthSnapshot {
    pub v2_weth_usdc_r0: u128,
    pub v2_arb_usdc_r1: u128,
    pub v3_weth_arb_liq: u128,
    pub v3_wsteth_weth_liq: u128,
    pub v4_wsteth_weth_liq: u128,
    pub v4_weth_arb_liq: u128,
}

pub const WETH: Address = address!("82aF49447D8a07e3bd95BD0d56f35241523fBab1");
pub const USDC: Address = address!("af88d065e77c8cC2239327C5EDb3A432268e5831");
pub const ARB: Address = address!("912CE59144191C1204E64559FE8253a0e49E6548");
pub const WSTETH: Address = address!("5979D7b546E38E414F7E9822514be443A4800529");

pub const V2_PAIR_WETH_USDC: Address = address!("F64Dfe17C8b87F012FCf50FbDA1D62bfA148366a");
pub const V2_PAIR_ARB_USDC: Address = address!("011f31D20C8778c8Beb1093b73E3A5690Ee6271b");
pub const V3_POOL_WETH_ARB: Address = address!("C6F780497A95e246EB9449f5e4770916DCd6396A");
pub const V3_POOL_WSTETH_WETH: Address = address!("35218a1cbaC5Bbc3E57fd9Bd38219D37571b3537");
pub const RECIPIENT_ROUTER: Address = address!("0000000000000000000000000000000000000002");

pub const CONTRACT_BALANCE: U256 = U256::from_be_bytes([
    0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
]);

pub const ACT_SWAP_EXACT_IN: u8 = 0x07;
pub const ACT_SETTLE_ALL: u8 = 0x0c;
pub const ACT_TAKE: u8 = 0x0e;

pub const MIN_V2_WETH_USDC_R0: u128 = 5_238_677_443_858_472_693;
pub const MIN_V2_ARB_USDC_R1: u128 = 2_116_659_189;
pub const MIN_V3_WETH_ARB_LIQ: u128 = 107_401_392_065_706_421_925_966;
pub const MIN_V3_WSTETH_WETH_LIQ: u128 = 11_718_824_313_541_001_222_374;
pub const MIN_V4_WSTETH_WETH_LIQ: u128 = 1;
pub const MIN_V4_WETH_ARB_LIQ: u128 = 1;

pub const BPS_DENOMINATOR: u64 = 10_000;
pub const MAX_AUTO_SLIPPAGE_BPS: u64 = 1_000;

pub const CHECK_DEPTH_SELECTOR: [u8; 4] = [0x02, 0xce, 0x3e, 0x5c];
pub const QUOTE_SELECTOR: [u8; 4] = [0x31, 0x5f, 0x1a, 0x41];
pub const RESCUE_NATIVE_SELECTOR: [u8; 4] = [0xc8, 0xdf, 0x42, 0x30];
pub const SWAP_SELECTOR: [u8; 4] = [0xc4, 0x5c, 0x5c, 0x30];
pub const SWAP_WITH_AUTO_SLIPPAGE_SELECTOR: [u8; 4] = [0x98, 0xb6, 0xd7, 0xda];
pub const SWAP_WITH_QUOTED_V4_INPUT_SELECTOR: [u8; 4] = [0x88, 0x11, 0x08, 0x60];

#[must_use]
pub fn depth_is_sufficient(snapshot: DepthSnapshot) -> bool {
    snapshot.v2_weth_usdc_r0 >= MIN_V2_WETH_USDC_R0
        && snapshot.v2_arb_usdc_r1 >= MIN_V2_ARB_USDC_R1
        && snapshot.v3_weth_arb_liq >= MIN_V3_WETH_ARB_LIQ
        && snapshot.v3_wsteth_weth_liq >= MIN_V3_WSTETH_WETH_LIQ
        && snapshot.v4_wsteth_weth_liq >= MIN_V4_WSTETH_WETH_LIQ
        && snapshot.v4_weth_arb_liq >= MIN_V4_WETH_ARB_LIQ
}

pub fn validate_swap_static(input: SwapStaticInput) -> Result<(), MultiHopError> {
    if input.msg_value != input.amount_in {
        return Err(MultiHopError::WrongValue);
    }
    if input.now > input.deadline {
        return Err(MultiHopError::Expired);
    }
    Ok(())
}

pub fn validate_auto_slippage(
    input: SwapStaticInput,
    slippage_bps: U256,
) -> Result<(), MultiHopError> {
    if slippage_bps > U256::from(MAX_AUTO_SLIPPAGE_BPS) {
        return Err(MultiHopError::SlippageOutOfRange);
    }
    validate_swap_static(input)
}

pub fn validate_quoted_v4_input(
    input: SwapStaticInput,
    v4_amount_in: u128,
) -> Result<(), MultiHopError> {
    validate_swap_static(input)?;
    if v4_amount_in == 0 {
        return Err(MultiHopError::V4AmountInZero);
    }
    Ok(())
}

pub fn apply_slippage(amount: U256, bps: U256) -> Result<U256, MultiHopError> {
    let denominator = U256::from(BPS_DENOMINATOR);
    if bps > denominator {
        return Err(MultiHopError::SlippageOutOfRange);
    }
    let multiplier = denominator - bps;
    amount
        .checked_mul(multiplier)
        .map(|scaled| scaled / denominator)
        .ok_or(MultiHopError::MathOverflow)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn valid_input() -> SwapStaticInput {
        SwapStaticInput {
            now: U256::from(100),
            msg_value: U256::from(1_000),
            amount_in: U256::from(1_000),
            deadline: U256::from(101),
        }
    }

    #[test]
    fn multihop_selectors_match_solidity_artifact() {
        assert_eq!([0x02, 0xce, 0x3e, 0x5c], CHECK_DEPTH_SELECTOR);
        assert_eq!([0x31, 0x5f, 0x1a, 0x41], QUOTE_SELECTOR);
        assert_eq!([0xc8, 0xdf, 0x42, 0x30], RESCUE_NATIVE_SELECTOR);
        assert_eq!([0xc4, 0x5c, 0x5c, 0x30], SWAP_SELECTOR);
        assert_eq!([0x98, 0xb6, 0xd7, 0xda], SWAP_WITH_AUTO_SLIPPAGE_SELECTOR);
        assert_eq!([0x88, 0x11, 0x08, 0x60], SWAP_WITH_QUOTED_V4_INPUT_SELECTOR);
    }

    #[test]
    fn multihop_constants_match_solidity_literals() {
        assert_eq!(WETH, address!("82aF49447D8a07e3bd95BD0d56f35241523fBab1"));
        assert_eq!(USDC, address!("af88d065e77c8cC2239327C5EDb3A432268e5831"));
        assert_eq!(0x07, ACT_SWAP_EXACT_IN);
        assert_eq!(0x0c, ACT_SETTLE_ALL);
        assert_eq!(0x0e, ACT_TAKE);
        assert_eq!(U256::from(1) << 255, CONTRACT_BALANCE);
        assert_eq!(10_000, BPS_DENOMINATOR);
        assert_eq!(1_000, MAX_AUTO_SLIPPAGE_BPS);
    }

    #[test]
    fn multihop_depth_snapshot_uses_pinned_floors() {
        let sufficient = DepthSnapshot {
            v2_weth_usdc_r0: MIN_V2_WETH_USDC_R0,
            v2_arb_usdc_r1: MIN_V2_ARB_USDC_R1,
            v3_weth_arb_liq: MIN_V3_WETH_ARB_LIQ,
            v3_wsteth_weth_liq: MIN_V3_WSTETH_WETH_LIQ,
            v4_wsteth_weth_liq: MIN_V4_WSTETH_WETH_LIQ,
            v4_weth_arb_liq: MIN_V4_WETH_ARB_LIQ,
        };
        assert!(depth_is_sufficient(sufficient));

        let thin = DepthSnapshot {
            v2_weth_usdc_r0: MIN_V2_WETH_USDC_R0 - 1,
            ..sufficient
        };
        assert!(!depth_is_sufficient(thin));
    }

    #[test]
    fn multihop_static_entrypoint_guards_match_solidity() {
        assert_eq!(Ok(()), validate_swap_static(valid_input()));
        assert_eq!(
            Ok(()),
            validate_auto_slippage(valid_input(), U256::from(1_000))
        );
        assert_eq!(Ok(()), validate_quoted_v4_input(valid_input(), 1));

        assert_eq!(
            Err(MultiHopError::WrongValue),
            validate_swap_static(SwapStaticInput {
                msg_value: U256::from(999),
                ..valid_input()
            })
        );
        assert_eq!(
            Err(MultiHopError::Expired),
            validate_swap_static(SwapStaticInput {
                now: U256::from(102),
                ..valid_input()
            })
        );
        assert_eq!(
            Err(MultiHopError::SlippageOutOfRange),
            validate_auto_slippage(valid_input(), U256::from(1_001))
        );
        assert_eq!(
            Err(MultiHopError::V4AmountInZero),
            validate_quoted_v4_input(valid_input(), 0)
        );
    }

    #[test]
    fn multihop_slippage_math_matches_solidity_formula() {
        assert_eq!(
            Ok(U256::from(9_900)),
            apply_slippage(U256::from(10_000), U256::from(100))
        );
        assert_eq!(
            Ok(U256::from(9_000)),
            apply_slippage(U256::from(10_000), U256::from(1_000))
        );
        assert_eq!(
            Err(MultiHopError::SlippageOutOfRange),
            apply_slippage(U256::from(10_000), U256::from(10_001))
        );
    }
}
