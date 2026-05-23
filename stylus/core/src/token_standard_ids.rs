use stylus_sdk::alloy_primitives::{Address, FixedBytes, U256, keccak256};

pub const IERC165_ID: [u8; 4] = [0x01, 0xff, 0xc9, 0xa7];
pub const IERC1271_ID: [u8; 4] = [0x16, 0x26, 0xba, 0x7e];
pub const IERC721_RECEIVER_ID: [u8; 4] = [0x15, 0x0b, 0x7a, 0x02];
pub const IERC1155_RECEIVER_ID: [u8; 4] = [0x4e, 0x23, 0x12, 0xe0];
pub const IERC1155_SINGLE_RECEIVED_RET: [u8; 4] = [0xf2, 0x3a, 0x6e, 0x61];
pub const IERC1155_BATCH_RECEIVED_RET: [u8; 4] = [0xbc, 0x19, 0x7c, 0x81];
pub const IACCOUNT_VALIDATE_USER_OP: [u8; 4] = [0x19, 0x82, 0x2f, 0x7c];
pub const IERC3156_FLASH_BORROWER_ID: [u8; 4] = [0x23, 0xe3, 0x0c, 0x8b];

const DOMAIN_PERMISSION: &[u8] = b"perm:";
const DOMAIN_STRATEGY_LEDGER: &[u8] = b"strategy:";
const DOMAIN_PAYMASTER_POOL: &[u8] = b"pool:";
const DOMAIN_INFLIGHT: &[u8] = b"inflight:";

pub fn permission_id(target: Address, selector: FixedBytes<4>) -> U256 {
    let mut input = [0u8; 29];
    input[..DOMAIN_PERMISSION.len()].copy_from_slice(DOMAIN_PERMISSION);
    input[DOMAIN_PERMISSION.len()..DOMAIN_PERMISSION.len() + 20].copy_from_slice(target.as_slice());
    input[DOMAIN_PERMISSION.len() + 20..].copy_from_slice(selector.as_slice());
    U256::from_be_bytes(keccak256(input).0)
}

pub fn strategy_id(strategy_tag: FixedBytes<32>) -> U256 {
    hash_prefixed_32(DOMAIN_STRATEGY_LEDGER, strategy_tag)
}

pub fn paymaster_pool_id(pool_tag: FixedBytes<32>) -> U256 {
    hash_prefixed_32(DOMAIN_PAYMASTER_POOL, pool_tag)
}

pub fn inflight_id(asset: Address) -> U256 {
    let mut input = [0u8; 29];
    input[..DOMAIN_INFLIGHT.len()].copy_from_slice(DOMAIN_INFLIGHT);
    input[DOMAIN_INFLIGHT.len()..].copy_from_slice(asset.as_slice());
    U256::from_be_bytes(keccak256(input).0)
}

fn hash_prefixed_32(prefix: &[u8], body: FixedBytes<32>) -> U256 {
    let mut input = [0u8; 41];
    input[..prefix.len()].copy_from_slice(prefix);
    input[prefix.len()..prefix.len() + 32].copy_from_slice(body.as_slice());
    U256::from_be_bytes(keccak256(&input[..prefix.len() + 32]).0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn constants_match_solidity_library() {
        assert_eq!([0x01, 0xff, 0xc9, 0xa7], IERC165_ID);
        assert_eq!([0x16, 0x26, 0xba, 0x7e], IERC1271_ID);
        assert_eq!([0x23, 0xe3, 0x0c, 0x8b], IERC3156_FLASH_BORROWER_ID);
    }

    #[test]
    fn ids_are_domain_separated() {
        let tag = FixedBytes::<32>::repeat_byte(0x11);
        assert_ne!(strategy_id(tag), paymaster_pool_id(tag));
    }
}
