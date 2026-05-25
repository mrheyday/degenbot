//! Rust canonical mirror of `contracts/src/interfaces/IExecutor.sol`.
//!
//! Phase F (Rust half). The submodules form the engine's typed view of the
//! Executor's strategy entry points and the wire format the coordinator
//! (`coordinator/src/types/`) and Python solver
//! (`solver/driver/types/`) share with us via `coordinator/src/types/fixtures.json`.
//!
//! - [`executor`] — `sol!`-generated structs: `SwapStep`, `NativeArbParams`,
//!   `MatchParams`, `ComposeParams` and the call types
//!   `executeNativeArbCall`, `matchInternalCall`, `composeFourLegCall`.
//!   ABI-encoding these types produces calldata byte-identical to viem's
//!   `encodeFunctionData` and the on-chain interface.
//! - [`wire`] — serde-friendly counterpart structs (`Wire*`) that round-trip
//!   the cross-language fixture JSON: camelCase keys, decimal-string `U256`,
//!   `0x...` lowercase hex `Bytes`, checksummed addresses. Carries
//!   `From<WireXxx> for sol::Xxx` bridges for the engine's hot path.
//!
//! See `engine/src/types/README.md` for the locking mechanism + spec
//! pointers.

pub mod executor;
pub mod settlement;
pub mod wire;

// Convenience re-exports for engine call sites.
pub use executor::{
    composeFourLegCall, executeNativeArbCall, matchInternalCall, ComposeParams, DexKind,
    FlashProtocol, MatchParams, NativeArbParams, SwapStep,
};
pub use wire::{
    WireComposeParams, WireMatchParams, WireNativeArbParams, WireSettlement, WireSwapStep,
};
