# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`degenbot` is a Python library of building blocks for Uniswap (V2/V3/V4), Curve V1, Solidly/Aerodrome, Balancer V2, and Aave arbitrage/MEV bots on EVM chains. **Python is the cockpit; Rust is the engine** — hot-path state ownership, swap math, ABI codec, event decoders, and the arbitrage engine live in a **Rust workspace** (`rust/`) exposed to Python via **PyO3/maturin**; Python orchestrates I/O. `web3.py` (and a faster Rust Alloy backend) handle JSON-RPC.

The codebase is mid-migration of responsibility from Python into Rust. When the docs disagree, **the ADRs (`docs/adr/`) are authoritative** — some long-form docs (`docs/architecture/rust-owned-bot.md`) and `rust/CONTEXT.md` contain stale transitional terms.

## Commands

Tooling is `just` (recipes in `justfile`) + `uv` (Python runner). Run `just --list` for all recipes.

| Task | Command |
|------|---------|
| Python tests | `just test-python` (runs `forge build` on test contracts first — **requires Foundry**) |
| Rust tests | `just test-rust` |
| Rust-wrapped Python tests | `just test-rust-python` |
| All tests | `just test-all` |
| Lint (Rust + Python + Markdown + context-maps) | `just lint` |
| Format (mutates tree) | `just format` |
| Rust clippy only (mutates: `--fix --allow-dirty`) | `just lint-rust` |
| Python lint (`ruff --fix` + `ty` type check) | `just lint-python` |
| Read-only format checks | `just fmt-check`, `just fmt-check-python` |
| Simulate CI | `just ci-full` (or `just ci-rust`) |
| Install git hooks (run once after clone) | `just setup-git-hooks` |

**Single Python test:** `uv run pytest tests/path/test_file.py::test_name`. The default `addopts` enable `pytest-xdist` (`-n auto`), `pytest-randomly`, coverage, and `-m "not slow and not base"`. For a clean, deterministic single run add `-p no:randomly -n0 --no-cov`.

**Critical build rule:** Do **NOT** manually rebuild the Rust extension, recreate `.venv`, or reinstall the package after editing Rust. maturin rebuilds the `degenbot_rs` extension automatically on import, so any `uv run …` (including `pytest`) picks up Rust changes (uv's `cache-keys` watch `rust/**`). The `cargo build`/`just build-*` recipes exist only for isolated Rust testing. `just dev` (`uv run maturin develop`) does an explicit editable rebuild if you want one.

## Architecture

### Hybrid Python/Rust three-layer FFI (ADR-005)

Mirrors Polars' topology. The Rust workspace (`rust/Cargo.toml`, a **pure virtual manifest**) has 11 members: pyo3-free core crates + one binding crate + an umbrella.

- **Rust cores (zero `pyo3` under default features):** `degenbot-core` (the `Bot`/`BotState` state owner, pool state structs, `DexIdentity` presets, reorg journal), `degenbot-cl-math`, `degenbot-curve-math`, `degenbot-balancer-math`, `degenbot-abi`, `degenbot-rpc`, `degenbot-decoders` (alloy-only event decoders), `degenbot-uniswap`, `degenbot-bot`, and the `degenbot` umbrella. **The no-pyo3-in-cores invariant is enforced by `just check-no-pyo3-in-cores`** — when adding a core crate, add it to that recipe's hand-maintained list or it goes unchecked.
- **PyO3 binding (`degenbot-python`, builds the `degenbot_rs` extension):** all `#[pyclass]`/`#[pyfunction]` live here. `PyBot` holds an `Arc` to the Rust `Bot`; mutable pool/token state lives behind an `RwLock` (over `BotState`). Thin handles (`PyLiquidityPool`, `PyErc20Token`) clone the *same* `Arc`, so N Python objects reference one Rust-owned state. **Read methods take a read guard, write methods a write guard — keep that classification when adding methods.** Wrappers keep the `Py` prefix unconditionally (no `#[pyclass(name=...)]` override); bare nouns are reserved for the Python companion classes.
- **Python session (`bot.py:Bot`, `async_bot.py:AsyncBot`):** the public orchestrator; constructs `PyBot()` and owns registries, config, DB, builders, and all I/O.

See **`rust/CLAUDE.md`** for in-depth Rust guidance (crate tiers, GIL discipline, the engine pump loop, lock ordering, build profiles).

### Bot is the single per-chain state owner (ADR-003, ADR-006)

**One `Bot` per chain.** It owns all I/O, the three registries, config, the DB session, and the Rust `PyBot` handle. Chain identity comes from `config.default_chain_id`, and the connected RPC's `eth_chainId` is enforced to match at construction (fail-fast). Multi-chain = N Bots. Tests get isolation by constructing separate Bots (registries are **per-session instances**, not singletons — the lone exception is `pool_type_registry`).

- **Never construct pool classes directly** (`UniswapV3Pool("0x...")` raises). Use `bot.build_pool(address)` (V2/V3/Curve/Balancer — auto-resolves type) or `bot.build_managed_pool(address, pool_id=...)` (V4, identified by PoolManager address + pool_id, not a pool address).
- `AsyncBot` cannot enforce chain_id eagerly (async providers' sync `chain_id` raises) — **construct it via `AsyncBot.from_provider(...)` / `from_config_file_async()`**, which await the chain check; direct `AsyncBot(...)` skips it.
- Lifecycle (`bot_lifecycle.py`): `release_python_state()` clears Python caches mid-run with `propagate_to_rust=False` (Rust stays canonical while the event pump runs); `close()`/`aclose()` tear down with `propagate_to_rust=True`. Mixing these up desyncs Python/Rust pool state. Both Bots are context managers.

### I/O-free pools + builders (ADR-001)

Pool and token classes are **pure-calculation objects**: all on-chain state is fetched at construction and injected; they hold immutable identity + a Rust state handle and expose only calculation/simulation methods. **No pool class performs RPC/DB I/O** — do not add a method that calls the provider. All post-construction state changes enter via `external_update()` (takes already-fetched data; it doesn't fetch).

Typed **Builders** (`V2PoolBuilder`, `V3PoolBuilder`, `V4PoolBuilder`, `CurvePoolBuilder`, `Erc20Builder`, internal to `Bot`) own the I/O choreography (DB lookup → RPC fetch → decode → construct → register in Rust + Python). Their `update()` methods are `@staticmethod`, with all I/O flowing through an injected `io` parameter — the **`PoolIO` seam**, a 7-method protocol (`call`, `call_raw`, `get_block_number`, `get_block`, `get_block_timestamp`, `get_code`, `get_balance`). The production sync seam is the Rust **`PyBotIo`** (not the Python `SyncPoolIO`); builder/type-resolution code probes `getattr(io, "...")` to delegate the encode→call→decode choreography to Rust, with the Python path as an offline/fork parity gate.

> Curve exception: V2/V3/V4/Aerodrome/Camelot are I/O-free at *calculation* time; some Curve variants (lending/crypto/A-ramping) require I/O at calculation time, exposed via `requires_io_at_calculation_time`.

### Pool type resolution & registry (ADR-002)

`bot.build_pool(address)` resolves the concrete pool class in order: (1) existing `bot.pools` registry → (2) DB `kind` column → (3) `pool_type_registry` mapping `(chain_id, factory) → class` → (4) on-chain probing (`slot0()`→concentrated, `getReserves()`→constant-product, Balancer probes, else stableswap; `DegenbotValueError` falls back to Curve, which has no `factory()`).

`pool_type_registry` (`registry/pool_type.py`) is the **one intentional module-level singleton** — each DEX module self-registers its factories **at import time**. Two distinct enums, don't conflate them: **`PoolFamily`** (`types/pool_type.py`) = build-dispatch/DB identity; **`PoolInvariant`** (`types/hop_types.py`) = runtime arbitrage-solver dispatch (one pool can yield different invariants by direction, e.g. Camelot volatile→`CONSTANT_PRODUCT`, stable→`SOLIDLY_STABLE`). Adding a DEX: give the pool class a `variant` ClassVar (or reuse `LiquidityPool` with `variant=`), call `pool_type_registry.register(...)` in its `__init__.py`, and ensure the top-level `__init__` imports the module (side-effect imports like `camelot`/`swapbased` exist purely to trigger registration).

### Arbitrage & the Rust engine bridge (ADR-006, ADR-007)

`arbitrage/` holds `ArbitragePath` (a closed pool loop that subscribes to pool state messages and recalculates on change), Python `Solver`s (f64 approximations for path discovery/testing — production execution uses the Rust U512 engine, so results can diverge at the wei level), and swap encoding (`generate_payloads`, `EncodedCall`; V4 encoding is unimplemented in Python).

**`EngineRegistry(bot=...)` (`arbitrage/engine_registry.py`) is the canonical, only correct way to start a `UniswapArbEngine`** — it constructs the engine with `py_bot=bot._py_bot` so the engine adopts the Bot's shared `BotState` (no dual-state split). Never construct a standalone engine for production, and **never double-register pools** (`build_pool` already put them in the shared state; the engine's `register_*_pool` is gone — intake is `register_path`). `start()` deliberately stops before `resume()` so the caller attaches its result consumer first.

## Layered documentation — read before editing

This repo runs two parallel governance systems: **ADRs** (decisions + rationale + history) and a **CONTEXT.md corpus** (ubiquitous-language vocabulary, *not* history). **Read the relevant module's `CONTEXT.md` before naming variables, classes, or docstrings** — use the term as the glossary defines it, and avoid synonyms on its `_Avoid_:` list.

- `CONTEXT-MAP.md` — root index + cross-module content. Terms belong to exactly one module's `src/degenbot/<module>/CONTEXT.md`; only cross-module ambiguity rulings (Pool vs Market, Reserves vs Asset, Asset vs Token) live at root.
- `docs/adr/` — ADR-001 I/O-free pools · ADR-002 pool-type-registry singleton · ADR-003 Bot as Rust state owner · ADR-004 typed TickMap boundary · ADR-005 three-layer FFI + `Py`-prefix naming · ADR-006 one-Bot-per-chain orchestrator · ADR-007 pool unregister seam (pool_ids are retired, never reused).
- `docs/migration-guides/three-layer-transition.md` — **the rubric for moving any Python responsibility into Rust** (four dispositions; core-leaf → PyO3-wrapper → route-and-delete; test-transition + oracle-retirement patterns).
- `docs/agents/context-map-maintenance.md` — the CONTEXT.md style contract; `docs/agents/domain.md` — domain glossary.
- `rust/CLAUDE.md` + `rust/CONTEXT.md`; `contract_reference/` — verified Solidity sources, ground truth for integer-exact ports.

`just lint-context-maps` mechanically enforces the contract (part of `just lint`): bans the brace dialect `{Foo}` (use `**Term**` or markdown links), bans status-prose/history markers in context maps (history goes in ADRs), bans references to the deleted connection module, and requires relative `CONTEXT.md` links to resolve on disk.

## Conventions

- **TDD (Red/Green)** is mandatory for refactors and new features — each migration sub-step leaves tests green before the next.
- **No backwards-compatibility layer** unless explicitly directed (this is a `0.x` project; breaking refactors delete old code outright rather than aliasing).
- **`Py`-prefix naming (ADR-005):** PyO3 wrappers keep `Py` as both Rust and Python name; stateless `#[pyfunction]`s get no prefix; the bare noun is the Python companion.
- **Standalone-Rust-core constraint:** anything a pure-Rust consumer needs (presets, identity, math) lands in a core crate **from day one** — never "put it on the Python side and move it later."
- **Hard module boundary:** `aave/` must never import from `cli/` (the arrow points `cli/` → `aave/` only).
- **Planning:** the repo uses `ergo` for feature planning (`.ergo/` holds its state); see `AGENTS.md`.
- **Commits:** Conventional Commits enforced by `commitlint` (`.commitlintrc.yml`; types `feat|fix|refactor|docs|lint|test|chore|remove`, scope enum). `just setup-git-hooks` installs `commit-msg` + a `pre-push` hook that re-lints the whole push range (catching `--no-verify` bypasses before CI). Check a range with `just lint-commits [main..HEAD]`. Node/`npx` must be present for hooks to enforce.

## Testing notes

- Tests in `tests/` mirror the source tree. README Python code blocks are also tested via **Sybil** doctests (root `conftest.py`; `README.md` is in `testpaths`) — keep README snippets importable, and don't break the ordering/single-worker pinning the hook applies to them.
- **RPC markers** gate fork tests: `ethereum`, `base`, `arbitrum`, `slow`. The default run excludes `slow` and `base`; `ethereum`/`arbitrum` are **not** excluded and will hit RPCs. Override `-m` to run excluded ones.
- RPC endpoints come from an **uncommitted `tests.env`** (via `python-dotenv`) with slow public-RPC fallbacks — set `{ETHEREUM,BASE,ARBITRUM}_{ARCHIVE,FULL}_NODE_{HTTP,WS}_URI` there (see `tests/conftest.py`). Deselect RPC-dependent tests by fixture with `--skip-fixture fork_mainnet_archive,...`. `AnvilFork` (`anvil_fork.py`) spawns a local fork for deterministic tests — requires `anvil`.
- DB migrations are **code-driven** (`database/operations.py` via Alembic's `command.upgrade`/`stamp`), not the `alembic` CLI; `env.py` honors `DEGENBOT_DATABASE_PATH`.

## Gotchas

- `just test-python` needs **Foundry (`forge`)**; `just test-rust` needs the venv libpython (the recipe sets `LD_LIBRARY_PATH`/`DYLD_LIBRARY_PATH`).
- `just lint-rust`/`lint-python` **mutate the working tree** (`clippy --fix --allow-dirty`, `ruff --fix`) — use the `fmt-check*` recipes to verify read-only.
- The Python type checker is **`ty` (Astral)**, not mypy. `# noqa: ...PLC0415` (import-not-at-top) is forbidden by a pre-commit hook — fix the import placement.
- uv's `exclude-newer = "14 days"` hides freshly-published deps from resolution.
- **V3 vs V4 `amountSpecified` sign convention is opposite** (V3 positive = exact-input; V4 negative). Getting it wrong → V3 reverts.
- Fee/`gamma` convention into Rust: `gamma_numer = denominator − fee_numerator` (the retained post-fee numerator, e.g. `997`), not the fee.
- Don't leave equivalence/parity test harnesses comparing two live implementations after a routing cutover — retire them with the oracle (they become tautologies).
