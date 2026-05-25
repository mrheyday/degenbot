"""Pure integer price-compatibility helpers for internal matching (Pick A)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from degenbot.decision.types import MatchCandidate

SCALE = 1_000_000_000_000_000_000


def outbound_min_price(o: MatchCandidate) -> int:
    """Outbound min-price (token-buy per unit token-sell, scaled 1e18)."""
    if o.amount_sell == 0:
        msg = "outbound_min_price: amount_sell cannot be zero"
        raise ValueError(msg)
    return (o.amount_buy_min * SCALE) // o.amount_sell


def counter_max_price(c: MatchCandidate) -> int:
    """Counter (inbound / uniswapx) max-price (token-sell per unit token-buy_min, scaled 1e18)."""
    if c.amount_buy_min == 0:
        msg = "counter_max_price: amount_buy_min cannot be zero"
        raise ValueError(msg)
    return (c.amount_sell * SCALE) // c.amount_buy_min


def is_opposing_pair(o: MatchCandidate, c: MatchCandidate) -> bool:
    """Pair pre-condition: token directions oppose."""
    return o.pair_sell == c.pair_buy and o.pair_buy == c.pair_sell


def is_price_compatible(o: MatchCandidate, c: MatchCandidate) -> bool:
    """Price compatibility check."""
    if not is_opposing_pair(o, c):
        return False
    return outbound_min_price(o) <= counter_max_price(c)


def clearing_price(o: MatchCandidate, c: MatchCandidate) -> int:
    """Clearing price = midpoint of the two bounds, scaled 1e18."""
    lo = outbound_min_price(o)
    hi = counter_max_price(c)
    return (lo + hi) // 2


def fill_amount(o: MatchCandidate, c: MatchCandidate) -> int:
    """Fill amount in token-sell units of `o`. The smaller side fully fills."""
    c_max = counter_max_price(c)
    c_budget_in_o_sell = (c.amount_buy_min * c_max) // SCALE
    return min(o.amount_sell, c_budget_in_o_sell)
