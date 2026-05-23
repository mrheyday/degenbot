use alloc::vec;
use alloc::vec::Vec;
use stylus_sdk::alloy_primitives::{Address, U256};

pub fn address(value: Address) -> Vec<Address> {
    vec![value]
}

pub fn u256(value: U256) -> Vec<U256> {
    vec![value]
}

pub fn bytes(value: Vec<u8>) -> Vec<Vec<u8>> {
    vec![value]
}
