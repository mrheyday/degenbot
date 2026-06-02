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

Historical external case studies, such as EigenPhi transaction-structure analyses, belong in
`src/degenbot/strategy_signals/` as descriptive taxonomies. They can feed classifiers, required
signals, and validation checklists, but they are not executable strategy authorization.

Parent `engine` Rust should move here when it is reusable hot-path logic:

- simulation and math helpers -> `rust/src/`;
- typed wire and IPC primitives -> `rust/src/` with Python wrappers when needed;
- provider/cache helpers -> `rust/src/` behind explicit Python APIs.

Keep parent wrappers small: translate degenbot outputs to coordinator DTOs, call the TypeScript
decision layer, and preserve deterministic provenance.

## Generated Contract Bindings

The useful part of `foundry-rs/foundry-rust-template` for this repository is the generated
Rust-binding workflow, not the template's sample app or contract layout. Solidity still lives in
the parent `contracts/` workspace. Degenbot may consume generated Alloy/Rust bindings when the Rust
hot path needs typed access to executor, paymaster, flash-loan, or settlement interfaces.

From `vendor/degenbot`, use:

```sh
just gen-contract-bindings
just check-contract-bindings
```

`gen-contract-bindings` builds the parent Foundry `src` tree into temporary artifacts and writes the
selected generated crate to `rust/crates/contract_bindings`. The default selection is intentionally
limited to executor, flash-loan, callback, paymaster/auth, settlement/ledger, pathfinder, router
registry, and multihop surfaces. It pins generated dependencies to Alloy `2.0.5` to match the Rust
engine.

The Rust extension exposes those checked-in bindings through `degenbot_rs::contract_bindings`.
Use that facade for host-side selector, calldata, and ABI parity checks. Stylus ports may reference
the same generated crate from `native-test` parity harnesses, but deployable Stylus WASM crates must
stay on the lean Stylus SDK dependency graph and should not link Alloy generated bindings.

`check-contract-bindings` regenerates into a temporary directory and fails if the checked-in crate is
missing or stale. Do not hand-edit generated binding files; change the Solidity source or binding
generator inputs, then regenerate.
