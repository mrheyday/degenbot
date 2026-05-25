"""Unit tests for AggregatorPathValidator.

Pure-logic tests on the slippage/verdict computation. Real HTTP wiring is
covered by integration tests once the coordinator /quote endpoint lands.
"""

from __future__ import annotations

import pytest
from degenbot.execution.aggregator_validator import (
    AggregatorPathValidator,
    AggregatorQuote,
    ValidationVerdict,
)


class TestSlippageMath:
    def test_aggregator_matches_degenbot_zero_bps(self) -> None:
        v = AggregatorPathValidator(coordinator_quote_url=None)
        bps = v._slippage_bps(1_000_000, 1_000_000)
        assert bps == 0

    def test_aggregator_beats_degenbot_returns_positive_bps(self) -> None:
        v = AggregatorPathValidator(coordinator_quote_url=None)
        bps = v._slippage_bps(1_000_000, 1_005_000)
        assert bps == 50

    def test_aggregator_worse_than_degenbot_returns_negative_bps(self) -> None:
        v = AggregatorPathValidator(coordinator_quote_url=None)
        bps = v._slippage_bps(1_000_000, 990_000)
        assert bps == -100

    def test_zero_degenbot_amount_does_not_divide_by_zero(self) -> None:
        v = AggregatorPathValidator(coordinator_quote_url=None)
        bps = v._slippage_bps(0, 100)
        assert bps == 0


class TestVerdictThresholds:
    def test_within_band_validates(self) -> None:
        v = AggregatorPathValidator(coordinator_quote_url=None, slippage_tolerance_bps=50)
        verdict = v._verdict_from_slippage(slippage_bps=25, agg_amount=1_000_000)
        assert verdict == ValidationVerdict.VALIDATED

    def test_below_band_disputes_when_aggregator_worse(self) -> None:
        v = AggregatorPathValidator(coordinator_quote_url=None, slippage_tolerance_bps=50)
        verdict = v._verdict_from_slippage(slippage_bps=-100, agg_amount=900_000)
        assert verdict == ValidationVerdict.DISPUTED

    def test_above_band_disputes_when_aggregator_far_better(self) -> None:
        # Even when aggregator beats by a wide margin, that's a dispute —
        # someone's wrong, the solver should flag for review.
        v = AggregatorPathValidator(coordinator_quote_url=None, slippage_tolerance_bps=50)
        verdict = v._verdict_from_slippage(slippage_bps=300, agg_amount=1_030_000)
        assert verdict == ValidationVerdict.DISPUTED

    def test_zero_aggregator_amount_signals_degraded(self) -> None:
        v = AggregatorPathValidator(coordinator_quote_url=None, slippage_tolerance_bps=50)
        verdict = v._verdict_from_slippage(slippage_bps=0, agg_amount=0)
        assert verdict == ValidationVerdict.DEGRADED


class TestValidatorIntegration:
    @pytest.mark.asyncio
    async def test_unreachable_endpoint_returns_unavailable(self) -> None:
        # Point at a definitely-unreachable URL; aggregator validator must
        # fail safe — never return VALIDATED on transport error.
        v = AggregatorPathValidator(
            coordinator_quote_url=None,
            llamaswap_url="http://127.0.0.1:1",  # closed port
            timeout_sec=0.1,
            slippage_tolerance_bps=50,
        )
        async with v:
            result = await v.validate(
                src_asset="0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
                dst_asset="0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
                src_amount=1_000_000,
                degenbot_amount_out=500_000_000_000_000,
            )

        assert result.verdict == ValidationVerdict.UNAVAILABLE
        assert result.aggregator_best_quote is None
        assert "unreachable" in result.rationale.lower()


class TestQuoteIntegerCoercion:
    def test_amount_out_property_coerces_string_to_int(self) -> None:
        q = AggregatorQuote(
            source="llamaswap",
            amount_out_str="1234567890123456",
            estimated_gas=200_000,
            fee_bps=0,
            timestamp_ms=1_700_000_000_000,
        )
        # bigint-precision integer; must round-trip exactly
        assert q.amount_out == 1_234_567_890_123_456

    def test_amount_out_property_handles_huge_values(self) -> None:
        q = AggregatorQuote(
            source="llamaswap",
            amount_out_str="999999999999999999999999999999999999999",
            estimated_gas=200_000,
            fee_bps=0,
            timestamp_ms=1_700_000_000_000,
        )
        assert q.amount_out == 999_999_999_999_999_999_999_999_999_999_999_999_999
