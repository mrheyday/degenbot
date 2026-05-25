"""Arbitrum MEV market-map POC from the May 2026 fee-density snapshot.

The snapshot is integer-only. Dollar quantities are whole USD, fee-density
values are basis points, and derivatives fee rates are unit-fraction PPM
(`1_000_000 == 100%`). No floating-point arithmetic is used.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class StrategyPocStatus(StrEnum):
    """Execution status for one market-derived strategy priority."""

    EXECUTABLE = "executable"
    INFRASTRUCTURE = "infrastructure"
    BUILD_READY = "build_ready"
    MONITOR_ONLY = "monitor_only"
    REQUIRES_INTEGRATION = "requires_integration"
    RESEARCH_ONLY = "research_only"
    UNINVESTIGATED = "uninvestigated"
    DEPRIORITIZED = "deprioritized"


@dataclass(frozen=True, slots=True)
class ProtocolFeeSnapshot:
    """One protocol row from the May 2026 Arbitrum fee-density table."""

    protocol: str
    tvl_usd: int | None
    fees_30d_usd: int | None
    fees_1d_usd: int | None
    revenue_1d_usd: int | None
    fee_density_bps: int | None
    deriv_vol_1d_usd: int | None
    oi_usd: int | None

    @property
    def annualized_fee_density_bps(self) -> int | None:
        """Compute annualised 30d fees / TVL in basis points."""
        tvl_usd = self.tvl_usd
        if tvl_usd is None or tvl_usd == 0 or self.fees_30d_usd is None:
            return None
        numerator = self.fees_30d_usd * 12 * 10_000
        return _div_round(numerator, tvl_usd)

    @property
    def daily_derivatives_fee_rate_ppm(self) -> int | None:
        """Compute one-day fees / derivatives volume as unit-fraction PPM."""
        deriv_vol_1d_usd = self.deriv_vol_1d_usd
        if deriv_vol_1d_usd is None or deriv_vol_1d_usd == 0 or self.fees_1d_usd is None:
            return None
        numerator = self.fees_1d_usd * 1_000_000
        return _div_round(numerator, deriv_vol_1d_usd)


@dataclass(frozen=True, slots=True)
class StrategyPriority:
    """One ranked MEV strategy priority derived from the market snapshot."""

    rank: int
    strategy_id: str
    label: str
    status: StrategyPocStatus
    source_protocols: tuple[str, ...]
    thesis: str
    immediate_action: str
    execution_gate: str
    code_refs: tuple[str, ...]
    proof_refs: tuple[str, ...]


def _div_round(numerator: int, denominator: int) -> int:
    """Round integer division to nearest integer."""
    return (numerator + denominator // 2) // denominator


FEE_DENSITY_SNAPSHOT: tuple[ProtocolFeeSnapshot, ...] = (
    ProtocolFeeSnapshot(
        "gmx", 193_160_000, 1_971_600, 48_700, 18_000, 1_220, 57_500_000, 88_800_000
    ),
    ProtocolFeeSnapshot(
        "Ostium", 48_300_000, 2_419_400, 31_200, 5_600, 6_010, 31_300_000, 98_500_000
    ),
    ProtocolFeeSnapshot("aave", 468_960_000, 7_647_100, 29_300, 3_600, 1_960, None, None),
    ProtocolFeeSnapshot("fluid", 132_280_000, 505_200, 19_800, 2_500, 460, None, None),
    ProtocolFeeSnapshot("morpho", 55_510_000, 167_100, 4_700, 0, 360, None, None),
    ProtocolFeeSnapshot("Gains Network", 9_700_000, 339_300, 4_300, 3_300, 4_200, 7_700_000, None),
    ProtocolFeeSnapshot("Boros", 10_470_000, 58_600, 2_500, 2_400, 670, 86_700_000, 144_500_000),
    # Variational is intentionally absent from DefiLlama fee rows in the
    # supplied snapshot, but has the largest OI signal in the write-up.
    ProtocolFeeSnapshot("Variational", None, None, None, None, None, None, 751_900_000),
)


STRATEGY_PRIORITIES: tuple[StrategyPriority, ...] = (
    StrategyPriority(
        rank=1,
        strategy_id="L-2",
        label="Morpho Blue atomic liquidation",
        status=StrategyPocStatus.BUILD_READY,
        source_protocols=("morpho",),
        thesis=(
            "Morpho Blue on Arbitrum has a live singleton, 0% flash-loan surface, and a "
            "native liquidation callback that can settle within one transaction."
        ),
        immediate_action=(
            "Build the Morpho position index and wire profitable candidates to the existing "
            "LiquidationExecutor or AtomicExecutor generic-call path."
        ),
        execution_gate=(
            "Reject unknown-oracle, hardcoded-oracle, bridge/restaking, bad-debt, and blacklisted "
            "markets; final state must be verified on-chain and fork-simulated."
        ),
        code_refs=(
            "contracts/src/executors/LiquidationExecutor.sol",
            "contracts/src/executors/AtomicExecutor.sol",
            "coordinator/src/ipc/types.ts",
        ),
        proof_refs=(
            "contracts/test/fork/LiquidationExecutor.morpho.fork.t.sol",
            "vendor/degenbot/tests/solver_driver/test_arbitrum_mev_market_map.py",
        ),
    ),
    StrategyPriority(
        rank=2,
        strategy_id="U-1",
        label="UniswapX DutchV3 filler",
        status=StrategyPocStatus.REQUIRES_INTEGRATION,
        source_protocols=("Uniswap",),
        thesis=(
            "Arbitrum DutchV3 orders are public immediately with block-based decay, but live fills "
            "are not admitted until the coordinator owns sourced reactor calldata simulation."
        ),
        immediate_action="Build the sourced reactor calldata simulation path before any fill broadcast.",
        execution_gate=(
            "Reactor address, chain id, order type, deadline, quote surplus, callback calldata, "
            "and same-calldata simulation must pass."
        ),
        code_refs=(
            "contracts/src/executors/Executor.sol",
            "contracts/src/interfaces/IReactorCallback.sol",
            "coordinator/src/strategies/filler-bid.ts",
        ),
        proof_refs=(
            "contracts/test/unit/ExecutorUniswapXFill.t.sol",
            "coordinator/src/strategies/filler-bid.test.ts",
        ),
    ),
    StrategyPriority(
        rank=3,
        strategy_id="A-1",
        label="Event-driven cyclic DEX arb",
        status=StrategyPocStatus.MONITOR_ONLY,
        source_protocols=("Uniswap", "Camelot", "fluid"),
        thesis=(
            "Uniswap V3, Camelot V3, and Fluid expose event-driven price gaps, but equilibrium "
            "spreads are below break-even; execution must be triggered by live gap events only."
        ),
        immediate_action=(
            "Deploy WETH/USDC and WBTC/USDC monitors, then fork-simulate only gaps above integer ppm thresholds."
        ),
        execution_gate=(
            "No fee-table arb; require live price gap above break-even, dynamic Camelot fee refresh, "
            "fixed-size calldata, and Balancer repay plus minProfit in simulation."
        ),
        code_refs=(
            "contracts/src/executors/AtomicExecutor.sol",
            "coordinator/src/integration/native-arb-e2e.test.ts",
            "vendor/degenbot/src/degenbot/execution_adapters/uniswap_addresses.py",
        ),
        proof_refs=(
            "contracts/test/unit/AtomicExecutor.t.sol",
            "vendor/degenbot/tests/solver_driver/test_arbitrum_mev_market_map.py",
        ),
    ),
    StrategyPriority(
        rank=4,
        strategy_id="V-1",
        label="Variational OLP flow signal arb",
        status=StrategyPocStatus.BUILD_READY,
        source_protocols=("Variational",),
        thesis=(
            "Variational is not externally liquidatable, but public OLP-to-pool funding events expose "
            "large permissioned flow that can be used as a signal for external venue positioning."
        ),
        immediate_action=(
            "Build an OLPToPoolTransfer monitor, correlate PoolCreated flow, infer direction off-chain, "
            "and route only fork-simulated opportunities through the native arb path."
        ),
        execution_gate=(
            "No liquidation calls; require event-size threshold, direction confidence, external venue depth, "
            "and flash repay plus minProfit simulation before submission."
        ),
        code_refs=(
            "coordinator/src/strategies/native-arb.ts",
            "contracts/src/executors/AtomicExecutor.sol",
            "docs/research/2026-05-17-arbitrum-atomic-flash-mev-corrections.md",
        ),
        proof_refs=(
            "coordinator/src/integration/native-arb-e2e.test.ts",
            "vendor/degenbot/tests/solver_driver/test_arbitrum_mev_market_map.py",
        ),
    ),
    StrategyPriority(
        rank=5,
        strategy_id="L-1",
        label="Aave V3 Atlas/SVR liquidation",
        status=StrategyPocStatus.REQUIRES_INTEGRATION,
        source_protocols=("aave",),
        thesis=(
            "Aave Arbitrum liquidation OEV is now mostly routed through Chainlink SVR/Atlas; "
            "public/Kairos liquidations are displaced for covered assets."
        ),
        immediate_action="Add Atlas solver support before treating covered-asset Aave liquidations as executable.",
        execution_gate=(
            "Bonded Atlas account, atlasSolverCall implementation, SVR bid endpoint, residual-profit "
            "model, and covered-asset detection must pass."
        ),
        code_refs=(
            "coordinator/src/strategies/liquidation/monitor.ts",
            "coordinator/src/strategies/liquidation/simulator.ts",
            "coordinator/src/strategies/liquidation/executor.ts",
            "contracts/src/executors/LiquidationExecutor.sol",
        ),
        proof_refs=(
            "coordinator/src/strategies/liquidation/index.test.ts",
            "coordinator/src/strategies/liquidation/executor.test.ts",
        ),
    ),
    StrategyPriority(
        rank=6,
        strategy_id="J-1",
        label="JIT liquidity research lane",
        status=StrategyPocStatus.RESEARCH_ONLY,
        source_protocols=("Uniswap",),
        thesis=(
            "External-user JIT on Arbitrum requires victim visibility and ordered mint/swap/burn; "
            "Timeboost priority is not a substitute for seeing hidden pending user flow."
        ),
        immediate_action="Keep disabled except for solver-owned/private orderflow liquidity optimization research.",
        execution_gate=(
            "Ordering proof, controlled orderflow, active tick liquidity, and fork-simulated profit are mandatory."
        ),
        code_refs=(
            ".agents/skills/jaredbot-mev-jit-v4/SKILL.md",
            "coordinator/src/strategies/v4-hooks.ts",
            "vendor/degenbot/src/degenbot/execution_adapters/uniswap_addresses.py",
        ),
        proof_refs=("vendor/degenbot/tests/solver_driver/test_arbitrum_mev_market_map.py",),
    ),
    StrategyPriority(
        rank=7,
        strategy_id="B-1",
        label="Boros spread/settlement decode",
        status=StrategyPocStatus.UNINVESTIGATED,
        source_protocols=("Boros",),
        thesis=(
            "$144.5M OI and $86.7M/day derivatives volume with near-zero effective fee rate still "
            "require event decode before any execution claim."
        ),
        immediate_action="Decode Boros settlement events and compare execution price against spot references.",
        execution_gate="No Boros adapter, oracle model, or settlement simulator exists yet; ranking only.",
        code_refs=("vendor/degenbot/tests/solver_driver/test_jaredbot_onchain_intel.py",),
        proof_refs=("vendor/degenbot/tests/solver_driver/test_arbitrum_mev_market_map.py",),
    ),
    StrategyPriority(
        rank=8,
        strategy_id="T-1",
        label="Timeboost/Kairos execution rail",
        status=StrategyPocStatus.INFRASTRUCTURE,
        source_protocols=("Timeboost", "Kairos"),
        thesis=(
            "Express-lane access is best treated as a per-event execution rail for liquidations, "
            "oracle gaps, and high-EV settlement strategies."
        ),
        immediate_action="Keep Timeboost/Kairos as route selection infrastructure, not standalone alpha.",
        execution_gate="Lane selection must be EV-gated against bid/fee cost and fallback explicitly.",
        code_refs=(
            "coordinator/src/submission/lane-router.ts",
            "coordinator/src/timeboost/timing-model.ts",
            "coordinator/src/signals/detectors/timeboost-round.ts",
        ),
        proof_refs=(
            "coordinator/src/submission/lane-router.test.ts",
            "coordinator/src/timeboost/timing-model.test.ts",
        ),
    ),
    StrategyPriority(
        rank=98,
        strategy_id="S-1",
        label="Variational settlement MEV",
        status=StrategyPocStatus.DEPRIORITIZED,
        source_protocols=("Variational",),
        thesis=(
            "Local recon invalidated the original S-1 framing: the MEV-rich contract was Vertex, "
            "while Variational itself appears to be private bilateral settlement without a public bounty."
        ),
        immediate_action="Do not build S-1 as framed; reopen only with new verified permissionless settlement hooks.",
        execution_gate="Requires a verified Variational event/call surface with externally capturable value.",
        code_refs=("docs/research/2026-05-17-variational-s1-recon.md",),
        proof_refs=("vendor/degenbot/tests/solver_driver/test_arbitrum_mev_market_map.py",),
    ),
    StrategyPriority(
        rank=99,
        strategy_id="K-1",
        label="GMX keeper / Uniswap cyclic arb",
        status=StrategyPocStatus.DEPRIORITIZED,
        source_protocols=("gmx", "Uniswap"),
        thesis="GMX keeper economics and Uniswap cyclic arb are lower EV than the identified settlement/credit lanes.",
        immediate_action=(
            "Do not allocate implementation priority before Morpho, UniswapX, cyclic arb, Atlas, or Boros work."
        ),
        execution_gate="Requires fresh evidence that expected EV exceeds higher-ranked lanes.",
        code_refs=("vendor/degenbot/src/degenbot/strategies_solver/arbitrum_mev_market_map.py",),
        proof_refs=("vendor/degenbot/tests/solver_driver/test_arbitrum_mev_market_map.py",),
    ),
)


_SNAPSHOT_BY_PROTOCOL = {row.protocol.lower(): row for row in FEE_DENSITY_SNAPSHOT}
_PRIORITY_BY_ID = {priority.strategy_id: priority for priority in STRATEGY_PRIORITIES}


def protocol_snapshot(protocol: str) -> ProtocolFeeSnapshot:
    """Return one protocol row by case-insensitive name."""
    try:
        return _SNAPSHOT_BY_PROTOCOL[protocol.lower()]
    except KeyError as exc:
        msg = f"unknown protocol in Arbitrum MEV snapshot: {protocol}"
        raise KeyError(msg) from exc


def strategy_priority(strategy_id: str) -> StrategyPriority:
    """Return one ranked strategy priority."""
    try:
        return _PRIORITY_BY_ID[strategy_id]
    except KeyError as exc:
        msg = f"unknown Arbitrum strategy priority: {strategy_id}"
        raise KeyError(msg) from exc


def ranked_strategy_priorities(
    *,
    include_deprioritized: bool = False,
) -> tuple[StrategyPriority, ...]:
    """Return priorities sorted by rank."""
    priorities = (
        STRATEGY_PRIORITIES
        if include_deprioritized
        else tuple(
            p for p in STRATEGY_PRIORITIES if p.status is not StrategyPocStatus.DEPRIORITIZED
        )
    )
    return tuple(sorted(priorities, key=lambda p: p.rank))


def top_fee_density_protocols() -> tuple[ProtocolFeeSnapshot, ...]:
    """Return protocols with calculable fee-density sorted high-to-low."""
    rows = [row for row in FEE_DENSITY_SNAPSHOT if row.annualized_fee_density_bps is not None]
    return tuple(sorted(rows, key=lambda row: row.annualized_fee_density_bps or 0, reverse=True))


def highest_open_interest_protocol() -> ProtocolFeeSnapshot:
    """Return the protocol with the largest open-interest signal."""
    rows = [row for row in FEE_DENSITY_SNAPSHOT if row.oi_usd is not None]
    return max(rows, key=lambda row: row.oi_usd or 0)


def snapshot_density_matches_table(
    row: ProtocolFeeSnapshot, *, abs_tolerance_bps: int = 15
) -> bool:
    """True when recomputed annualised density matches supplied table value."""
    if row.fee_density_bps is None:
        return row.annualized_fee_density_bps is None
    computed = row.annualized_fee_density_bps
    return computed is not None and abs(computed - row.fee_density_bps) <= abs_tolerance_bps
