"""Pick D3 — pre-batch filter classifier.

Classifies each open CoW order in an upcoming batch as either
`cow_matchable` (an opposing intent already exists in the batch, so
clearing margin is narrow) or `amm_routed` (no opposing intent, solvers
must hit AMM, wider spreads available). Pick D3 instructs us to bid only
on `amm_routed` orders.

Spec: `docs/architecture/03-LOCKED-STRATEGIES.md` Pick D3.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Literal, NamedTuple

OrderClass = Literal["cow_matchable", "amm_routed"]


class OrderShapeError(ValueError):
    """Raised when an auction order lacks the fields needed for D3 screening."""


class _NormalizedOrder(NamedTuple):
    uid: str
    sell_token: str
    buy_token: str
    sell_amount: int
    buy_amount: int


class D3Filter:
    """Pre-batch matchability classifier.

    Stateless. Each call considers a single `order` against `peer_orders`
    drawn from the same batch. Returns the classification only — the
    caller decides whether to bid based on Pick D3 policy.
    """

    def __init__(self) -> None:
        """Create a stateless D3 classifier."""

    def classify(self, order: object, peer_orders: Sequence[object]) -> OrderClass:
        """Return the matchability class for `order` within `peer_orders`.

        Pair-opposition heuristic per spec §03 Pick D3:
        - Same pair (sell/buy tokens swapped)
        - Opposite direction
        - Price-compatible using exact integer cross multiplication:
          `order.buyAmount / order.sellAmount <= peer.sellAmount / peer.buyAmount`

        If any peer satisfies all three -> `cow_matchable`. Otherwise
        `amm_routed`.
        """
        normalized = _normalize_order(order)
        for peer_order in peer_orders:
            peer = _normalize_order(peer_order)
            if peer.uid == normalized.uid:
                continue
            if _is_opposing_pair(normalized, peer) and _prices_overlap(normalized, peer):
                return "cow_matchable"
        return "amm_routed"

    def should_bid(self, order: object, peer_orders: Sequence[object]) -> bool:
        """Convenience wrapper: True iff the order is AMM-routed.

        Pick D3 policy: bid only on AMM-routed orders.
        """
        try:
            return self.classify(order, peer_orders) == "amm_routed"
        except OrderShapeError:
            return False


def _normalize_order(order: object) -> _NormalizedOrder:
    uid = _read_string(order, "uid")
    sell_token = _read_string(order, "sell_token", "sellToken").lower()
    buy_token = _read_string(order, "buy_token", "buyToken").lower()
    sell_amount = _read_int(order, "sell_amount", "sellAmount")
    buy_amount = _read_int(order, "buy_amount", "buyAmount")
    if sell_amount <= 0 or buy_amount <= 0:
        raise OrderShapeError("D3 order amounts must be positive")
    return _NormalizedOrder(
        uid=uid,
        sell_token=sell_token,
        buy_token=buy_token,
        sell_amount=sell_amount,
        buy_amount=buy_amount,
    )


def _is_opposing_pair(order: _NormalizedOrder, peer: _NormalizedOrder) -> bool:
    return order.sell_token == peer.buy_token and order.buy_token == peer.sell_token


def _prices_overlap(order: _NormalizedOrder, peer: _NormalizedOrder) -> bool:
    return order.buy_amount * peer.buy_amount <= order.sell_amount * peer.sell_amount


def _read_string(order: object, snake_key: str, camel_key: str | None = None) -> str:
    value = _read_value(order, snake_key, camel_key)
    if not isinstance(value, str) or value == "":
        raise OrderShapeError(f"missing string field {snake_key}")
    return value


def _read_int(order: object, snake_key: str, camel_key: str | None = None) -> int:
    value = _read_value(order, snake_key, camel_key)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value, 16) if value.startswith(("0x", "0X")) else int(value, 10)
        except ValueError as exc:
            raise OrderShapeError(f"invalid integer field {snake_key}") from exc
    raise OrderShapeError(f"missing integer field {snake_key}")


def _read_value(order: object, snake_key: str, camel_key: str | None) -> object:
    keys = (snake_key,) if camel_key is None else (snake_key, camel_key)
    if isinstance(order, Mapping):
        mapped = order
        for key in keys:
            if key in mapped:
                return mapped[key]
    for key in keys:
        value = getattr(order, key, None)
        if value is not None:
            return value
    raise OrderShapeError(f"missing field {snake_key}")
