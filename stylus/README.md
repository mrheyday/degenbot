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
- `runtime_adapter/` is the deployable Stylus contract for the live execution
  adapter proof surface. It reuses `core::runtime_adapter` and stays below the
  single-contract activation limit instead of relying on fragmented deployment
  support for the monolithic semantic core.
- `token_risk_adapter/` is the deployable Stylus contract for defensive token
  risk checks. It reuses `core::token_risk_filter`, performs bounded
  `staticcall` probes, and stores cache flags/timestamps in Stylus storage.

Run the local proof suite with:

```sh
just test-stylus
```

Run endpoint-backed deployability checks for the deployable artifacts with:

```sh
just stylus-check
```

Contracts here are not production replacements until ABI parity, storage-layout
review, and deployment/reactivation checks are complete. The monolithic `core`
crate is a semantic parity harness; production deployment should use split
Stylus contracts such as `runtime_adapter/` and `pool_adapter/`.
