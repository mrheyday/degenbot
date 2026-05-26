"""Lightweight signal bus for strategy coordination."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)

T = TypeVar("T")


class SignalBus:
    """Async signal bus for inter-strategy communication."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[[Any], Awaitable[None]]]] = {}

    def on(self, kind: str, handler: Callable[[Any], Awaitable[None]]) -> Callable[[], None]:
        """Register an async handler for a signal kind."""
        if kind not in self._handlers:
            self._handlers[kind] = []
        self._handlers[kind].append(handler)

        def unsubscribe() -> None:
            if kind in self._handlers:
                self._handlers[kind].remove(handler)

        return unsubscribe

    async def emit(self, kind: str, payload: Any) -> None:
        """Emit a signal to all registered handlers."""
        if kind not in self._handlers:
            return

        # Execute all handlers concurrently
        tasks = [h(payload) for h in self._handlers[kind]]
        await asyncio.gather(*tasks, return_exceptions=True)
