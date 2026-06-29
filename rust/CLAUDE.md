# CLAUDE.md — degenbot Rust workspace

Guidance for Claude Code instances editing the Rust workspace under `rust/`. This
is the high-performance core of degenbot: a Cargo workspace of pyo3-free crates
plus one PyO3 cdylib binding layer that Python imports as `degenbot_rs`.

**Read first, in this order:**
- `rust/AGENTS.md` — the three-layer pattern, GIL/Arc/lock rules, the Nine Rules, module naming. This is the architectural contract.
- `rust/CONTEXT.md` — a dense glossary (every type/term + its relationships). Treat it as the source of truth for *intent*; the code is the source of truth for *current shape* (a few terms describe the documented model rather than the exact field types — see "Doc-vs-code discrepancies" below).
- ADRs live in `docs/adr/` (ADR-003 Bot-as-state-owner, ADR-004 TickMap, ADR-005 Polars three-layer, ADR-006 per-chain orchestrator, ADR-007 unregister seam). Architecture prose: `docs/architecture/rust-owned-bot.md`.

## Workspace layout

Root `rust/Cargo.toml` is a **pure virtual manifest** — `[workspace]` + `[profile.*]` only. Cargo honors `[profile]` only at the workspace root, so profiles live there and nowhere else. There are **11 members**: 9 pyo3-free core crates, the `degenbot_rs` binding cdylib (`crates/degenbot-python/`), and the `degenbot` umbrella crate (`crates/degenbot/`).

### Crate responsibilities & dependency tiers

| Crate | Role | Depends on (internal) | pyo3? |
|-------|------|----------------------|-------|
| `degenbot-core` | Foundation: `errors`, `hex_utils`, `runtime` (shared Tokio singleton), `address_utils` (EIP-55) | — | **feature-gated only** (`pyo3` feature adds `From<Error> for PyErr`; off by default) |
| `degenbot-cl-math` | Uniswap V3/V4 concentrated-liquidity math ports (`cl_lib/`: bit/full/sqrt_price/tick/liquidity/swap math) | core | no |
| `degenbot-curve-math` | **alloy-only leaf.** Curve StableSwap math port. **Not yet wired** (no umbrella re-export, no binding wrapper, not in solve path) | — (only `alloy`) | no |
| `degenbot-balancer-math` | **alloy-only leaf.** Balancer V2 FixedPoint/LogExpMath/WeightedMath/StableMath ports. **Not yet wired** (same as curve-math) | — (only `alloy`) | no |
| `degenbot-abi` | ABI type/value system (`abi_types/`), encoder, decoder, signature parser, LRU type cache | core | no |
| `degenbot-rpc` | Alloy provider/contract/subscription pure core; `test-utils` feature exposes `AlloyProvider::from_provider` to downstream tests | core, abi | no |
| `degenbot-decoders` | **alloy-only leaf.** Hand-sliced V2/V3/V4 event-log decoders + topic constants + return structs. No core/abi/tokio/pyo3 | — (only `alloy`) | no |
| `degenbot-uniswap` | Uniswap-domain value objects: `DexIdentity`/`DexVariant` presets + V2 swap calldata encoder (`encode_v2_swap`) | core, abi | no |
| `degenbot-bot` | The big one. `bot_core` (`BotState`, reorg journal, pump, dispatcher, V2/V3/V4 + Curve/Balancer state, verifier, tick maps) + `solvers` (Möbius solvers + `uniswap_engine/`). One crate by ADR-003 (state↔solver coupling is genuine, ~30 mutual refs) | core, cl-math, abi, rpc, decoders, uniswap | no |
| `degenbot-python` | **The binding cdylib** (`degenbot_rs`). All `#[pyclass]`/`#[pyfunction]` live here. Enables each core's `pyo3` feature | all cores | **YES — the only crate that pulls pyo3 in production** |
| `degenbot` | **Umbrella.** Re-exports 7 of 9 cores (NOT curve-math/balancer-math) with zero pyo3 for `cargo add degenbot` standalone Rust use. Mirrors the `polars` Rust crate | 7 cores | no |

The whole layout mirrors `polars` / `polars-python`: cores ≈ `polars-core`, the binding cdylib ≈ `polars-python`, the umbrella ≈ the `polars` Rust crate.

## The no-pyo3-in-cores invariant (critical)

**Core crates must not pull `pyo3` under default features.** This is what lets a Rust consumer use the math/state/decoders without a Python interpreter, and lets cores be unit-tested without the GIL.

- The single intentional exception: `degenbot-core` has an **optional, non-default** `pyo3` feature (gating `From<*Error> for PyErr` impls in `errors.rs`, behind `#[cfg(feature = "pyo3")]`). The orphan rule forces those impls into core (both `PyErr` and the error types are foreign to the cdylib). Only `degenbot-python` enables it (`degenbot-core = { features = ["pyo3"] }`); every other internal dep on core uses default features (no pyo3).
- Enforced by **`just check-no-pyo3-in-cores`**: it loops over `degenbot-core degenbot-cl-math degenbot-abi degenbot-rpc degenbot-bot degenbot-decoders degenbot-uniswap degenbot` and runs `cargo tree -p <crate> | grep -qi 'pyo3 v'`, failing if any of them pulls pyo3 under default features. It is part of `just ci-rust`.
- **GOTCHA — the check list is hand-maintained.** It does NOT currently include `degenbot-curve-math` or `degenbot-balancer-math` (they predate being wired in). **If you add a new core crate, you MUST add it to the loop in the justfile** (recipe `check-no-pyo3-in-cores`) or the invariant silently won't cover it.
- **GOTCHA — `cargo tree` greps the literal string `pyo3 v`.** A core crate that *feature-gates* pyo3 still passes only because the feature is off by default. If you add a pyo3 dep to a core, it must be `optional = true` and never in `default`.
- If you find yourself reaching for `pyo3::` inside a core crate file (outside its opt-in feature), that is the code smell the three-layer pattern exists to prevent: split the pure logic into the core and put the `#[pyfunction]`/`#[pyclass]` wrapper in `degenbot-python/src/`.

## The three-layer pattern (from AGENTS.md — internalize it)

1. **Python module** (`src/degenbot/*.py`) — user-facing API, docstrings, `Fraction` prices, DB lookups, pub/sub. Knows nothing of Rust internals.
2. **PyO3 binding** (`rust/crates/degenbot-python/src/<domain>/*.rs`) — `#[pyclass]`/`#[pyfunction]` only. Extract args → release GIL → call core → wrap result. **No business logic.**
3. **Rust core** (the 9 core crates) — idiomatic `Result<T,E>`, zero pyo3, independently testable.

The **crate boundary** (not a filename suffix) is the separator. The old `*_py.rs` suffix convention is **dropped inside the binding crate** — every file there is "py" by default; the binding crate has zero `*_py.rs` files. Binding files live in per-domain subdirs mirroring the cores: `abi/`, `cl_math/`, `rpc/`, `uniswap/`, `bot/` (+ `bot/engine/`), with `conversion/` for shared PyO3 converters, `c_api.rs` for the registration site, `prelude.rs` for the curated re-export surface.

## FFI topology (the stateful specialization — ADR-005)

This is the part most likely to be edited wrong. The runtime state lives in **one** Rust-owned object; many Python handles share it via `Arc`.

```
Python Bot session   →  self._py_bot = PyBot(chain_id)
PyBot { bot: Arc<Bot> }                          # the per-chain orchestrator
   └─ Bot { chain_id, state: Arc<RwLock<BotState>>, dispatcher }
         ├─ PyLiquidityPool { core: Arc<RwLock<BotState>>, pool_id }   # thin handle, clones the SAME Arc via Bot::state_arc()
         ├─ PyErc20Token    { core: Arc<RwLock<BotState>>, address }   # thin handle, same Arc
         └─ UniswapEngine   { core: Arc<RwLock<BotState>>, ... }       # adopts the SAME Arc via with_core()
```

- **`Bot`** (`bot_core/mod.rs`) is the per-chain orchestrator (ADR-006): owns `chain_id`, the shared `state: Arc<RwLock<BotState>>`, the `LogDispatcher` event bus, and the pump. One `Bot` = one chain + one RPC; multi-chain = N Bots. `Bot::state_arc()` hands out clones of the `Arc<RwLock<BotState>>`.
- **`BotState`** (not `Bot`) is what the `RwLock` actually wraps: the pure-data registries — `pools: HashMap<u64, PoolEntry>` (single source of truth), token metadata, reorg journals, swap math, event buffers.
- **`PyBot`** holds `Arc<Bot>` and exposes register/update/calculate/encode/get/unregister methods. **Reads take `.state_arc().read()`; mutations take `.state_arc().write()`** — the guard is scoped in a `{ }` block so it drops before any Python object construction. `unregister_pool(address, pool_id: Option<...>)` is the ADR-007 removal seam (V2/V3 only on PyBot; passing a V4 `pool_id` raises `ValueError` — V4 removal is engine-side).
- **`PyLiquidityPool` / `PyErc20Token`** are *thin handles*: they hold a cloned `Arc<RwLock<BotState>>` + a key (`pool_id` / `Address`), own no state themselves, and cross the read guard on every property access. Keep the `Py` prefix (ADR-005 naming); the Python companions `LiquidityPool` / `Erc20Token` wrap them.
- **`pool_id`s are retired, never reused.** `next_pool_id` only advances, so a stale handle can never alias to a different pool after a remove+recreate. Do not "recycle" ids.

**Doc-vs-code discrepancy to know:** CONTEXT.md/AGENTS.md describe the shared object as `Arc<RwLock<Bot>>` and `with_core(Arc<RwLock<BotState>>)`. In the actual code the `RwLock` wraps **`BotState`**, and `PyBot` holds `Arc<Bot>` where `Bot` *contains* the `Arc<RwLock<BotState>>`. When in doubt, the code is authoritative; the docs describe the model, not the exact generic.

### Read/write guard & GIL discipline

- **GIL held** for: Python object construction (`PyList`/`PyDict`/`HexBytes`), RPC-type→dict conversion (`conversion::rpc_types` — inherently needs the GIL).
- **GIL released** (`py.detach()`) for: I/O-bound work (sync provider `block_on`) and long CPU work (ABI decode). Threshold is empirical: GIL release/reacquire ≈ 200ns, so sub-200ns pure compute (tick math, address utils) **holds** the GIL.
- **Copy borrowed Python data into owned Rust types BEFORE `py.detach()`.** The detached closure must not touch any `Bound<'_, PyAny>` — doing so is UB. Use `Py<T>` to store across a GIL release, `Bound<'py,T>` only inside GIL-held code.
- Every `Python::attach()`/`try_attach()` call site (on Tokio worker threads, in `conversion/{alloy,cache,json}.rs` + `rpc/async_provider.rs`) carries a `// SAFETY:` comment justifying no circular wait. Prefer `try_attach()` where a missed GIL (interpreter teardown) can be tolerated.

## The arbitrage engine (`UniswapEngine` / `PyUniswapArbEngine`)

`UniswapEngine` (`crates/degenbot-bot/src/solvers/uniswap_engine/`) is a **peer module to `Bot`** (ADR-003): it owns the path registry, solver dispatch, result batching, and diagnostics, but **owns no pool state** — it reads/mutates through the shared `Arc<RwLock<BotState>>` adopted via `with_core(...)`. It keeps its own `Mutex<UniswapEngine>` for path/solver state and associates with a `Bot` as an `EventSink`.

- **V2/V3/V4 composition:** composes a `V2BlockEngine`/`V3BlockEngine`/`V4BlockEngine` as sub-state. V4 pools are keyed by `(pool_manager, pool_id: [u8;32])` and carry the same CL tick-range sequence type as V3 — the solver can't tell V3 from V4. Solver dispatch: V2-V2 → `exact_mobius_solve`; CL×CL (V3/V4 any mix) → `int_solve_v3_v3`; mixed V2↔CL → `exact_solve_mixed_v2_v3_sequence`.
- **The pump loop** (`UniswapEnginePump`, "Eager Processing"): two WS subscriptions — `newHeads` + unfiltered `logs` (all filtering is Rust-side via `filter_relevant_logs`, checking topic0 against the 6 monitored topics AND address against registered pools/PoolManager). Each log is applied to state **immediately** via `apply_log` (zero-latency, returns affected path IDs, does NOT solve). Solves are **deferred & coalesced** at the top of the next loop iteration into one `solve_dirty` (which solves into `self.results` but does NOT send). Sends are **decoupled**: `send_result_batch` → `compute_diff_and_send`, driven by a 50ms debounce timer (`DEBOUNCE_MS`), force-flushed on block boundaries (`finalize_if_dirty`) and a 60s-timeout recovery path. Recorded invariant: *"no compute_diff_and_send here — the pump controls when batches are dispatched."*
- **Reorg journal + Removed-Flag:** every WS log carries a `removed: bool` (matches Alloy's `Log::removed`). The pump reads this directly rather than inferring reorgs from block numbers. On any `removed: true` for pool P at block B, `ReorgCoordinator` calls `restore_before_block(B)` for P (popping per-block deltas from the bounded `VecDeque` journal on the `PoolEntry`) and fires the **same** `on_pool_state_updated(P)` as a forward update (no separate `on_reorg`). Journal depth is `Bot::with_journal_depth` (default 32 = 1 mainnet epoch); reorgs deeper than depth **fail-stop the pump** rather than silently corrupting state. `V2BlockDelta` = scalar reserve priors; `V3BlockDelta` = scalar (sqrt/liq/tick) + per-tick priors, and serves both V3 and V4.
- **Result batching (`ResultBatch`):** an incremental diff carrying `solve_block` + block metadata + four lists: `fresh`/`updated`/`expired`/`removed`. Sent over an **unbounded `mpsc`** (every diff delivered, no silent drops). `self.delivered` tracks what Python has seen. Profit window: `profit > min_profit && profit <= max_profit` (strict lower, inclusive upper; defaults `ZERO`/`MAX`, set via `set_profit_thresholds`).
- **Sim-revert diagnostics:** `diagnostic_inspect_path()` returns a `DiagnosticPathState` snapshot (per-hop pool id/version/zfo/tokens/engine-state + on-chain diff when an RPC URL is set). Code-injection sim uses `eth_simulateV1` `stateOverrides.code` with the executor runtime bytecode from `contracts/cmd_executor_runtime_bytecode.txt` — **do NOT strip the CBOR metadata** (CODECOPY offsets misalign; the CBOR doubles as runtime data).
- **V4 rejection floors** enforced in `BotState::register_v4_pool` (correctness floor, in Rust not Python, per ADR-005 standalone constraint): amount-modifying hooks (`hook_flags & 0xCC != 0`) → `HookedPoolRejectedError`; dynamic fee (`fee == 0x100000`) → `DynamicFeePoolRejectedError`. Both subclass `ValueError`.

### Engine wrapper (`PyUniswapArbEngine`)

Lives in `degenbot-python/src/bot/engine/`, split into per-concern `#[pymethods]` impl blocks (register/snapshot/verify/solve/result_channel) — this requires the **`multiple-pymethods` pyo3 feature; do not drop it.** Canonical startup flow: **`subscribe()` → `backfill_from_snapshot()` → `resume_from_subscribe()`** (resume is the single gate after which result batches flow; attach the Python consumer before resuming). Exception types (`#[create_exception]`) live in `engine/errors.rs`: `VerificationMismatchError`/`VerificationRpcError` (subclass `RuntimeError`), `HookedPoolRejectedError`/`DynamicFeePoolRejectedError` (subclass `ValueError`).

### Lock order — engine-then-core (never reverse)

Nested locking is always **engine `Mutex` → core `RwLock<BotState>`**. The pump applies a log under the core write lock, **releases it**, then the engine dirties the pool id in its own per-engine dirty set (taking the engine `Mutex` alone), and reads `BotState` again later in `solve_dirty`. No code path nests core-then-engine. Violating this risks deadlock.

## What lives in Rust vs Python (ADR-003: Bot is the state owner)

- **Rust owns:** all pool state (V2 reserves/fees, V3/V4 `sqrt_price_x96`/`liquidity`/`tick`/`tick_data`), token metadata, reorg journals, the RPC `AlloyProvider`, the per-block pump, path resolution, solver dispatch, result batching, the event decoders + dispatch. Pool calc math (`calculate_tokens_out/in`) is pure Rust and EVM-exact (U512 arithmetic).
- **Python owns:** the user-facing API, DB/snapshot loading, `Erc20Token` identity & price oracle (`Fraction`), pub/sub (`WeakSet`), registry bookkeeping. Python imports `degenbot_rs` and constructs/drives the Rust objects; the production example (`examples/eth_backrun_v2_v3_v4_rust.py`) drives the Rust engine pump exclusively.
- **Python→Rust call surface** (registered in `c_api.rs`): classes `PyBot`, `PyLiquidityPool`, `PyErc20Token`, `PyDexIdentity`, `UniswapArbEngine` (the Python name for `PyUniswapArbEngine`), `AlloyProvider`/async variants, `Contract`, subscription handles; functions `decode`/`encode`/selector/tick-math/checksum; the V4 exception types. The Python `PoolRegistry.remove`/`_reset` propagate V2/V3 removals into Rust via `py_bot.unregister_pool` (the `py_bot: PyBot | None = None` kwarg; `None` = test-only Python-only path).
- The f64 Möbius solver stack is **deleted** from Rust (gen-3 is U512-integer-exact and f64-free; any `f64` in gen-3 modules is a `#[cfg(test)]` oracle). A pure-Python f64 solver package survives in `degenbot/arbitrage/solvers/` only for not-yet-ported paths; do not re-introduce f64 into the Rust solve path.

## Build, profiles, test setup

- **Release profile** (workspace root, the shipped `degenbot_rs` cdylib): `lto = "thin"`, `strip = true`, `codegen-units = 1`. `lto`/`strip` are profile-level (Cargo has no per-package `lto`) so they apply workspace-wide, but the thin-LTO link only spans units surviving into the cdylib.
- **Per-package override:** every core crate gets `[profile.release.package.<crate>] codegen-units = 16` for faster compilation during a cdylib release build — they re-converge under the cdylib's thin LTO at the final link, so runtime is unaffected. Dev profile uses `codegen-units = 16` across the board for fast incremental builds. If you add a core crate, add its `[profile.release.package....]` block too.
- **`extension-module` feature subtlety:** the `degenbot_rs` cdylib has crate-types `["rlib","cdylib"]`. The `extension-module` feature (`pyo3/extension-module`) leaves libpython symbols undefined, resolved at load time by the host interpreter. `maturin develop`/`build` set this automatically. A **raw `cargo build` does NOT** — and on macOS, `ld` rejects undefined symbols without `-undefined dynamic_lookup`. The `just ci-rust`/`build-rust-extension` recipes add `-C link-arg=-undefined -C link-arg=dynamic_lookup` to RUSTFLAGS on Darwin. Build the actual extension with `just dev` (= `maturin develop`), not bare cargo.
- **`auto-initialize` feature** (default-on) auto-initializes the Python interpreter — **required** by the two integration tests (`tests/python_integration.rs`, `tests/concurrency_stress.rs`, both declared with `required-features = ["auto-initialize"]`). A `#[ctor]` in `lib.rs` pre-initializes Python before test threads spawn (avoids a `Py_InitializeEx` race).
- **`just test-rust`** sets up libpython paths so the pyo3 test binary finds it at runtime: it reads `sysconfig LIBDIR` from `.venv/bin/python3` and exports it to **both** `LD_LIBRARY_PATH` (Linux loader) **and** `DYLD_LIBRARY_PATH` (macOS dyld), then `cargo test --workspace`. If Rust tests fail to load libpython, this env setup is why.
- **Binding-layer features** are per-domain (`bot`, `rpc`, `abi`, `cl-math`, `uniswap`, `decoders`, `async`), default = all-on. Implicit coupling: `bot` → `rpc`+`decoders`+`uniswap`; `rpc` → `abi`. Keep these consistent if you add a binding module.

## Gotchas a contributor will likely hit

- **Don't put pyo3 in a core crate.** Even one un-gated `use pyo3` fails the invariant and breaks the standalone-Rust / GIL-free-test guarantee. Split it (core fn + binding wrapper).
- **`PyBot` does not wrap `Arc<RwLock<Bot>>` literally** — it's `Arc<Bot>`, and `Bot` holds `Arc<RwLock<BotState>>`. Handles and the engine share the `BotState` arc (via `state_arc()`/`with_core()`), not a `Bot` arc. The docs simplify this.
- **Scope your lock guards.** Read methods take `.read()`, mutations `.write()`, both in a `{ }` block that drops the guard before constructing any Python object. Holding a guard across `Python` object creation, or across an `.await`, is wrong.
- **Never reverse the engine-then-core lock order.**
- **Solving and sending are decoupled** in the engine. `solve_dirty` updates `self.results` and must NOT send a batch; only the pump (debounce/boundary/timeout) calls `send_result_batch`. Adding a send into `solve_dirty` breaks the coalescing contract.
- **`multiple-pymethods` and `auto-initialize` pyo3 features are load-bearing** — the engine wrapper's multi-impl-block split needs the former; integration tests need the latter.
- **New core crate checklist:** add to `[workspace] members`, add a `[profile.release.package.<crate>]` block, and **add it to the `check-no-pyo3-in-cores` justfile loop** (and to the umbrella re-export if it should be in the standalone surface).
- **`curve-math` and `balancer-math` are pure-math leaves that are NOT yet wired** (no umbrella re-export, no binding wrapper, not in the solve path) and NOT in the pyo3 check loop. Their *state* layers (`bot_core/{curve,balancer_*}_state.rs`) are integrated, but the math leaves are pending.
- **Edit Rust, then run `just ci-rust`** (= `fmt-check` + `check-no-pyo3-in-cores` + `lint-rust` (clippy `--deny warnings`, pedantic) + `test-rust`). Clippy is strict (pedantic/perf/correctness all warn-as-deny-equivalent); use `parking_lot::Mutex`/`RwLock` (no poisoning, satisfies `expect_used`/`unwrap_used`), never `std::sync::Mutex` or `RefCell` (the latter is unsafe under free-threaded Python).
