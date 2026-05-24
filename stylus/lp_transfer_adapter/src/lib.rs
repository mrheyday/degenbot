#![cfg_attr(
    not(any(test, feature = "export-abi", feature = "native-test")),
    no_main
)]
#![cfg_attr(feature = "contract-client-gen", allow(unused_imports))]
#![cfg_attr(feature = "native-test", allow(dead_code))]

extern crate alloc;

use alloc::vec::Vec;

#[cfg(not(any(test, feature = "native-test")))]
use stylus_sdk::alloy_primitives::{Address, FixedBytes, U256};

#[path = "../../core/src/lp_transfer_lib.rs"]
pub mod lp_transfer_lib;

#[cfg(all(not(any(test, feature = "native-test")), not(target_arch = "wasm32")))]
mod native_hostio_shims {
    include!("../../test_hostio_shims.rs");
}

#[cfg(not(any(test, feature = "native-test")))]
use stylus_sdk::{call::RawCall, prelude::*, stylus_core::host::AccountAccess};

pub const LP_OK: u8 = 0;
pub const LP_INVALID_PARAMS: u8 = 1;
pub const LP_TARGET_HAS_NO_CODE: u8 = 2;
pub const LP_CALL_REVERTED: u8 = 3;
pub const LP_RETURN_FALSE: u8 = 4;
pub const LP_RETURN_MALFORMED: u8 = 5;

#[cfg(not(any(test, feature = "native-test")))]
sol_storage! {
    #[entrypoint]
    pub struct LpTransferAdapter {}
}

#[cfg(not(any(test, feature = "native-test")))]
#[public]
impl LpTransferAdapter {
    pub fn lp_kind_v2_erc20(&self) -> u8 {
        lp_transfer_lib::LpKind::V2Erc20 as u8
    }

    pub fn lp_kind_v3_nft(&self) -> u8 {
        lp_transfer_lib::LpKind::V3Nft as u8
    }

    pub fn lp_kind_v4_erc6909(&self) -> u8 {
        lp_transfer_lib::LpKind::V4Erc6909 as u8
    }

    pub fn erc20_transfer_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(lp_transfer_lib::ERC20_TRANSFER)
    }

    pub fn erc721_safe_transfer_from_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(lp_transfer_lib::ERC721_SAFE_TRANSFER_FROM)
    }

    pub fn erc6909_transfer_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(lp_transfer_lib::ERC6909_TRANSFER)
    }

    pub fn erc6909_set_operator_selector(&self) -> FixedBytes<4> {
        FixedBytes::from(lp_transfer_lib::ERC6909_SET_OPERATOR)
    }

    pub fn validate_move_code(&self, lp_contract: Address, to: Address) -> u8 {
        code_from_validation(lp_transfer_lib::validate_move(lp_contract, to))
    }

    pub fn validate_set_operator_code(&self, pool_manager: Address, operator: Address) -> u8 {
        code_from_validation(lp_transfer_lib::validate_set_operator(
            pool_manager,
            operator,
        ))
    }

    pub fn encode_v2_transfer(&self, to: Address, amount: U256) -> Vec<u8> {
        lp_transfer_lib::encode_v2_transfer(to, amount)
    }

    pub fn encode_v3_safe_transfer_from(
        &self,
        from: Address,
        to: Address,
        token_id: U256,
    ) -> Vec<u8> {
        lp_transfer_lib::encode_v3_safe_transfer_from(from, to, token_id)
    }

    pub fn encode_v4_transfer(&self, to: Address, id: U256, amount: U256) -> Vec<u8> {
        lp_transfer_lib::encode_v4_transfer(to, id, amount)
    }

    pub fn encode_v4_set_operator(&self, operator: Address, approved: bool) -> Vec<u8> {
        lp_transfer_lib::encode_v4_set_operator(operator, approved)
    }

    pub fn move_v2_code(&mut self, pool: Address, amount: U256, to: Address) -> u8 {
        if let Err(error) = lp_transfer_lib::validate_move(pool, to) {
            return code_from_error(error);
        }
        if self.vm().code_size(pool) == 0 {
            return LP_TARGET_HAS_NO_CODE;
        }

        let calldata = lp_transfer_lib::encode_v2_transfer(to, amount);
        normalize_erc20_call(self.raw_mutating_call(pool, &calldata))
    }

    pub fn move_v3_code(&mut self, position_manager: Address, token_id: U256, to: Address) -> u8 {
        if let Err(error) = lp_transfer_lib::validate_move(position_manager, to) {
            return code_from_error(error);
        }
        if self.vm().code_size(position_manager) == 0 {
            return LP_TARGET_HAS_NO_CODE;
        }

        let calldata = lp_transfer_lib::encode_v3_safe_transfer_from(
            self.vm().contract_address(),
            to,
            token_id,
        );
        normalize_void_call(self.raw_mutating_call(position_manager, &calldata))
    }

    pub fn move_v4_code(
        &mut self,
        pool_manager: Address,
        id: U256,
        amount: U256,
        to: Address,
    ) -> u8 {
        if let Err(error) = lp_transfer_lib::validate_move(pool_manager, to) {
            return code_from_error(error);
        }
        if self.vm().code_size(pool_manager) == 0 {
            return LP_TARGET_HAS_NO_CODE;
        }

        let calldata = lp_transfer_lib::encode_v4_transfer(to, id, amount);
        normalize_strict_bool_call(self.raw_mutating_call(pool_manager, &calldata))
    }

    pub fn set_v4_operator_code(
        &mut self,
        pool_manager: Address,
        operator: Address,
        approved: bool,
    ) -> u8 {
        if let Err(error) = lp_transfer_lib::validate_set_operator(pool_manager, operator) {
            return code_from_error(error);
        }
        if self.vm().code_size(pool_manager) == 0 {
            return LP_TARGET_HAS_NO_CODE;
        }

        let calldata = lp_transfer_lib::encode_v4_set_operator(operator, approved);
        normalize_strict_bool_call(self.raw_mutating_call(pool_manager, &calldata))
    }
}

#[cfg(not(any(test, feature = "native-test")))]
impl LpTransferAdapter {
    fn raw_mutating_call(&mut self, target: Address, calldata: &[u8]) -> Result<Vec<u8>, Vec<u8>> {
        unsafe {
            RawCall::new(self.vm())
                .limit_return_data(0, 32)
                .flush_storage_cache()
                .call(target, calldata)
        }
    }
}

fn code_from_validation(result: Result<(), lp_transfer_lib::LpTransferError>) -> u8 {
    result.map_or_else(code_from_error, |_| LP_OK)
}

fn code_from_error(error: lp_transfer_lib::LpTransferError) -> u8 {
    match error {
        lp_transfer_lib::LpTransferError::InvalidParams => LP_INVALID_PARAMS,
        lp_transfer_lib::LpTransferError::V4TransferFailed
        | lp_transfer_lib::LpTransferError::V4SetOperatorFailed => LP_RETURN_FALSE,
    }
}

fn normalize_void_call(result: Result<Vec<u8>, Vec<u8>>) -> u8 {
    match result {
        Ok(_) => LP_OK,
        Err(_) => LP_CALL_REVERTED,
    }
}

fn normalize_erc20_call(result: Result<Vec<u8>, Vec<u8>>) -> u8 {
    match result {
        Ok(data) if data.is_empty() => LP_OK,
        Ok(data) => match decode_abi_bool(&data) {
            Some(true) => LP_OK,
            Some(false) => LP_RETURN_FALSE,
            None => LP_RETURN_MALFORMED,
        },
        Err(_) => LP_CALL_REVERTED,
    }
}

fn normalize_strict_bool_call(result: Result<Vec<u8>, Vec<u8>>) -> u8 {
    match result {
        Ok(data) => match decode_abi_bool(&data) {
            Some(true) => LP_OK,
            Some(false) => LP_RETURN_FALSE,
            None => LP_RETURN_MALFORMED,
        },
        Err(_) => LP_CALL_REVERTED,
    }
}

fn decode_abi_bool(data: &[u8]) -> Option<bool> {
    if data.len() != 32 || data[..31].iter().any(|byte| *byte != 0) {
        return None;
    }
    match data[31] {
        0 => Some(false),
        1 => Some(true),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use stylus_sdk::alloy_primitives::Address;

    #[test]
    fn erc20_normalization_matches_solady_success_cases() {
        assert_eq!(LP_OK, normalize_erc20_call(Ok(Vec::new())));

        let mut true_word = [0_u8; 32];
        true_word[31] = 1;
        assert_eq!(LP_OK, normalize_erc20_call(Ok(true_word.to_vec())));

        let mut false_word = [0_u8; 32];
        false_word[31] = 0;
        assert_eq!(
            LP_RETURN_FALSE,
            normalize_erc20_call(Ok(false_word.to_vec()))
        );
        assert_eq!(LP_RETURN_MALFORMED, normalize_erc20_call(Ok(vec![1])));
        assert_eq!(LP_CALL_REVERTED, normalize_erc20_call(Err(Vec::new())));
    }

    #[test]
    fn erc6909_normalization_requires_strict_bool() {
        assert_eq!(
            LP_RETURN_MALFORMED,
            normalize_strict_bool_call(Ok(Vec::new()))
        );

        let mut true_word = [0_u8; 32];
        true_word[31] = 1;
        assert_eq!(LP_OK, normalize_strict_bool_call(Ok(true_word.to_vec())));

        true_word[0] = 1;
        assert_eq!(
            LP_RETURN_MALFORMED,
            normalize_strict_bool_call(Ok(true_word.to_vec()))
        );
    }

    #[test]
    fn validation_codes_track_core_library_errors() {
        let pool = Address::repeat_byte(0x11);
        let to = Address::repeat_byte(0x22);

        assert_eq!(
            LP_OK,
            code_from_validation(lp_transfer_lib::validate_move(pool, to))
        );
        assert_eq!(
            LP_INVALID_PARAMS,
            code_from_validation(lp_transfer_lib::validate_move(Address::ZERO, to))
        );
        assert_eq!(
            LP_INVALID_PARAMS,
            code_from_validation(lp_transfer_lib::validate_set_operator(pool, Address::ZERO))
        );
    }
}
