"""Four-leg cross-protocol composition strategy.

Algorithm reference: docs/architecture/03-LOCKED-STRATEGIES.md#pick-b
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from degenbot.decision.types import Address, Hex
from degenbot.flash.source_router import resolve_executor_flash_route
from degenbot.strategies_coordinator.types import (
    DEX_KIND,
    ComposeParams,
    FlashProtocol,
    SwapStep,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from degenbot.adapters.config import Settings
    from degenbot.flash.source_router import FlashRouteCandidate
    from degenbot.types_solver.wire import Opportunity

logger = logging.getLogger(__name__)

MIN_PROFIT_BPS_OF_ESTIMATE = 9500
BPS_DENOMINATOR = 10000
DEFAULT_DEADLINE_BUFFER_S = 60


@dataclass(frozen=True, slots=True)
class FourLegPlan:
    opportunity_id: str
    across_fill_calldata: Hex
    arb_swaps: Sequence[SwapStep]
    cow_fill_calldata: Hex
    uniswapx_rebalance_calldata: Hex
    flash_token: Address
    flash_amount: int
    expected_profit_wei: int
    flash_protocol: FlashProtocol | None = None
    flash_lender: Address | None = None
    flash_candidates: Sequence[FlashRouteCandidate] | None = None


class FourLegStrategy:
    """Four-leg cross-protocol composition strategy."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def preflight(self, opp: Opportunity) -> FourLegPlan | None:
        """Validate and prepare a four-leg plan from an opportunity."""
        # This is a simplified port of the TS preflight.
        # It expects the opaque legs to be present in the opportunity enrichment
        # or attached metadata.

        # 1. Identify opaque legs (Across, CoW, UniswapX)
        # For now we only support the 'hint' path where they are pre-supplied.

        enrichment = getattr(opp, "enrichment", {}) or {}
        hint = enrichment.get("four_leg_hint")
        if not hint:
            return None

        across_leg = hint.get("across_fill_calldata")
        cow_leg = hint.get("cow_fill_calldata")
        ux_leg = hint.get("uniswapx_rebalance_calldata")

        if not across_leg or not cow_leg or not ux_leg:
            return None

        # 2. Resolve arb swaps
        # If the hint has them, use them; otherwise use the engine path.
        arb_swaps = hint.get("arb_swaps")
        if not arb_swaps:
            arb_swaps = [self._map_engine_swap_to_contract(step) for step in opp.path]

        if not arb_swaps:
            return None

        return FourLegPlan(
            opportunity_id=opp.id,
            across_fill_calldata=across_leg,
            arb_swaps=arb_swaps,
            cow_fill_calldata=cow_leg,
            uniswapx_rebalance_calldata=ux_leg,
            flash_token=opp.flash_token,
            flash_amount=opp.flash_amount,
            expected_profit_wei=opp.estimated_profit_wei,
        )

    def build_params(self, plan: FourLegPlan) -> ComposeParams:
        """Convert a FourLegPlan into ComposeParams."""
        self._assert_executable_plan(plan)

        flash_route = resolve_executor_flash_route(
            token=plan.flash_token,
            amount=plan.flash_amount,
            context="FourLegStrategy",
            requested_protocol=plan.flash_protocol,
            explicit_lender=plan.flash_lender,
            candidates=plan.flash_candidates,
            aave_v3_pool=self._settings.aave_v3_pool,
            morpho_blue=self._settings.morpho_blue,
        )

        min_profit = (plan.expected_profit_wei * MIN_PROFIT_BPS_OF_ESTIMATE) // BPS_DENOMINATOR
        deadline = int(time.time()) + DEFAULT_DEADLINE_BUFFER_S

        return ComposeParams(
            across_fill_calldata=plan.across_fill_calldata,
            arb_swaps=plan.arb_swaps,
            cow_fill_calldata=plan.cow_fill_calldata,
            uniswapx_rebalance_calldata=plan.uniswapx_rebalance_calldata,
            flash_lender=flash_route.lender,
            flash_protocol=flash_route.protocol,
            flash_token=plan.flash_token,
            flash_amount=plan.flash_amount,
            min_profit=min_profit,
            deadline=deadline,
        )

    def _map_engine_swap_to_contract(self, step: Any) -> SwapStep:
        dex_map = {
            "UniswapV2": DEX_KIND.V2,
            "UniswapV3": DEX_KIND.V3,
            "UniswapV4": DEX_KIND.V4,
            "Curve": DEX_KIND.CURVE,
            "Algebra": DEX_KIND.ALGEBRA,
            "Solidly": DEX_KIND.SOLIDLY,
        }
        dex_kind = dex_map.get(getattr(step, "dex", ""), DEX_KIND.V2)

        return SwapStep(
            dex_kind=dex_kind,
            router=getattr(step, "pool", getattr(step, "router", "")),
            call_data=Hex("0x"),
            token_in=step.token_in,
            token_out=step.token_out,
            amount_in=step.amount_in,
            amount_out_min=step.amount_out_min,
        )

    def _assert_executable_plan(self, plan: FourLegPlan) -> None:
        if not plan.across_fill_calldata or plan.across_fill_calldata == "0x":
            msg = "FourLegStrategy: across_fill_calldata must be non-empty"
            raise ValueError(msg)
        if not plan.arb_swaps:
            msg = "FourLegStrategy: arb_swaps must contain at least one bridge swap"
            raise ValueError(msg)
        if not plan.cow_fill_calldata or plan.cow_fill_calldata == "0x":
            msg = "FourLegStrategy: cow_fill_calldata must be non-empty"
            raise ValueError(msg)
        if not plan.uniswapx_rebalance_calldata or plan.uniswapx_rebalance_calldata == "0x":
            msg = "FourLegStrategy: uniswapx_rebalance_calldata must be non-empty"
            raise ValueError(msg)
        if plan.flash_amount <= 0:
            msg = "FourLegStrategy: flash_amount must be > 0"
            raise ValueError(msg)
        if plan.expected_profit_wei <= 0:
            msg = "FourLegStrategy: expected_profit_wei must be > 0"
            raise ValueError(msg)
