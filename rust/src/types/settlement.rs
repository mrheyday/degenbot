//! Phase I — Settlement (Rust canonical mirror of the on-chain
//! `Settlement` struct).
//!
//! The Settlement payload is the result-of-execution event the Rust
//! engine emits over the IPC socket once a Plan has finished its
//! lifecycle (broadcast and mined, broadcast and reverted, dropped
//! pre-inclusion, REVM-rejected at preflight, or hit by an internal
//! error). The `coordinator/src/types/settlement.ts` is the TS mirror
//! and `coordinator/src/types/fixtures.json` (the `settlements` array)
//! is the byte-level cross-language lock.
//!
//! ## sol! form vs JSON wire form
//!
//! The struct is declared via alloy's `sol!` so the on-chain ABI shape
//! stays centralized, but **the Settlement is not ABI-encoded for any
//! on-chain call** in v1 — it lives purely on the IPC channel as JSON.
//! The actual cross-language byte lock is `WireSettlement` in
//! [`super::wire`]. Keep the sol! declaration here for two reasons:
//!
//! 1. If a future on-chain consumer (e.g., a settlement attestation
//!    contract) wants to ingest a Settlement, the encoder is one
//!    `abi_encode()` call away.
//! 2. Centralizes the schema source of truth — the field types and
//!    field order match the IExecutor.sol declaration exactly.
//!
//! ## Result enum
//!
//! `SettlementResult` is lowered by alloy's `sol!` to a bare `u8`
//! field, so we provide a separate Rust enum [`SettlementResultKind`]
//! with explicit `repr(u8)` discriminants and `name()` / `from_name()`
//! / `from_ordinal()` accessors. The JSON wire form carries the
//! variant **NAME string** (`"Included"`, …), not the ordinal —
//! [`super::wire::WireSettlement`] handles the conversion.
//!
//! Locked ordinal table (matches `IExecutor.sol`):
//!
//! | ordinal | name              | when emitted                                              |
//! |--------:|-------------------|-----------------------------------------------------------|
//! | 0       | `Included`        | tx mined, status=true                                     |
//! | 1       | `Reverted`        | tx mined, status=false                                    |
//! | 2       | `Dropped`         | not included within `Plan.deadline`                       |
//! | 3       | `PreflightFailed` | REVM simulation rejected the plan; no broadcast attempted |
//! | 4       | `Error`           | internal engine error before broadcast                    |
//!
//! Adding a variant is a wire-protocol break — bump
//! [`SETTLEMENT_VERSION`] when that lands.
//!
//! ## Spec pointers
//!
//! - `coordinator/src/types/settlement.ts` — TS canonical mirror.
//! - `coordinator/src/types/settlement-wire.ts` — TS JSON codec.
//! - `coordinator/src/types/settlement-README.md` — wire-format invariants.
//! - `coordinator/src/types/fixtures.json` (`settlements` array) — byte-level lock.

use alloy::sol;

sol! {
    /// SettlementResult ordinal — locked to the Solidity `enum SettlementResult`.
    /// 0=Included, 1=Reverted, 2=Dropped, 3=PreflightFailed, 4=Error.
    type SettlementResult is uint8;

    /// Result-of-execution payload emitted by the engine once a Plan has
    /// finished its lifecycle. See module docs for the full state machine.
    /// Field order MUST match `IExecutor.sol`.
    #[derive(Debug)]
    struct Settlement {
        bytes32 planId;
        uint8   version;
        SettlementResult result;
        bytes32 txHash;
        uint64  block;
        uint64  gasUsed;
        uint256 preflightDelta;
        uint256 gasEstimate;
        string  error;
    }
}

// ---------------------------------------------------------------------------
// SettlementResultKind — Rust mirror with explicit ordinals + name accessors.
// ---------------------------------------------------------------------------

/// Result of a Plan's execution lifecycle. Discriminants match the Solidity
/// `enum SettlementResult` ordinals exactly (locked at module level via the
/// `sol!` declaration above and the `WireSettlement` lock test).
///
/// alloy lowers `type SettlementResult is uint8;` to a bare `u8` field, so
/// this enum exists separately to give Rust call sites a typed view + the
/// `name()` / `from_name()` / `from_ordinal()` accessors needed by the JSON
/// wire codec.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
#[repr(u8)]
pub enum SettlementResultKind {
    /// 0 — tx mined, status=true (happy path).
    Included = 0,
    /// 1 — tx mined, status=false (on-chain assertion / OOG).
    Reverted = 1,
    /// 2 — not included within `Plan.deadline`; never broadcast or dropped
    /// from the mempool without inclusion.
    Dropped = 2,
    /// 3 — REVM simulation rejected the plan; no broadcast attempted.
    PreflightFailed = 3,
    /// 4 — internal engine error before broadcast (nonce manager unavailable,
    /// signing fault, …).
    Error = 4,
}

impl SettlementResultKind {
    /// Variant NAME as it appears on the JSON wire form. Matches the TS
    /// `SettlementResultName` map and the `result` field in
    /// `coordinator/src/types/fixtures.json`.
    #[must_use]
    pub const fn name(&self) -> &'static str {
        match self {
            Self::Included => "Included",
            Self::Reverted => "Reverted",
            Self::Dropped => "Dropped",
            Self::PreflightFailed => "PreflightFailed",
            Self::Error => "Error",
        }
    }

    /// Parse a wire `result` string into a `SettlementResultKind`. Returns
    /// `None` for unknown names — callers (typically the JSON codec) MUST
    /// surface an error rather than silently coerce.
    #[must_use]
    pub fn from_name(s: &str) -> Option<Self> {
        match s {
            "Included" => Some(Self::Included),
            "Reverted" => Some(Self::Reverted),
            "Dropped" => Some(Self::Dropped),
            "PreflightFailed" => Some(Self::PreflightFailed),
            "Error" => Some(Self::Error),
            _ => None,
        }
    }

    /// Lift the underlying ordinal back into the typed kind. Returns `None`
    /// for any byte > 4 — a stricter behaviour than the C-style numeric
    /// fall-through alloy's `From<u8>` newtype wrapper provides for the
    /// `sol!`-generated `SettlementResult`.
    #[must_use]
    pub const fn from_ordinal(u: u8) -> Option<Self> {
        match u {
            0 => Some(Self::Included),
            1 => Some(Self::Reverted),
            2 => Some(Self::Dropped),
            3 => Some(Self::PreflightFailed),
            4 => Some(Self::Error),
            _ => None,
        }
    }

    /// Numeric ordinal — equivalent to `*self as u8`, exposed as a method
    /// so call sites stay readable (`kind.ordinal()`) instead of casting.
    #[must_use]
    pub const fn ordinal(&self) -> u8 {
        *self as u8
    }
}

// ---------------------------------------------------------------------------
// Constants — wire protocol version + canonical zero literal.
// ---------------------------------------------------------------------------

/// Phase I wire-protocol version. Bumped any time a Settlement field is
/// added, removed, or its semantics change. The `version` field on
/// [`Settlement`] / [`super::wire::WireSettlement`] carries this value.
pub const SETTLEMENT_VERSION: u8 = 1;

#[cfg(test)]
mod tests {
    use super::*;

    /// `name()` must reproduce the exact strings the TS encoder emits and
    /// `fixtures.json` records. Drift here = wire-protocol break.
    #[test]
    fn settlement_result_kind_name_matches_locked_strings() {
        assert_eq!(SettlementResultKind::Included.name(), "Included");
        assert_eq!(SettlementResultKind::Reverted.name(), "Reverted");
        assert_eq!(SettlementResultKind::Dropped.name(), "Dropped");
        assert_eq!(
            SettlementResultKind::PreflightFailed.name(),
            "PreflightFailed"
        );
        assert_eq!(SettlementResultKind::Error.name(), "Error");
    }

    /// Round-trip every variant through `name()` ↔ `from_name()`.
    #[test]
    fn settlement_result_kind_name_round_trip() {
        for kind in [
            SettlementResultKind::Included,
            SettlementResultKind::Reverted,
            SettlementResultKind::Dropped,
            SettlementResultKind::PreflightFailed,
            SettlementResultKind::Error,
        ] {
            let name = kind.name();
            let back = SettlementResultKind::from_name(name)
                .unwrap_or_else(|| panic!("from_name({name:?}) returned None"));
            assert_eq!(back, kind, "round-trip diverged for {name:?}");
        }
    }

    /// `from_name` rejects unknown strings — silent coercion would leak past
    /// the wire boundary and produce malformed Settlement payloads.
    #[test]
    fn settlement_result_kind_from_name_rejects_unknown() {
        assert!(
            SettlementResultKind::from_name("included").is_none(),
            "case-sensitive"
        );
        assert!(SettlementResultKind::from_name("").is_none());
        assert!(SettlementResultKind::from_name("Success").is_none());
    }

    /// Round-trip every ordinal through `ordinal()` ↔ `from_ordinal()`.
    #[test]
    fn settlement_result_kind_ordinal_round_trip() {
        for raw in 0u8..=4 {
            let kind = SettlementResultKind::from_ordinal(raw)
                .unwrap_or_else(|| panic!("from_ordinal({raw}) returned None"));
            assert_eq!(kind.ordinal(), raw, "ordinal round-trip diverged at {raw}");
        }
    }

    /// `from_ordinal` rejects out-of-range bytes. Trips on unsigned-overflow
    /// silent acceptance (alloy's user-defined-uint8-newtype `From<u8>`
    /// would happily accept any byte; we want stricter here).
    #[test]
    fn settlement_result_kind_from_ordinal_rejects_out_of_range() {
        assert!(SettlementResultKind::from_ordinal(5).is_none());
        assert!(SettlementResultKind::from_ordinal(255).is_none());
    }

    /// Locked discriminants — the `repr(u8)` ordinals MUST match the
    /// Solidity enum ordering. Casting via `as u8` is the cheapest way to
    /// observe each variant's discriminant directly.
    #[test]
    fn settlement_result_kind_discriminants_locked() {
        assert_eq!(SettlementResultKind::Included as u8, 0);
        assert_eq!(SettlementResultKind::Reverted as u8, 1);
        assert_eq!(SettlementResultKind::Dropped as u8, 2);
        assert_eq!(SettlementResultKind::PreflightFailed as u8, 3);
        assert_eq!(SettlementResultKind::Error as u8, 4);
    }

    /// Sanity-check the locked wire-protocol version. Bumping this is the
    /// signal to coordinator + python solver that a schema break is in
    /// flight; this test should fail and force an explicit rev.
    #[test]
    fn settlement_version_is_one() {
        assert_eq!(SETTLEMENT_VERSION, 1);
    }
}
