"""Atomic flash-financed Arbitrum research lanes.

These records are intentionally non-dispatchable. They preserve the research
ordering and promotion gates from the Arbitrum atomic flash opportunity review
so strategy orchestration can reason about the lanes without treating them as
live capital-moving code.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AtomicFlashStatus(StrEnum):
    """Promotion state for one atomic flash research lane."""

    REQUIRES_DECODE = "requires_decode"
    QUICK_CHECK = "quick_check"


@dataclass(frozen=True, slots=True)
class AtomicFlashTarget:
    """Machine-readable atomic flash research target."""

    target_id: str
    rank: int
    protocol: str
    thesis: str
    flash_source: str
    execution_surface: str
    status: AtomicFlashStatus
    tvl_usd: int
    fees_30d_usd: int
    trend_30d_bps: int
    atomic_single_tx: bool
    dispatchable: bool
    required_checks: tuple[str, ...]
    workflow_requirements: tuple[str, ...]
    poc_steps: tuple[str, ...]
    code_refs: tuple[str, ...]
    proof_refs: tuple[str, ...]


_COMMON_CODE_REFS = (
    "vendor/degenbot/src/degenbot/strategy_signals/arbitrum_atomic_flash_research.py",
)
_COMMON_PROOF_REFS = ("vendor/degenbot/tests/solver_driver/test_arbitrum_atomic_flash_research.py",)


ATOMIC_FLASH_TARGETS: tuple[AtomicFlashTarget, ...] = (
    AtomicFlashTarget(
        target_id="E-1",
        rank=1,
        protocol="Euler v2",
        thesis=(
            "Euler v2 EVC can batch controller enablement, collateral enablement, "
            "liquidation, withdrawal, swap-back, and repayment."
        ),
        flash_source="Balancer V3 Vault.unlock external flash source",
        execution_surface="EVC.batch liquidate through controller vaults",
        status=AtomicFlashStatus.REQUIRES_DECODE,
        tvl_usd=0,
        fees_30d_usd=0,
        trend_30d_bps=0,
        atomic_single_tx=True,
        dispatchable=False,
        required_checks=(
            "resolve Arbitrum Euler v2 vault registry",
            "decode controller-vault liquidation discount formula",
            "verify oracle implementation and freshness per vault",
        ),
        workflow_requirements=(
            "fork test EVC.batch liquidation before any live route",
            "swap collateral back with amountOutMin >= principal + fees + minProfit",
            "fail closed on unknown vault, stale oracle, or missing sub-account authority",
        ),
        poc_steps=(
            "Vault.unlock(encoded Euler flash plan)",
            "EVC.batch enableController/enableCollateral/liquidate",
            "withdraw seized collateral and swap back to debt asset",
            "settle principal and assert raw-unit minProfit",
        ),
        code_refs=_COMMON_CODE_REFS,
        proof_refs=_COMMON_PROOF_REFS,
    ),
    AtomicFlashTarget(
        target_id="P-2",
        rank=2,
        protocol="Pendle",
        thesis=(
            "PT + YT = SY creates a hard identity arb when live PT/YT/SY prices "
            "diverge after router fees, market fees, and slippage."
        ),
        flash_source="Balancer V3 Vault.unlock external flash source",
        execution_surface="PendleRouter mint/redeem/swap PT/YT/SY paths",
        status=AtomicFlashStatus.REQUIRES_DECODE,
        tvl_usd=0,
        fees_30d_usd=0,
        trend_30d_bps=0,
        atomic_single_tx=True,
        dispatchable=False,
        required_checks=(
            "resolve top Arbitrum Pendle market addresses",
            "verify PT, YT, SY tokens and expiry state",
            "decode router selectors for mint, redeem, and swap paths",
        ),
        workflow_requirements=(
            "compute PT + YT = SY fair value in raw integer units",
            "swap back to flash token with principal + fees + minProfit floor",
            "reject post-expiry markets with changed PY semantics",
        ),
        poc_steps=(
            "Vault.unlock(encoded Pendle identity-arb plan)",
            "buy PT and YT or mint PT/YT from SY",
            "redeemPyToSy(receiver, market, netPyIn)",
            "settle flash principal and raw-unit profit",
        ),
        code_refs=_COMMON_CODE_REFS,
        proof_refs=_COMMON_PROOF_REFS,
    ),
    AtomicFlashTarget(
        target_id="D-1",
        rank=3,
        protocol="Dolomite",
        thesis=(
            "Dolomite generic liquidation and trader paths can close a liquidatable "
            "account and sell seized collateral in the same transaction."
        ),
        flash_source="Dolomite negative-balance flash accounting or Balancer V3 Vault.unlock",
        execution_surface="LiquidatorProxyV4WithGenericTrader liquidation path",
        status=AtomicFlashStatus.REQUIRES_DECODE,
        tvl_usd=0,
        fees_30d_usd=0,
        trend_30d_bps=0,
        atomic_single_tx=True,
        dispatchable=False,
        required_checks=(
            "resolve DolomiteMargin and LiquidatorProxyV4WithGenericTrader addresses",
            "decode market ids, collateral factors, oracles, and expiry spread",
            "verify GenericTrader adapter exact min-out compatibility",
        ),
        workflow_requirements=(
            "fork test liquidatable account solvency snapshot",
            "prove seized collateral sale repays principal + fees + minProfit",
            "fail closed if residual protocol debt or negative balance remains",
        ),
        poc_steps=(
            "enter Dolomite flash context or Vault.unlock wrapper",
            "LiquidatorProxyV4WithGenericTrader.liquidate(...)",
            "sell held asset through GenericTrader exact-min-out path",
            "repay negative balance and assert profit",
        ),
        code_refs=_COMMON_CODE_REFS,
        proof_refs=_COMMON_PROOF_REFS,
    ),
    AtomicFlashTarget(
        target_id="C-1",
        rank=4,
        protocol="Compound v3 / Silo v2",
        thesis=(
            "Compound v3 absorb plus buyCollateral and Silo liquidate paths are "
            "structurally atomic once a profitable account set is fork-proven."
        ),
        flash_source="Balancer V3 Vault.unlock external flash source",
        execution_surface="Comet.absorb / buyCollateral or Silo.liquidate",
        status=AtomicFlashStatus.QUICK_CHECK,
        tvl_usd=0,
        fees_30d_usd=0,
        trend_30d_bps=0,
        atomic_single_tx=True,
        dispatchable=False,
        required_checks=(
            "commit current liquidatable account set",
            "verify collateral-to-base swap-back route",
            "prove flash principal, fees, and profit repayment on fork",
        ),
        workflow_requirements=(
            "fork test Comet.absorb then buyCollateral in one transaction",
            "gate every route with raw-unit minProfit",
            "reject if no exact swap-back route exists",
        ),
        poc_steps=(
            "Vault.unlock(encoded Comet plan)",
            "Comet.absorb(address(this), accounts)",
            "Comet.buyCollateral(collateralAsset, minAmount, baseAmount, address(this))",
            "swap collateral to base and settle principal",
        ),
        code_refs=_COMMON_CODE_REFS,
        proof_refs=_COMMON_PROOF_REFS,
    ),
    AtomicFlashTarget(
        target_id="P-3",
        rank=5,
        protocol="Pendle / Uniswap v4",
        thesis=(
            "A stale Pendle limit order can be flash-filled and hedged when the "
            "signed price is stale against current fair value."
        ),
        flash_source="Balancer V3 Vault.unlock external flash source",
        execution_surface="Pendle limit-order fill plus Uniswap v4 hook-classified hedge",
        status=AtomicFlashStatus.QUICK_CHECK,
        tvl_usd=0,
        fees_30d_usd=0,
        trend_30d_bps=0,
        atomic_single_tx=True,
        dispatchable=False,
        required_checks=(
            "verify Pendle limit-order signature path",
            "classify hedge AMM and hook permissions",
            "prove stale-order edge after fees and lane cost",
        ),
        workflow_requirements=(
            "fork test fill and hedge before live dispatch",
            "reject any unclassified v4 hook",
            "settle flash principal with raw-unit minProfit",
        ),
        poc_steps=(
            "Vault.unlock(encoded limit-order plan)",
            "fill signed Pendle limit-order calldata",
            "classify v4 hook permissions before hedge",
            "hedge PT/YT/SY exposure and settle principal",
        ),
        code_refs=_COMMON_CODE_REFS,
        proof_refs=_COMMON_PROOF_REFS,
    ),
)

_TARGETS_BY_ID = {target.target_id: target for target in ATOMIC_FLASH_TARGETS}


def ranked_atomic_flash_targets() -> tuple[AtomicFlashTarget, ...]:
    """Return targets in research priority order."""

    return tuple(sorted(ATOMIC_FLASH_TARGETS, key=lambda target: target.rank))


def workflow_required_atomic_flash_targets() -> tuple[AtomicFlashTarget, ...]:
    """Return lanes that need workflow proof before dispatch."""

    return tuple(target for target in ranked_atomic_flash_targets() if not target.dispatchable)


def atomic_flash_target(target_id: str) -> AtomicFlashTarget:
    """Return one target by ID."""

    return _TARGETS_BY_ID[target_id]
