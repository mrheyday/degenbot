# degenbot Stylus Workspace

This workspace contains Stylus contracts and deterministic parity ports used by
the MEV-Arbitrum integration:

- `core/` ports pure Solidity execution libraries into testable Stylus Rust.
- `pool_adapter/` exposes a guarded read-only pool adapter contract.

Run the local proof suite with:

```sh
just test-stylus
```

Contracts here are not production replacements until ABI parity, storage-layout
review, and deployment/reactivation checks are complete.
