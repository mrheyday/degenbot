# degenbot Stylus Workspace

This workspace contains Stylus contracts and deterministic parity ports used by
the MEV-Arbitrum integration:

- `core/` ports pure Solidity execution libraries into testable Stylus Rust.
  It now also carries the full 62-file migration manifest, auth/account
  semantic fragments, executor static semantics, POC fail-closed gates, and
  selector parity surfaces. `core::runtime_adapter` binds the live execution
  adapter proof: callback auth, flash settlement, approval/call allowlists, and
  execution receipt hashing.
- `pool_adapter/` exposes a guarded read-only pool adapter contract.

Run the local proof suite with:

```sh
just test-stylus
```

Contracts here are not production replacements until ABI parity, storage-layout
review, and deployment/reactivation checks are complete.
