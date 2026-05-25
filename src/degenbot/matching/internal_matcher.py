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
    from degenbot.degenbot_rs import find_best_match_json
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
            
            res_json = find_best_match_json(
                json.dumps([o.model_dump(by_alias=True) for o in outbound_list]),
                json.dumps([c.model_dump(by_alias=True) for c in counters_list])
            )
            if res_json:
                data = json.loads(res_json)
                # Reconstruct the MatchPair
                return MatchPair.model_validate(data)
            return None
        except Exception:
            pass

    best: MatchPair | None = None
    for m in find_matches(outbound, counters):
        if best is None or m.fill_amount > best.fill_amount:
            best = m
    return best
