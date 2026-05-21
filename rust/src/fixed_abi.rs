//! Type-safe ABI helpers for stable hot-path contracts.
//!
//! Dynamic ABI handling remains the generic fallback for user-supplied signatures.
//! Fixed, high-volume interfaces live here so calldata and return decoding are
//! checked by Alloy's `sol!` bindings at compile time.

use crate::errors::{ContractError, ContractResult};
use alloy::primitives::{Address, Bytes, U256};
use alloy::sol;
use alloy::sol_types::SolCall;

sol! {
    #[allow(missing_docs)]
    interface IERC20View {
        function balanceOf(address owner) external view returns (uint256);
        function totalSupply() external view returns (uint256);
    }
}

/// Build calldata for `IERC20.balanceOf(address)`.
#[must_use]
pub fn erc20_balance_of_calldata(owner: Address) -> Bytes {
    Bytes::from(IERC20View::balanceOfCall { owner }.abi_encode())
}

/// Build calldata for `IERC20.totalSupply()`.
#[must_use]
pub fn erc20_total_supply_calldata() -> Bytes {
    Bytes::from(IERC20View::totalSupplyCall.abi_encode())
}

/// Decode a single `uint256` return value from an ERC-20 view call.
///
/// # Errors
///
/// Returns `ContractError::DecodingError` if the return data is not a single ABI
/// encoded `uint256`.
pub fn decode_erc20_u256_return(data: &[u8]) -> ContractResult<U256> {
    IERC20View::balanceOfCall::abi_decode_returns(data).map_err(|e| ContractError::DecodingError {
        message: format!("invalid ERC-20 uint256 return: {e}"),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use alloy::hex;

    #[test]
    fn erc20_balance_of_calldata_uses_static_selector() {
        let owner = Address::repeat_byte(0x11);
        let calldata = erc20_balance_of_calldata(owner);

        assert_eq!(&calldata[..4], &hex!("70a08231"));
        assert_eq!(calldata.len(), 36);
    }

    #[test]
    fn erc20_total_supply_calldata_uses_static_selector() {
        let calldata = erc20_total_supply_calldata();

        assert_eq!(&calldata[..], &hex!("18160ddd"));
    }

    #[test]
    fn decode_erc20_u256_return_decodes_single_word() {
        let value = U256::from(123_u64);
        let encoded = alloy::sol_types::SolValue::abi_encode(&value);

        match decode_erc20_u256_return(&encoded) {
            Ok(decoded) => assert_eq!(decoded, value),
            Err(err) => panic!("decode_erc20_u256_return failed: {err}"),
        }
    }
}
