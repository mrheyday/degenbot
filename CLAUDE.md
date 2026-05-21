# CLAUDE.md

This file is the Claude entrypoint for this vendored degenbot checkout. `AGENTS.md` remains the
source of truth for repository conventions; read it first, then apply the project-specific guidance
below.

## Project Role

This repository is the MEV-Arbitrum home for Python market intelligence and Rust latency helpers:

- Python protocol adapters, market analysis, source provenance, signal emitters, and candidate
  scoring live under `src/degenbot`.
- Rust deterministic hot-path helpers live under `rust/src` and are exposed through the maturin
  `degenbot_rs` binding.
- Parent-repo TypeScript orchestration stays in `coordinator/`.
- Parent-repo Solidity settlement and enforcement stays in `contracts/`.

See `docs/architecture/mev-arbitrum-code-home.md` before moving logic across those boundaries.

## Operating Rules

- Preserve unrelated local changes. Check `git status --short` before editing.
- Use red/green TDD for new behavior and focused regression tests for bug fixes.
- Prefer frozen dataclasses for value objects and `TypedDict` for known structured dictionaries.
- Keep arithmetic deterministic and integer-exact. Do not add tolerances to Aave or accounting
  verification paths.
- Do not manually rebuild, recreate, or reinstall the Rust extension after Rust edits. Imports and
  tests trigger the maturin rebuild.
- Use repo-local errors derived from `DegenbotError`.
- Use `from degenbot.logging import logger` for logging.

## Verification Commands

- Python: `just test-python`
- Rust: `just test-rust`
- Rust lint: `just lint-rust`
- Combined tests: `just test-all`
- Full lint: `just lint`
- Formatting: `just format`

For narrow work, run the smallest relevant test first, then a broader command when risk warrants it.

## Claude Workflow Layer

Adapted Claude agents and commands live under `.claude/`. They are intentionally scoped to degenbot:

- `.claude/agents/` contains read-only codebase and EVM investigation roles.
- `.claude/commands/` contains research, planning, implementation, validation, debug, worktree, and
  commit workflows.
- `scripts/claude_spec_metadata.sh` gathers deterministic metadata for research and plan documents.
- `scripts/defillama_reference_checkout.sh` creates sparse DefiLlama reference checkouts for
  protocol-source intelligence.

Do not copy generic boilerplate instructions into this repository without adapting them to the
Python/Rust/Aave/MEV architecture above.
