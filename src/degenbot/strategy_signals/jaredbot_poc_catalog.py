"""JaredBot skill-to-system POC catalog.

The JaredBot skill files are playbooks. This module turns each named playbook
into a machine-readable proof-of-concept lane so the system can reason about
coverage without confusing a POC with permission to move capital.

POC status semantics:
- ``EXECUTABLE``: the repo has an end-to-end code path and tests for the lane.
- ``INFRASTRUCTURE``: the repo has monitor/submission infrastructure, but the
  strategy-specific transaction is not the direct owner of capital movement.
- ``DEFENSIVE``: the lane protects routing, custody, or accounting and should
  not emit transactions by itself.
- ``NEEDS_WORKFLOW``: the repo contains useful signals or scaffolding, and the
  next step is a dedicated builder/simulator/test workflow before live tx output.
"""

from __future__ import annotations

# ruff: noqa: E501
from dataclasses import dataclass
from enum import StrEnum


class PocStatus(StrEnum):
    """Operational state of a JaredBot POC lane."""

    EXECUTABLE = "executable"
    INFRASTRUCTURE = "infrastructure"
    DEFENSIVE = "defensive"
    NEEDS_WORKFLOW = "needs_workflow"


class CapitalMode(StrEnum):
    """How the POC is allowed to interact with capital."""

    LIVE_TX = "live_tx"
    READ_ONLY = "read_only"
    NO_TX = "no_tx"
    WORKFLOW_REQUIRED = "workflow_required"


@dataclass(frozen=True, slots=True)
class PocStage:
    """One stage in a JaredBot end-to-end POC lane."""

    order: int
    name: str
    code_refs: tuple[str, ...]
    validation: str


@dataclass(frozen=True, slots=True)
class JaredBotPoc:
    """Machine-readable binding from one JaredBot skill to repo POC code."""

    skill_name: str
    skill_path: str
    module: str
    status: PocStatus
    capital_mode: CapitalMode
    strategy_surface: str
    allowed_use: str
    scope_note: str
    workflow_requirement: str
    required_signals: tuple[str, ...]
    safety_invariants: tuple[str, ...]
    code_refs: tuple[str, ...]
    proof_refs: tuple[str, ...]
    stages: tuple[PocStage, ...]

    @property
    def can_emit_transaction(self) -> bool:
        """True only for POCs wired to an existing transaction path."""
        return self.capital_mode is CapitalMode.LIVE_TX

    @property
    def needs_workflow(self) -> bool:
        """True when live tx output needs a dedicated workflow before execution."""
        return self.capital_mode is CapitalMode.WORKFLOW_REQUIRED


def _stage(
    order: int,
    name: str,
    code_refs: tuple[str, ...],
    validation: str,
) -> PocStage:
    return PocStage(order=order, name=name, code_refs=code_refs, validation=validation)


JAREDBOT_POCS: tuple[JaredBotPoc, ...] = (
    JaredBotPoc(
        skill_name="jaredbot-crypto-bot-security",
        skill_path=".agents/skills/jaredbot-crypto-bot-security/SKILL.md",
        module="JB-12 Crypto-Bot Security",
        status=PocStatus.DEFENSIVE,
        capital_mode=CapitalMode.NO_TX,
        strategy_surface="custody, service onboarding, anomaly response, admin kill-switches",
        allowed_use="Reject unsafe services, enforce env-only secrets, and preserve pause/owner controls.",
        scope_note="Third-party bot binaries, SDKs, wallet approvals, and admin-key integrations need review.",
        workflow_requirement="Security POC emits no transaction; it documents deployment and incident surfaces.",
        required_signals=(
            "owner model",
            "bytecode presence",
            "secret source",
            "anomaly signal",
            "pause path",
        ),
        safety_invariants=(
            "keys stay env-only",
            "admin actions stay owner/Safe-bound",
            "anomalies fail closed before strategy dispatch",
        ),
        code_refs=(
            "coordinator/src/http/admin.ts",
            "coordinator/src/submission/submitter.ts",
            "contracts/src/executors/Executor.sol",
            "solver/driver/ops/readiness_gate.py",
        ),
        proof_refs=(
            "solver/driver/tests/test_anomaly_response.py",
            "solver/driver/tests/test_readiness_gate.py",
        ),
        stages=(
            _stage(
                1,
                "Collect security posture",
                ("coordinator/src/http/admin.ts",),
                "Admin and pause surfaces are visible.",
            ),
            _stage(
                2,
                "Classify service risk",
                ("solver/driver/ops/readiness_gate.py",),
                "Readiness checks report missing or unsafe prerequisites.",
            ),
            _stage(
                3,
                "Bind signer path",
                ("coordinator/src/submission/submitter.ts",),
                "Signer is loaded from environment-backed config only.",
            ),
            _stage(
                4,
                "Enforce on-chain stop",
                ("contracts/src/executors/Executor.sol",),
                "Pause and owner checks guard capital-moving entrypoints.",
            ),
            _stage(
                5,
                "Verify incident response",
                ("solver/driver/tests/test_anomaly_response.py",),
                "Anomaly response remains test-backed.",
            ),
        ),
    ),
    JaredBotPoc(
        skill_name="jaredbot-defi-adjacent-context",
        skill_path=".agents/skills/jaredbot-defi-adjacent-context/SKILL.md",
        module="JB-13 Adjacent DeFi, Treasury, And Tax",
        status=PocStatus.DEFENSIVE,
        capital_mode=CapitalMode.NO_TX,
        strategy_surface="treasury exposure labels, PnL metrics, and accounting evidence",
        allowed_use="Tag PnL, strategy revenue, gas, and treasury exposure for later accounting export.",
        scope_note="Idle-treasury yield farming or LST/LRT allocation belongs in a separate treasury workflow.",
        workflow_requirement="Accounting POC is metadata-only; treasury movement needs a Safe-governed path.",
        required_signals=(
            "strategy label",
            "profit token",
            "gas cost",
            "receipt status",
            "realized delta",
        ),
        safety_invariants=(
            "treasury movement is out of scope",
            "tax evidence is derived from receipts and metrics",
            "profit labels are strategy-specific",
        ),
        code_refs=(
            "coordinator/src/http/metrics.ts",
            "coordinator/src/submission/submitter.ts",
            "coordinator/src/types/domain.ts",
        ),
        proof_refs=(
            "coordinator/src/submission/submitter.test.ts",
            "solver/driver/tests/test_readiness_gate.py",
        ),
        stages=(
            _stage(
                1,
                "Attach strategy label",
                ("coordinator/src/submission/submitter.ts",),
                "DirectTxRequest carries shadowStrategy/profitToken.",
            ),
            _stage(
                2,
                "Record outcome metrics",
                ("coordinator/src/http/metrics.ts",),
                "Metrics expose dispatch and error counters.",
            ),
            _stage(
                3,
                "Preserve domain evidence",
                ("coordinator/src/types/domain.ts",),
                "Decision and route types preserve strategy identity.",
            ),
            _stage(
                4,
                "Prove readiness gate",
                ("solver/driver/tests/test_readiness_gate.py",),
                "Operational readiness is test-backed.",
            ),
        ),
    ),
    JaredBotPoc(
        skill_name="jaredbot-mev-amm-economics",
        skill_path=".agents/skills/jaredbot-mev-amm-economics/SKILL.md",
        module="JB-02 AMM Economics",
        status=PocStatus.DEFENSIVE,
        capital_mode=CapitalMode.READ_ONLY,
        strategy_surface="AMM sizing, slippage floors, route-comparison economics",
        allowed_use="Compute deterministic quote floors and sizing bounds before calldata is emitted.",
        scope_note="Fee-differential arbitrage requires a real price gap, not only differing fee tiers.",
        workflow_requirement="Economics POC feeds downstream min-out/min-profit requirements; it does not submit.",
        required_signals=("reserve state", "fee tier", "amountOutMin", "gas cost", "flash fee"),
        safety_invariants=(
            "amountOutMin is never optional on executable swaps",
            "fee-differential-only candidates are filtered",
            "all profit gates are raw integer based",
        ),
        code_refs=(
            "coordinator/src/strategies/sandwich/sizing.ts",
            "coordinator/src/quotes/execution-path.ts",
            "coordinator/src/strategies/route-comparator/comparator.ts",
        ),
        proof_refs=(
            "coordinator/src/strategies/sandwich/sizing.test.ts",
            "coordinator/src/strategies/route-comparator/route-comparator.test.ts",
        ),
        stages=(
            _stage(
                1,
                "Read pool economics",
                ("coordinator/src/strategies/sandwich/sizing.ts",),
                "Sizing uses pool-state inputs, not float approximations.",
            ),
            _stage(
                2,
                "Build quote floor",
                ("coordinator/src/quotes/execution-path.ts",),
                "Executor path applies slippage bps into amountOutMin.",
            ),
            _stage(
                3,
                "Compare route economics",
                ("coordinator/src/strategies/route-comparator/comparator.ts",),
                "Manual and aggregator route economics are compared deterministically.",
            ),
            _stage(
                4,
                "Verify math tests",
                ("coordinator/src/strategies/sandwich/sizing.test.ts",),
                "Sizing regressions are covered.",
            ),
        ),
    ),
    JaredBotPoc(
        skill_name="jaredbot-mev-bot-engineering",
        skill_path=".agents/skills/jaredbot-mev-bot-engineering/SKILL.md",
        module="JB-01 Bot Engineering",
        status=PocStatus.INFRASTRUCTURE,
        capital_mode=CapitalMode.READ_ONLY,
        strategy_surface="monitor -> decision -> simulator/planner -> submitter pipeline",
        allowed_use="Use Rust/Python/TS boundaries to move opportunities through deterministic dispatch.",
        scope_note="Monitor output flows through decision, simulation, and submitter workflow stages.",
        workflow_requirement="Pipeline POC requires a typed Opportunity and a strategy-specific dispatcher.",
        required_signals=(
            "opportunity id",
            "latency",
            "queue depth",
            "decision kind",
            "submit status",
        ),
        safety_invariants=(
            "single opportunity maps to one decision",
            "dispatch failures are counted and logged",
            "shadow/replay modes stay typed",
        ),
        code_refs=(
            "engine/src/lib.rs",
            "coordinator/src/index.ts",
            "solver/driver/execution/degenbot_ipc.py",
            "coordinator/src/decision/engine.ts",
        ),
        proof_refs=(
            "coordinator/src/integration/native-arb-e2e.test.ts",
            "solver/driver/tests/test_degenbot_ipc_integration.py",
        ),
        stages=(
            _stage(
                1,
                "Emit opportunity",
                ("engine/src/lib.rs", "solver/driver/execution/degenbot_ipc.py"),
                "Engine/Python adapter emits typed opportunities.",
            ),
            _stage(
                2,
                "Route decision",
                ("coordinator/src/decision/engine.ts",),
                "DecisionEngine selects exactly one route.",
            ),
            _stage(
                3,
                "Dispatch strategy",
                ("coordinator/src/index.ts",),
                "Coordinator switch owns all strategy dispatch.",
            ),
            _stage(
                4,
                "Verify E2E",
                ("coordinator/src/integration/native-arb-e2e.test.ts",),
                "Integration test exercises monitor-to-dispatch path.",
            ),
        ),
    ),
    JaredBotPoc(
        skill_name="jaredbot-mev-flash-arbitrage",
        skill_path=".agents/skills/jaredbot-mev-flash-arbitrage/SKILL.md",
        module="JB-04 Flash Arbitrage",
        status=PocStatus.EXECUTABLE,
        capital_mode=CapitalMode.LIVE_TX,
        strategy_surface="flash-funded native arbitrage and cross-DEX cyclic routes",
        allowed_use="Execute atomic flash-funded routes with repayment and minProfit enforced on-chain.",
        scope_note="Owned-inventory arbitrage and fee-differential-only routing are separate workflow surfaces.",
        workflow_requirement="Flash route must resolve to a supported lender and swaps must close back to flashToken.",
        required_signals=("flash liquidity", "swap path", "amountOutMin", "flash fee", "minProfit"),
        safety_invariants=(
            "flashAmount > 0",
            "first tokenIn and last tokenOut equal flashToken",
            "post-callback balance covers premium plus minProfit",
        ),
        code_refs=(
            "coordinator/src/strategies/native-arb.ts",
            "coordinator/src/flash/source-router.ts",
            "contracts/src/executors/Executor.sol",
        ),
        proof_refs=(
            "coordinator/src/strategies/native-arb.test.ts",
            "contracts/test/unit/ExecutorStrategies.t.sol",
        ),
        stages=(
            _stage(
                1,
                "Detect price gap",
                ("engine/src/lib.rs",),
                "Opportunity carries flash amount and route.",
            ),
            _stage(
                2,
                "Resolve flash source",
                ("coordinator/src/flash/source-router.ts",),
                "Supported lender is selected deterministically.",
            ),
            _stage(
                3,
                "Encode swaps",
                ("coordinator/src/strategies/native-arb.ts",),
                "SwapStep calldata maps to Executor ABI.",
            ),
            _stage(
                4,
                "Execute callback",
                ("contracts/src/executors/Executor.sol",),
                "Flash callback dispatches strategy and checks profit.",
            ),
            _stage(
                5,
                "Verify route",
                ("coordinator/src/strategies/native-arb.test.ts",),
                "TS route builder has regression tests.",
            ),
        ),
    ),
    JaredBotPoc(
        skill_name="jaredbot-mev-frontrun",
        skill_path=".agents/skills/jaredbot-mev-frontrun/SKILL.md",
        module="JB-07 Frontrun Timing",
        status=PocStatus.INFRASTRUCTURE,
        capital_mode=CapitalMode.READ_ONLY,
        strategy_surface="Timeboost/Kairos timing decisions and sequencer-feed candidate handling",
        allowed_use="Use timing signals only where a downstream strategy has its own execution guard.",
        scope_note="Timing signals are scoped to strategy-owned calldata, not unrelated victim-copy transactions.",
        workflow_requirement="Timing POC selects priority lane; transaction calldata comes from the strategy lane.",
        required_signals=(
            "target timing",
            "transport latency",
            "bid cost",
            "inclusion window",
            "replay evidence",
        ),
        safety_invariants=(
            "frontrun timing is strategy-scoped",
            "Timeboost bid is economics-priced",
            "no displacement or suppression transaction is emitted",
        ),
        code_refs=(
            "coordinator/src/strategies/timeboost-economics.ts",
            "coordinator/src/signals/detectors/timeboost-round.ts",
            "coordinator/src/submission/lane-router.ts",
        ),
        proof_refs=(
            "coordinator/src/strategies/timeboost-economics.test.ts",
            "coordinator/src/submission/lane-router.test.ts",
        ),
        stages=(
            _stage(
                1,
                "Detect timing window",
                ("coordinator/src/signals/detectors/timeboost-round.ts",),
                "Timeboost round detector provides timing state.",
            ),
            _stage(
                2,
                "Price priority",
                ("coordinator/src/strategies/timeboost-economics.ts",),
                "Bid decision is EV-priced.",
            ),
            _stage(
                3,
                "Select lane",
                ("coordinator/src/submission/lane-router.ts",),
                "LaneRouter resolves direct/Kairos path.",
            ),
            _stage(
                4,
                "Verify timing economics",
                ("coordinator/src/strategies/timeboost-economics.test.ts",),
                "Timeboost decision tests cover edge cases.",
            ),
        ),
    ),
    JaredBotPoc(
        skill_name="jaredbot-mev-jit-v4",
        skill_path=".agents/skills/jaredbot-mev-jit-v4/SKILL.md",
        module="JB-06 JIT/V4",
        status=PocStatus.NEEDS_WORKFLOW,
        capital_mode=CapitalMode.WORKFLOW_REQUIRED,
        strategy_surface="V4 hook classification and JIT policy guard",
        allowed_use="Classify hook permissions and source approved hook execution surfaces.",
        scope_note="Mint-swap-burn JIT lifecycle needs its own deterministic lifecycle builder.",
        workflow_requirement="Add dedicated mint/burn/collect builder, source binding, simulation, and fork tests.",
        required_signals=(
            "tick state",
            "liquidity",
            "hook address",
            "permission flags",
            "simulation trace",
        ),
        safety_invariants=(
            "unknown hook permissions require explicit classification",
            "LP mutation requires a lower-lane owner",
            "no generic V4 hook can move capital",
        ),
        code_refs=(
            "coordinator/src/strategies/v4-hooks.ts",
            "contracts/src/libraries/RouterRegistry.sol",
        ),
        proof_refs=("coordinator/src/strategies/v4-hooks.test.ts",),
        stages=(
            _stage(
                1,
                "Classify hook",
                ("coordinator/src/strategies/v4-hooks.ts",),
                "Hook permission flags are explicit.",
            ),
            _stage(
                2,
                "Classify unknown hook",
                ("coordinator/src/strategies/v4-hooks.ts",),
                "Unclassified hook path is surfaced for workflow completion.",
            ),
            _stage(
                3,
                "Pin router context",
                ("contracts/src/libraries/RouterRegistry.sol",),
                "V4 router constants are canonical.",
            ),
            _stage(
                4,
                "Verify hook policy",
                ("coordinator/src/strategies/v4-hooks.test.ts",),
                "Hook classification behavior is tested.",
            ),
        ),
    ),
    JaredBotPoc(
        skill_name="jaredbot-mev-launch-sniper",
        skill_path=".agents/skills/jaredbot-mev-launch-sniper/SKILL.md",
        module="JB-10 Launch Sniper And Tail-Token Defense",
        status=PocStatus.NEEDS_WORKFLOW,
        capital_mode=CapitalMode.WORKFLOW_REQUIRED,
        strategy_surface="tail-token discovery and honeypot/rug filter scaffold",
        allowed_use="Use launch-sniper signals to classify tail-token routes and source executable candidates.",
        scope_note="Same-block buy/sell sniper output needs a dedicated executor workflow before live tx emission.",
        workflow_requirement="Connect sourced token checks, audited executor calldata, simulation, and fork tests.",
        required_signals=(
            "token bytecode",
            "liquidity",
            "transfer-tax simulation",
            "owner/admin model",
            "private transport",
        ),
        safety_invariants=(
            "known honeypots are filtered",
            "own capital remains zero",
            "execution path awaits dedicated executor workflow",
        ),
        code_refs=("coordinator/src/strategies/launch-sniper.ts",),
        proof_refs=("solver/driver/tests/test_jaredbot_poc_catalog.py",),
        stages=(
            _stage(
                1,
                "Observe factory event",
                ("coordinator/src/strategies/launch-sniper.ts",),
                "Pair/pool event parser identifies target token.",
            ),
            _stage(
                2,
                "Apply tail-token checks",
                ("coordinator/src/strategies/launch-sniper.ts",),
                "Blocklist and liquidity checks classify targets.",
            ),
            _stage(
                3,
                "Await executor workflow",
                ("coordinator/src/strategies/launch-sniper.ts",),
                "executeSnipe records the missing executor workflow and returns null.",
            ),
            _stage(
                4,
                "Verify workflow-required catalog",
                ("solver/driver/tests/test_jaredbot_poc_catalog.py",),
                "Catalog asserts the sniper POC needs a dedicated workflow.",
            ),
        ),
    ),
    JaredBotPoc(
        skill_name="jaredbot-mev-liquidations",
        skill_path=".agents/skills/jaredbot-mev-liquidations/SKILL.md",
        module="JB-05 Liquidations",
        status=PocStatus.EXECUTABLE,
        capital_mode=CapitalMode.LIVE_TX,
        strategy_surface="Aave/Balancer liquidation plus Morpho liquidation fork-proven contract path",
        allowed_use="Execute profitable liquidations with preflight, amountOutMinimum, deadline, and minNetProfit.",
        scope_note="Liquidation txs use simulator, eth_call preflight, and on-chain profit guard stages.",
        workflow_requirement="Position must be urgent, simulator profitable, preflight successful, and deadline fresh.",
        required_signals=(
            "health factor",
            "debt amount",
            "collateral",
            "swap-back quote",
            "latency lane",
            "minProfit",
        ),
        safety_invariants=(
            "amountOutMinimum > 0",
            "deadline is caller-supplied and hash-pinned",
            "NotProfitable reverts preserve capital",
        ),
        code_refs=(
            "coordinator/src/strategies/liquidation/index.ts",
            "coordinator/src/strategies/liquidation/simulator.ts",
            "coordinator/src/strategies/liquidation/executor.ts",
            "contracts/src/executors/LiquidationExecutor.sol",
        ),
        proof_refs=(
            "coordinator/src/strategies/liquidation/index.test.ts",
            "coordinator/src/strategies/liquidation/simulator.test.ts",
            "coordinator/src/strategies/liquidation/executor.test.ts",
            "contracts/test/fork/LiquidationExecutor.morpho.fork.t.sol",
        ),
        stages=(
            _stage(
                1,
                "Monitor risky positions",
                ("coordinator/src/strategies/liquidation/monitor.ts",),
                "Health factors are swept before simulation.",
            ),
            _stage(
                2,
                "Simulate profit",
                ("coordinator/src/strategies/liquidation/simulator.ts",),
                "Simulator derives amountOutMinimum and netProfit.",
            ),
            _stage(
                3,
                "Preflight calldata",
                ("coordinator/src/strategies/liquidation/executor.ts",),
                "eth_call catches stale or unprofitable state.",
            ),
            _stage(
                4,
                "Execute liquidation",
                ("contracts/src/executors/LiquidationExecutor.sol",),
                "Contract enforces callback and profit guards.",
            ),
            _stage(
                5,
                "Verify fork path",
                ("contracts/test/fork/LiquidationExecutor.morpho.fork.t.sol",),
                "Morpho liquidation path has fork coverage.",
            ),
        ),
    ),
    JaredBotPoc(
        skill_name="jaredbot-mev-mempool-relay",
        skill_path=".agents/skills/jaredbot-mev-mempool-relay/SKILL.md",
        module="JB-03 Mempool, Relay, And Timeboost",
        status=PocStatus.INFRASTRUCTURE,
        capital_mode=CapitalMode.READ_ONLY,
        strategy_surface="Arbitrum sequencer-feed awareness and private/express submission routing",
        allowed_use="Select direct, Kairos, or shadow routing according to strategy latency requirements.",
        scope_note="Arbitrum relay workflow uses Arbitrum transport assumptions instead of L1 public mempool paths.",
        workflow_requirement="Relay POC chooses transport; transaction calldata comes from a strategy lane.",
        required_signals=(
            "transport kind",
            "latency",
            "fallback policy",
            "round state",
            "submission status",
        ),
        safety_invariants=(
            "Arbitrum has no public mempool dependency",
            "fallback route is explicit",
            "shadow mode preserves replay evidence",
        ),
        code_refs=(
            "coordinator/src/submission/lane-router.ts",
            "coordinator/src/signals/detectors/timeboost-round.ts",
            "coordinator/src/signals/actions/bid-timeboost-round.ts",
            "engine/src/lib.rs",
        ),
        proof_refs=(
            "coordinator/src/submission/lane-router.test.ts",
            "coordinator/src/strategies/timeboost-economics.test.ts",
        ),
        stages=(
            _stage(
                1,
                "Consume feed/timing",
                ("engine/src/lib.rs", "coordinator/src/signals/detectors/timeboost-round.ts"),
                "Feed and round state are typed inputs.",
            ),
            _stage(
                2,
                "Choose route",
                ("coordinator/src/submission/lane-router.ts",),
                "LaneRouter makes route selection explicit.",
            ),
            _stage(
                3,
                "Bid when justified",
                ("coordinator/src/signals/actions/bid-timeboost-round.ts",),
                "Bid action is isolated from calldata builders.",
            ),
            _stage(
                4,
                "Verify lane routing",
                ("coordinator/src/submission/lane-router.test.ts",),
                "Routing behavior is tested.",
            ),
        ),
    ),
    JaredBotPoc(
        skill_name="jaredbot-mev-ostium-oracle-gap",
        skill_path=".agents/skills/jaredbot-mev-ostium-oracle-gap/SKILL.md",
        module="JB-11 Ostium Oracle Gap",
        status=PocStatus.NEEDS_WORKFLOW,
        capital_mode=CapitalMode.WORKFLOW_REQUIRED,
        strategy_surface="oracle-gap telemetry -> oracle-sandwich workflow surface",
        allowed_use="Observe Ostium/reference price divergence and build sourced execution evidence.",
        scope_note=(
            "Ostium oracle-gap signal needs atomically repayable execution before capital-moving calldata output."
        ),
        workflow_requirement="Add sourced exact simulation, same-calldata executor, and replay evidence.",
        required_signals=(
            "oracle freshness",
            "market calendar",
            "external reference price",
            "profit estimate",
            "dispatch window",
        ),
        safety_invariants=(
            "calendar window is explicit",
            "profit estimator precedes dispatch",
            "leg builder owns calldata construction",
        ),
        code_refs=(
            "coordinator/src/signals/detectors/ostium-oracle-gap.ts",
            "coordinator/src/strategies/oracle-sandwich/orchestrator.ts",
            "coordinator/src/strategies/oracle-sandwich/leg-builder.ts",
            "coordinator/src/signals/actions/dispatch-oracle-sandwich.ts",
            "contracts/src/executors/Executor.sol",
        ),
        proof_refs=(
            "coordinator/src/strategies/oracle-sandwich/orchestrator.test.ts",
            "coordinator/src/strategies/oracle-sandwich/leg-builder.test.ts",
            "coordinator/src/signals/actions/dispatch-oracle-sandwich.test.ts",
        ),
        stages=(
            _stage(
                1,
                "Detect oracle gap",
                ("coordinator/src/signals/detectors/ostium-oracle-gap.ts",),
                "Detector identifies stale/opening windows.",
            ),
            _stage(
                2,
                "Estimate profit",
                ("coordinator/src/strategies/oracle-sandwich/profit-estimator.ts",),
                "Profit estimator prices the executable window.",
            ),
            _stage(
                3,
                "Build legs",
                ("coordinator/src/strategies/oracle-sandwich/leg-builder.ts",),
                "Leg builder owns executable calldata.",
            ),
            _stage(
                4,
                "Dispatch action",
                ("coordinator/src/signals/actions/dispatch-oracle-sandwich.ts",),
                "Dispatch is routed through the signal action surface.",
            ),
            _stage(
                5,
                "Verify orchestration",
                ("coordinator/src/strategies/oracle-sandwich/orchestrator.test.ts",),
                "Orchestrator tests bind signal to dispatch.",
            ),
        ),
    ),
    JaredBotPoc(
        skill_name="jaredbot-mev-protection",
        skill_path=".agents/skills/jaredbot-mev-protection/SKILL.md",
        module="JB-09 MEV Protection",
        status=PocStatus.DEFENSIVE,
        capital_mode=CapitalMode.NO_TX,
        strategy_surface="slippage, deadline, private-route, and quote-age protection policy",
        allowed_use="Reject unsafe quotes and protected-swap paths before submission.",
        scope_note="Direct AMM and aggregator routes carry amountOutMin/deadline protection in their workflow.",
        workflow_requirement=(
            "Protection POC is a pre-dispatch filter; accepted quotes still need a strategy submitter."
        ),
        required_signals=(
            "amountOutMin",
            "deadline",
            "quote age",
            "route impact",
            "private-required flag",
        ),
        safety_invariants=(
            "protected swaps require floors",
            "stale quotes are filtered",
            "large/user-facing swaps prefer intent or private paths",
        ),
        code_refs=(
            "coordinator/src/strategies/mev-protection.ts",
            "coordinator/src/strategies/route-comparator/mev-protection.ts",
            "coordinator/src/quotes/execution-path.ts",
        ),
        proof_refs=("coordinator/src/strategies/route-comparator/route-comparator.test.ts",),
        stages=(
            _stage(
                1,
                "Inspect quote",
                ("coordinator/src/strategies/mev-protection.ts",),
                "Policy receives quote protection inputs.",
            ),
            _stage(
                2,
                "Apply route-comparator guard",
                ("coordinator/src/strategies/route-comparator/mev-protection.ts",),
                "Route comparator filters unsafe exposure.",
            ),
            _stage(
                3,
                "Preserve amountOutMin",
                ("coordinator/src/quotes/execution-path.ts",),
                "Quote-to-executor plan preserves slippage floor.",
            ),
            _stage(
                4,
                "Verify protected comparison",
                ("coordinator/src/strategies/route-comparator/route-comparator.test.ts",),
                "Route comparator tests cover protection path.",
            ),
        ),
    ),
)


_POCS_BY_SKILL = {poc.skill_name: poc for poc in JAREDBOT_POCS}


def poc_for_skill(skill_name: str) -> JaredBotPoc:
    """Return one JaredBot POC by skill name."""
    try:
        return _POCS_BY_SKILL[skill_name]
    except KeyError as exc:
        message = f"unknown JaredBot skill POC: {skill_name}"
        raise KeyError(message) from exc


def pocs_for_status(status: PocStatus) -> tuple[JaredBotPoc, ...]:
    """Return all POCs with the given status."""
    return tuple(poc for poc in JAREDBOT_POCS if poc.status is status)


def executable_pocs() -> tuple[JaredBotPoc, ...]:
    """Return all POCs that are allowed to emit transactions through existing paths."""
    return tuple(poc for poc in JAREDBOT_POCS if poc.can_emit_transaction)


def workflow_required_pocs() -> tuple[JaredBotPoc, ...]:
    """Return all POCs that need a dedicated workflow before live tx output."""
    return tuple(poc for poc in JAREDBOT_POCS if poc.needs_workflow)
