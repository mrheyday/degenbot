"""Timeboost express-lane bid economics for MEV opportunities.

Per ADR-017, Timeboost is enabled conditionally for Pick B fast paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TimeboostStrategyClass = Literal[
    "oracle-sandwich",
    "liquidation",
    "native-arb",
    "four-leg",
    "morpho_liquidation",
]

PROBABILITY_BPS_DENOMINATOR = 10_000


@dataclass(frozen=True, slots=True)
class TimeboostOpportunity:
    expected_profit_wei: int
    non_express_win_probability_bps: int
    gas_cost_wei: int
    strategy_class: TimeboostStrategyClass


@dataclass(frozen=True, slots=True)
class TimeboostRoundState:
    current_round_bid: int
    round_duration_sec: int
    expected_ops_per_round: int


TimeboostAction = Literal["bid-express-lane", "use-non-express-feed"]


@dataclass(frozen=True, slots=True)
class TimeboostDecision:
    action: TimeboostAction
    recommended_bid_wei: int
    net_expected_profit_wei: int
    rationale: str


def decide_timeboost_bid(
    opp: TimeboostOpportunity,
    round_state: TimeboostRoundState,
) -> TimeboostDecision:
    """Decide whether to bid the Timeboost express lane."""

    # -- Sentinels -----------------------------------------------------------
    if round_state.expected_ops_per_round <= 0:
        return TimeboostDecision(
            action="use-non-express-feed",
            recommended_bid_wei=0,
            net_expected_profit_wei=_apply_probability(
                opp.expected_profit_wei - opp.gas_cost_wei,
                _clamp_probability_bps(opp.non_express_win_probability_bps),
            ),
            rationale="expectedOpsPerRound <= 0 sentinel",
        )

    if round_state.current_round_bid <= 0:
        return TimeboostDecision(
            action="use-non-express-feed",
            recommended_bid_wei=0,
            net_expected_profit_wei=_apply_probability(
                opp.expected_profit_wei - opp.gas_cost_wei,
                _clamp_probability_bps(opp.non_express_win_probability_bps),
            ),
            rationale="currentRoundBid <= 0 sentinel",
        )

    if round_state.round_duration_sec <= 0:
        return TimeboostDecision(
            action="use-non-express-feed",
            recommended_bid_wei=0,
            net_expected_profit_wei=_apply_probability(
                opp.expected_profit_wei - opp.gas_cost_wei,
                _clamp_probability_bps(opp.non_express_win_probability_bps),
            ),
            rationale="roundDurationSec <= 0 sentinel",
        )

    # -- Core EV comparison --------------------------------------------------
    amortized_bid_wei = round_state.current_round_bid // round_state.expected_ops_per_round

    gross_profit_wei = opp.expected_profit_wei - opp.gas_cost_wei
    profit_express_wei = gross_profit_wei - amortized_bid_wei
    profit_non_express_wei = _apply_probability(
        gross_profit_wei,
        _clamp_probability_bps(opp.non_express_win_probability_bps),
    )

    should_bid = profit_express_wei > profit_non_express_wei and profit_express_wei > 0
    if should_bid:
        return TimeboostDecision(
            action="bid-express-lane",
            recommended_bid_wei=amortized_bid_wei,
            net_expected_profit_wei=profit_express_wei,
            rationale=f"bid express: profitExpress={profit_express_wei} > profitNonExpress={profit_non_express_wei}",
        )

    return TimeboostDecision(
        action="use-non-express-feed",
        recommended_bid_wei=0,
        net_expected_profit_wei=profit_non_express_wei,
        rationale=f"non-express: profitExpress={profit_express_wei} <= profitNonExpress={profit_non_express_wei}",
    )


def _clamp_probability_bps(probability_bps: int) -> int:
    return max(0, min(PROBABILITY_BPS_DENOMINATOR, probability_bps))


def _apply_probability(value: int, probability_bps: int) -> int:
    return (value * probability_bps) // PROBABILITY_BPS_DENOMINATOR
