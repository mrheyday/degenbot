unsafe fn write_zeroes(dest: *mut u8, len: usize) {
    if !dest.is_null() {
        unsafe {
            core::ptr::write_bytes(dest, 0, len);
        }
    }
}

unsafe fn set_return_data_len(return_data_len: *mut usize, len: usize) {
    if !return_data_len.is_null() {
        unsafe {
            *return_data_len = len;
        }
    }
}

#[unsafe(no_mangle)]
pub unsafe extern "C" fn call_contract(
    _contract: *const u8,
    _calldata: *const u8,
    _calldata_len: usize,
    _value: *const u8,
    _gas: u64,
    return_data_len: *mut usize,
) -> u8 {
    unsafe {
        set_return_data_len(return_data_len, 0);
    }
    1
}

#[unsafe(no_mangle)]
pub unsafe extern "C" fn delegate_call_contract(
    _contract: *const u8,
    _calldata: *const u8,
    _calldata_len: usize,
    _gas: u64,
    return_data_len: *mut usize,
) -> u8 {
    unsafe {
        set_return_data_len(return_data_len, 0);
    }
    1
}

#[unsafe(no_mangle)]
pub extern "C" fn msg_reentrant() -> bool {
    false
}

#[unsafe(no_mangle)]
pub unsafe extern "C" fn msg_sender(sender: *mut u8) {
    unsafe {
        write_zeroes(sender, 20);
    }
}

#[unsafe(no_mangle)]
pub unsafe extern "C" fn msg_value(value: *mut u8) {
    unsafe {
        write_zeroes(value, 32);
    }
}

#[unsafe(no_mangle)]
pub extern "C" fn pay_for_memory_grow(_pages: u16) {}

#[unsafe(no_mangle)]
pub extern "C" fn read_args(_dest: *mut u8) {}

#[unsafe(no_mangle)]
pub extern "C" fn read_return_data(_dest: *mut u8, _offset: usize, _size: usize) -> usize {
    0
}

#[unsafe(no_mangle)]
pub extern "C" fn return_data_size() -> usize {
    0
}

#[unsafe(no_mangle)]
pub unsafe extern "C" fn static_call_contract(
    _contract: *const u8,
    _calldata: *const u8,
    _calldata_len: usize,
    _gas: u64,
    return_data_len: *mut usize,
) -> u8 {
    unsafe {
        set_return_data_len(return_data_len, 0);
    }
    1
}

#[unsafe(no_mangle)]
pub extern "C" fn storage_cache_bytes32(_key: *const u8, _value: *const u8) {}

#[unsafe(no_mangle)]
pub extern "C" fn storage_flush_cache(_clear: bool) {}

#[unsafe(no_mangle)]
pub unsafe extern "C" fn storage_load_bytes32(_key: *const u8, dest: *mut u8) {
    unsafe {
        write_zeroes(dest, 32);
    }
}

#[unsafe(no_mangle)]
pub extern "C" fn write_result(_data: *const u8, _len: usize) {}
