"""Correlation window for joining disparate strategy signals."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SignalEntry:
    kind: str
    payload: Any
    received_at_ms: int


@dataclass(frozen=True, slots=True)
class SignalPair:
    a: SignalEntry
    b: SignalEntry
    delta_ms: int


class CorrelationWindow:
    """Time-indexed buffer for signal correlation."""

    def __init__(self, max_window_ms: int = 5_000) -> None:
        self._max_window_ms = max_window_ms
        self._buffer: list[SignalEntry] = []

    def record(self, kind: str, payload: Any, now_ms: int | None = None) -> None:
        """Record a new signal arrival."""
        if now_ms is None:
            now_ms = int(time.time() * 1000)

        self._buffer.append(SignalEntry(kind=kind, payload=payload, received_at_ms=now_ms))
        self._prune(now_ms)

    def pairs_across_kinds(
        self,
        kind_a: str,
        kind_b: str,
        window_ms: int,
        now_ms: int | None = None,
    ) -> list[SignalPair]:
        """Find all pairs of (A, B) that occurred within window_ms of each other."""
        if now_ms is None:
            now_ms = int(time.time() * 1000)

        # 1. Extract recent signals of requested kinds
        cutoff = now_ms - window_ms
        signals_a = [s for s in self._buffer if s.kind == kind_a and s.received_at_ms > cutoff]
        signals_b = [s for s in self._buffer if s.kind == kind_b and s.received_at_ms > cutoff]

        pairs: list[SignalPair] = []
        for a in signals_a:
            for b in signals_b:
                delta = abs(a.received_at_ms - b.received_at_ms)
                if delta <= window_ms:
                    pairs.append(SignalPair(a=a, b=b, delta_ms=delta))

        # Sort by arrival of the second signal in the pair (freshest correlation)
        pairs.sort(key=lambda p: max(p.a.received_at_ms, p.b.received_at_ms))
        return pairs

    def _prune(self, now_ms: int) -> None:
        cutoff = now_ms - self._max_window_ms
        self._buffer = [s for s in self._buffer if s.received_at_ms > cutoff]
