use stylus_sdk::alloy_primitives::{FixedBytes, U256, keccak256};

pub const REACTIVATION_PERIOD_SECONDS: u64 = 365 * 24 * 60 * 60;

pub fn erc1967_implementation_slot() -> FixedBytes<32> {
    let slot = U256::from_be_bytes(keccak256(b"eip1967.proxy.implementation").0) - U256::from(1);
    FixedBytes::from(slot.to_be_bytes::<32>())
}

pub fn proxiable_uuid() -> FixedBytes<32> {
    erc1967_implementation_slot()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn implementation_slot_matches_erc1967() {
        let expected = FixedBytes::<32>::from([
            0x36, 0x08, 0x94, 0xa1, 0x3b, 0xa1, 0xa3, 0x21, 0x06, 0x67, 0xc8, 0x28, 0x49, 0x2d,
            0xb9, 0x8d, 0xca, 0x3e, 0x20, 0x76, 0xcc, 0x37, 0x35, 0xa9, 0x20, 0xa3, 0xca, 0x50,
            0x5d, 0x38, 0x2b, 0xbc,
        ]);

        assert_eq!(expected, erc1967_implementation_slot());
        assert_eq!(expected, proxiable_uuid());
    }

    #[test]
    fn reactivation_window_is_one_year() {
        assert_eq!(31_536_000, REACTIVATION_PERIOD_SECONDS);
    }
}
