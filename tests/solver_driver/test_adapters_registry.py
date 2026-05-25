"""Tests for the category-level adapter registry."""

from __future__ import annotations

import pytest
from degenbot.adapters import registry
from degenbot.adapters.laneadapters import EXECUTION_LANES


def test_all_adapters_is_non_empty() -> None:
    assert len(registry.ALL_ADAPTERS) > 0
    assert len(EXECUTION_LANES) > 0


def test_adapters_by_category_filters_to_the_requested_category() -> None:
    category = registry.ALL_ADAPTERS[0].category
    result = registry.adapters_by_category(category)
    assert len(result) > 0
    assert all(adapter.category is category for adapter in result)
    # Accepts the string form too.
    assert registry.adapters_by_category(category.value) == result


def test_adapters_by_status_filters_to_the_requested_status() -> None:
    status = registry.ALL_ADAPTERS[0].status
    result = registry.adapters_by_status(status)
    assert all(adapter.status is status for adapter in result)


def test_adapter_for_resolves_a_known_category_venue_pair() -> None:
    sample = registry.ALL_ADAPTERS[0]
    category, venue = sample.key
    assert registry.adapter_for(category, venue) is sample


def test_adapter_for_raises_keyerror_for_an_unknown_venue() -> None:
    category = registry.ALL_ADAPTERS[0].key[0]
    with pytest.raises(KeyError, match="unknown adapter"):
        registry.adapter_for(category, "no-such-venue")


def test_lanes_by_status_filters_to_the_requested_status() -> None:
    status = EXECUTION_LANES[0].status
    result = registry.lanes_by_status(status)
    assert all(lane.status is status for lane in result)


def test_lane_for_resolves_a_known_lane() -> None:
    sample = EXECUTION_LANES[0]
    assert registry.lane_for(sample.key) is sample
    assert registry.lane_for(sample.key.value) is sample
