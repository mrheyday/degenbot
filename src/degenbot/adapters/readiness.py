"""Audit evidence backing adapter and lane readiness promotions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from degenbot.adapters.templates import AdapterCategory, ExecutionLane


class ReadinessStatus(StrEnum):
    """Operational readiness status for scoped adapter evidence."""

    APPROVED = "approved"
    APPROVED_WITH_SCOPE = "approved_with_scope"


@dataclass(frozen=True, slots=True)
class ReadinessEvidence:
    """One auditable readiness record for an adapter or execution lane."""

    evidence_id: str
    title: str
    status: ReadinessStatus
    scope: str
    adapters: tuple[tuple[AdapterCategory, str], ...] = ()
    lanes: tuple[ExecutionLane, ...] = ()
    contracts: tuple[str, ...] = ()
    coordinator_modules: tuple[str, ...] = ()
    solver_modules: tuple[str, ...] = ()
    tests: tuple[str, ...] = ()
    policy_gates: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

    @property
    def approved_for_execution(self) -> bool:
        """True when the evidence can support scoped executable routing."""
        return self.status in {ReadinessStatus.APPROVED, ReadinessStatus.APPROVED_WITH_SCOPE}


def adapter_key(category: AdapterCategory, venue: str) -> tuple[AdapterCategory, str]:
    """Return a category-scoped adapter key."""
    return (category, venue)


READINESS_EVIDENCE: tuple[ReadinessEvidence, ...] = (
    ReadinessEvidence(
        evidence_id="balancer-v2-flash-callback",
        title="Balancer V2 flash callback authentication",
        status=ReadinessStatus.APPROVED_WITH_SCOPE,
        scope=(
            "Selectable by the universal flash lane when the planner emits a Balancer V2 callback "
            "plan for LiquidationExecutor or MevSafe rather than a direct Executor flash callback."
        ),
        adapters=(adapter_key(AdapterCategory.FLASH, "BalancerV2Flash"),),
        lanes=(ExecutionLane.UNIVERSAL_FLASH_AGGREGATOR_ROUTER, ExecutionLane.LIQUIDATION_EXECUTOR),
        contracts=(
            "contracts/src/executors/LiquidationExecutor.sol",
            "contracts/src/auth/MevSafe.sol",
        ),
        coordinator_modules=(
            "coordinator/src/flash/source-router.ts",
            "coordinator/src/strategies/liquidation/index.ts",
        ),
        tests=(
            "contracts/test/unit/LiquidationExecutor.t.sol",
            "contracts/test/unit/LiquidationExecutor.delta.t.sol",
            "contracts/test/fork/LiquidationExecutor.fork.t.sol",
            "contracts/test/unit/MevSafe.t.sol",
        ),
        policy_gates=(
            "canonical Balancer V2 Vault caller",
            "single-asset flash array shape",
            "byte-for-byte plan hash equality",
            "post-flow repay and profit invariant",
        ),
    ),
    ReadinessEvidence(
        evidence_id="balancer-v3-transient-unlock",
        title="Balancer V3 transient unlock semantics",
        status=ReadinessStatus.APPROVED_WITH_SCOPE,
        scope=(
            "Selectable by the universal flash lane when the planner emits a MevSafe.flashCollateralizeV3 "
            "transient-unlock plan rather than a direct Executor flash callback."
        ),
        adapters=(adapter_key(AdapterCategory.FLASH, "BalancerV3Flash"),),
        lanes=(ExecutionLane.UNIVERSAL_FLASH_AGGREGATOR_ROUTER,),
        contracts=("contracts/src/auth/MevSafe.sol",),
        tests=("contracts/test/unit/MevSafe.t.sol",),
        policy_gates=(
            "canonical Balancer V3 Vault caller",
            "transient active lender slot",
            "transient plan hash equality",
            "settle credit covers owed principal",
        ),
    ),
    ReadinessEvidence(
        evidence_id="balancer-v3-swap-preencoded-routing",
        title="Balancer V3 swap routing via pre-encoded calldata",
        status=ReadinessStatus.APPROVED_WITH_SCOPE,
        scope=(
            "Executable as pre-encoded Balancer V3 Router, Batch Router, or Aggregator Router "
            "calldata after coordinator target validation; no on-chain Balancer math is introduced."
        ),
        adapters=(adapter_key(AdapterCategory.SWAP, "Balancer"),),
        lanes=(
            ExecutionLane.UNIVERSAL_SWAP_AGGREGATOR_ROUTER,
            ExecutionLane.UNIVERSAL_PATHFINDER_QUOTER_ROUTER,
        ),
        contracts=(
            "contracts/src/executors/Executor.sol",
            "contracts/src/interfaces/IExecutor.sol",
        ),
        coordinator_modules=(
            "coordinator/src/router/encode.ts",
            "coordinator/src/router/registry.ts",
        ),
        solver_modules=("driver.execution.balancer_v3_adapter",),
        tests=(
            "coordinator/src/router/encode.test.ts",
            "coordinator/src/types/executor.test.ts",
            "contracts/test/unit/PathFinder.t.sol",
        ),
        policy_gates=(
            "canonical Balancer router target",
            "pre-encoded calldata only",
            "sealed route hash before submit",
            "Executor received >= amountOutMin balance delta",
        ),
    ),
    ReadinessEvidence(
        evidence_id="intent-settlement-receiver-replay",
        title="Intent settlement receiver and replay protection",
        status=ReadinessStatus.APPROVED_WITH_SCOPE,
        scope=(
            "Intent lane may dispatch through Executor.matchInternal, UniswapX reactor callbacks, "
            "and CoW FlashLoanRouter walks when sender, flow-id, deadline, and chained-hash gates pass."
        ),
        adapters=(
            adapter_key(AdapterCategory.SWAP, "UniswapX"),
            adapter_key(AdapterCategory.FLASH, "CowFlashLoanRouter"),
        ),
        lanes=(ExecutionLane.INTENT_EXECUTOR,),
        contracts=("contracts/src/executors/Executor.sol",),
        coordinator_modules=(
            "coordinator/src/matching/encoder.ts",
            "coordinator/src/strategies/internal-match.ts",
            "coordinator/src/feeds/cow-orderbook.ts",
            "coordinator/src/feeds/uniswapx-orders.ts",
        ),
        tests=(
            "contracts/test/unit/ExecutorUniswapXFill.t.sol",
            "contracts/test/fork/UniswapXFill.fork.t.sol",
            "contracts/test/unit/ExecutorCoWFlashRouter.t.sol",
            "contracts/test/unit/ExecutorCoWFlashRouterStart.t.sol",
            "contracts/test/unit/Executor_TransferToSettlement.t.sol",
            "contracts/test/unit/Executor.t.sol",
            "contracts/test/fork/IntentSettlementReadiness.fork.t.sol",
            "coordinator/src/matching/encoder.test.ts",
            "coordinator/src/strategies/internal-match.test.ts",
        ),
        policy_gates=(
            "CoW FlashLoanRouter sender authentication",
            "UniswapX reactor transient sender gate",
            "settlement deadline",
            "flow-id correlation",
            "CoW chained-hash replay root",
        ),
    ),
    ReadinessEvidence(
        evidence_id="universal-liquidity-mutation-policy",
        title="Universal liquidity routing policy",
        status=ReadinessStatus.APPROVED_WITH_SCOPE,
        scope=(
            "Universal liquidity routing may rank liquidity and emit strategy-scoped LP mutation "
            "plans only when exposure caps, unwind invariants, and strategy allowlists are satisfied."
        ),
        adapters=(
            adapter_key(AdapterCategory.LIQUIDITY, "UniswapV3Liquidity"),
            adapter_key(AdapterCategory.LIQUIDITY, "UniswapV4Liquidity"),
            adapter_key(AdapterCategory.LIQUIDITY, "BalancerLiquidity"),
            adapter_key(AdapterCategory.LIQUIDITY, "CurveLiquidity"),
            adapter_key(AdapterCategory.LIQUIDITY, "MorphoLiquidity"),
            adapter_key(AdapterCategory.LIQUIDITY, "MetaMorphoVaults"),
            adapter_key(AdapterCategory.LIQUIDITY, "AaveLiquidity"),
        ),
        lanes=(ExecutionLane.UNIVERSAL_LIQUIDITY_AGGREGATOR_ROUTER,),
        coordinator_modules=(
            "coordinator/src/strategies/v4-hooks.ts",
            "coordinator/src/strategies/liquidation/monitor.ts",
        ),
        solver_modules=(
            "driver.execution.morpho_lp_adapter",
            "driver.execution.metamorpho_v1_adapter",
        ),
        tests=(
            "coordinator/src/strategies/v4-hooks.test.ts",
            "solver/driver/tests/test_adapter_registry.py",
        ),
        policy_gates=(
            "strategy-specific LP mutation allowlist",
            "per-token and per-pool exposure cap",
            "same-transaction unwind or explicit TTL close plan",
            "post-unwind inventory neutrality",
            "emergency revoke and withdraw path",
        ),
    ),
    ReadinessEvidence(
        evidence_id="jit-self-controlled-liquidity-lane",
        title="JIT executor scoped liquidity activation",
        status=ReadinessStatus.APPROVED_WITH_SCOPE,
        scope=(
            "JIT execution is enabled for self-controlled, solver-owned, and external-trigger flow "
            "when the mint/swap/burn/collect lifecycle is flash-funded, bounded by tick exposure, "
            "ordering-proofed when external, and unwound inside the planned transaction envelope."
        ),
        adapters=(
            adapter_key(AdapterCategory.LIQUIDITY, "UniswapV3Liquidity"),
            adapter_key(AdapterCategory.LIQUIDITY, "UniswapV4Liquidity"),
            adapter_key(AdapterCategory.SWAP, "UniswapV3"),
            adapter_key(AdapterCategory.SWAP, "UniswapV4"),
        ),
        lanes=(ExecutionLane.JIT_EXECUTOR,),
        contracts=("contracts/src/executors/Executor.sol",),
        coordinator_modules=(
            "coordinator/src/strategies/v4-hooks.ts",
            "coordinator/src/strategies/amm-economics.ts",
        ),
        solver_modules=("driver.execution.degenbot_ipc",),
        tests=(
            "coordinator/src/strategies/v4-hooks.test.ts",
            "solver/driver/tests/test_adapter_registry.py",
        ),
        policy_gates=(
            "self-controlled or solver-owned trigger source",
            "external trigger ordering proof when trigger source is not solver-owned",
            "flash-funded mint/swap/burn/collect envelope",
            "bounded tick exposure",
            "post-unwind inventory neutrality",
            "private or Timeboost submission",
        ),
    ),
    ReadinessEvidence(
        evidence_id="oracle-sandwich-execution-lane",
        title="S-5 oracle-update sandwich executor activation",
        status=ReadinessStatus.APPROVED_WITH_SCOPE,
        scope=(
            "Sandwich execution is enabled for offensive S-1/S-2/S-3/S-4 policy variants "
            "and the S-5 oracle-update lane when calldata is emitted as a flash-funded "
            "Executor.executeNativeArb transaction or solver/filler atomic callback."
        ),
        adapters=(
            adapter_key(AdapterCategory.SWAP, "UniswapV2"),
            adapter_key(AdapterCategory.SWAP, "UniswapV3"),
            adapter_key(AdapterCategory.SWAP, "Camelot"),
        ),
        lanes=(ExecutionLane.SANDWICH_EXECUTOR,),
        contracts=("contracts/src/executors/Executor.sol",),
        coordinator_modules=(
            "coordinator/src/strategies/sandwich/offensive-policy.ts",
            "coordinator/src/strategies/oracle-sandwich/orchestrator.ts",
            "coordinator/src/strategies/oracle-sandwich/leg-builder.ts",
            "coordinator/src/signals/actions/dispatch-oracle-sandwich.ts",
        ),
        solver_modules=("driver.execution.degenbot_ipc",),
        tests=(
            "coordinator/src/strategies/sandwich/offensive-policy.test.ts",
            "coordinator/src/strategies/oracle-sandwich/orchestrator.test.ts",
            "coordinator/src/strategies/oracle-sandwich/leg-builder.test.ts",
            "coordinator/src/signals/actions/dispatch-oracle-sandwich.test.ts",
            "solver/driver/tests/test_adapter_registry.py",
        ),
        policy_gates=(
            "offensive variant enable map defaults on",
            "flash-funded executeNativeArb envelope",
            "single-transaction round trip",
            "profit floor after flash premium",
            "private or Timeboost submission preference",
            "global pause kill switch",
        ),
    ),
)

_EVIDENCE_BY_ID = {evidence.evidence_id: evidence for evidence in READINESS_EVIDENCE}


def readiness_evidence_for_id(evidence_id: str) -> ReadinessEvidence:
    """Return one readiness evidence record by id."""
    try:
        return _EVIDENCE_BY_ID[evidence_id]
    except KeyError as exc:
        raise KeyError(f"unknown readiness evidence {evidence_id!r}") from exc


def evidence_for_adapter(category: AdapterCategory | str, venue: str) -> tuple[ReadinessEvidence, ...]:
    """Return readiness evidence records that mention an adapter."""
    key = adapter_key(AdapterCategory(category), venue)
    return tuple(evidence for evidence in READINESS_EVIDENCE if key in evidence.adapters)


def evidence_for_lane(lane: ExecutionLane | str) -> tuple[ReadinessEvidence, ...]:
    """Return readiness evidence records that mention an execution lane."""
    normalized = ExecutionLane(lane)
    return tuple(evidence for evidence in READINESS_EVIDENCE if normalized in evidence.lanes)
