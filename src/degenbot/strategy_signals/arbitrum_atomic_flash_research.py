"""Atomic flash-financed Arbitrum workflow targets.

This module tracks candidates that are structurally atomic and flash-fundable,
and need dedicated workflow completion before dispatch. It is stricter than prose research:
every target must name the exact single-transaction primitive, flash source,
POC call sequence, and workflow requirements before any implementation can be
promoted into the executable strategy workflow catalog.
"""

from __future__ import annotations

# ruff: noqa: E501
from dataclasses import dataclass
from enum import StrEnum


class AtomicFlashStatus(StrEnum):
    """Research maturity of an atomic flash target."""

    REQUIRES_DECODE = "requires_decode"
    QUICK_CHECK = "quick_check"


@dataclass(frozen=True, slots=True)
class AtomicFlashTarget:
    """One zero-capital, single-transaction MEV research lane."""

    target_id: str
    rank: int
    protocol: str
    label: str
    status: AtomicFlashStatus
    tvl_usd: int | None
    fees_30d_usd: int | None
    trend_30d_bps: int | None
    flash_source: str
    execution_surface: str
    thesis: str
    required_checks: tuple[str, ...]
    poc_steps: tuple[str, ...]
    workflow_requirements: tuple[str, ...]
    code_refs: tuple[str, ...]
    proof_refs: tuple[str, ...]

    @property
    def atomic_single_tx(self) -> bool:
        """True when the target is designed as one transaction."""
        return all("async" not in step.lower() for step in self.poc_steps)

    @property
    def dispatchable(self) -> bool:
        """True when this target has a dedicated execution workflow."""
        return False


ATOMIC_FLASH_TARGETS: tuple[AtomicFlashTarget, ...] = (
    AtomicFlashTarget(
        target_id="E-1",
        rank=1,
        protocol="Euler v2",
        label="Euler v2 EVC flash liquidation",
        status=AtomicFlashStatus.REQUIRES_DECODE,
        tvl_usd=None,
        fees_30d_usd=None,
        trend_30d_bps=None,
        flash_source="Balancer V3 Vault.unlock",
        execution_surface="EVC batch liquidate flow",
        thesis=(
            "Euler v2's EVC batching can atomically combine controller enablement, liquidation, "
            "collateral withdrawal, swap-back, and flash repayment if Arbitrum vaults expose "
            "profitable external liquidation discounts."
        ),
        required_checks=(
            "Arbitrum Euler v2 vault registry and controller vault addresses",
            "collateral vault liquidation discount formula",
            "oracle freshness and feed type per vault",
            "EVC batch call ordering and sub-account ownership semantics",
            "Balancer V3 flash liquidity for the debt asset",
        ),
        poc_steps=(
            "BalancerV3.unlock(debtAsset, debtAmount, encodedEvcBatch)",
            "EVC.batch(enableController, enableCollateral, controllerVault.liquidate)",
            "collateralVault.withdraw(seizedCollateral, executor)",
            "Swap seized collateral back to debtAsset with amountOutMin >= debtAmount + minProfit",
            "BalancerV3.settle(debtAsset, debtAmount)",
        ),
        workflow_requirements=(
            "Euler vault address or controller not verified on Arbitrum",
            "liquidation discount or oracle type is unknown",
            "EVC sub-account ownership cannot be proven for the executor",
            "fork simulation cannot repay flash principal plus minProfit",
        ),
        code_refs=(
            "contracts/src/executors/AtomicExecutor.sol",
            "coordinator/src/strategies/native-arb.ts",
        ),
        proof_refs=(
            "solver/driver/tests/test_arbitrum_atomic_flash_research.py",
            "docs/research/2026-05-17-arbitrum-atomic-flash-opportunities.md",
        ),
    ),
    AtomicFlashTarget(
        target_id="P-2",
        rank=2,
        protocol="Pendle",
        label="Pendle PT/YT/SY identity arb",
        status=AtomicFlashStatus.REQUIRES_DECODE,
        tvl_usd=144_400_000,
        fees_30d_usd=60_700,
        trend_30d_bps=1_760,
        flash_source="Balancer V3 Vault.unlock",
        execution_surface="Pendle Router PY mint/redeem plus PT/YT swaps",
        thesis=(
            "Pendle's PT + YT = SY identity creates a hard atomic arb when the combined PT/YT "
            "market price deviates from redeemable SY value after fees and slippage."
        ),
        required_checks=(
            "top Arbitrum Pendle market addresses by TVL",
            "PT, YT, SY token addresses and expiry state",
            "live PT plus YT value against SY redemption value",
            "Pendle Router route calldata and limit order fill priority",
            "swap-back route into the flash token",
        ),
        poc_steps=(
            "BalancerV3.unlock(SY or base asset, flashAmount, encodedPendleArb)",
            "Cheap-combo path: buy PT and YT, then redeemPyToSy",
            "Rich-combo path: mint PT and YT from SY, then sell PT/YT",
            "Swap final asset back to flashToken with amountOutMin >= principal + minProfit",
            "BalancerV3.settle(flashToken, principal)",
        ),
        workflow_requirements=(
            "market is post-expiry and redeem path semantics differ",
            "PT/YT/SY decimals or accounting asset are unresolved",
            "Pendle router quote cannot be reproduced on fork",
            "identity spread does not exceed fees, slippage, lane cost, and minProfit",
        ),
        code_refs=(
            "contracts/src/executors/AtomicExecutor.sol",
            "coordinator/src/strategies/native-arb.ts",
        ),
        proof_refs=(
            "solver/driver/tests/test_arbitrum_atomic_flash_research.py",
            "docs/research/2026-05-17-arbitrum-atomic-flash-opportunities.md",
        ),
    ),
    AtomicFlashTarget(
        target_id="D-1",
        rank=3,
        protocol="Dolomite",
        label="Dolomite generic flash liquidation",
        status=AtomicFlashStatus.REQUIRES_DECODE,
        tvl_usd=21_600_000,
        fees_30d_usd=38_600,
        trend_30d_bps=810,
        flash_source="Dolomite negative-balance flash or Balancer V3 Vault.unlock",
        execution_surface="LiquidatorProxyV4WithGenericTrader",
        thesis=(
            "Dolomite's generic trader/liquidator surface may combine free internal flash liquidity, "
            "liquidation, external sale, and repayment inside a single operate/liquidate sequence."
        ),
        required_checks=(
            "DolomiteMargin and LiquidatorProxyV4WithGenericTrader Arbitrum addresses",
            "market list, collateral factors, and oracle configs",
            "expiry liquidation spread and 0 to 5 percent ramp timing",
            "GenericTrader path compatibility with external swap routers",
            "account solvency and owed/held asset accounting",
        ),
        poc_steps=(
            "Open flash-funded Dolomite operate or BalancerV3.unlock context",
            "LiquidatorProxyV4WithGenericTrader.liquidate(targetAccount, marketIds, traderPath)",
            "Sell seized held asset through GenericTrader or external router",
            "Repay negative balance or Balancer principal",
            "Assert final held flashToken balance >= principal + minProfit",
        ),
        workflow_requirements=(
            "liquidation path requires pre-funded Dolomite account state",
            "generic trader route cannot be simulated with exact min-out",
            "expiry spread ramp is not active or is already competed away",
            "negative balance flash accounting leaves residual protocol debt or misses minProfit",
        ),
        code_refs=(
            "contracts/src/executors/AtomicExecutor.sol",
            "coordinator/src/strategies/liquidation/executor.ts",
        ),
        proof_refs=(
            "solver/driver/tests/test_arbitrum_atomic_flash_research.py",
            "docs/research/2026-05-17-arbitrum-atomic-flash-opportunities.md",
        ),
    ),
    AtomicFlashTarget(
        target_id="C-1",
        rank=4,
        protocol="Compound v3 / Silo v2",
        label="Unexplored isolated-lending liquidation check",
        status=AtomicFlashStatus.QUICK_CHECK,
        tvl_usd=None,
        fees_30d_usd=None,
        trend_30d_bps=None,
        flash_source="Balancer V3 Vault.unlock",
        execution_surface="Compound Comet absorb/buyCollateral or Silo liquidate",
        thesis=(
            "Compound v3 and Silo v2 may expose external liquidation/buy-discount surfaces on "
            "Arbitrum, but each must be separated from permissionless gas-only maintenance calls "
            "before any EV claim is trusted."
        ),
        required_checks=(
            "Compound Comet proxy addresses and collateral asset configs on Arbitrum",
            "Comet isLiquidatable/account absorb/buyCollateral economics",
            "Silo v2 deployment and liquidate function access",
            "auction or discount timing for seized collateral",
            "flash-funded same-transaction buy and swap feasibility",
        ),
        poc_steps=(
            "BalancerV3.unlock(baseAsset, baseAmount, encodedLendingLiq)",
            "Compound path: Comet.absorb(executor, accounts) then Comet.buyCollateral",
            "Silo path: liquidate borrower and receive discounted collateral",
            "Swap discounted collateral back to baseAsset",
            "BalancerV3.settle(baseAsset, baseAmount)",
        ),
        workflow_requirements=(
            "absorb pays no liquidator discount in the same transaction",
            "buyCollateral discount is unavailable or not atomically created",
            "Silo liquidate is permissioned or bonus is below cost",
            "collateral sale cannot repay flash principal plus minProfit",
        ),
        code_refs=(
            "contracts/src/executors/AtomicExecutor.sol",
            "coordinator/src/strategies/liquidation/executor.ts",
        ),
        proof_refs=(
            "solver/driver/tests/test_arbitrum_atomic_flash_research.py",
            "docs/research/2026-05-17-arbitrum-atomic-flash-opportunities.md",
        ),
    ),
    AtomicFlashTarget(
        target_id="P-3",
        rank=5,
        protocol="Pendle / Uniswap v4",
        label="Pendle limit-order plus cross-AMM flash arb",
        status=AtomicFlashStatus.QUICK_CHECK,
        tvl_usd=144_400_000,
        fees_30d_usd=60_700,
        trend_30d_bps=1_760,
        flash_source="Balancer V3 Vault.unlock",
        execution_surface="Pendle limit-order fill plus external AMM hedge",
        thesis=(
            "Pendle limit orders are filled before AMM paths; stale implied-yield orders can be "
            "flash-filled and hedged through Uniswap v4 or another deep AMM when the limit price "
            "is stale against current fair value."
        ),
        required_checks=(
            "Pendle Arbitrum limit-order contract and order encoding",
            "best live PT/YT fair value against AMM and oracle inputs",
            "Uniswap v4 pool and hook classification for the hedge leg",
            "hook permissions and callback safety",
            "single-transaction fill and hedge calldata",
        ),
        poc_steps=(
            "BalancerV3.unlock(fillAsset, fillAmount, encodedPendleLimitArb)",
            "Fill stale Pendle limit order at favorable implied yield",
            "Hedge acquired PT/YT/SY exposure through Uniswap v4 or another approved AMM",
            "Swap proceeds back to flashToken",
            "BalancerV3.settle(flashToken, principal)",
        ),
        workflow_requirements=(
            "limit-order contract or order signature path is not verified",
            "v4 hook is unclassified or can reenter unsafe callback surfaces",
            "stale order edge is below fees, slippage, and lane cost",
            "fork simulation cannot prove principal plus minProfit",
        ),
        code_refs=(
            "contracts/src/executors/AtomicExecutor.sol",
            "coordinator/src/strategies/v4-hooks.ts",
        ),
        proof_refs=(
            "solver/driver/tests/test_arbitrum_atomic_flash_research.py",
            "docs/research/2026-05-17-arbitrum-atomic-flash-opportunities.md",
        ),
    ),
)

_TARGETS_BY_ID = {target.target_id: target for target in ATOMIC_FLASH_TARGETS}


def atomic_flash_target(target_id: str) -> AtomicFlashTarget:
    """Return one research target by id."""
    try:
        return _TARGETS_BY_ID[target_id]
    except KeyError as exc:
        message = f"unknown atomic flash target: {target_id}"
        raise KeyError(message) from exc


def ranked_atomic_flash_targets() -> tuple[AtomicFlashTarget, ...]:
    """Return research targets sorted by rank."""
    return tuple(sorted(ATOMIC_FLASH_TARGETS, key=lambda target: target.rank))


def workflow_required_atomic_flash_targets() -> tuple[AtomicFlashTarget, ...]:
    """Return all targets that need a dedicated workflow before live tx output."""
    return tuple(target for target in ranked_atomic_flash_targets() if not target.dispatchable)
