"""Internal matcher — Pick A core algorithm.

Reference: docs/architecture/06-OFFCHAIN-SERVICES-SPEC.md §2.3
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from degenbot.decision.types import MatchPair
from degenbot.matching.price_compat import (
    clearing_price,
    fill_amount,
    is_price_compatible,
)

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

    from degenbot.decision.types import MatchCandidate


def find_matches(
    outbound: Sequence[MatchCandidate],
    inbound: Sequence[MatchCandidate],
    uniswapx: Sequence[MatchCandidate],
) -> Generator[MatchPair, None, None]:
    """Yields all viable internal-match pairs from the current queue snapshot."""
    counters = list(inbound) + list(uniswapx)

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
    outbound: Sequence[MatchCandidate],
    inbound: Sequence[MatchCandidate],
    uniswapx: Sequence[MatchCandidate],
) -> MatchPair | None:
    """Find the single best match by greedy fill_amount maximization."""
    best: MatchPair | None = None
    for m in find_matches(outbound, inbound, uniswapx):
        if best is None or m.fill_amount > best.fill_amount:
            best = m
    return best
