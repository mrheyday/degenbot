# `engine/src/types/` — Rust canonical mirror of `IExecutor.sol`

Phase F (Rust half). Defines the on-chain struct shapes the engine ABI-encodes when composing
calldata for `Executor.executeNativeArb`, `Executor.matchInternal`, and `Executor.composeFourLeg`.
Sibling mirrors: `coordinator/src/types/` (TS, source of `fixtures.json`) and `solver/driver/types/`
(Python). All three are locked against the same fixture snapshot — divergence is a wire-protocol
break.

Phase I (Rust half) extends this with `Settlement` — the result-of-execution payload the engine
emits over IPC once a Plan has finished its lifecycle. Settlement lives purely on the IPC channel as
JSON (no on-chain ABI use in v1) and is locked byte-for-byte against the `settlements` array in the
same fixture snapshot.

## Files

| File            | Role                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `executor.rs`   | alloy `sol!`-generated `SwapStep`, `NativeArbParams`, `MatchParams`, `ComposeParams` and the call types `executeNativeArbCall` / `matchInternalCall` / `composeFourLegCall`. Selectors locked in unit tests.                                                                                                                                                                                                                                                                                                         |
| `settlement.rs` | alloy `sol!`-generated `Settlement` struct + `SettlementResult` user-defined uint8 type. Plus the Rust mirror enum `SettlementResultKind` (`Included=0` … `Error=4`) with `name()` / `from_name()` / `from_ordinal()` accessors used by the wire codec. Locked `SETTLEMENT_VERSION = 1`.                                                                                                                                                                                                                             |
| `wire.rs`       | serde mirror structs (`WireSwapStep`, `WireNativeArbParams`, `WireMatchParams`, `WireComposeParams`, `WireSettlement`) for the cross-language fixture format. Decimal-string adapters (`decimal_u256`, `decimal_u256_vec`, `decimal_u64`). `From<WireXxx> for sol::Xxx` bridges (Phase F structs only — `WireSettlement` ↔ sol::Settlement is omitted because Settlement is JSON-only in v1 and the wire `result: String` makes the bridge fallible; use `WireSettlement::result_kind()` to lift to the typed enum). |
| `mod.rs`        | Module entry; re-exports for engine call sites.                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |

## Running the lock

```bash
# Unit tests (selectors, u8 round-trip, wire/serde, settlement enum).
cargo test -p mev-engine types::

# Phase F — verifies Rust encoder produces byte-identical calldata
# for every Phase F fixture in coordinator/src/types/fixtures.json.
cargo test -p mev-engine --test fixtures_lock

# Phase I — verifies the Settlement JSON wire codec round-trips
# byte-identical against every fixture in fixtures.json#settlements.
cargo test -p mev-engine --test settlement_fixtures_lock
```

If `fixtures.json` is missing or stale, regenerate it from the TS side:

```bash
bun run coordinator/src/types/fixtures.gen.ts
```

The Rust tests load the file via
`concat!(env!("CARGO_MANIFEST_DIR"), "/../coordinator/src/types/fixtures.json")` so they work
regardless of the cwd `cargo test` is invoked from.

## Wire format (locked invariants)

- **camelCase keys** — matches `coordinator/src/types/executor.ts` and the on-chain ABI tuple names
  (`flashLender`, `dexKind`, …).
- **`U256` as plain decimal string** — `"1000000000"`, NOT hex and NOT the `{__bi: "<dec>"}`
  envelope `coordinator/src/types/wire.ts` uses for TS-internal IPC. The TS side has two serializers
  on purpose; the cross-language one (`coordinator/src/types/fixtures.ts::toFixtureValue`) matches
  what Python and Rust expect.
- **`Address` as `"0x..."` checksummed** on emission; alloy accepts any case on decode.
- **`Bytes` as even-length lowercase hex with `0x` prefix**; `"0x"` is a valid empty value.

## Locked selectors and ordinals

- `executeNativeArb` = `0xf6f6add1`
- `matchInternal` = `0x5f188678`
- `composeFourLeg` = `0x72c0469b`
- `FlashProtocol`: `0=AaveV3, 1=Morpho, 2=ERC3156, 3=UniV3, 4=UniV2, 5=UniV4`
- `DexKind`:
  `0=UniV2Style, 1=UniV3Pool, 2=UniV4PoolManager, 3=Curve, 4=Reserved, 5=AggregatorV6, 6=MorphoBlueAction, 7=Algebra, 8=Solidly, 9=CurveNG, 10=BalancerV2, 11=MaverickV2, 12=DodoPmm, 13=FluidDex, 14=BalancerV3, 15=KyberElastic, 16=LFJLiquidityBook, 17=GMXV2, 18=Wombat, 19=Bebop, 20=Hashflow, 21=WooFi, 22=OKXDex, 23=Enso, 24=Squid, 25=LiFi, 26=Rango, 27=Rubic, 28=Native`
  (registry POC append; ordinals 14..28 added 2026-05-13)

## sol! macro shape note

alloy 2.x lowers `type FlashProtocol is uint8;` and `type DexKind is uint8;` to plain `u8` fields on
the surrounding structs. The user-defined wrapper types `FlashProtocol` and `DexKind` are still
emitted (with `From<u8>` and `Into<u8>` impls — exercised in unit tests) so external code can prefer
them when typed clarity matters, but the struct fields and the `From<WireXxx>` bridges work directly
with `u8` to avoid an unnecessary wrap/unwrap on every encode.

## Spec pointers

- [`contracts/src/interfaces/IExecutor.sol`](../../../contracts/src/interfaces/IExecutor.sol) —
  struct shape source.
- [`contracts/src/interfaces/IFlashLoanInterfaces.sol`](../../../contracts/src/interfaces/IFlashLoanInterfaces.sol)
  — `FlashProtocol` enum.
- [`coordinator/src/types/README.md`](../../../coordinator/src/types/README.md) — wire-format
  invariants (TS source).
- [`coordinator/src/types/fixtures.json`](../../../coordinator/src/types/fixtures.json) — the
  snapshot this directory locks against.

## Phase I — Settlement

Locked schema source: the `settlements` array inside
[`coordinator/src/types/fixtures.json`](../../../coordinator/src/types/fixtures.json). Five
fixtures, one per `SettlementResult` variant — `Included`, `Reverted`, `Dropped`, `PreflightFailed`,
`Error`. The TS sources of truth are
[`coordinator/src/types/settlement.ts`](../../../coordinator/src/types/settlement.ts) (struct +
numeric ordinal),
[`coordinator/src/types/settlement-wire.ts`](../../../coordinator/src/types/settlement-wire.ts)
(JSON codec), and
[`coordinator/src/types/settlement-README.md`](../../../coordinator/src/types/settlement-README.md)
(format invariants).

### Wire format vs in-memory

| Field            | sol! type       | Wire JSON shape                       |
| ---------------- | --------------- | ------------------------------------- |
| `planId`         | `bytes32`       | `0x` + 64-char hex string             |
| `version`        | `uint8`         | bare JSON number (currently `1`)      |
| `result`         | `uint8`-typedef | **variant NAME string** (not ordinal) |
| `txHash`         | `bytes32`       | `0x` + 64-char hex string             |
| `block`          | `uint64`        | bare JSON number                      |
| `gasUsed`        | `uint64`        | **decimal STRING** (e.g. `"350000"`)  |
| `preflightDelta` | `uint256`       | decimal string                        |
| `gasEstimate`    | `uint256`       | decimal string                        |
| `error`          | `string`        | bare JSON string                      |

Two intentional deviations from a strict numeric encoding:

1. **`result` is the STRING name on the wire**, not the integer ordinal. The TS canonical struct
   keeps a numeric ordinal in memory (matching the Solidity enum 1:1) but the wire codec emits the
   variant name so the JSON is self-describing. The Rust side mirrors this: the
   `WireSettlement.result: String` field carries the wire form, and `WireSettlement::result_kind()`
   lifts to the typed `SettlementResultKind` enum (returning `None` on unknown names — strict by
   design; callers must surface an error rather than silently coerce).
2. **`gasUsed` is a decimal STRING, not a JSON number.** TS emits `bigint.toString()` for
   forward-compat with a future widening of the Solidity field to `uint256`. `block` stays as a
   number because Arbitrum block heights fit comfortably below `Number.MAX_SAFE_INTEGER`. The Rust
   side uses the new [`decimal_u64`](./wire.rs) adapter for `gas_used` (mirroring the existing
   `decimal_u256` pattern) — diverging here breaks the cross-language byte lock.

### Why no `From<WireSettlement> for Settlement` bridge?

The Phase F bridges (`WireSwapStep → SwapStep`, …) are infallible — every field is a
straight-through copy plus the `u8` lowering. `WireSettlement` is different: `result: String` can
carry an unknown name. To stay consistent with the existing infallible-`From` pattern AND obey the
"no `unwrap()` outside tests" rule, we omit the bridge entirely. Settlement is JSON-only in v1 (no
on-chain ABI use), so the bridge would be unused anyway. If a future on-chain consumer ships, add a
`TryFrom<WireSettlement> for Settlement` returning `eyre::Result<Settlement>`.

### Run the Settlement lock

```bash
cargo test -p mev-engine --test settlement_fixtures_lock
```

This integration test loads `fixtures.json#settlements`, deserializes each entry into
`WireSettlement`, re-serializes via `serde_json`, and asserts the resulting `serde_json::Value` is
byte-identical to the original. Five per-variant decode tests pin the field-level invariants for
each variant (`txHash` zero on non-broadcast paths, `error` empty only on `Included`, `gasEstimate`
zero on `Error` and `PreflightFailed`, …). Two cross-checks (`settlement_result_name_round_trip`,
`settlement_fixture_versions_match_locked_constant`) catch enum-name drift and forgotten-version
bumps.

## Phase G — IPC envelope framing

The 4-byte-LE-prefix + JSON envelope layer that wraps Plan + Settlement

- Heartbeat traffic on the IPC channel lives at [`engine/src/ipc/`](../ipc/) — see
  [`engine/src/ipc/framing-README.md`](../ipc/framing-README.md) for the Rust spec, the
  `serde_json/preserve_order` caveat, and the integration test command
  (`cargo test -p mev-engine --test envelope_fixtures_lock`).

Phase G surfaced a latent regression in this directory: alloy's default `Address` `Serialize` emits
lowercase, but viem (the TS fixture generator) emits the EIP-55 mixed-case checksum. The
[`checksum_address`](./wire.rs) and [`checksum_address_vec`](./wire.rs) adapters now bring Rust's
`Address` emission in line, applied to every `Address` field across the wire structs. Phase F's
binary ABI lock remained intact through the bug because ABI encoding is case-insensitive; the Phase
G JSON lock is what caught it.
