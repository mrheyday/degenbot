"""Internal matching strategy implementation."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from degenbot.flash.source_router import resolve_executor_flash_route
from degenbot.matching.encoder import (
    BPS_DENOMINATOR,
    DEFAULT_MIN_PROFIT_BPS_OF_ESTIMATE,
    encode_match_pair,
)
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

        min_profit = (
            trade.estimated_profit_wei * DEFAULT_MIN_PROFIT_BPS_OF_ESTIMATE
        ) // BPS_DENOMINATOR

        return MatchParams(
            cow_settlement_calldata=trade.cow_settlement_calldata,
            uniswapx_batch_calldata=trade.uniswapx_batch_calldata,
            expected_token_inflows=trade.expected_token_inflows,
            expected_token_inflow_min=trade.expected_token_inflow_min,
            flash_lender=flash_route.lender,
            flash_protocol=flash_route.protocol,
            flash_token=trade.flash_token,
            flash_amount=trade.flash_amount,
            min_profit=max(1, min_profit) if trade.estimated_profit_wei > 0 else 0,
            deadline=deadline,
        )

    def build_params_from_pair(self, pair: MatchPair, estimated_profit_wei: int) -> MatchParams:
        """Build executable MatchParams from an attached order pair."""
        trade = self.build_trade_from_pair(pair, estimated_profit_wei)
        return self.build_params(trade)

    def build_trade_from_pair(self, pair: MatchPair, estimated_profit_wei: int) -> MatchedTrade:
        """Encode a MatchPair when both signed order summaries are attached."""
        cow_order = pair.o.cow_order or pair.c.cow_order
        uniswapx_order = pair.o.uniswapx_order or pair.c.uniswapx_order
        if cow_order is None or uniswapx_order is None:
            msg = "InternalMatchStrategy: signed CoW and UniswapX summaries are required"
            raise ValueError(msg)

        return encode_match_pair(
            pair=pair,
            cow_order=cow_order,
            uniswapx_order=uniswapx_order,
            estimated_profit_wei=estimated_profit_wei,
            flash_token=pair.o.pair_sell,
            flash_amount=pair.fill_amount,
            executor_address=self._settings.executor_address,
        )

    def simulate(self, simulator: Any, params: MatchParams) -> bool:
        """Simulate the internal match using REVM."""
        from degenbot.simulation import encode_match_params, simulate_executor_call

        result = simulate_executor_call(
            simulator=simulator,
            settings=self._settings,
            calldata=encode_match_params(params),
        )
        return result.success

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
