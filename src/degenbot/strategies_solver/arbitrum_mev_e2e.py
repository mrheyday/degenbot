"""End-to-end Arbitrum MEV master-strategy plan.

All economic values in this module are integer cents or basis points. No
floating-point arithmetic is used in the EV path. The goal is deterministic
strategy gating: a high-EV thesis becomes either an executable existing
workflow, a recon-only item, or a fail-closed/deprioritized route.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from degenbot.strategies_solver.arbitrum_mev_market_map import (
    StrategyPocStatus,
    StrategyPriority,
    ranked_strategy_priorities,
    strategy_priority,
)
from degenbot.strategies_solver.execution_workflows import WorkflowStatus, workflow_for_id

EXPECTED_KNOWN_VECTOR_BASE_USD_CENTS = 181_111_635
MAX_TIMEBOOST_ON_DEMAND_ANNUAL_COST_USD_CENTS = 1_000_000


class E2EAction(StrEnum):
    """Action class selected by the master strategy plan."""

    BUILD_NOW = "build_now"
    EXECUTE_NOW = "execute_now"
    MONITOR_AND_EXECUTE = "monitor_and_execute"
    CALIBRATE_AND_EXECUTE = "calibrate_and_execute"
    INTEGRATE = "integrate"
    RECON = "recon"
    EXECUTION_RAIL = "execution_rail"
    RESEARCH_ONLY = "research_only"
    DEPRIORITIZED = "deprioritized"


class E2ELane(StrEnum):
    """Submission lane selected by the plan."""

    KAIROS_ON_DEMAND = "kairos_on_demand"
    DIRECT_RPC = "direct_rpc"
    RECON_ONLY = "recon_only"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class StrategyEvEstimate:
    """Integer EV model for one strategy lane."""

    strategy_id: str
    annual_low_usd_cents: int
    annual_base_usd_cents: int
    annual_high_usd_cents: int
    events_per_month: int | None = None
    capture_bps: int | None = None
    net_per_event_usd_cents: int | None = None
    avg_flash_size_usd_cents: int | None = None
    annual_cost_usd_cents: int = 0
    notes: tuple[str, ...] = ()

    @property
    def captured_events_per_year(self) -> int | None:
        """Return captured event count per year when the integer model is exact."""
        if self.events_per_month is None:
            return None
        capture_bps = 10_000 if self.capture_bps is None else self.capture_bps
        numerator = self.events_per_month * 12 * capture_bps
        if numerator % 10_000 != 0:
            return None
        return numerator // 10_000

    @property
    def derived_annual_base_usd_cents(self) -> int | None:
        """Return event-derived annual base EV in cents when inputs are present."""
        captured = self.captured_events_per_year
        if captured is None or self.net_per_event_usd_cents is None:
            return None
        return captured * self.net_per_event_usd_cents - self.annual_cost_usd_cents


@dataclass(frozen=True, slots=True)
class StrategyE2ERoute:
    """E2E route from market thesis to code-backed action."""

    priority: StrategyPriority
    action: E2EAction
    lane: E2ELane
    workflow_id: str | None
    dispatchable: bool
    ev: StrategyEvEstimate
    required_inputs: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    next_steps: tuple[str, ...]

    @property
    def strategy_id(self) -> str:
        """Return the market-map strategy id."""
        return self.priority.strategy_id

    @property
    def workflow_status(self) -> WorkflowStatus | None:
        """Return the backing workflow status if the route has one."""
        if self.workflow_id is None:
            return None
        return workflow_for_id(self.workflow_id).status

    def to_evidence(self) -> dict[str, Any]:
        """Return JSON-serializable evidence for operators and tests."""
        return {
            "strategy_id": self.strategy_id,
            "label": self.priority.label,
            "action": self.action.value,
            "lane": self.lane.value,
            "workflow_id": self.workflow_id,
            "workflow_status": self.workflow_status.value if self.workflow_status else None,
            "dispatchable": self.dispatchable,
            "annual_ev_usd_cents": {
                "low": self.ev.annual_low_usd_cents,
                "base": self.ev.annual_base_usd_cents,
                "high": self.ev.annual_high_usd_cents,
            },
            "required_inputs": list(self.required_inputs),
            "stop_conditions": list(self.stop_conditions),
            "next_steps": list(self.next_steps),
            "code_refs": list(self.priority.code_refs),
            "proof_refs": list(self.priority.proof_refs),
        }


@dataclass(frozen=True, slots=True)
class ArbitrumMevMasterPlan:
    """Deterministic E2E plan for the May 17 2026 Arbitrum strategy set."""

    snapshot_date: str
    routes: tuple[StrategyE2ERoute, ...]
    timeboost_cost_per_event_usd_cents: int
    timeboost_annual_cost_usd_cents: int
    kelp_scale_single_event_usd_cents: int
    total_low_usd_cents: int
    total_base_usd_cents: int
    total_high_usd_cents: int
    known_vectors_base_usd_cents: int
    conditional_variational_low_usd_cents: int
    conditional_variational_high_usd_cents: int

    def route_for(self, strategy_id: str) -> StrategyE2ERoute:
        """Return the E2E route for one strategy id."""
        for route in self.routes:
            if route.strategy_id == strategy_id:
                return route
        msg = f"unknown E2E strategy route: {strategy_id}"
        raise KeyError(msg)

    def execution_queue(self) -> tuple[StrategyE2ERoute, ...]:
        """Return routes that may dispatch through existing workflows."""
        return tuple(route for route in self.routes if route.dispatchable)

    def recon_queue(self) -> tuple[StrategyE2ERoute, ...]:
        """Return routes that must decode/measure before any dispatch."""
        return tuple(route for route in self.routes if route.action is E2EAction.RECON)

    def fail_closed_queue(self) -> tuple[StrategyE2ERoute, ...]:
        """Return non-dispatch routes, including recon and deprioritized lanes."""
        return tuple(route for route in self.routes if not route.dispatchable)

    def to_evidence(self) -> dict[str, Any]:
        """Return JSON-serializable plan evidence."""
        return {
            "snapshot_date": self.snapshot_date,
            "timeboost": {
                "cost_per_event_usd_cents": self.timeboost_cost_per_event_usd_cents,
                "annual_cost_usd_cents": self.timeboost_annual_cost_usd_cents,
                "policy": "on-demand only",
            },
            "kelp_scale_single_event_usd_cents": self.kelp_scale_single_event_usd_cents,
            "totals": {
                "known_vectors_base_usd_cents": self.known_vectors_base_usd_cents,
                "conditional_variational_low_usd_cents": self.conditional_variational_low_usd_cents,
                "conditional_variational_high_usd_cents": self.conditional_variational_high_usd_cents,
                "low_usd_cents": self.total_low_usd_cents,
                "base_usd_cents": self.total_base_usd_cents,
                "high_usd_cents": self.total_high_usd_cents,
            },
            "execution_queue": [route.strategy_id for route in self.execution_queue()],
            "recon_queue": [route.strategy_id for route in self.recon_queue()],
            "routes": [route.to_evidence() for route in self.routes],
        }


TIMEBOOST_COST_PER_EVENT_USD_CENTS = 235
TIMEBOOST_ANNUAL_COST_USD_CENTS = 560_000
KELP_SCALE_SINGLE_EVENT_USD_CENTS = 605_000_000

EV_ESTIMATES: tuple[StrategyEvEstimate, ...] = (
    StrategyEvEstimate(
        strategy_id="L-2",
        annual_low_usd_cents=0,
        annual_base_usd_cents=0,
        annual_high_usd_cents=0,
        net_per_event_usd_cents=21_422,
        notes=(
            "Morpho annual EV is intentionally unpinned until the borrower index is live.",
            "Representative event net uses the $214.22 @ $5K 86% LLTV user-supplied model.",
        ),
    ),
    StrategyEvEstimate(
        strategy_id="U-1",
        annual_low_usd_cents=14_016_000,
        annual_base_usd_cents=112_146_250,
        annual_high_usd_cents=210_276_500,
        net_per_event_usd_cents=7_500,
        notes=(
            "Low/high annual bounds are $384/day and $5,761/day from the supplied DutchV3 report.",
            "Base uses the integer midpoint until live fill capture data exists.",
        ),
    ),
    StrategyEvEstimate(
        strategy_id="A-1",
        annual_low_usd_cents=0,
        annual_base_usd_cents=0,
        annual_high_usd_cents=0,
        notes=(
            "Cyclic arb is below break-even at rest; annual EV is not modeled until event-gap telemetry exists.",
            "Only execute when live gaps exceed integer ppm thresholds and fork simulation passes.",
        ),
    ),
    StrategyEvEstimate(
        strategy_id="V-1",
        annual_low_usd_cents=2_447_781,
        annual_base_usd_cents=9_791_125,
        annual_high_usd_cents=19_582_250,
        net_per_event_usd_cents=5_365,
        notes=(
            "DefiLlama shared Variational decode models five qualifying OLP flow events per day at $53.65 net.",
            "Route stays non-dispatchable until the OLPToPoolTransfer monitor and direction inference are implemented.",
        ),
    ),
    StrategyEvEstimate(
        strategy_id="L-1",
        annual_low_usd_cents=22_123_800,
        annual_base_usd_cents=59_734_260,
        annual_high_usd_cents=132_742_800,
        events_per_month=75,
        capture_bps=6_000,
        net_per_event_usd_cents=409_700,
        notes=(
            "Post-SVR base EV applies a 7300 bps recapture haircut to the prior $2,212,380/year model.",
            "Pure public/Kairos Aave liquidations are no-go for SVR-covered assets.",
        ),
    ),
    StrategyEvEstimate(
        strategy_id="J-1",
        annual_low_usd_cents=0,
        annual_base_usd_cents=0,
        annual_high_usd_cents=0,
        notes=(
            "JIT remains research-only without controlled/private orderflow and ordering proof.",
        ),
    ),
    StrategyEvEstimate(
        strategy_id="B-1",
        annual_low_usd_cents=0,
        annual_base_usd_cents=0,
        annual_high_usd_cents=0,
        notes=("Boros requires settlement-event decode before any EV can be trusted.",),
    ),
    StrategyEvEstimate(
        strategy_id="T-1",
        annual_low_usd_cents=-TIMEBOOST_ANNUAL_COST_USD_CENTS,
        annual_base_usd_cents=-TIMEBOOST_ANNUAL_COST_USD_CENTS,
        annual_high_usd_cents=-TIMEBOOST_ANNUAL_COST_USD_CENTS,
        annual_cost_usd_cents=TIMEBOOST_ANNUAL_COST_USD_CENTS,
        notes=("Timeboost/Kairos is an execution cost center, not standalone alpha.",),
    ),
    StrategyEvEstimate(
        strategy_id="S-1",
        annual_low_usd_cents=0,
        annual_base_usd_cents=0,
        annual_high_usd_cents=0,
        notes=("Variational S-1 is dropped as framed by local contract recon.",),
    ),
    StrategyEvEstimate(
        strategy_id="K-1",
        annual_low_usd_cents=0,
        annual_base_usd_cents=0,
        annual_high_usd_cents=0,
        notes=("GMX keeper and Uniswap cyclic arb are explicitly deprioritized.",),
    ),
)

_EV_BY_ID = {estimate.strategy_id: estimate for estimate in EV_ESTIMATES}


def ev_estimate(strategy_id: str) -> StrategyEvEstimate:
    """Return EV estimate by strategy id."""
    try:
        return _EV_BY_ID[strategy_id]
    except KeyError as exc:
        msg = f"unknown EV estimate: {strategy_id}"
        raise KeyError(msg) from exc


def build_master_plan() -> ArbitrumMevMasterPlan:
    """Build the deterministic E2E master-strategy plan."""
    routes = (
        StrategyE2ERoute(
            priority=strategy_priority("L-2"),
            action=E2EAction.BUILD_NOW,
            lane=E2ELane.KAIROS_ON_DEMAND,
            workflow_id="morpho_liquidation_decision",
            dispatchable=False,
            ev=ev_estimate("L-2"),
            required_inputs=(
                "Morpho borrower index",
                "market params verified on-chain",
                "oracle type allowlist",
                "collateral route simulation",
                "bad-debt and bridge collateral blacklist",
            ),
            stop_conditions=(
                "unknown oracle type",
                "hardcoded oracle or vault-share collateral",
                "blacklisted market id",
                "fork simulation fails repay plus minProfit",
            ),
            next_steps=(
                "wire Morpho position index from Borrow/Repay/SupplyCollateral/WithdrawCollateral events",
                "route candidates to LiquidationExecutor.liquidateMorpho or AtomicExecutor generic calls",
                "keep GraphQL as discovery only; final execution state comes from on-chain reads",
            ),
        ),
        StrategyE2ERoute(
            priority=strategy_priority("U-1"),
            action=E2EAction.INTEGRATE,
            lane=E2ELane.RECON_ONLY,
            workflow_id="uniswapx_filler",
            dispatchable=False,
            ev=ev_estimate("U-1"),
            required_inputs=(
                "DutchV3 encoded order",
                "reactor equals Arbitrum DutchV3 reactor",
                "order is not expired",
                "route quote exceeds required outputs",
                "callbackData encodes expectedSelf and deadline",
                "sourced reactor calldata simulation path",
            ),
            stop_conditions=(
                "reactor mismatch",
                "quote surplus below minProfit plus risk buffer",
                "order deadline or decay window invalid",
                "unsupported token route",
                "same-calldata reactor simulation missing",
            ),
            next_steps=(
                "wire sourced reactor calldata simulation before Executor.executeUniswapXFill",
                "poll UniswapX open Dutch_V3 orders on chainId 42161",
                "simulate surplus at candidate block offsets before submit",
            ),
        ),
        StrategyE2ERoute(
            priority=strategy_priority("A-1"),
            action=E2EAction.INTEGRATE,
            lane=E2ELane.RECON_ONLY,
            workflow_id="native_arb",
            dispatchable=False,
            ev=ev_estimate("A-1"),
            required_inputs=(
                "live Uniswap/Camelot/Fluid pool state",
                "dynamic Camelot fee",
                "gap above threshold ppm",
                "fixed-size executable calldata",
                "SourcedPriceSpreadArbSignal wrapper",
                "fork simulation covers Balancer repay plus minProfit",
            ),
            stop_conditions=(
                "gap below break-even",
                "Fluid WBTC/USDC direct route requested",
                "intermediate amount cannot be fixed safely",
                "simulation cannot repay flash principal",
                "direct native_arb dispatch requested",
            ),
            next_steps=(
                "route WETH/USDC and WBTC/USDC gaps through SourcedPriceSpreadArbSignal only",
                "monitor WBTC/USDC Uniswap-Camelot only",
                "reject fee-table-only opportunities",
            ),
        ),
        StrategyE2ERoute(
            priority=strategy_priority("V-1"),
            action=E2EAction.BUILD_NOW,
            lane=E2ELane.KAIROS_ON_DEMAND,
            workflow_id="native_arb",
            dispatchable=False,
            ev=ev_estimate("V-1"),
            required_inputs=(
                "OLPToPoolTransfer log subscription",
                "PoolCreated correlation by poolUuid",
                "USDC size threshold",
                "direction inference confidence score",
                "external venue depth and flash simulation",
            ),
            stop_conditions=(
                "treating Variational as externally liquidatable",
                "direction cannot be inferred with policy confidence",
                "external venue impact exceeds modeled capture",
                "fork simulation cannot repay flash principal plus minProfit",
            ),
            next_steps=(
                "subscribe to Oracle/Settlement Router OLPToPoolTransfer events",
                "filter amount above 50_000 USDC raw threshold",
                "feed confirmed signals into native_arb only after direction inference passes",
            ),
        ),
        StrategyE2ERoute(
            priority=strategy_priority("L-1"),
            action=E2EAction.INTEGRATE,
            lane=E2ELane.RECON_ONLY,
            workflow_id="liquidation",
            dispatchable=False,
            ev=ev_estimate("L-1"),
            required_inputs=(
                "Atlas bonded searcher account",
                "atlasSolverCall contract",
                "SVR covered-asset map",
                "bid endpoint subscription",
                "residual EV after SVR bid",
            ),
            stop_conditions=(
                "covered Aave asset without Atlas route",
                "SVR residual profit below bid/gas/risk cost",
                "fallback/non-SVR event not proven",
            ),
            next_steps=(
                "bond Atlas account before covered-asset Aave execution",
                "implement atlasSolverCall wrapper around liquidation path",
                "keep legacy Kairos path only for non-SVR or fallback events",
            ),
        ),
        StrategyE2ERoute(
            priority=strategy_priority("J-1"),
            action=E2EAction.RESEARCH_ONLY,
            lane=E2ELane.RECON_ONLY,
            workflow_id="jit_liquidity",
            dispatchable=False,
            ev=ev_estimate("J-1"),
            required_inputs=(
                "controlled or private orderflow",
                "ordering proof",
                "active tick liquidity",
                "fork simulation with IL and inventory unwind",
            ),
            stop_conditions=(
                "depends on normal Arbitrum pending tx visibility",
                "Timeboost priority treated as victim visibility",
                "V4 hook not fully classified",
            ),
            next_steps=("keep disabled except for solver-owned liquidity optimization research",),
        ),
        StrategyE2ERoute(
            priority=strategy_priority("B-1"),
            action=E2EAction.RECON,
            lane=E2ELane.RECON_ONLY,
            workflow_id=None,
            dispatchable=False,
            ev=ev_estimate("B-1"),
            required_inputs=(
                "Boros settlement event ABI",
                "oracle timestamp source",
                "30d spread sample",
            ),
            stop_conditions=(
                "spread is LP-absorbed",
                "no delayed settlement price",
                "capturable spread below cost",
            ),
            next_steps=(
                "decode Boros settlement and PositionFilled events",
                "measure execution/oracle spread",
            ),
        ),
        StrategyE2ERoute(
            priority=strategy_priority("T-1"),
            action=E2EAction.EXECUTION_RAIL,
            lane=E2ELane.KAIROS_ON_DEMAND,
            workflow_id=None,
            dispatchable=False,
            ev=ev_estimate("T-1"),
            required_inputs=("event EV exceeds $33 break-even", "Kairos endpoint configured"),
            stop_conditions=("always-on bidding requested", "event EV below on-demand fee"),
            next_steps=(
                "use as per-event rail for L-2, U-1, A-1, V-1, L-1 Atlas, and confirmed B-1 only",
            ),
        ),
        StrategyE2ERoute(
            priority=strategy_priority("S-1"),
            action=E2EAction.DEPRIORITIZED,
            lane=E2ELane.NONE,
            workflow_id=None,
            dispatchable=False,
            ev=ev_estimate("S-1"),
            required_inputs=("new verified permissionless Variational hook",),
            stop_conditions=("current recon remains true",),
            next_steps=("do not build Variational S-1 as framed",),
        ),
        StrategyE2ERoute(
            priority=strategy_priority("K-1"),
            action=E2EAction.DEPRIORITIZED,
            lane=E2ELane.NONE,
            workflow_id=None,
            dispatchable=False,
            ev=ev_estimate("K-1"),
            required_inputs=("fresh evidence that EV exceeds L-1/P-1/S-1/B-1",),
            stop_conditions=("current EV remains compressed",),
            next_steps=("do not allocate build capacity before higher-ranked lanes",),
        ),
    )

    known_base = (
        ev_estimate("U-1").annual_base_usd_cents
        + ev_estimate("V-1").annual_base_usd_cents
        + ev_estimate("L-1").annual_base_usd_cents
        + ev_estimate("T-1").annual_base_usd_cents
    )
    total_low = sum(route.ev.annual_low_usd_cents for route in routes)
    total_base = sum(route.ev.annual_base_usd_cents for route in routes)
    total_high = sum(route.ev.annual_high_usd_cents for route in routes)

    return ArbitrumMevMasterPlan(
        snapshot_date="2026-05-17",
        routes=routes,
        timeboost_cost_per_event_usd_cents=TIMEBOOST_COST_PER_EVENT_USD_CENTS,
        timeboost_annual_cost_usd_cents=TIMEBOOST_ANNUAL_COST_USD_CENTS,
        kelp_scale_single_event_usd_cents=KELP_SCALE_SINGLE_EVENT_USD_CENTS,
        total_low_usd_cents=total_low,
        total_base_usd_cents=total_base,
        total_high_usd_cents=total_high,
        known_vectors_base_usd_cents=known_base,
        conditional_variational_low_usd_cents=0,
        conditional_variational_high_usd_cents=0,
    )


def dispatchable_strategy_ids() -> tuple[str, ...]:
    """Return strategy ids that can move to existing execution workflows."""
    return tuple(route.strategy_id for route in build_master_plan().execution_queue())


def recon_strategy_ids() -> tuple[str, ...]:
    """Return strategy ids that are high-EV but fail closed into recon."""
    return tuple(route.strategy_id for route in build_master_plan().recon_queue())


def validate_master_plan(plan: ArbitrumMevMasterPlan | None = None) -> tuple[str, ...]:
    """Return invariant violations for the E2E plan."""
    plan = plan or build_master_plan()
    violations: list[str] = []

    ranked_ids = tuple(
        priority.strategy_id for priority in ranked_strategy_priorities(include_deprioritized=True)
    )
    route_ids = tuple(route.strategy_id for route in plan.routes)
    if route_ids != ranked_ids:
        violations.append(
            f"route order {route_ids!r} does not match market-map order {ranked_ids!r}"
        )

    for route in plan.routes:
        if route.dispatchable:
            if route.workflow_id is None:
                violations.append(f"{route.strategy_id} dispatchable without workflow")
                continue
            workflow = workflow_for_id(route.workflow_id)
            if workflow.status is not WorkflowStatus.EXECUTABLE:
                violations.append(
                    f"{route.strategy_id} dispatches through non-executable workflow {route.workflow_id}"
                )
            if route.priority.status not in {
                StrategyPocStatus.EXECUTABLE,
                StrategyPocStatus.MONITOR_ONLY,
            }:
                violations.append(
                    f"{route.strategy_id} dispatchable but market status is {route.priority.status}"
                )
        elif route.priority.status is StrategyPocStatus.EXECUTABLE:
            violations.append(
                f"{route.strategy_id} executable market status is not dispatchable in E2E plan"
            )

    if plan.known_vectors_base_usd_cents != EXPECTED_KNOWN_VECTOR_BASE_USD_CENTS:
        violations.append("known vector base EV drifted")
    if plan.total_base_usd_cents != EXPECTED_KNOWN_VECTOR_BASE_USD_CENTS:
        violations.append("total base EV drifted")
    if plan.timeboost_annual_cost_usd_cents > MAX_TIMEBOOST_ON_DEMAND_ANNUAL_COST_USD_CENTS:
        violations.append("timeboost on-demand cost unexpectedly exceeds budget")

    return tuple(violations)
