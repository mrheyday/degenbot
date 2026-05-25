"""Internal matcher — Pick A core algorithm."""

import json
from typing import Iterable, Sequence

from degenbot.decision.types import (
    CowOrderSummary,
    MatchCandidate,
    MatchPair,
    UniswapXOrderSummary,
)
from degenbot.matching.price_compat import clearing_price, fill_amount, is_price_compatible

try:
    from degenbot.degenbot_rs.execution_engine import find_best_match_json
    HAS_RUST_ACCEL = True
except ImportError:
    HAS_RUST_ACCEL = False


def find_matches(
    outbound: Iterable[MatchCandidate], counters: Iterable[MatchCandidate]
) -> Iterable[MatchPair]:
    """Yields all viable internal-match pairs from the current queue snapshot."""
    # Note: find_matches remains in Python for now to support Generator yielding.
    # The hot-path greedy find_best_match is accelerated in Rust.
    for o in outbound:
        for c in counters:
            if not is_price_compatible(o, c):
                continue

            fill = fill_amount(o, c)
            if fill == 0:
                continue

            yield MatchPair(
                o=o,
                c=c,
                fill_amount=fill,
                clearing_price=clearing_price(o, c),
            )


def find_best_match(
    outbound: Iterable[MatchCandidate], counters: Iterable[MatchCandidate]
) -> MatchPair | None:
    """Find the single best match by greedy fillAmount maximization."""
    if HAS_RUST_ACCEL:
        try:
            outbound_list = list(outbound)
            counters_list = list(counters)
            if not outbound_list or not counters_list:
                return None
            
            # Simple attribute-to-dict mapper for non-Pydantic dataclasses
            def to_dict(c: MatchCandidate):
                d = c.__dict__.copy()
                if c.cow_order: d["cow_order"] = c.cow_order.__dict__
                if c.uniswapx_order: d["uniswapx_order"] = c.uniswapx_order.__dict__
                return d

            res_json = find_best_match_json(
                json.dumps([to_dict(o) for o in outbound_list]),
                json.dumps([to_dict(c) for c in counters_list])
            )
            if res_json:
                data = json.loads(res_json)
                # Reconstruct the MatchPair
                return MatchPair(
                    o=_reconstruct_candidate(data["o"]),
                    c=_reconstruct_candidate(data["c"]),
                    fill_amount=int(data["fill_amount"]),
                    clearing_price=int(data["clearing_price"])
                )
            return None
        except Exception:
            pass

    best: MatchPair | None = None
    for m in find_matches(outbound, counters):
        if best is None or m.fill_amount > best.fill_amount:
            best = m
    return best


def _reconstruct_candidate(data: dict) -> MatchCandidate:
    cow = None
    if data.get("cow_order"):
        cow = CowOrderSummary(**data["cow_order"])
    ux = None
    if data.get("uniswapx_order"):
        ux = UniswapXOrderSummary(**data["uniswapx_order"])
    
    return MatchCandidate(
        id=data["id"],
        side=data["side"],
        pair_sell=data["pair_sell"],
        pair_buy=data["pair_buy"],
        amount_sell=int(data["amount_sell"]),
        amount_buy_min=int(data["amount_buy_min"]),
        source_id=data["source_id"],
        source_venue=data["source_venue"],
        source_expires_at=int(data["source_expires_at"]),
        received_at_ms=int(data["received_at_ms"]),
        cow_order=cow,
        uniswapx_order=ux
    )
