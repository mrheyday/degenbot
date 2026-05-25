"""Pick C — SolutionBuilder.

Given an auction instance, builds a Solution that:
1. Skips orders that Pick D3 marks as CoW-matchable (when D3 enabled).
2. For the remaining AMM-routed orders, fetches a best aggregator quote
   from the TS coordinator's quote engine.
3. Computes a margin per the spec.
4. Returns a Solution iff estimated profit clears the configured floor.

Spec: `docs/architecture/03-LOCKED-STRATEGIES.md` Pick C +
`docs/architecture/06-OFFCHAIN-SERVICES-SPEC.md` §3.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from degenbot.cow.models import Auction, Trade
from degenbot.cow.models import Solution as ProtocolSolution
from degenbot.quote_engine import QuoteRequest

if TYPE_CHECKING:
    from degenbot.quote_engine import QuoteEngineClient
    from degenbot.strategies_solver.d3_filter import D3Filter


@dataclass(init=False)
class Solution:
    """A signed-or-signable solution to a CoW batch auction."""

    auction_id: str
    estimated_profit_usd: float
    # The protocol solution ready for serialization.
    protocol_solution: ProtocolSolution
    # Min profit gate; the builder injects the configured floor here.
    min_profit_usd: float

    def __init__(
        self,
        auction_id: str,
        estimated_profit_usd: float,
        protocol_solution: ProtocolSolution | None = None,
        min_profit_usd: float = 0.0,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Normalize legacy raw payloads into a protocol solution model."""
        if protocol_solution is None and payload is not None:
            protocol_solution = ProtocolSolution.model_validate(payload)
        if protocol_solution is None:
            msg = "Solution requires protocol_solution or payload"
            raise ValueError(msg)
        self.auction_id = auction_id
        self.estimated_profit_usd = estimated_profit_usd
        self.protocol_solution = protocol_solution
        self.min_profit_usd = min_profit_usd

    def is_profitable(self) -> bool:
        """Return True iff estimated profit clears the configured floor."""
        return self.estimated_profit_usd >= self.min_profit_usd


class SolutionBuilder:
    """Builds Solutions for Pick C bidding.

    Orchestrates the D3 filter and the quote engine. Stateless across
    auctions; safe to share across the asyncio loop.
    """

    def __init__(
        self,
        quote_engine: QuoteEngineClient,
        d3_filter: D3Filter,
        min_profit_usd: float = 0.0,
        strategy_d3_enabled: bool = True,
    ) -> None:
        self._quote_engine = quote_engine
        self._d3_filter = d3_filter
        self._min_profit_usd = min_profit_usd
        self._d3_enabled = strategy_d3_enabled

    async def build(self, auction: Auction) -> Solution | None:
        """Build a Solution for `auction`, or `None` to pass.

        Steps:
        1. Optionally filter orders via Pick D3.
        2. For surviving orders, fan out quotes to the coordinator.
        3. Compose a settlement calldata blob + clearing prices.
        4. Estimate profit (USD) vs. the aggregator best-quote baseline.
        """
        # 1. Filter orders
        surviving_orders = []
        for order in auction.orders:
            if not self._d3_enabled:
                surviving_orders.append(order)
                continue

            peers = [o for o in auction.orders if o.uid != order.uid]
            if self._d3_filter.should_bid(order, peers):
                surviving_orders.append(order)

        if not surviving_orders:
            return None

        # 2. Fan out quotes
        # For simplicity in this slice, we solve each order independently.
        # CoW allows matching multiple orders in one solution, but Pick C
        # focuses on AMM-routed single orders with margin.
        tasks = [
            self._quote_engine.quote(
                QuoteRequest(
                    sell_token=order.sell_token,
                    buy_token=order.buy_token,
                    sell_amount=str(order.sell_amount),
                    kind=order.kind,
                )
            )
            for order in surviving_orders
        ]

        quotes = await asyncio.gather(*tasks, return_exceptions=True)

        # 3. Compose solution
        # In this slice, we pick the first profitable order.
        # Production would optimize across all orders.
        for order, quote in zip(surviving_orders, quotes, strict=True):
            if isinstance(quote, BaseException):
                continue

            # Compute margin: (our_quote - user_limit) * size
            # Margin = quote.buy_amount - order.buy_amount
            # (Note: this assumes SELL order kind; BUY kind is symmetric)

            margin_wei = int(quote.buy_amount) - int(order.buy_amount)

            # Estimate profit in USD using buy_token's reference_price
            buy_token_meta = auction.tokens.get(order.buy_token)
            reference_price = int(buy_token_meta.reference_price or 0) if buy_token_meta else 0

            # Basic USD conversion: (margin_wei / 10**decimals) * price_per_token
            # For PoC, we just use the raw reference_price weight.
            # In CoW, referencePrice is usually in 1e18 units relative to a reference.
            estimated_profit_usd = (margin_wei * reference_price) / 10**36  # Rough approximation

            # Mock protocol solution
            protocol_sol = ProtocolSolution(
                id=0,
                prices={
                    order.sell_token: quote.buy_amount,
                    order.buy_token: quote.sell_amount,
                },
                trades=[
                    Trade(
                        kind=order.kind,
                        sell_token=order.sell_token,
                        buy_token=order.buy_token,
                        amount=order.sell_amount,
                        executed_amount=order.sell_amount,
                        fee_amount=0,
                        order_uid=order.uid,
                    )
                ],
                interactions=[],
            )

            sol = Solution(
                auction_id=auction.id or "unknown",
                estimated_profit_usd=float(estimated_profit_usd),
                protocol_solution=protocol_sol,
                min_profit_usd=self._min_profit_usd,
            )

            if sol.is_profitable():
                return sol

        return None
