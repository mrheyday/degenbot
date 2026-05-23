//! Deterministic auth-layer semantics shared by the Stylus migration.
//!
//! This module ports the pure, non-storage-dependent invariants from
//! `auth/PermissionToken.sol`, `auth/StrategyLedger.sol`, and the two
//! validator contracts. Stateful mint/burn/signature-precompile behavior still
//! requires contract-specific Stylus runtime ports.

use stylus_sdk::alloy_primitives::{Address, FixedBytes, U256};

use crate::token_standard_ids;

pub const PERMISSION_TOKEN_NAME: &str = "MEV Permission";
pub const PERMISSION_TOKEN_SYMBOL: &str = "PERM";
pub const PERMISSION_TOKEN_DECIMALS: u8 = 0;

pub const STRATEGY_LEDGER_NAME: &str = "MEV Strategy Ledger";
pub const STRATEGY_LEDGER_SYMBOL: &str = "MEV-PNL";
pub const STRATEGY_LEDGER_DECIMALS: u8 = 18;

pub const SESSION_VALIDATOR_DATA_LENGTH: usize = 85;
pub const SESSION_USER_OP_SIGNATURE_LENGTH: usize = 105;
pub const PASSKEY_PUBKEY_LENGTH: usize = 64;
pub const PASSKEY_VALIDATOR_MIN_DATA_LENGTH: usize = 32;
pub const SIG_VALIDATION_FAILED: U256 = U256::from_limbs([1, 0, 0, 0]);
pub const ERC1271_MAGIC_VALUE: [u8; 4] = [0x16, 0x26, 0xba, 0x7e];
pub const ERC1271_FAILURE_VALUE: [u8; 4] = [0xff, 0xff, 0xff, 0xff];

pub const HALF_N_PLUS_1: U256 = U256::from_be_bytes([
    0x7f, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
    0x5d, 0x57, 0x6e, 0x73, 0x57, 0xa4, 0x50, 0x1d, 0xdf, 0xe9, 0x2f, 0x46, 0x68, 0x1b, 0x20, 0xa1,
]);

pub const PERMISSION_GRANT_SELECTOR: [u8; 4] = [0xa6, 0x51, 0x5b, 0xf1];
pub const PERMISSION_GRANT_BATCH_SELECTOR: [u8; 4] = [0x29, 0x22, 0x89, 0x90];
pub const PERMISSION_REVOKE_SELECTOR: [u8; 4] = [0x5c, 0xf3, 0x69, 0x3c];
pub const PERMISSION_HAS_PERMISSION_SELECTOR: [u8; 4] = [0x15, 0x77, 0x18, 0x45];
pub const STRATEGY_SET_EXECUTOR_SELECTOR: [u8; 4] = [0x1e, 0x1b, 0xff, 0x3f];
pub const STRATEGY_RECORD_PROFIT_SELECTOR: [u8; 4] = [0x3e, 0x10, 0xc1, 0x86];
pub const STRATEGY_RESET_SELECTOR: [u8; 4] = [0x10, 0x82, 0xbd, 0x73];
pub const SESSION_ADD_SELECTOR: [u8; 4] = [0x30, 0x9e, 0x48, 0xcd];
pub const SESSION_REMOVE_SELECTOR: [u8; 4] = [0x5c, 0x9f, 0xec, 0x4c];
pub const PASSKEY_ADD_SELECTOR: [u8; 4] = [0x76, 0xee, 0x7b, 0x49];
pub const PASSKEY_REMOVE_SELECTOR: [u8; 4] = [0x8c, 0xc6, 0xf4, 0x4c];
pub const VALIDATOR_VALIDATE_SELECTOR: [u8; 4] = [0x5c, 0xac, 0x52, 0x63];
pub const VALIDATOR_ERC1271_SELECTOR: [u8; 4] = ERC1271_MAGIC_VALUE;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum AuthParamError {
    InvalidParams,
    InvalidExpiry,
    InvalidPubkey,
    InvalidValidatorData,
}

#[must_use]
pub fn permission_grant_params_valid(
    account: Address,
    target: Address,
    selector: FixedBytes<4>,
) -> bool {
    account != Address::ZERO && target != Address::ZERO && selector != FixedBytes::<4>::ZERO
}

#[must_use]
pub fn permission_id(target: Address, selector: FixedBytes<4>) -> U256 {
    token_standard_ids::permission_id(target, selector)
}

#[must_use]
pub fn strategy_profit_params_valid(is_executor: bool, to: Address, amount: U256) -> bool {
    is_executor && to != Address::ZERO && amount != U256::ZERO
}

#[must_use]
pub fn strategy_id(strategy_tag: FixedBytes<32>) -> U256 {
    token_standard_ids::strategy_id(strategy_tag)
}

pub fn validate_session_registration(
    now: U256,
    signer: Address,
    expiry: U256,
) -> Result<(), AuthParamError> {
    if signer == Address::ZERO {
        return Err(AuthParamError::InvalidParams);
    }
    if expiry <= now || expiry > U256::from((1u64 << 48) - 1) {
        return Err(AuthParamError::InvalidExpiry);
    }
    Ok(())
}

#[must_use]
pub fn pack_session_validation_data(expiry: U256) -> U256 {
    expiry << 160
}

#[must_use]
pub fn session_validator_data_len_valid(len: usize) -> bool {
    len == SESSION_VALIDATOR_DATA_LENGTH
}

#[must_use]
pub fn passkey_pubkey_len_valid(len: usize) -> bool {
    len == PASSKEY_PUBKEY_LENGTH
}

#[must_use]
pub fn passkey_validator_data_len_valid(len: usize) -> bool {
    len >= PASSKEY_VALIDATOR_MIN_DATA_LENGTH
}

#[must_use]
pub fn ecdsa_s_is_malleable(s: U256) -> bool {
    s >= HALF_N_PLUS_1
}

#[cfg(test)]
mod tests {
    use super::*;
    use alloy_primitives::address;
    use stylus_sdk::alloy_primitives::keccak256;

    #[test]
    fn auth_selectors_match_solidity_artifacts() {
        assert_eq!([0xa6, 0x51, 0x5b, 0xf1], PERMISSION_GRANT_SELECTOR);
        assert_eq!([0x29, 0x22, 0x89, 0x90], PERMISSION_GRANT_BATCH_SELECTOR);
        assert_eq!([0x5c, 0xf3, 0x69, 0x3c], PERMISSION_REVOKE_SELECTOR);
        assert_eq!([0x15, 0x77, 0x18, 0x45], PERMISSION_HAS_PERMISSION_SELECTOR);
        assert_eq!([0x1e, 0x1b, 0xff, 0x3f], STRATEGY_SET_EXECUTOR_SELECTOR);
        assert_eq!([0x3e, 0x10, 0xc1, 0x86], STRATEGY_RECORD_PROFIT_SELECTOR);
        assert_eq!([0x10, 0x82, 0xbd, 0x73], STRATEGY_RESET_SELECTOR);
        assert_eq!([0x30, 0x9e, 0x48, 0xcd], SESSION_ADD_SELECTOR);
        assert_eq!([0x5c, 0x9f, 0xec, 0x4c], SESSION_REMOVE_SELECTOR);
        assert_eq!([0x76, 0xee, 0x7b, 0x49], PASSKEY_ADD_SELECTOR);
        assert_eq!([0x8c, 0xc6, 0xf4, 0x4c], PASSKEY_REMOVE_SELECTOR);
        assert_eq!([0x5c, 0xac, 0x52, 0x63], VALIDATOR_VALIDATE_SELECTOR);
        assert_eq!([0x16, 0x26, 0xba, 0x7e], VALIDATOR_ERC1271_SELECTOR);
    }

    #[test]
    fn erc6909_metadata_matches_solidity_overrides() {
        assert_eq!("MEV Permission", PERMISSION_TOKEN_NAME);
        assert_eq!("PERM", PERMISSION_TOKEN_SYMBOL);
        assert_eq!(0, PERMISSION_TOKEN_DECIMALS);
        assert_eq!("MEV Strategy Ledger", STRATEGY_LEDGER_NAME);
        assert_eq!("MEV-PNL", STRATEGY_LEDGER_SYMBOL);
        assert_eq!(18, STRATEGY_LEDGER_DECIMALS);
    }

    #[test]
    fn permission_params_and_id_match_token_standard_library() {
        let account = address!("000000000000000000000000000000000000a11c");
        let target = address!("2222222222222222222222222222222222222222");
        let selector = FixedBytes::from([0xde, 0xad, 0xbe, 0xef]);
        assert!(permission_grant_params_valid(account, target, selector));
        assert!(!permission_grant_params_valid(
            Address::ZERO,
            target,
            selector
        ));
        assert!(!permission_grant_params_valid(
            account,
            Address::ZERO,
            selector
        ));
        assert!(!permission_grant_params_valid(
            account,
            target,
            FixedBytes::<4>::ZERO
        ));
        assert_eq!(
            token_standard_ids::permission_id(target, selector),
            permission_id(target, selector)
        );
    }

    #[test]
    fn strategy_params_and_id_match_token_standard_library() {
        let to = address!("000000000000000000000000000000000000a11c");
        assert!(strategy_profit_params_valid(true, to, U256::from(1)));
        assert!(!strategy_profit_params_valid(false, to, U256::from(1)));
        assert!(!strategy_profit_params_valid(
            true,
            Address::ZERO,
            U256::from(1)
        ));
        assert!(!strategy_profit_params_valid(true, to, U256::ZERO));

        let tag = keccak256(b"strategy/native-arb");
        assert_eq!(token_standard_ids::strategy_id(tag), strategy_id(tag));
    }

    #[test]
    fn session_validator_shapes_match_solidity_constants() {
        let signer = address!("000000000000000000000000000000000000a11c");
        assert_eq!(85, SESSION_VALIDATOR_DATA_LENGTH);
        assert_eq!(105, SESSION_USER_OP_SIGNATURE_LENGTH);
        assert!(session_validator_data_len_valid(85));
        assert!(!session_validator_data_len_valid(84));
        assert_eq!(
            Ok(()),
            validate_session_registration(U256::from(99), signer, U256::from(100))
        );
        assert_eq!(
            Err(AuthParamError::InvalidParams),
            validate_session_registration(U256::from(99), Address::ZERO, U256::from(100))
        );
        assert_eq!(
            Err(AuthParamError::InvalidExpiry),
            validate_session_registration(U256::from(100), signer, U256::from(100))
        );
        assert_eq!(
            U256::from(100) << 160,
            pack_session_validation_data(U256::from(100))
        );
    }

    #[test]
    fn passkey_validator_shapes_match_solidity_contract() {
        assert!(passkey_pubkey_len_valid(64));
        assert!(!passkey_pubkey_len_valid(63));
        assert!(passkey_validator_data_len_valid(32));
        assert!(!passkey_validator_data_len_valid(31));
    }

    #[test]
    fn session_high_s_gate_matches_eip2_boundary() {
        assert!(!ecdsa_s_is_malleable(HALF_N_PLUS_1 - U256::from(1)));
        assert!(ecdsa_s_is_malleable(HALF_N_PLUS_1));
    }
}
