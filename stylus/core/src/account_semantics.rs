//! Runtime-adjacent static semantics for `auth/*`.
//!
//! This module ports account, paymaster, and CoWShed guards that are
//! deterministic before storage mutation or external protocol calls. It is not
//! a storage-layout or token-flow runtime replacement.

use alloy_primitives::address;
use stylus_sdk::alloy_primitives::{Address, FixedBytes, U256};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum AccountStaticError {
    InvalidParams = 1,
    ThresholdOutOfRange = 2,
    Erc6909OperatorBlocked = 3,
    TransferRequiresZeroApproved = 4,
    SetOperatorRequiresZeroIdAndAmount = 5,
    UnsupportedFlashLender = 6,
    InvalidSignatureLength = 7,
    InvalidPaymasterData = 8,
    MarkupTooHigh = 9,
    BudgetExceeded = 10,
    InvalidPoolId = 11,
    InvalidImplementation = 12,
    Unauthorized = 13,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum Erc6909Op {
    Transfer = 0,
    SetOperator = 1,
}

impl Erc6909Op {
    pub fn from_u8(value: u8) -> Option<Self> {
        match value {
            0 => Some(Self::Transfer),
            1 => Some(Self::SetOperator),
            _ => None,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Erc6909CallStatic {
    pub op: u8,
    pub token: Address,
    pub counterparty: Address,
    pub id: U256,
    pub amount: U256,
    pub approved: bool,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct SafeFinancePlanStatic {
    pub flash_lender: Address,
    pub flash_asset: Address,
    pub flash_amount: U256,
    pub aave_pool: Address,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct PaymasterErc20ConfigStatic {
    pub token: Address,
    pub token_oracle: Address,
    pub treasury: Address,
    pub max_staleness: u32,
    pub markup_bps: u16,
    pub oracle_decimals: u8,
}

pub const ENTRY_POINT_V06: Address = address!("5FF137D4b0FDCD49DcA30c7CF57E578a026d2789");
pub const ENTRY_POINT_V07: Address = address!("0000000071727De22E5E9d8BAf0edAc6f37da032");
pub const ENTRY_POINT_V08: Address = address!("4337084D9E255Ff0702461CF8895CE9E3b5Ff108");
pub const ENTRY_POINT_V09: Address = address!("0A630a99Df908A81115A3022927Be82f9299987e");
pub const BEBE_DELEGATE: Address = address!("00000000BEBEDB7C30ee418158e26E31a5A8f3E2");

pub const BALANCER_V2_VAULT: Address = address!("BA12222222228d8Ba445958a75a0704d566BF2C8");
pub const BALANCER_V3_VAULT: Address = address!("bA1333333333a1BA1108E8412f11850A5C319bA9");
pub const AAVE_V3_POOL: Address = address!("794a61358D6845594F94dc1DB02A252b5b4814aD");
pub const MORPHO_BLUE: Address = address!("6c247b1F6182318877311737BaC0844bAa518F5e");

pub const ERC1271_MAGIC: [u8; 4] = [0x16, 0x26, 0xba, 0x7e];
pub const SELECTOR_LENGTH: usize = 4;
pub const ERC6909_SET_OPERATOR_SELECTOR: [u8; 4] = [0x55, 0x8a, 0x72, 0x97];
pub const ERC6909_APPROVE_SELECTOR: [u8; 4] = [0x42, 0x6a, 0x84, 0x93];
pub const EIP7702_PREFIX: [u8; 3] = [0xef, 0x01, 0x00];
pub const INITCODE_EIP7702_MARKER: [u8; 2] = [0x77, 0x02];

pub const SAFE_EXECUTE_SELECTOR: [u8; 4] = [0x5c, 0x1c, 0x6d, 0xcd];
pub const SAFE_EXECUTE_BATCH_SELECTOR: [u8; 4] = [0x34, 0xfc, 0xd5, 0xbe];
pub const SAFE_EXECUTE_ERC6909_BATCH_SELECTOR: [u8; 4] = [0x42, 0x03, 0xa9, 0x34];
pub const SAFE_FLASH_COLLATERALIZE_SELECTOR: [u8; 4] = [0x53, 0x03, 0xad, 0x28];
pub const SAFE_FLASH_COLLATERALIZE_V3_SELECTOR: [u8; 4] = [0x8f, 0x20, 0x5a, 0x1d];
pub const SAFE_VALIDATE_USER_OP_SELECTOR: [u8; 4] = [0x19, 0x82, 0x2f, 0x7c];

pub const BOT_EXECUTE_SELECTOR: [u8; 4] = [0xb6, 0x1d, 0x27, 0xf6];
pub const BOT_SET_VALIDATOR_SELECTOR: [u8; 4] = [0x46, 0x23, 0xc9, 0x1d];
pub const BOT_RECEIVE_ERC3009_SELECTOR: [u8; 4] = [0xbd, 0x37, 0x10, 0xb0];
pub const BOT_TRANSFER_ERC3009_SELECTOR: [u8; 4] = [0xe9, 0x50, 0x05, 0x29];

pub const SAFE_FACTORY_DEPLOY_SELECTOR: [u8; 4] = [0xb0, 0x31, 0x10, 0x79];
pub const SAFE_FACTORY_PREDICT_SELECTOR: [u8; 4] = [0xae, 0xfb, 0x4a, 0xbc];
pub const SAFE_FACTORY_SALT_FOR_SELECTOR: [u8; 4] = [0xdf, 0x25, 0xdf, 0xf9];

pub const PAYMASTER_V06_VALIDATE_SELECTOR: [u8; 4] = [0xf4, 0x65, 0xc7, 0x7e];
pub const PAYMASTER_V07_VALIDATE_SELECTOR: [u8; 4] = [0x52, 0xb7, 0x51, 0x2c];
pub const PAYMASTER_V06_POST_OP_SELECTOR: [u8; 4] = [0xa9, 0xa2, 0x34, 0x09];
pub const PAYMASTER_V07_POST_OP_SELECTOR: [u8; 4] = [0x7c, 0x62, 0x7b, 0x21];
pub const PAYMASTER_SET_TUNING_SELECTOR: [u8; 4] = [0x6c, 0xa1, 0x8f, 0xc6];
pub const PAYMASTER_SET_ERC20_CONFIG_SELECTOR: [u8; 4] = [0x2a, 0x89, 0x5f, 0x35];
pub const PAYMASTER_SET_TRUSTED_DELEGATE_SELECTOR: [u8; 4] = [0xb1, 0xc5, 0xaf, 0x77];

pub const COWSHED_EXECUTE_HOOKS_SELECTOR: [u8; 4] = [0xff, 0xda, 0xce, 0xfc];
pub const COWSHED_TRUSTED_EXECUTE_HOOKS_SELECTOR: [u8; 4] = [0xc7, 0x64, 0xc6, 0x15];
pub const COWSHED_INITIALIZE_SELECTOR: [u8; 4] = [0x40, 0x0a, 0xda, 0x75];
pub const COWSHED_UPDATE_TRUSTED_EXECUTOR_SELECTOR: [u8; 4] = [0xf9, 0xb1, 0x94, 0xe1];
pub const COWSHED_UPDATE_IMPLEMENTATION_SELECTOR: [u8; 4] = [0x02, 0x5b, 0x22, 0xbc];

pub const MODE_ETH: u8 = 0;
pub const MODE_ERC20: u8 = 1;
pub const CTX_ETH: u8 = 0;
pub const CTX_ERC20: u8 = 1;
pub const CTX_POOL_ETH: u8 = 2;
pub const CTX_POOL_ERC20: u8 = 3;
pub const CHAINLINK_USD_DECIMALS: u8 = 8;
pub const MAX_MARKUP_BPS: u16 = 5_000;
pub const ERC20_PAYMASTER_DATA_LENGTH: usize = 53;
pub const PENALTY_GAS_THRESHOLD: u64 = 40_000;
pub const PENALTY_PERCENT: u64 = 10;
pub const MAX_POOL_ID_EXCLUSIVE: U256 = U256::from_limbs([0, 1, 0, 0]);

#[must_use]
pub fn error_code(result: Result<(), AccountStaticError>) -> u8 {
    match result {
        Ok(()) => 0,
        Err(error) => error as u8,
    }
}

#[must_use]
pub fn is_entry_point(addr: Address) -> bool {
    matches!(
        addr,
        ENTRY_POINT_V06 | ENTRY_POINT_V07 | ENTRY_POINT_V08 | ENTRY_POINT_V09
    )
}

pub fn validate_threshold(threshold: U256, signer_count: U256) -> Result<(), AccountStaticError> {
    if threshold == U256::ZERO || threshold > signer_count {
        return Err(AccountStaticError::ThresholdOutOfRange);
    }
    Ok(())
}

pub fn validate_nonzero_account(account: Address) -> Result<(), AccountStaticError> {
    if account == Address::ZERO {
        return Err(AccountStaticError::InvalidParams);
    }
    Ok(())
}

pub fn validate_safe_execute(target: Address, selector: [u8; 4]) -> Result<(), AccountStaticError> {
    if target == Address::ZERO {
        return Err(AccountStaticError::InvalidParams);
    }
    if is_blocked_erc6909_authority_selector(selector) {
        return Err(AccountStaticError::Erc6909OperatorBlocked);
    }
    Ok(())
}

#[must_use]
pub fn is_blocked_erc6909_authority_selector(selector: [u8; 4]) -> bool {
    selector == ERC6909_SET_OPERATOR_SELECTOR || selector == ERC6909_APPROVE_SELECTOR
}

pub fn validate_erc6909_call(input: Erc6909CallStatic) -> Result<(), AccountStaticError> {
    if input.token == Address::ZERO || input.counterparty == Address::ZERO {
        return Err(AccountStaticError::InvalidParams);
    }
    match Erc6909Op::from_u8(input.op) {
        Some(Erc6909Op::Transfer) => {
            if input.approved {
                return Err(AccountStaticError::TransferRequiresZeroApproved);
            }
        }
        Some(Erc6909Op::SetOperator) => {
            if input.id != U256::ZERO || input.amount != U256::ZERO {
                return Err(AccountStaticError::SetOperatorRequiresZeroIdAndAmount);
            }
        }
        None => return Err(AccountStaticError::InvalidParams),
    }
    Ok(())
}

pub fn validate_safe_finance_plan(input: SafeFinancePlanStatic) -> Result<(), AccountStaticError> {
    if input.flash_lender == Address::ZERO
        || input.flash_asset == Address::ZERO
        || input.flash_amount == U256::ZERO
        || input.aave_pool == Address::ZERO
    {
        return Err(AccountStaticError::InvalidParams);
    }
    if input.flash_lender != BALANCER_V2_VAULT {
        return Err(AccountStaticError::UnsupportedFlashLender);
    }
    Ok(())
}

pub fn validate_safe_finance_v3_plan(
    input: SafeFinancePlanStatic,
) -> Result<(), AccountStaticError> {
    if input.flash_asset == Address::ZERO
        || input.flash_amount == U256::ZERO
        || input.aave_pool == Address::ZERO
    {
        return Err(AccountStaticError::InvalidParams);
    }
    Ok(())
}

#[must_use]
pub fn signature_kind(signature_len: usize) -> u8 {
    if signature_len == 64 || signature_len == 65 {
        1
    } else if signature_len >= 21 {
        2
    } else {
        0
    }
}

pub fn validate_modular_signature_len(signature_len: usize) -> Result<(), AccountStaticError> {
    if signature_kind(signature_len) == 0 {
        return Err(AccountStaticError::InvalidSignatureLength);
    }
    Ok(())
}

pub fn validate_paymaster_tuning(
    max_wei_per_epoch: U256,
    epoch_length: u64,
) -> Result<(), AccountStaticError> {
    if max_wei_per_epoch == U256::ZERO || epoch_length == 0 {
        return Err(AccountStaticError::InvalidParams);
    }
    Ok(())
}

pub fn validate_paymaster_erc20_config(
    input: PaymasterErc20ConfigStatic,
) -> Result<(), AccountStaticError> {
    if input.token == Address::ZERO
        || input.token_oracle == Address::ZERO
        || input.treasury == Address::ZERO
        || input.max_staleness == 0
    {
        return Err(AccountStaticError::InvalidParams);
    }
    if input.markup_bps > MAX_MARKUP_BPS {
        return Err(AccountStaticError::MarkupTooHigh);
    }
    if input.oracle_decimals != CHAINLINK_USD_DECIMALS {
        return Err(AccountStaticError::InvalidParams);
    }
    Ok(())
}

pub fn validate_paymaster_data_shape(len: usize, first_byte: u8) -> Result<u8, AccountStaticError> {
    if len == 0 {
        return Ok(MODE_ETH);
    }
    if first_byte == MODE_ETH {
        return if len == 1 {
            Ok(MODE_ETH)
        } else {
            Err(AccountStaticError::InvalidPaymasterData)
        };
    }
    if first_byte != MODE_ERC20 || len != ERC20_PAYMASTER_DATA_LENGTH {
        return Err(AccountStaticError::InvalidPaymasterData);
    }
    Ok(MODE_ERC20)
}

pub fn validate_budget_reservation(
    spent: U256,
    reservation: U256,
    max_wei_per_epoch: U256,
) -> Result<(), AccountStaticError> {
    match spent.checked_add(reservation) {
        Some(projected) if projected <= max_wei_per_epoch => Ok(()),
        _ => Err(AccountStaticError::BudgetExceeded),
    }
}

pub fn validate_pool_id(pool_id: U256, allow_zero: bool) -> Result<(), AccountStaticError> {
    if (!allow_zero && pool_id == U256::ZERO) || pool_id >= MAX_POOL_ID_EXCLUSIVE {
        return Err(AccountStaticError::InvalidPoolId);
    }
    Ok(())
}

#[must_use]
pub fn encode_pool_token_id(pool_id: U256, token: Address) -> U256 {
    let mut token_word = [0_u8; 32];
    token_word[12..].copy_from_slice(token.as_slice());
    (pool_id << 160) | U256::from_be_bytes(token_word)
}

pub fn validate_cowshed_initialize(
    admin: Address,
    already_initialized: bool,
) -> Result<(), AccountStaticError> {
    if already_initialized {
        return Err(AccountStaticError::Unauthorized);
    }
    if admin == Address::ZERO {
        return Err(AccountStaticError::InvalidParams);
    }
    Ok(())
}

pub fn validate_cowshed_update_implementation(
    implementation: Address,
    implementation_has_code: bool,
) -> Result<(), AccountStaticError> {
    if implementation == Address::ZERO || !implementation_has_code {
        return Err(AccountStaticError::InvalidImplementation);
    }
    Ok(())
}

pub fn validate_cowshed_execute_hooks(
    call_count: usize,
    nonce_used: bool,
    signature_len: usize,
) -> Result<(), AccountStaticError> {
    if call_count == 0 {
        return Err(AccountStaticError::InvalidParams);
    }
    if nonce_used {
        return Err(AccountStaticError::Unauthorized);
    }
    validate_modular_signature_len(signature_len)
}

#[must_use]
pub fn fixed4(bytes: [u8; 4]) -> FixedBytes<4> {
    FixedBytes::from(bytes)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn token(byte: u8) -> Address {
        Address::repeat_byte(byte)
    }

    #[test]
    fn account_selectors_match_foundry_artifacts() {
        assert_eq!([0x5c, 0x1c, 0x6d, 0xcd], SAFE_EXECUTE_SELECTOR);
        assert_eq!([0x34, 0xfc, 0xd5, 0xbe], SAFE_EXECUTE_BATCH_SELECTOR);
        assert_eq!(
            [0x42, 0x03, 0xa9, 0x34],
            SAFE_EXECUTE_ERC6909_BATCH_SELECTOR
        );
        assert_eq!([0xb6, 0x1d, 0x27, 0xf6], BOT_EXECUTE_SELECTOR);
        assert_eq!([0x52, 0xb7, 0x51, 0x2c], PAYMASTER_V07_VALIDATE_SELECTOR);
        assert_eq!([0xf4, 0x65, 0xc7, 0x7e], PAYMASTER_V06_VALIDATE_SELECTOR);
        assert_eq!([0xff, 0xda, 0xce, 0xfc], COWSHED_EXECUTE_HOOKS_SELECTOR);
        assert_eq!([0xb0, 0x31, 0x10, 0x79], SAFE_FACTORY_DEPLOY_SELECTOR);
    }

    #[test]
    fn entry_points_and_erc7702_markers_are_pinned() {
        assert!(is_entry_point(ENTRY_POINT_V06));
        assert!(is_entry_point(ENTRY_POINT_V07));
        assert!(is_entry_point(ENTRY_POINT_V08));
        assert!(is_entry_point(ENTRY_POINT_V09));
        assert!(!is_entry_point(token(0x55)));
        assert_eq!([0xef, 0x01, 0x00], EIP7702_PREFIX);
        assert_eq!([0x77, 0x02], INITCODE_EIP7702_MARKER);
    }

    #[test]
    fn safe_control_guards_match_solidity_shape() {
        assert_eq!(Ok(()), validate_threshold(U256::from(2), U256::from(3)));
        assert_eq!(
            Err(AccountStaticError::ThresholdOutOfRange),
            validate_threshold(U256::ZERO, U256::from(3))
        );
        assert_eq!(
            Ok(()),
            validate_safe_execute(token(0x11), [0xde, 0xad, 0xbe, 0xef])
        );
        assert_eq!(
            Err(AccountStaticError::Erc6909OperatorBlocked),
            validate_safe_execute(token(0x11), ERC6909_SET_OPERATOR_SELECTOR)
        );
    }

    #[test]
    fn erc6909_discriminated_union_is_enforced() {
        assert_eq!(
            Ok(()),
            validate_erc6909_call(Erc6909CallStatic {
                op: Erc6909Op::Transfer as u8,
                token: token(0x01),
                counterparty: token(0x02),
                id: U256::from(1),
                amount: U256::from(2),
                approved: false,
            })
        );
        assert_eq!(
            Err(AccountStaticError::TransferRequiresZeroApproved),
            validate_erc6909_call(Erc6909CallStatic {
                approved: true,
                ..Erc6909CallStatic {
                    op: Erc6909Op::Transfer as u8,
                    token: token(0x01),
                    counterparty: token(0x02),
                    id: U256::from(1),
                    amount: U256::from(2),
                    approved: false,
                }
            })
        );
        assert_eq!(
            Err(AccountStaticError::SetOperatorRequiresZeroIdAndAmount),
            validate_erc6909_call(Erc6909CallStatic {
                op: Erc6909Op::SetOperator as u8,
                id: U256::from(1),
                ..Erc6909CallStatic {
                    op: Erc6909Op::SetOperator as u8,
                    token: token(0x01),
                    counterparty: token(0x02),
                    id: U256::ZERO,
                    amount: U256::ZERO,
                    approved: true,
                }
            })
        );
    }

    #[test]
    fn safe_finance_guards_match_v2_and_v3_entrypoints() {
        assert_eq!(
            Ok(()),
            validate_safe_finance_plan(SafeFinancePlanStatic {
                flash_lender: BALANCER_V2_VAULT,
                flash_asset: token(0x01),
                flash_amount: U256::from(1),
                aave_pool: AAVE_V3_POOL,
            })
        );
        assert_eq!(
            Err(AccountStaticError::UnsupportedFlashLender),
            validate_safe_finance_plan(SafeFinancePlanStatic {
                flash_lender: BALANCER_V3_VAULT,
                flash_asset: token(0x01),
                flash_amount: U256::from(1),
                aave_pool: AAVE_V3_POOL,
            })
        );
        assert_eq!(
            Ok(()),
            validate_safe_finance_v3_plan(SafeFinancePlanStatic {
                flash_lender: Address::ZERO,
                flash_asset: token(0x01),
                flash_amount: U256::from(1),
                aave_pool: AAVE_V3_POOL,
            })
        );
    }

    #[test]
    fn paymaster_static_guards_match_solidity_shape() {
        assert_eq!(Ok(()), validate_paymaster_tuning(U256::from(1), 1));
        assert_eq!(
            Err(AccountStaticError::MarkupTooHigh),
            validate_paymaster_erc20_config(PaymasterErc20ConfigStatic {
                token: token(0x01),
                token_oracle: token(0x02),
                treasury: token(0x03),
                max_staleness: 1,
                markup_bps: MAX_MARKUP_BPS + 1,
                oracle_decimals: CHAINLINK_USD_DECIMALS,
            })
        );
        assert_eq!(Ok(MODE_ETH), validate_paymaster_data_shape(0, 0));
        assert_eq!(Ok(MODE_ETH), validate_paymaster_data_shape(1, MODE_ETH));
        assert_eq!(
            Ok(MODE_ERC20),
            validate_paymaster_data_shape(ERC20_PAYMASTER_DATA_LENGTH, MODE_ERC20)
        );
        assert_eq!(
            Err(AccountStaticError::InvalidPaymasterData),
            validate_paymaster_data_shape(2, MODE_ETH)
        );
        assert_eq!(
            Err(AccountStaticError::BudgetExceeded),
            validate_budget_reservation(U256::from(90), U256::from(11), U256::from(100))
        );
    }

    #[test]
    fn pool_token_ids_use_uint96_uint160_layout() {
        assert_eq!(Ok(()), validate_pool_id(U256::from(1), false));
        assert_eq!(
            Err(AccountStaticError::InvalidPoolId),
            validate_pool_id(U256::ZERO, false)
        );
        let id = encode_pool_token_id(U256::from(7), token(0xab));
        assert_eq!(U256::from(7), id >> 160);
        assert_eq!(token(0xab).as_slice(), &id.to_be_bytes::<32>()[12..]);
    }

    #[test]
    fn cowshed_static_guards_match_entrypoint_shape() {
        assert_eq!(Ok(()), validate_cowshed_initialize(token(0x01), false));
        assert_eq!(
            Err(AccountStaticError::Unauthorized),
            validate_cowshed_initialize(token(0x01), true)
        );
        assert_eq!(
            Err(AccountStaticError::InvalidImplementation),
            validate_cowshed_update_implementation(token(0x02), false)
        );
        assert_eq!(Ok(()), validate_cowshed_execute_hooks(1, false, 65));
        assert_eq!(
            Err(AccountStaticError::InvalidSignatureLength),
            validate_cowshed_execute_hooks(1, false, 20)
        );
    }
}
