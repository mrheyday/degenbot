# Justfile for degenbot development
# https://github.com/casey/just

# Default recipe - show available commands
default:
    @just --list

# ========== Rust Development ==========

# Run Rust tests
test-rust:
    cargo test --features auto-initialize --manifest-path rust/Cargo.toml -- --test-threads=1

# Run wrapped Rust Python tests
test-rust-python:
    uv run pytest tests/rust -x -q --no-header

# Run Stylus contract tests
test-stylus:
    cargo test --manifest-path stylus/Cargo.toml --locked --offline --lib --features native-test

# Run Rust linter (clippy)
lint-rust:
    cargo clippy --all-targets --all-features --manifest-path rust/Cargo.toml -- -D warnings

# Run Stylus linter
lint-stylus:
    cargo clippy --manifest-path stylus/Cargo.toml --tests --locked --offline --features native-test -- -D warnings

# Build Rust release library (links Python - for testing only)
build-rust-debug:
    cargo build --release --manifest-path rust/Cargo.toml

# Build Rust extension module (correct for Python extension)
build-rust-extension:
    cargo build --release --features extension-module --manifest-path rust/Cargo.toml

# ========== Python Development ==========

# Build and install Python extension in development mode
dev:
    uv run --no-project maturin develop --manifest-path rust/Cargo.toml

# Build Python extension wheels
build-wheels:
    uv run --no-project maturin build --release --manifest-path rust/Cargo.toml

# Compile Solidity test contracts
compile-test-contracts:
    cd tests/aave/libraries/contracts && forge build --quiet

# Run Python tests
test-python: compile-test-contracts
    uv run pytest tests/ -x -q --no-header

# Run Python tests with coverage
test-python-cov: compile-test-contracts
    uv run pytest tests/ -x -q --no-header --cov=src/degenbot --cov-branch

# Run all tests (Rust + Python)
test-all: test-rust test-stylus test-python

# ========== Code Quality ==========

# Run all linters (Rust + Python)
lint: lint-rust lint-stylus
    uv run ruff check src/
    uv run mypy src/

# Format all code
format: 
    cargo fmt --manifest-path rust/Cargo.toml
    cargo fmt --manifest-path stylus/core/Cargo.toml
    cargo fmt --manifest-path stylus/pool_adapter/Cargo.toml
    uv run ruff format src/

# ========== CI/CD ==========

# Simulate CI Rust checks
ci-rust: lint-rust test-rust
    cargo build --release --features extension-module --manifest-path rust/Cargo.toml

# Simulate CI Stylus checks
ci-stylus: lint-stylus test-stylus
    cargo build --manifest-path stylus/core/Cargo.toml --release --target wasm32-unknown-unknown --locked --offline

# Probe local WebAssembly inspection dependencies
stylus-wasm-probe:
    stylus/tools/wasm-inspect.sh --probe

# Inspect a compiled Stylus wasm artifact
stylus-wasm-inspect wasm="stylus/target/wasm32-unknown-unknown/release/degenbot_stylus_core.wasm":
    stylus/tools/wasm-inspect.sh --wasm {{ wasm }}

# Simulate full CI pipeline
ci-full: ci-rust ci-stylus test-python

# ========== Documentation ==========

# Build documentation
docs:
    cargo doc --no-deps --manifest-path rust/Cargo.toml
    uv run mkdocs build 2>/dev/null || echo "mkdocs not configured"

# Serve documentation locally
serve-docs:
    cargo doc --open 2>/dev/null --manifest-path rust/Cargo.toml || echo "Open rust/target/doc/degenbot_rs/index.html"
