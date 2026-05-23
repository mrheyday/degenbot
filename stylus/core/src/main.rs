#![cfg_attr(
    not(any(test, feature = "export-abi", feature = "native-test")),
    no_main
)]

#[cfg(not(any(test, feature = "export-abi", feature = "native-test")))]
#[unsafe(no_mangle)]
pub extern "C" fn main() {}

#[cfg(all(feature = "native-test", not(feature = "export-abi")))]
fn main() {}

#[cfg(feature = "export-abi")]
fn main() {
    degenbot_stylus_core::print_from_args();
}
