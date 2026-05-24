#![cfg_attr(
    not(any(test, feature = "export-abi", feature = "native-test")),
    no_main
)]

#[cfg(not(any(test, feature = "export-abi", feature = "native-test")))]
#[unsafe(no_mangle)]
pub extern "C" fn main() {}

#[cfg(feature = "native-test")]
fn main() {}

#[cfg(all(feature = "export-abi", not(feature = "native-test")))]
fn main() {
    degenbot_runtime_adapter::print_from_args();
}
