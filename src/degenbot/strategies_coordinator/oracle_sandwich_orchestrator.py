"""Oracle update sandwich orchestrator (S-5).

Correlates 'ostium_oracle_gap' with 'sequencer_feed_tx' to confirm triggers.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from degenbot.strategies_coordinator.oracle_sandwich import (
    OracleSandwichStrategy,
)
from degenbot.strategy_signals.correlation import CorrelationWindow

if TYPE_CHECKING:
    from degenbot.adapters.config import Settings
    from degenbot.strategy_signals.bus import SignalBus

logger = logging.getLogger(__name__)


class OracleSandwichOrchestrator:
    """Orchestrator for the S-5 oracle-update sandwich strategy."""

    def __init__(
        self,
        settings: Settings,
        bus: SignalBus,
        correlation_window: CorrelationWindow | None = None,
    ) -> None:
        self._settings = settings
        self._bus = bus
        self._correlation_window = correlation_window or CorrelationWindow(max_window_ms=5_000)
        self._strategy = OracleSandwichStrategy(settings)
        self._unsubs: list[Any] = []

    def start(self) -> None:
        """Subscribe to the signal bus."""
        self._unsubs.append(self._bus.on("ostium_oracle_gap", self.handle_gap))
        self._unsubs.append(self._bus.on("sequencer_feed_tx", self.handle_tx))

    def stop(self) -> None:
        """Unsubscribe from the signal bus."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    async def handle_gap(self, payload: Any) -> None:
        """Handle a new oracle gap signal."""
        self._correlation_window.record("ostium_oracle_gap", payload)
        await self._handle_correlation()

    async def handle_tx(self, payload: Any) -> None:
        """Handle a new sequencer feed transaction signal."""
        self._correlation_window.record("sequencer_feed_tx", payload)
        await self._handle_correlation()

    async def _handle_correlation(self) -> None:
        """Join gaps and txs within the correlation window."""
        if not self._settings.strategy_oracle_sandwich_enabled:
            return

        pairs = self._correlation_window.pairs_across_kinds(
            "ostium_oracle_gap",
            "sequencer_feed_tx",
            window_ms=200,  # Correlation window from TS
        )
        if not pairs:
            return

        # Use the freshest correlation
        pair = pairs[-1]
        _gap = pair.a.payload
        _sequencer_tx = pair.b.payload

        # In Python, we don't have a direct 'Opportunity' for this yet.
        # We need to construct one or use the strategy directly.
        # For parity with the TS coordinator, we'll build the plan here.

        # 1. TODO: Resolve symbol -> Pool (using a resolver)
        # For now, we expect the pool address in the gap signal or
        # use a hardcoded mapping.

        # 2. TODO: Read live reserves via Stylus.

        # 3. Build plan and dispatch
        # This part requires more plumbing (resolver, reader) which
        # is currently mocked in the tests.
