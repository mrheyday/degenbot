# Stylus WASM Tooling

This workspace treats WebAssembly tooling as operator-supplied infrastructure,
not vendored source. The tools below are pinned by role, invoked explicitly, and
never auto-installed by repository scripts.

## Source Set

| Role | Upstream | Current inspected `HEAD` |
| --- | --- | --- |
| Fidelity inspection and validation | `https://github.com/WebAssembly/wabt.git` | `03a00a1334e6121fb0cce4fccbd6bb109b68acaa` |
| Deterministic wasm optimization | `https://github.com/WebAssembly/binaryen.git` | `5cbd7f09bc5087e1c339f4df72fc01e3fd6aaf89` |
| WAT language diagnostics/editor server | `https://github.com/g-plane/wasm-language-tools.git` | `85a30110c2855e69f71ec8567699039526be685b` |

## Required Binaries

- WABT: `wasm-validate`, `wasm-objdump`, `wasm2wat`
- Binaryen: `wasm-opt`
- WebAssembly Language Tools: `wat_server`
- Offchain Labs CLI: `cargo-stylus`

`wat_server` is not required for non-interactive CI inspection, but operator
workstations should install it so generated `.wat` artifacts receive static
diagnostics in editors.

## macOS Notes

For Stylus Rust contracts, prefer the Rust target declared in
`core/rust-toolchain.toml`:

```sh
rustup target add wasm32-unknown-unknown --toolchain 1.91
```

Do not permanently replace the system LLVM just to inspect Stylus artifacts. If
an operator compiles standalone C/C++ wasm fixtures, Xcode's `clang` usually
lacks the `wasm32` backend; use Homebrew LLVM only for that command:

```sh
PATH="/opt/homebrew/opt/llvm/bin:$PATH" ./build.sh
```

On Intel Homebrew installs, the LLVM path may be `/usr/local/opt/llvm/bin`.
Browser demos that fetch `.wasm` must be served over HTTP; direct `file://`
loads are blocked by same-origin policy. A local static server is sufficient:

```sh
python3 -m http.server 8004
```

## Inspection Flow

Run a local availability check:

```sh
just stylus-wasm-probe
```

Inspect a compiled Stylus wasm artifact:

```sh
just stylus-wasm-inspect stylus/target/wasm32-unknown-unknown/release/degenbot_stylus_core.wasm
```

The harness writes:

- `<name>.sections.txt` from `wasm-objdump -h`
- `<name>.wat` from `wasm2wat`
- `<name>.opt.wasm` from `wasm-opt -O3 --enable-bulk-memory`

The generated files live under the artifact-local `inspect/` directory unless
`--out-dir` is provided directly to `stylus/tools/wasm-inspect.sh`.

Additional WABT tools are useful during manual review:

```sh
wasm-objdump -x <artifact.wasm>
wasm-decompile <artifact.wasm>
wasm-opcodecnt <artifact.wasm>
```

## Stylus CLI Flow

Install and verify the Stylus CLI:

```sh
cargo install --force cargo-stylus
cargo stylus -V
```

Add the WASM target for the pinned local Rust toolchain:

```sh
rustup target add wasm32-unknown-unknown --toolchain 1.91
```

Build the local Stylus workspace:

```sh
cargo build --manifest-path stylus/Cargo.toml --release --target wasm32-unknown-unknown
```

Check deployable artifacts from each contract directory so `cargo-stylus` can
read the matching `Stylus.toml`:

```sh
just stylus-check
```

`stylus/core` is the monolithic semantic parity harness. On Arbitrum One it
currently compresses above the EIP-170 single-contract limit and enters the
fragment activation path, so it is not the deployment target unless the
operator has independently verified fragment activation for that endpoint.

For deployment dry runs against a dev node or configured Arbitrum endpoint,
prefer gas estimation first:

```sh
cargo stylus deploy --endpoint http://localhost:8547 --estimate-gas
```

Activation/reactivation is explicit operational work:

```sh
cargo stylus activate --address <CONTRACT_ADDRESS>
```

Use `--private-key-path`, `--keystore-path`, and
`--keystore-password-path` for transaction-authenticated commands. Avoid
passing `--private-key` interactively because it can land in shell history.

## Operational Rules

- Do not vendor WABT, Binaryen, or WebAssembly Language Tools into this repo
  without a separate pinned dependency review.
- Do not let the inspection harness install tools or mutate the developer
  machine.
- Treat WABT output as the readable fidelity layer. WABT is not the optimizer.
- Treat Binaryen output as an optimization candidate. Do not deploy optimized
  wasm until `cargo stylus check` accepts that exact file.
- Treat `wat_server` diagnostics as editor/operator feedback. It is not a
  replacement for `cargo test`, `cargo check`, or `cargo stylus check`.
