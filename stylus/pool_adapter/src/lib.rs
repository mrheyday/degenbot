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
}

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
