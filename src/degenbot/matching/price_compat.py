"""Pure integer price-compatibility helpers for internal matching (Pick A).

Algorithm reference: docs/architecture/06-OFFCHAIN-SERVICES-SPEC.md §2.3
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from degenbot.decision.types import MatchCandidate

PRICE_SCALE = 1_000_000_000_000_000_000  # 1e18
MAX_TOKEN_DECIMALS = 255


def normalize_amount_to_wad(amount: int, decimals: int) -> int:
    """Convert a raw token amount into 18-decimal human-unit WAD."""
    if amount < 0:
        msg = "amount cannot be negative"
        raise ValueError(msg)
    _validate_decimals(decimals)
    if decimals == 18:
        return amount
    if decimals < 18:
        return amount * 10 ** (18 - decimals)
    return amount // 10 ** (decimals - 18)


def denormalize_amount_from_wad(amount_wad: int, decimals: int) -> int:
    """Convert an 18-decimal human-unit WAD amount into raw token units."""
    if amount_wad < 0:
        msg = "amount_wad cannot be negative"
        raise ValueError(msg)
    _validate_decimals(decimals)
    if decimals == 18:
        return amount_wad
    if decimals < 18:
        return amount_wad // 10 ** (18 - decimals)
    return amount_wad * 10 ** (decimals - 18)


def project_sell_to_buy(
    amount_sell: int,
    price: int,
    sell_decimals: int,
    buy_decimals: int,
) -> int:
    """Project raw sell amount to raw buy amount at a WAD buy-per-sell price."""
    sell_wad = normalize_amount_to_wad(amount_sell, sell_decimals)
    buy_wad = (sell_wad * price) // PRICE_SCALE
    return denormalize_amount_from_wad(buy_wad, buy_decimals)


def project_buy_to_sell(
    amount_buy: int,
    price: int,
    sell_decimals: int,
    buy_decimals: int,
) -> int:
    """Project raw buy budget to raw sell amount at a WAD buy-per-sell price."""
    if price == 0:
        msg = "project_buy_to_sell: price cannot be zero"
        raise ValueError(msg)
    buy_wad = normalize_amount_to_wad(amount_buy, buy_decimals)
    sell_wad = (buy_wad * PRICE_SCALE) // price
    return denormalize_amount_from_wad(sell_wad, sell_decimals)


def _validate_decimals(decimals: int) -> None:
    if not 0 <= decimals <= MAX_TOKEN_DECIMALS:
        msg = f"token decimals must be in range 0..{MAX_TOKEN_DECIMALS}: {decimals}"
        raise ValueError(msg)


def outbound_min_price(o: MatchCandidate) -> int:
    """Outbound min-price (token-buy per unit token-sell, scaled 1e18)."""
    amount_sell_wad = normalize_amount_to_wad(o.amount_sell, o.pair_sell_decimals)
    if amount_sell_wad == 0:
        msg = "outbound_min_price: amount_sell cannot be zero"
        raise ValueError(msg)
    amount_buy_min_wad = normalize_amount_to_wad(o.amount_buy_min, o.pair_buy_decimals)
    return (amount_buy_min_wad * PRICE_SCALE) // amount_sell_wad


def counter_max_price(c: MatchCandidate) -> int:
    """Counter (inbound / uniswapx) max-price (token-sell per unit token-buy_min, scaled 1e18)."""
    amount_buy_min_wad = normalize_amount_to_wad(c.amount_buy_min, c.pair_buy_decimals)
    if amount_buy_min_wad == 0:
        msg = "counter_max_price: amount_buy_min cannot be zero"
        raise ValueError(msg)
    amount_sell_wad = normalize_amount_to_wad(c.amount_sell, c.pair_sell_decimals)
    return (amount_sell_wad * PRICE_SCALE) // amount_buy_min_wad


def is_opposing_pair(o: MatchCandidate, c: MatchCandidate) -> bool:
    """Pair pre-condition: token directions oppose."""
    return (
        o.pair_sell.lower() == c.pair_buy.lower()
        and o.pair_buy.lower() == c.pair_sell.lower()
    )


def is_price_compatible(o: MatchCandidate, c: MatchCandidate) -> bool:
    """Price compatibility check (§06 §2.3)."""
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
    cp = clearing_price(o, c)
    if cp == 0:
        return 0
    c_budget_in_o_sell = project_buy_to_sell(
        amount_buy=c.amount_sell,
        price=cp,
        sell_decimals=o.pair_sell_decimals,
        buy_decimals=o.pair_buy_decimals,
    )
    return min(o.amount_sell, c_budget_in_o_sell)
