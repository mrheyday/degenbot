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
- `executor_abi_adapter/` is the deployable Stylus contract for dynamic executor
  calldata codecs. It exposes the already-proven `core::executor_abi` encoders
  for native arb, owned swaps, CoW/UniswapX matching, four-leg composition,
  UniswapX fill/callback data, and CoW flash-loan-router start payloads without
  requiring the oversized semantic core to activate.
- `lp_transfer_adapter/` is the deployable Stylus contract for LP transfer
  runtime normalization. It reuses `core::lp_transfer_lib`, calls ERC-20,
  ERC-721, and ERC-6909 targets with bounded return data, rejects no-code
  targets, and exposes deterministic status codes for revert, false-return,
  and malformed-return cases.
- `token_risk_adapter/` is the deployable Stylus contract for defensive token
  risk checks. It reuses `core::token_risk_filter`, performs bounded
  `staticcall` probes, stores cache flags/timestamps in Stylus storage, exposes
  Solidity-parity `RiskVerdict`/`RiskVerdict[]` returns for
  `assessExternal`, `assessBatch`, and `updateCache`, and keeps explicit
  flags/safety helper ABIs for hot execution gates.

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
Stylus contracts such as `runtime_adapter/`, `lp_transfer_adapter/`,
`executor_abi_adapter/`, `token_risk_adapter/`, and `pool_adapter/`.
