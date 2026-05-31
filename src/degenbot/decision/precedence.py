"""Decision precedence for the strategy routing engine."""

from __future__ import annotations

from typing import Literal

DecisionKind = Literal[
    "internal_match",
    "four_leg",
    "morpho_liquidation",
    "dolomite_liquidation",
    "native_arb",
    "oracle_sandwich",
    "sandwich",
    "launch_sniper",
    "cow_user_submit",
    "across_fill",
    "pass",
]

PRECEDENCE: tuple[DecisionKind, ...] = (
    "internal_match",
    "four_leg",
    "morpho_liquidation",
    "dolomite_liquidation",
    "native_arb",
    "oracle_sandwich",
    "sandwich",
    "launch_sniper",
    "cow_user_submit",
    "across_fill",
    "pass",
)

PRIORITY_INDEX: dict[DecisionKind, int] = {k: i for i, k in enumerate(PRECEDENCE)}


def compare_priority(a: DecisionKind, b: DecisionKind) -> int:
    """Compare two decision kinds by priority.

    Returns:
      < 0 if `a` is higher priority than `b`
      = 0 if equal
      > 0 if `b` is higher priority than `a`

    Unknown kinds sort last.
    """
    ai = PRIORITY_INDEX.get(a, 999_999)
    bi = PRIORITY_INDEX.get(b, 999_999)
    return ai - bi


def is_higher_priority(a: DecisionKind, b: DecisionKind) -> bool:
    """True if `a` is strictly higher priority than `b`."""
    return compare_priority(a, b) < 0
