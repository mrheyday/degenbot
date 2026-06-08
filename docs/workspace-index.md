# Workspace Index

Date: 2026-06-08

Scope: `vendor/degenbot` inside the MEV-Arbitrum workspace.

This index is the practical navigation map for source ownership, verification
commands, and high-risk execution areas. It is not a generated dependency graph.

## Repository Posture

- Current branch: `main`.
- Package: `degenbot` version `0.6.0a2`.
- Runtime: Python `>=3.12`, Rust extension built through maturin, Stylus Rust
  crates for Arbitrum WASM ports.
- Package runner: `uv`.
- Task runner: `just`.
- Refactoring rule: use red/green TDD for feature work and behavior changes.

## Canonical Ownership

- `src/degenbot/` owns Python market intelligence, protocol adapters, strategy
  signal generation, scoring, provenance, execution adapters, and operator
  verification helpers.
- `rust/src/` owns latency-sensitive deterministic helpers exposed through the
  maturin `degenbot_rs` binding.
- `rust/crates/contract_bindings/` contains checked-in generated Alloy/Rust
  bindings sourced from parent MEV-Arbitrum Foundry contracts.
- `stylus/` owns reusable Stylus contract ports and parity harnesses. These are
  not executable replacements until ABI parity, storage layout, and deployment
  readiness checks pass.
- `src/driver/` is thin integration glue for parent-repo solver/driver flows.
- Parent-repo TypeScript decisions stay in `coordinator/`; parent-repo Solidity
  execution stays in `contracts/`.

## Python Source Map

- Core package: `config.py`, `constants.py`, `logging.py`, `functions.py`,
  `types/`, `exceptions/`, `validation/`.
- Chain and provider plumbing: `connection/`, `provider/`, `contract/`,
  `erc20/`, `checksum_cache.py`, `chainlink.py`.
- Persistence: `database/`, `database/models/`, `migrations/`.
- Protocol packages: `aave/`, `uniswap/`, `curve/`, `balancer/`,
  `aerodrome/`, `camelot/`, `pancakeswap/`, `solidly/`, `sushiswap/`,
  `swapbased/`, `cow/`, `orderbook/`.
- Strategy and signal surfaces: `strategies/`, `strategies_coordinator/`,
  `strategies_solver/`, `strategy_signals/`, `intel/`.
- Execution and routing: `execution.py`, `execution_engine.py`,
  `execution_adapters/`, `adapters/`, `flash/`, `submission/`, `dispatch.py`.
- Matching and quote paths: `matching/`, `quote_engine/`, `quotes/`,
  `arbitrage/`, `pathfinding.py`, `pipeline.py`, `pnl.py`.
- Operator readiness and policy tools: `ops_solver/`.
- CLI entrypoint: `degenbot = degenbot.cli:cli`; command modules live under
  `src/degenbot/cli/`.

## Rust Source Map

- Python bridge and runtime: `lib.rs`, `runtime.rs`, `alloy_py.rs`,
  `py_converters.rs`, `provider_py.rs`, `contract_py.rs`.
- Deterministic execution helpers: `executor/`, `execution.rs`,
  `execution_engine.rs`, `signed_order_admission.rs`.
- Market math and simulation: `simulation/`, `tick_math.rs`,
  `simulation_py.rs`.
- Matching and decision helpers: `matching/`, `decision/`.
- Sequencer and monitoring helpers: `monitor/`.
- Wire and settlement types: `types/`.
- Utility primitives: `utils/`, `address_utils.rs`, `hex_utils.rs`,
  `signature_parser.rs`, `fixed_abi.rs`.

## Stylus Source Map

- Workspace manifest: `stylus/Cargo.toml`.
- Shared core crate: `stylus/core/`.
- Deployable or parity adapter crates:
  `stylus/runtime_adapter/`, `stylus/executor_abi_adapter/`,
  `stylus/lp_transfer_adapter/`, `stylus/pool_adapter/`,
  `stylus/token_risk_adapter/`.
- WASM tooling and readiness docs: `stylus/tools/`, `stylus/WASM_TOOLING.md`,
  `stylus/UPGRADE_READINESS.md`, `stylus/PORTING_STATUS.md`.

## Tests And Docs

- Python tests mirror protocol and execution domains under `tests/`.
- Rust-wrapped Python tests live in `tests/rust/`.
- Stylus tests run from the Stylus workspace with native-test features.
- Aave flow documentation lives under `docs/aave/`.
- Architecture notes live under `docs/architecture/`.
- CLI docs live under `docs/cli/`.

## Verification Commands

- Python: `just test-python`.
- Python coverage: `just test-python-cov`.
- Rust: `just test-rust`.
- Rust-wrapped Python: `just test-rust-python`.
- Stylus: `just test-stylus`.
- Full local test sweep: `just test-all`.
- Lint: `just lint`.
- Format: `just format`.
- Generate parent-contract Rust bindings: `just gen-contract-bindings`.
- Check generated binding freshness: `just check-contract-bindings`.
- Stylus WASM probe: `just stylus-wasm-probe`.
- Stylus deployability check: `just stylus-check`.

Do not manually rebuild the Rust extension or recreate the virtual environment
after Rust code changes. Imports and tests trigger the maturin rebuild path.

## Generated Or Build Artifacts

Treat these as non-source unless a task explicitly targets generated output:

- `.coverage`, `htmlcov/`
- `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `__pycache__/`
- `dist/`, `out/`, `cache/`
- `rust/target/`, `stylus/target/`
- compiled test contract artifacts

Generated contract bindings under `rust/crates/contract_bindings/` are checked
source for this repository, but should be updated through the binding generator
rather than hand-edited.

## Database Surface

- Config: `~/.config/degenbot/config.toml`.
- Default database: `~/.config/degenbot/degenbot.db`.
- ORM models: `src/degenbot/database/models/`.
- Session pattern: `with db_session() as session:` from
  `degenbot.database.db_session`.

## Engineering Constraints

- Exceptions should inherit from `DegenbotError`.
- Use `from degenbot.logging import logger`.
- Prefer frozen dataclasses for value objects.
- Prefer `TypedDict` when dict keys and value types are known.
- Add focused tests for behavior changes; use `Fake*` test doubles rather than
  broad mocks.
- Keep execution policy deterministic and fail-closed. Do not widen admission,
  routing, or submission behavior without local proof and tests.
