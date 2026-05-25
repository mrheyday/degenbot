"""Compatibility module for the CoW orderbook HTTP client."""

from degenbot.cow.client import (
    DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT_SEC,
    OrderbookClient,
    OrderbookError,
)

__all__ = ["DEFAULT_BASE_URL", "DEFAULT_TIMEOUT_SEC", "OrderbookClient", "OrderbookError"]
