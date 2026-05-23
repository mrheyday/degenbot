# Claude Workflow Layer

This directory adapts the useful parts of `bleu/claude-boilerplate` for degenbot. It keeps the
workflow scaffolding and removes unrelated Rails, Linear, setup, and generic template content.

## What Belongs Here

- Agents that help locate, analyze, and compare degenbot code paths.
- Agents that govern MEV-Arbitrum execution boundaries, Stylus parity, Aave revision math, and
  LangChain/LangGraph/Deep Agents/LangSmith framework fit when those topics are explicitly in scope.
- Agents that mine DefiLlama sources for protocol evidence without vendoring upstream code.
- Commands that standardize research, planning, implementation, validation, Aave debugging, local
  review, DefiLlama protocol intelligence, worktree setup, and commits.
- Instructions that reference this repository's real commands: `just`, `uv`, Python tests, Rust
  tests, and the maturin import behavior.

## What Does Not Belong Here

- Generic app setup scripts.
- Framework-specific guidance for code that does not exist in this repo.
- Duplicate architecture documents that drift from `AGENTS.md` and
  `docs/architecture/mev-arbitrum-code-home.md`.

## Verification Discipline

Before claiming a change is ready, capture:

- the exact command run;
- pass or fail status;
- any environment blocker;
- why the selected verification scope matches the changed surface.
