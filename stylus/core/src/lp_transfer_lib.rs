use alloc::vec::Vec;

use stylus_sdk::alloy_primitives::{Address, U256};

pub const ERC20_TRANSFER: [u8; 4] = [0xa9, 0x05, 0x9c, 0xbb];
pub const ERC721_SAFE_TRANSFER_FROM: [u8; 4] = [0x42, 0x84, 0x2e, 0x0e];
pub const ERC6909_TRANSFER: [u8; 4] = [0x09, 0x5b, 0xcd, 0xb6];
pub const ERC6909_SET_OPERATOR: [u8; 4] = [0x55, 0x8a, 0x72, 0x97];

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum LpKind {
    V2Erc20 = 0,
    V3Nft = 1,
    V4Erc6909 = 2,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum LpTransferError {
    InvalidParams,
    V4TransferFailed,
    V4SetOperatorFailed,
}

pub fn validate_move(lp_contract: Address, to: Address) -> Result<(), LpTransferError> {
    if lp_contract == Address::ZERO || to == Address::ZERO {
        Err(LpTransferError::InvalidParams)
    } else {
        Ok(())
    }
}

pub fn validate_set_operator(
    pool_manager: Address,
    operator: Address,
) -> Result<(), LpTransferError> {
    if pool_manager == Address::ZERO || operator == Address::ZERO {
        Err(LpTransferError::InvalidParams)
    } else {
        Ok(())
    }
}

pub fn encode_v2_transfer(to: Address, amount: U256) -> Vec<u8> {
    encode_selector_address_u256(ERC20_TRANSFER, to, amount)
}

pub fn encode_v3_safe_transfer_from(from: Address, to: Address, token_id: U256) -> Vec<u8> {
    let mut out = Vec::with_capacity(4 + 32 * 3);
    out.extend_from_slice(&ERC721_SAFE_TRANSFER_FROM);
    push_address_word(&mut out, from);
    push_address_word(&mut out, to);
    push_u256_word(&mut out, token_id);
    out
}

pub fn encode_v4_transfer(to: Address, id: U256, amount: U256) -> Vec<u8> {
    let mut out = Vec::with_capacity(4 + 32 * 3);
    out.extend_from_slice(&ERC6909_TRANSFER);
    push_address_word(&mut out, to);
    push_u256_word(&mut out, id);
    push_u256_word(&mut out, amount);
    out
}

pub fn encode_v4_set_operator(operator: Address, approved: bool) -> Vec<u8> {
    let mut out = Vec::with_capacity(4 + 32 * 2);
    out.extend_from_slice(&ERC6909_SET_OPERATOR);
    push_address_word(&mut out, operator);
    push_bool_word(&mut out, approved);
    out
}

fn encode_selector_address_u256(selector: [u8; 4], address: Address, value: U256) -> Vec<u8> {
    let mut out = Vec::with_capacity(4 + 32 * 2);
    out.extend_from_slice(&selector);
    push_address_word(&mut out, address);
    push_u256_word(&mut out, value);
    out
}

fn push_address_word(out: &mut Vec<u8>, address: Address) {
    out.extend_from_slice(&[0u8; 12]);
    out.extend_from_slice(address.as_slice());
}

fn push_u256_word(out: &mut Vec<u8>, value: U256) {
    out.extend_from_slice(&value.to_be_bytes::<32>());
}

fn push_bool_word(out: &mut Vec<u8>, value: bool) {
    out.extend_from_slice(&[0u8; 31]);
    out.push(u8::from(value));
}
