#![cfg_attr(not(any(test, feature = "export-abi")), no_main)]
#![cfg_attr(feature = "contract-client-gen", allow(unused_imports))]

extern crate alloc;

use alloy_sol_types::sol;
use stylus_sdk::{
    abi::Bytes,
    alloy_primitives::Address,
    call::static_call,
    prelude::*,
};

sol_storage! {
    #[entrypoint]
    pub struct PoolAdapter {
        address owner;
        address pool;
        bool initialized;
    }
}

sol! {
    error AlreadyInitialized();
    error Unauthorized(address caller);
    error ZeroPoolAddress();
    error PoolStaticCallFailed();
}

#[derive(SolidityError)]
pub enum PoolAdapterError {
    AlreadyInitialized(AlreadyInitialized),
    Unauthorized(Unauthorized),
    ZeroPoolAddress(ZeroPoolAddress),
    PoolStaticCallFailed(PoolStaticCallFailed),
}

#[public]
impl PoolAdapter {
    pub fn initialize(&mut self, pool: Address) -> Result<(), PoolAdapterError> {
        if self.initialized.get() {
            return Err(PoolAdapterError::AlreadyInitialized(AlreadyInitialized {}));
        }
        if pool == Address::ZERO {
            return Err(PoolAdapterError::ZeroPoolAddress(ZeroPoolAddress {}));
        }

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
        if pool == Address::ZERO {
            return Err(PoolAdapterError::ZeroPoolAddress(ZeroPoolAddress {}));
        }
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

#[cfg(test)]
mod tests {
    use super::*;
    use stylus_sdk::testing::TestVM;

    #[test]
    fn initialize_sets_owner_and_pool() {
        let vm = TestVM::default();
        let mut adapter = PoolAdapter::from(&vm);
        let pool = Address::repeat_byte(0x11);

        assert!(adapter.initialize(pool).is_ok());

        assert_eq!(pool, adapter.pool());
        assert_eq!(vm.msg_sender(), adapter.owner());
    }
}
