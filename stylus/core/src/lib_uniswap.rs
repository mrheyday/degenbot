use alloy_primitives::fixed_bytes;
use stylus_sdk::alloy_primitives::{Address, FixedBytes, keccak256};

pub const V3_POOL_INIT_CODE_HASH: FixedBytes<32> =
    fixed_bytes!("0xe34f199b19b2b4f47f68442619d555527d244f78a3297ea89325f843f87b8b54");
pub const V2_PAIR_INIT_CODE_HASH: FixedBytes<32> =
    fixed_bytes!("0xe18a34eb0f55c3c04145d80d1e4ca51e60f06e67614e59f4f46927d63659223a");

pub fn compute_v3_address(
    factory: Address,
    token_a: Address,
    token_b: Address,
    fee: u32,
) -> Address {
    let (token0, token1) = sort_tokens(token_a, token_b);
    let mut abi_encoded = [0u8; 96];
    abi_encoded[12..32].copy_from_slice(token0.as_slice());
    abi_encoded[44..64].copy_from_slice(token1.as_slice());
    abi_encoded[92..96].copy_from_slice(&fee.to_be_bytes());
    create2_address(factory, keccak256(abi_encoded), V3_POOL_INIT_CODE_HASH)
}

pub fn compute_v2_address(factory: Address, token_a: Address, token_b: Address) -> Address {
    let (token0, token1) = sort_tokens(token_a, token_b);
    let mut packed = [0u8; 40];
    packed[..20].copy_from_slice(token0.as_slice());
    packed[20..].copy_from_slice(token1.as_slice());
    create2_address(factory, keccak256(packed), V2_PAIR_INIT_CODE_HASH)
}

fn sort_tokens(token_a: Address, token_b: Address) -> (Address, Address) {
    if token_a < token_b {
        (token_a, token_b)
    } else {
        (token_b, token_a)
    }
}

fn create2_address(
    factory: Address,
    salt: FixedBytes<32>,
    init_code_hash: FixedBytes<32>,
) -> Address {
    let mut packed = [0u8; 85];
    packed[0] = 0xff;
    packed[1..21].copy_from_slice(factory.as_slice());
    packed[21..53].copy_from_slice(salt.as_slice());
    packed[53..85].copy_from_slice(init_code_hash.as_slice());
    let hash = keccak256(packed);
    Address::from_slice(&hash.as_slice()[12..])
}
