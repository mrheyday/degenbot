# Institutional Solver Intelligence Doctrine

## 1) Complete Solidity / execution system baseline
- Deployer-side execution remains in existing `contracts/` and `coordinator/` boundaries.
- Off-chain policy and adaptive intelligence are implemented in `src/degenbot`.
- Contract execution constraints are enforced through strict preflight policy before signing (`compose_strict_dispatch_envelope`).
- Existing execution gates are fail-closed and deterministic by default.

## 2) Additional attached modules
- `src/degenbot/ops_solver/execution_policy.py`
  - transport allowlist
  - flash-amount/profit/provenance checks
  - strict policy violations as typed errors
- `src/degenbot/ops_solver/strict_dispatch.py`
  - single composition path applying engine admission + policy enforcement
- `src/degenbot/strategy_signals/institutional_solver_intelligence.py`
  - deterministic AI governance gate for adaptive control changes
- `src/degenbot/strategy_signals/__init__.py`
  - wired exports for deterministic policy modules

## 3) AI administrator framework
- Canonical persona: `InstitutionalSolverIntelligence`.
- Responsibilities encode deterministic profit defense, bounded drawdown policy, and governance discipline.
- Decisions are deterministic: `APPROVE`, `REVIEW`, or `BLOCK`.
- All recommendations are auditable dataclass records with explicit rationale + control tags.

## 4) Execution policy doctrine
- Fail-closed as default:
  - non-positive flash amount => reject
  - non-positive min-profit => reject
  - missing preflight => reject
  - weak transport / public submission => reject
  - missing executeWithSig gate => reject
- Explicit policy transport allowlist in one module (`ALLOWED_STRICT_TRANSPORTS`).
- Dispatch is blocked early before any envelope reaches signing/submission.

## 5) Security posture statement
- Zero-trust on callback entrypoints and transport.
- Never mutate thresholds directly from observation proposals.
- Human review required for high-risk recommendation paths.
- Every policy adjustment remains explicit, gated, and replay-verifiable.
- No silent tolerance-based behavior in capital-moving lanes.

## 6) Failure doctrine & recovery plan
- If policy enforcement fails: reject envelope and return structured `StrictExecutionPolicyError` with violation codes.
- If policy correction proposes risk drift: block/review, route through governance, and require replay.
- If adaptive candidate is ambiguous: `REVIEW` + additional controls instead of auto-deploying.
- Recovery path always preserves on-chain state and does not assume prior assumptions.

## 7) Operational readiness specification
- Execution surfaces:
  - strict dispatch helper (`compose_strict_dispatch_envelope`) as single entry for policy-sensitive flows.
  - strict policy context built from plan and transport metadata.
- Metrics:
  - violation codes are machine-readable and deterministic.
  - `trace_id` is propagated for post-failure correlation.
- Process:
  1. classify candidate
  2. preflight/dispatch compose
  3. strict policy enforcement
  4. submit only on pass

## 8) Monetization framework
- Keep all policy controls in preflight and execution phases.
- Preserve profitable execution only when replayed min-profit conditions pass.
- Avoid opportunistic risk by preventing public/private ambiguity and by requiring explicit supported transports.
- Profitability remains tied to deterministic deltas and not to stochastic override heuristics.

## 9) Formal correctness stance
- Determinism over heuristic optimization.
- Explicit integer thresholds, no tolerance-based overrides for capital-moving decisions.
- Fail conditions are exhaustive and typed (`ExecutionPolicyViolation`).
- No policy mutation without explicit proposal path.

## 10) Auditor-ready architecture rationale
- Boundaries are explicit:
  - policy logic in Python (`degenbot`)
  - execution strategy and routing in coordinator/type system
  - settlement in contracts
- All enforcement points are named and logged with stable identifiers.
- The system is designed for review: deterministic predicates, auditable proposals, and explicit control evidence.
