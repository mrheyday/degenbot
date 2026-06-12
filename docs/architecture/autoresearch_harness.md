# Autoresearch Harness Lane

Date: 2026-06-12

## Purpose

The autoresearch lane captures gas-optimization and executable-shape experiments for
mock-chain arbitrage execution paths.

It is now a first-class suite under:

- `tests/autoresearch/` for test artifacts and experiment fixtures
- `just test-autoresearch` for execution dispatch
- `tests/autoresearch/AR_TASK_MANIFEST.md` for lane definitions and target set

## Execution path

- Run all AR fixtures and lane tests:
  - `just test-autoresearch`
- Export benchmark outputs from AR loops by emitting:
  - `METRIC gas_used=<value>`

## Scope

- Keep-Stream parsing and callback ordering checks
- Mixed V2/V3/V4 arbitrage chain scenarios
- Zero-balance ordering/pathing variants
- Harness contract shape validation through deterministic fake world fixtures

## Commit-lane policy

- This lane is first-class only for experiment execution and reproducibility.
- Core production code paths continue to be governed by existing degenbot tests and
  policy gates.
- Any harness-derived optimization must be propagated by explicit follow-up work into
  production execution code with the same policy and security bar.

