"""Category-level adapter registry."""

from __future__ import annotations

from types import MappingProxyType

from degenbot.adapters.flashadapters import FLASH_ADAPTERS
from degenbot.adapters.laneadapters import EXECUTION_LANES
from degenbot.adapters.liquidityadapters import LIQUIDITY_ADAPTERS
from degenbot.adapters.swapadapters import SWAP_ADAPTERS
from degenbot.adapters.templates import (
    AdapterCategory,
    AdapterStatus,
    AdapterTemplate,
    ExecutionLane,
    ExecutionLaneTemplate,
)

ALL_ADAPTERS: tuple[AdapterTemplate, ...] = (
    *SWAP_ADAPTERS,
    *FLASH_ADAPTERS,
    *LIQUIDITY_ADAPTERS,
)

_ADAPTERS_BY_KEY = MappingProxyType({adapter.key: adapter for adapter in ALL_ADAPTERS})
_LANES_BY_KEY = MappingProxyType({lane.key: lane for lane in EXECUTION_LANES})


def adapters_by_category(category: AdapterCategory | str) -> tuple[AdapterTemplate, ...]:
    """Return adapters for a category."""
    normalized = AdapterCategory(category)
    return tuple(adapter for adapter in ALL_ADAPTERS if adapter.category is normalized)


def adapters_by_status(status: AdapterStatus | str) -> tuple[AdapterTemplate, ...]:
    """Return adapters with a given status."""
    normalized = AdapterStatus(status)
    return tuple(adapter for adapter in ALL_ADAPTERS if adapter.status is normalized)


def adapter_for(category: AdapterCategory | str, venue: str) -> AdapterTemplate:
    """Return a single adapter by `(category, venue)`."""
    key = (AdapterCategory(category), venue)
    try:
        return _ADAPTERS_BY_KEY[key]
    except KeyError as exc:
        msg = f"unknown adapter {key[0].value}:{venue}"
        raise KeyError(msg) from exc


def lanes_by_status(status: AdapterStatus | str) -> tuple[ExecutionLaneTemplate, ...]:
    """Return execution lanes with a given operational status."""
    normalized = AdapterStatus(status)
    return tuple(lane for lane in EXECUTION_LANES if lane.status is normalized)


def lane_for(lane: ExecutionLane | str) -> ExecutionLaneTemplate:
    """Return a single execution lane."""
    key = ExecutionLane(lane)
    try:
        return _LANES_BY_KEY[key]
    except KeyError as exc:
        msg = f"unknown execution lane {key.value}"
        raise KeyError(msg) from exc
