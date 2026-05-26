"""Unit tests for Timeboost express-lane EV decisions."""

from degenbot.decision.timeboost import (
    TimeboostOpportunity,
    TimeboostRoundState,
    decide_timeboost_bid,
)


def test_timeboost_bids_when_express_ev_wins() -> None:
    decision = decide_timeboost_bid(
        TimeboostOpportunity(
            expected_profit_wei=10_000,
            gas_cost_wei=1_000,
            non_express_win_probability_bps=5_000,
            strategy_class="native-arb",
        ),
        TimeboostRoundState(
            current_round_bid=2_000,
            round_duration_sec=60,
            expected_ops_per_round=2,
        ),
    )

    assert decision.action == "bid-express-lane"
    assert decision.recommended_bid_wei == 1_000
    assert decision.net_expected_profit_wei == 8_000


def test_timeboost_uses_non_express_when_probability_adjusted_ev_wins() -> None:
    decision = decide_timeboost_bid(
        TimeboostOpportunity(
            expected_profit_wei=10_000,
            gas_cost_wei=1_000,
            non_express_win_probability_bps=9_000,
            strategy_class="four-leg",
        ),
        TimeboostRoundState(
            current_round_bid=5_000,
            round_duration_sec=60,
            expected_ops_per_round=1,
        ),
    )

    assert decision.action == "use-non-express-feed"
    assert decision.recommended_bid_wei == 0
    assert decision.net_expected_profit_wei == 8_100


def test_timeboost_sentinel_avoids_express_lane() -> None:
    decision = decide_timeboost_bid(
        TimeboostOpportunity(
            expected_profit_wei=10_000,
            gas_cost_wei=1_000,
            non_express_win_probability_bps=15_000,
            strategy_class="liquidation",
        ),
        TimeboostRoundState(
            current_round_bid=2_000,
            round_duration_sec=60,
            expected_ops_per_round=0,
        ),
    )

    assert decision.action == "use-non-express-feed"
    assert decision.recommended_bid_wei == 0
    assert decision.net_expected_profit_wei == 9_000
