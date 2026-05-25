"""Internal matcher — Pick A core algorithm."""

from __future__ import annotations

from typing import Iterable, Sequence

from degenbot.decision.types import MatchCandidate, MatchPair
from degenbot.matching.price_compat import clearing_price, fill_amount, is_price_compatible


def find_matches(
    outbound: Iterable[MatchCandidate], counters: Iterable[MatchCandidate]
) -> Iterable[MatchPair]:
    """Yields all viable internal-match pairs from the current queue snapshot."""
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
    best: MatchPair | None = None
    for m in find_matches(outbound, counters):
        if best is None or m.fill_amount > best.fill_amount:
            best = m
    return best
