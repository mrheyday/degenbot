# `solver/driver/types/` — Python canonical mirror of `IExecutor.sol`

Phase F (Python half). Mirrors the on-chain struct shapes consumed by `Executor.executeNativeArb`,
`Executor.matchInternal`, and `Executor.composeFourLeg`. Field names, ordering, and wire types match
`contracts/src/interfaces/IExecutor.sol` verbatim — reordering or renaming silently breaks ABI
parity with the contract.

The TypeScript mirror at [`coordinator/src/types/`](../../../coordinator/src/types/) is the
cross-language source of truth. `coordinator/src/types/fixtures.json` holds the locked calldata
snapshots; the Python encoders here MUST reproduce each fixture's `calldata` field byte-identically.

## Files

| File                    | Role                                                                                                                                 |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `executor.py`           | Frozen dataclasses + `IntEnum` ordinals (`SwapStep`, `NativeArbParams`, `MatchParams`, `ComposeParams`, `FlashProtocol`, `DexKind`). |
| `wire.py`               | JSON wire-format parsers; camelCase keys, decimal-string `bigint`.                                                                   |
| `codec.py`              | `eth_abi`-backed encoders that produce 0x-prefixed lowercase hex calldata.                                                           |
| `test_fixtures_lock.py` | Cross-language ABI lock — pytest assertions that each fixture in `fixtures.json` round-trips through wire+encode unchanged.          |

## Verifying the lock

```bash
cd solver
uv run pytest driver/types/test_fixtures_lock.py
```

Expected: every fixture in `coordinator/src/types/fixtures.json` produces calldata equal to its
locked `calldata` field.

## Regenerating fixtures (TS side)

Only re-run if you intentionally changed an Executor struct shape and have already updated
`IExecutor.sol`, `coordinator/src/types/executor.ts`, and `coordinator/src/types/abi.ts`:

```bash
bun run coordinator/src/types/fixtures.gen.ts
```

After regeneration, run the lock test again — if the Python encoder cannot reproduce the new
fixture, the Python side has diverged and must be fixed.

## Locked enum ordinals

- `FlashProtocol`: `0=AAVE_V3, 1=MORPHO, 2=ERC3156, 3=UNI_V3, 4=UNI_V2, 5=UNI_V4`
  (`IFlashLoanInterfaces.sol`).
- `DexKind`:
  `0=UNI_V2_STYLE, 1=UNI_V3_POOL, 2=UNI_V4_POOL_MANAGER, 3=CURVE, 4=RESERVED, 5=AGGREGATOR_V6, 6=MORPHO_BLUE_ACTION, 7=ALGEBRA, 8=SOLIDLY, 9=CURVE_NG, 10=BALANCER_V2, 11=MAVERICK_V2, 12=DODO_PMM, 13=FLUID_DEX, 14=BALANCER_V3, 15=KYBER_ELASTIC, 16=LFJ_LIQUIDITY_BOOK, 17=GMX_V2, 18=WOMBAT, 19=BEBOP, 20=HASHFLOW, 21=WOOFI, 22=OKX_DEX, 23=ENSO, 24=SQUID, 25=LIFI, 26=RANGO, 27=RUBIC, 28=NATIVE`
  (`IExecutor.sol`; ordinals 14..28 added as registry POC lanes 2026-05-13).

## Locked function selectors

- `executeNativeArb` = `0xf6f6add1`
- `matchInternal` = `0x5f188678`
- `composeFourLeg` = `0x72c0469b`

`codec.selectors_match_signatures()` re-derives each via `keccak256(canonical_sig)[:4]` as a CI
guard against drift.
