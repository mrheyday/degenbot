"""Internal matching strategy implementation."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from degenbot.flash.source_router import resolve_executor_flash_route
from degenbot.matching.encoder import encode_match_pair
from degenbot.strategies_coordinator.types import (
    MatchParams,
)

if TYPE_CHECKING:
    from degenbot.adapters.config import Settings
    from degenbot.decision.types import (
        CowOrderSummary,
        MatchPair,
        UniswapXOrderSummary,
    )
    from degenbot.matching.encoder import MatchedTrade

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InternalMatchPlan:
    pair: MatchPair
    cow_order: CowOrderSummary
    uniswapx_order: UniswapXOrderSummary
    estimated_profit_wei: int
    flash_token: str
    flash_amount: int


class InternalMatchStrategy:
    """Internal matching strategy."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def build_params(self, trade: MatchedTrade) -> MatchParams:
        """Convert a MatchedTrade into MatchParams."""
        flash_route = resolve_executor_flash_route(
            token=trade.flash_token,
            amount=trade.flash_amount,
            context="InternalMatchStrategy",
            aave_v3_pool=self._settings.aave_v3_pool,
            morpho_blue=self._settings.morpho_blue,
        )

        # min_profit and deadline are already computed in encoder for matched legs,
        # but we also need the outer strategy envelope.
        deadline = int(time.time()) + 60

        return MatchParams(
            cow_settlement_calldata=trade.cow_settlement_calldata,
            uniswapx_batch_calldata=trade.uniswapx_batch_calldata,
            expected_token_inflows=trade.expected_token_inflows,
            expected_token_inflow_min=trade.expected_token_inflow_min,
            flash_lender=flash_route.lender,
            flash_protocol=flash_route.protocol,
            flash_token=trade.flash_token,
            flash_amount=trade.flash_amount,
            min_profit=trade.estimated_profit_wei,  # TODO: apply buffer if not already done
            deadline=deadline,
        )

    def preflight(self, plan: InternalMatchPlan) -> MatchedTrade:
        """Validate and encode the match plan."""
        return encode_match_pair(
            pair=plan.pair,
            cow_order=plan.cow_order,
            uniswapx_order=plan.uniswapx_order,
            estimated_profit_wei=plan.estimated_profit_wei,
            flash_token=plan.flash_token,
            flash_amount=plan.flash_amount,
            executor_address=self._settings.executor_address,
        )
