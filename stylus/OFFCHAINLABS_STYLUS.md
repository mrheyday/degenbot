# OffchainLabs Stylus Source Map

The user-provided source root is `https://github.com/OffchainLabs`. For this
workspace, the actionable Stylus/Nitro sources are narrowed to the repositories
below. They are references for compatibility and operator verification, not
vendored dependencies.

| Role | Upstream | Current inspected `HEAD` |
| --- | --- | --- |
| Stylus build/check/deploy CLI | `https://github.com/OffchainLabs/cargo-stylus.git` | `5c520876d54594d9ca93cf017cb966075b4f4ca5` |
| Rust SDK and ABI-equivalent contract macros | `https://github.com/OffchainLabs/stylus-sdk-rs.git` | `a811b1530dd55b711b6949f6fc823bdef30d2366` |
| Nitro node/runtime source of truth | `https://github.com/OffchainLabs/nitro.git` | `6dce8d13902649a1acdfd3f2504129f1f5612358` |
| Parent-chain Nitro contracts and Stylus deployment contracts | `https://github.com/OffchainLabs/nitro-contracts.git` | `67487333202561b74492d07de62a4f56be28560e` |
| Local Nitro/Stylus testnode harness | `https://github.com/OffchainLabs/nitro-testnode.git` | `928b79a6bb300998053116ae66adc4e194898fba` |

## Local Compatibility Baseline

- `stylus/core/Cargo.toml` and `stylus/pool_adapter/Cargo.toml` currently pin
  `stylus-sdk`, `stylus-core`, and `stylus-proc` to `0.10.7`. Native unit tests
  use the local `native-test` feature instead of `stylus-test`/`stylus-tools` so
  the Stylus lockfile does not pull the off-chain Alloy provider/RPC graph.
- `stylus/core/rust-toolchain.toml` requires the
  `wasm32-unknown-unknown` target.
- `stylus/tools/wasm-inspect.sh --probe` checks `cargo-stylus`
  alongside WABT and Binaryen tooling so deployment-oriented operators do not
  confuse generic wasm validity with Stylus activation readiness.

## Operational Rules

- Use `cargo stylus check --wasm-file <artifact>` as the deployability gate for
  any optimized wasm emitted by Binaryen.
- Do not treat `awesome-stylus` examples as canonical for this repo. Many public
  examples target older `cargo-stylus` and `stylus-sdk` releases.
- Keep Nitro/testnode sources as execution-environment references. Contract
  behavior in this repo remains locked by local Rust tests and Solidity parity
  fixtures before activation.
