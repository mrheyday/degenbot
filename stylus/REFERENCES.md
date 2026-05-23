# Stylus References

## Primary References

- Offchain Labs `cargo-stylus` CLI: build, check, deploy, verify, and export ABI
  commands for Stylus WASM contracts.
- OffchainLabs/cargo-stylus: canonical CLI implementation for Stylus
  build/check/deploy/export-ABI workflows.
- OffchainLabs/stylus-sdk-rs: canonical Rust SDK and ABI-equivalence source for
  Stylus contracts.
- Arbitrum Stylus recommended libraries: dependency compatibility policy for
  WASM contracts; prefer single-threaded, no-randomness, no-floating-point,
  `no_std`-friendly crates that build for `wasm32-unknown-unknown`.
- Stylus by Example: concise reference examples for entrypoints, storage,
  errors, selectors, ABI encoding/decoding, VM affordances, and contract tests.
- OffchainLabs/nitro, OffchainLabs/nitro-contracts, and
  OffchainLabs/nitro-testnode: Nitro runtime, deployment contracts, and local
  execution-environment references.
- WABT: `wasm-validate`, `wasm-objdump`, and `wasm2wat` for faithful
  WebAssembly validation and text inspection.
- Binaryen: `wasm-opt` for deterministic WebAssembly optimization passes.
- WebAssembly Language Tools: `wat_server` for WAT diagnostics and editor
  integration.
- OpenZeppelin Contracts for Stylus UUPS proxy documentation: ERC-1967,
  ERC-1822, proxy initialization, and access-controlled upgrades.

## Secondary References

- Yinka Abeeb, "How to write an Arbitrum Contract with Stylus", Medium,
  2025-08-21. The visible public preview covers Stylus basics, ERC-20 contract
  authoring, tests, and local dev-node deployment. The full article is
  member-only, so implementation decisions must still be checked against
  primary documentation and local verification.
