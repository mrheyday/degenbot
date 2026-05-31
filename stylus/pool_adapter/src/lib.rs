#![cfg_attr(
    not(any(test, feature = "export-abi", feature = "native-test")),
    no_main
)]
#![cfg_attr(feature = "contract-client-gen", allow(unused_imports))]

extern crate alloc;

#[cfg(all(not(any(test, feature = "native-test")), not(target_arch = "wasm32")))]
mod native_hostio_shims {
    include!("../../test_hostio_shims.rs");
}

#[cfg(not(any(test, feature = "native-test")))]
use alloy_sol_types::sol;
use stylus_sdk::alloy_primitives::Address;
#[cfg(not(any(test, feature = "native-test")))]
use stylus_sdk::alloy_primitives::U256;
#[cfg(not(any(test, feature = "native-test")))]
use stylus_sdk::{abi::Bytes, call::static_call, prelude::*};

#[cfg(not(any(test, feature = "native-test")))]
sol_storage! {
    #[entrypoint]
    pub struct PoolAdapter {
        address owner;
        address pool;
        bool initialized;
    }
}

#[cfg(not(any(test, feature = "native-test")))]
sol! {
    error AlreadyInitialized();
    error Unauthorized(address caller);
    error ZeroPoolAddress();
    error PoolStaticCallFailed();
    error InvalidV2ReturnData();
    error InvalidV3ReturnData();
}

#[cfg(not(any(test, feature = "native-test")))]
const GET_RESERVES_SELECTOR: [u8; 4] = [0x09, 0x02, 0xf1, 0xac];
#[cfg(not(any(test, feature = "native-test")))]
const SLOT0_SELECTOR: [u8; 4] = [0x38, 0x50, 0xc7, 0xbd];
#[cfg(not(any(test, feature = "native-test")))]
const LIQUIDITY_SELECTOR: [u8; 4] = [0x1a, 0x68, 0x65, 0x02];

#[cfg(any(test, feature = "native-test"))]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ZeroPoolAddress {}

#[cfg(any(test, feature = "native-test"))]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PoolAdapterError {
    ZeroPoolAddress(ZeroPoolAddress),
}

#[cfg(not(any(test, feature = "native-test")))]
#[derive(SolidityError)]
pub enum PoolAdapterError {
    AlreadyInitialized(AlreadyInitialized),
    Unauthorized(Unauthorized),
    ZeroPoolAddress(ZeroPoolAddress),
    PoolStaticCallFailed(PoolStaticCallFailed),
    InvalidV2ReturnData(InvalidV2ReturnData),
    InvalidV3ReturnData(InvalidV3ReturnData),
}

#[cfg(not(any(test, feature = "native-test")))]
#[public]
impl PoolAdapter {
    pub fn initialize(&mut self, pool: Address) -> Result<(), PoolAdapterError> {
        if self.initialized.get() {
            return Err(PoolAdapterError::AlreadyInitialized(AlreadyInitialized {}));
        }
        ensure_nonzero_pool(pool)?;

        self.owner.set(self.vm().msg_sender());
        self.pool.set(pool);
        self.initialized.set(true);
        Ok(())
    }

    pub fn owner(&self) -> Address {
        self.owner.get()
    }

    pub fn pool(&self) -> Address {
        self.pool.get()
    }

    pub fn set_pool(&mut self, pool: Address) -> Result<(), PoolAdapterError> {
        self.only_owner()?;
        ensure_nonzero_pool(pool)?;
        self.pool.set(pool);
        Ok(())
    }

    pub fn read_pool(&self, calldata: Bytes) -> Result<Bytes, PoolAdapterError> {
        let pool = self.pool.get();
        if pool == Address::ZERO {
            return Err(PoolAdapterError::ZeroPoolAddress(ZeroPoolAddress {}));
        }

        let calldata = calldata.to_vec();
        let returndata = static_call(self.vm(), Call::new(), pool, calldata.as_slice())
            .map_err(|_| PoolAdapterError::PoolStaticCallFailed(PoolStaticCallFailed {}))?;
        Ok(returndata.into())
    }

    /// Read Uniswap V2 (or compatible) pool reserves.
    /// Returns (reserve0, reserve1, blockTimestampLast)
    pub fn read_v2_reserves(&self) -> Result<(u128, u128, u32), PoolAdapterError> {
        let pool = self.pool.get();
        if pool == Address::ZERO {
            return Err(PoolAdapterError::ZeroPoolAddress(ZeroPoolAddress {}));
        }

        let returndata = static_call(self.vm(), Call::new(), pool, &GET_RESERVES_SELECTOR)
            .map_err(|_| PoolAdapterError::PoolStaticCallFailed(PoolStaticCallFailed {}))?;
        let data = returndata.as_slice();
        if data.len() < 96 {
            return Err(PoolAdapterError::InvalidV2ReturnData(
                InvalidV2ReturnData {},
            ));
        }

        Ok((
            read_uint112(data, 0).ok_or(PoolAdapterError::InvalidV2ReturnData(
                InvalidV2ReturnData {},
            ))?,
            read_uint112(data, 32).ok_or(PoolAdapterError::InvalidV2ReturnData(
                InvalidV2ReturnData {},
            ))?,
            read_uint32(data, 64).ok_or(PoolAdapterError::InvalidV2ReturnData(
                InvalidV2ReturnData {},
            ))?,
        ))
    }

    /// Read Uniswap V3 (or compatible) pool state.
    /// Returns (sqrtPriceX96, tick, liquidity)
    pub fn read_v3_state(&self) -> Result<(U256, i32, u128), PoolAdapterError> {
        let pool = self.pool.get();
        if pool == Address::ZERO {
            return Err(PoolAdapterError::ZeroPoolAddress(ZeroPoolAddress {}));
        }

        let slot0 = static_call(self.vm(), Call::new(), pool, &SLOT0_SELECTOR)
            .map_err(|_| PoolAdapterError::PoolStaticCallFailed(PoolStaticCallFailed {}))?;
        let slot0_data = slot0.as_slice();
        if slot0_data.len() < 224 {
            return Err(PoolAdapterError::InvalidV3ReturnData(
                InvalidV3ReturnData {},
            ));
        }

        let liquidity = static_call(self.vm(), Call::new(), pool, &LIQUIDITY_SELECTOR)
            .map_err(|_| PoolAdapterError::PoolStaticCallFailed(PoolStaticCallFailed {}))?;
        let liquidity_data = liquidity.as_slice();
        if liquidity_data.len() < 32 {
            return Err(PoolAdapterError::InvalidV3ReturnData(
                InvalidV3ReturnData {},
            ));
        }

        Ok((
            read_uint160_as_u256(slot0_data, 0).ok_or(PoolAdapterError::InvalidV3ReturnData(
                InvalidV3ReturnData {},
            ))?,
            read_int24(slot0_data, 32).ok_or(PoolAdapterError::InvalidV3ReturnData(
                InvalidV3ReturnData {},
            ))?,
            read_uint128(liquidity_data, 0).ok_or(PoolAdapterError::InvalidV3ReturnData(
                InvalidV3ReturnData {},
            ))?,
        ))
    }

    /// Read Uniswap V4 pool state from PoolManager.
    /// Returns (sqrtPriceX96, tick, liquidity)
    pub fn read_v4_state(
        &self,
        pool_id: stylus_sdk::alloy_primitives::FixedBytes<32>,
    ) -> Result<(U256, i32, u128), PoolAdapterError> {
        let manager = self.pool.get();
        if manager == Address::ZERO {
            return Err(PoolAdapterError::ZeroPoolAddress(ZeroPoolAddress {}));
        }

        // V4 StateLibrary logic:
        // pools_slot = bytes32(uint256(6))
        // state_slot = keccak256(abi.encode(poolId, pools_slot))
        let mut packed = [0u8; 64];
        packed[..32].copy_from_slice(pool_id.as_slice());
        packed[60..64].copy_from_slice(&6u32.to_be_bytes());
        let state_slot = stylus_sdk::alloy_primitives::keccak256(packed);

        // extsload(bytes32,uint256) selector: 0x93786196? No.
        // extsload(bytes32) is 0x104e8a93
        // extsload(bytes32,uint256) is 0x140ed97c

        let mut extsload_calldata = [0u8; 68];
        extsload_calldata[..4].copy_from_slice(&[0x14, 0x0e, 0xd9, 0x7c]);
        extsload_calldata[4..36].copy_from_slice(state_slot.as_slice());
        extsload_calldata[67] = 4; // n_slots = 4

        let returndata = static_call(self.vm(), Call::new(), manager, &extsload_calldata)
            .map_err(|_| PoolAdapterError::PoolStaticCallFailed(PoolStaticCallFailed {}))?;

        let data = returndata.as_slice();
        // The return is bytes32[] which is 32 + (n * 32) bytes
        // Word 0: length (4)
        // Word 1: slot0
        // Word 2: feeGrowth0
        // Word 3: feeGrowth1
        // Word 4: liquidity
        if data.len() < 160 {
            return Err(PoolAdapterError::PoolStaticCallFailed(
                PoolStaticCallFailed {},
            ));
        }

        let slot0 = &data[32..64];
        let sqrt_price_x96 = U256::from_be_slice(&slot0[12..32]);
        let tick_bytes = [slot0[9], slot0[10], slot0[11]];
        let tick = read_int24_from_3bytes(tick_bytes);

        let liquidity_word = &data[128..160];
        let liquidity = u128::from_be_bytes(liquidity_word[16..32].try_into().unwrap());

        Ok((sqrt_price_x96, tick, liquidity))
    }

    /// Read Curve pool state (balances and amplification coefficient).
    /// Returns (balances, A)
    pub fn read_curve_state(&self, n_coins: u8) -> Result<(Vec<U256>, U256), PoolAdapterError> {
        let pool = self.pool.get();
        if pool == Address::ZERO {
            return Err(PoolAdapterError::ZeroPoolAddress(ZeroPoolAddress {}));
        }

        let mut balances = Vec::with_capacity(n_coins as usize);
        for i in 0..n_coins {
            let mut calldata = [0u8; 36];
            calldata[..4].copy_from_slice(&[0x4f, 0x03, 0xaa, 0x3d]); // balances(uint256)
            calldata[35] = i;

            let res = static_call(self.vm(), Call::new(), pool, &calldata)
                .map_err(|_| PoolAdapterError::PoolStaticCallFailed(PoolStaticCallFailed {}))?;
            if res.len() < 32 {
                return Err(PoolAdapterError::PoolStaticCallFailed(
                    PoolStaticCallFailed {},
                ));
            }
            balances.push(U256::from_be_slice(res.as_slice()));
        }

        let a_selector = [0xf4, 0x46, 0xc1, 0xd0]; // A()
        let a_res = static_call(self.vm(), Call::new(), pool, &a_selector)
            .map_err(|_| PoolAdapterError::PoolStaticCallFailed(PoolStaticCallFailed {}))?;
        if a_res.len() < 32 {
            return Err(PoolAdapterError::PoolStaticCallFailed(
                PoolStaticCallFailed {},
            ));
        }
        let a = U256::from_be_slice(a_res.as_slice());

        Ok((balances, a))
    }

    fn only_owner(&self) -> Result<(), PoolAdapterError> {
        let caller = self.vm().msg_sender();
        if caller != self.owner.get() {
            return Err(PoolAdapterError::Unauthorized(Unauthorized { caller }));
        }
        Ok(())
    }
}

#[cfg_attr(feature = "native-test", allow(dead_code))]
fn ensure_nonzero_pool(pool: Address) -> Result<(), PoolAdapterError> {
    if pool == Address::ZERO {
        return Err(PoolAdapterError::ZeroPoolAddress(ZeroPoolAddress {}));
    }
    Ok(())
}

#[cfg(not(any(test, feature = "native-test")))]
fn read_int24_from_3bytes(bytes: [u8; 3]) -> i32 {
    let raw = i32::from_be_bytes([0, bytes[0], bytes[1], bytes[2]]);
    if (raw & 0x0080_0000) == 0 {
        raw
    } else {
        raw | !0x00ff_ffff
    }
}

#[cfg(not(any(test, feature = "native-test")))]
fn read_uint112(data: &[u8], offset: usize) -> Option<u128> {
    read_uint128_with_max_prefix(data, offset, 18)
}

#[cfg(not(any(test, feature = "native-test")))]
fn read_uint128(data: &[u8], offset: usize) -> Option<u128> {
    read_uint128_with_max_prefix(data, offset, 16)
}

#[cfg(not(any(test, feature = "native-test")))]
fn read_uint160_as_u256(data: &[u8], offset: usize) -> Option<U256> {
    let word = data.get(offset..offset.checked_add(32)?)?;
    if word[..12].iter().any(|byte| *byte != 0) {
        return None;
    }
    Some(U256::from_be_slice(word))
}

#[cfg(not(any(test, feature = "native-test")))]
fn read_uint32(data: &[u8], offset: usize) -> Option<u32> {
    let word = data.get(offset..offset.checked_add(32)?)?;
    if word[..28].iter().any(|byte| *byte != 0) {
        return None;
    }
    Some(u32::from_be_bytes(word[28..32].try_into().ok()?))
}

#[cfg(not(any(test, feature = "native-test")))]
fn read_int24(data: &[u8], offset: usize) -> Option<i32> {
    let word = data.get(offset..offset.checked_add(32)?)?;
    let sign = if (word[29] & 0x80) == 0 { 0x00 } else { 0xff };
    if word[..29].iter().any(|byte| *byte != sign) {
        return None;
    }

    let raw = i32::from_be_bytes([0, word[29], word[30], word[31]]);
    if (raw & 0x0080_0000) == 0 {
        Some(raw)
    } else {
        Some(raw | !0x00ff_ffff)
    }
}

#[cfg(not(any(test, feature = "native-test")))]
fn read_uint128_with_max_prefix(
    data: &[u8],
    offset: usize,
    zero_prefix_len: usize,
) -> Option<u128> {
    let word = data.get(offset..offset.checked_add(32)?)?;
    if word[..zero_prefix_len].iter().any(|byte| *byte != 0) {
        return None;
    }
    Some(u128::from_be_bytes(word[16..32].try_into().ok()?))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pool_address_validation_rejects_zero_address() {
        assert!(matches!(
            ensure_nonzero_pool(Address::ZERO),
            Err(PoolAdapterError::ZeroPoolAddress(_))
        ));
        assert!(ensure_nonzero_pool(Address::repeat_byte(0x11)).is_ok());
    }
}
