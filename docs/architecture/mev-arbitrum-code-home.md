# MEV-Arbitrum Code Home

Date: 2026-05-18

`vendor/degenbot` is the canonical home for the MEV-Arbitrum Python and Rust market-intelligence
stack. Parent-repo code may import degenbot, package it, or provide thin coordinator glue, but
durable protocol logic should live here.

## Responsibilities

- Python in `src/degenbot` owns protocol adapters, market intel, analysis, strategy signal
  generation, trigger emission, source provenance, and candidate scoring.
- Rust in `rust/src` owns latency-sensitive deterministic helpers exposed through the maturin-built
  `degenbot_rs` binding.
- Stylus in `stylus/` owns WASM contract ports and parity harnesses that are reusable from this
  integration. These ports are not executable replacements until ABI parity, storage layout, and
  deployment/reactivation checks pass.
- TypeScript stays in the parent `coordinator/` and owns decisions, external TS SDK workflows,
  routing orchestration, and submitter handoff.
- Solidity stays in the parent `contracts/` and owns deterministic settlement, callback checks,
  repayment, access control, and realized-profit enforcement.

## Migration Targets

Parent `solver/driver` Python should move here when it is reusable market logic:

- `execution/*_adapter.py` -> `src/degenbot/<protocol>/` or a shared adapter package;
- `intel/*` -> `src/degenbot/intel/`;
- strategy analysis/catalog modules -> `src/degenbot/strategy_signals/`;
- address/source metadata -> protocol-specific packages with tests.

Parent `engine` Rust should move here when it is reusable hot-path logic:

- simulation and math helpers -> `rust/src/`;
- typed wire and IPC primitives -> `rust/src/` with Python wrappers when needed;
- provider/cache helpers -> `rust/src/` behind explicit Python APIs.

Keep parent wrappers small: translate degenbot outputs to coordinator DTOs, call the TypeScript
decision layer, and preserve deterministic provenance.
