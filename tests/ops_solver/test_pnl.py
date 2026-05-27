"""Tests for the per-solution P&L recorder."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from driver import pnl


def _counter_value(counter: object, *, strategy: str, outcome: str) -> float:
    labelled = counter.labels(strategy=strategy, outcome=outcome)  # type: ignore[attr-defined]
    return labelled._value.get()  # prometheus_client test introspection


def test_record_emits_a_structured_log_without_raising() -> None:
    tracker = pnl.PnLTracker()
    auction = SimpleNamespace(id="auction-1")
    solution = SimpleNamespace(estimated_profit_usd=12.5)
    # `record` is log-only in the scaffold — it must not raise.
    tracker.record(auction, solution)


def test_record_tolerates_objects_missing_optional_attributes() -> None:
    tracker = pnl.PnLTracker()
    tracker.record(SimpleNamespace(), SimpleNamespace())


def test_record_outcome_increments_both_prometheus_counters() -> None:
    tracker = pnl.PnLTracker()
    before_auctions = _counter_value(pnl._AUCTIONS_TOTAL, strategy="C", outcome="won")
    before_pnl = _counter_value(pnl._PNL_USD_TOTAL, strategy="C", outcome="won")

    tracker.record_outcome(strategy="C", outcome="won", profit_usd=42.0)

    assert _counter_value(pnl._AUCTIONS_TOTAL, strategy="C", outcome="won") == before_auctions + 1
    assert _counter_value(pnl._PNL_USD_TOTAL, strategy="C", outcome="won") == pytest.approx(
        before_pnl + 42.0
    )


def test_record_outcome_keeps_separate_series_per_strategy_and_outcome() -> None:
    tracker = pnl.PnLTracker()
    before = _counter_value(pnl._AUCTIONS_TOTAL, strategy="C+D3", outcome="lost")

    tracker.record_outcome(strategy="C+D3", outcome="lost", profit_usd=0.0)

    assert _counter_value(pnl._AUCTIONS_TOTAL, strategy="C+D3", outcome="lost") == before + 1
