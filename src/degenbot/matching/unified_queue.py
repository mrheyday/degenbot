"""Unified queue — Q_outbound, Q_inbound, Q_uniswapx, Q_native.

Algorithm reference: docs/architecture/06-OFFCHAIN-SERVICES-SPEC.md §2.2 / §2.3.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar, cast

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from degenbot.decision.types import MatchCandidate
    from degenbot.types_solver.wire import Opportunity

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class QueueItem[T]:
    value: T
    enqueued_at_ms: int
    expires_at_ms: int


class UnifiedQueue:
    """Mutex-protected unified queue for internal matching."""

    def __init__(
        self,
        default_candidate_ttl_ms: int = 30_000,
        default_native_ttl_ms: int = 5_000,
    ) -> None:
        self._outbound_q: list[QueueItem[MatchCandidate]] = []
        self._inbound_q: list[QueueItem[MatchCandidate]] = []
        self._uniswapx_q: list[QueueItem[MatchCandidate]] = []
        self._native_q: list[QueueItem[Opportunity]] = []

        self._default_candidate_ttl_ms = default_candidate_ttl_ms
        self._default_native_ttl_ms = default_native_ttl_ms
        self._lock = asyncio.Lock()

    # -- Add* ------------------------------------------------------------------

    async def add_outbound(self, o: MatchCandidate) -> None:
        async with self._lock:
            self._outbound_q.append(self._wrap_candidate(o))

    async def add_inbound(self, c: MatchCandidate) -> None:
        async with self._lock:
            self._inbound_q.append(self._wrap_candidate(c))

    async def add_uniswapx(self, c: MatchCandidate) -> None:
        async with self._lock:
            self._uniswapx_q.append(self._wrap_candidate(c))

    async def add_native(self, opp: Opportunity) -> None:
        async with self._lock:
            now = int(time.time() * 1000)
            self._native_q.append(
                QueueItem(
                    value=opp,
                    enqueued_at_ms=now,
                    expires_at_ms=now + self._default_native_ttl_ms,
                )
            )

    # -- Consume / removal -----------------------------------------------------

    async def consume(self, item: MatchCandidate) -> bool:
        """Remove a candidate by id from whichever queue holds it."""
        async with self._lock:
            for q in [self._outbound_q, self._inbound_q, self._uniswapx_q]:
                for i, entry in enumerate(q):
                    if entry.value.id == item.id:
                        q.pop(i)
                        return True
            return False

    async def consume_native(self, opp: Opportunity) -> bool:
        """Drop a native opportunity by id."""
        async with self._lock:
            for i, entry in enumerate(self._native_q):
                if entry.value.id == opp.id:
                    self._native_q.pop(i)
                    return True
            return False

    async def sweep_expired(self, now_ms: int | None = None) -> int:
        """Sweep expired items across all four queues."""
        if now_ms is None:
            now_ms = int(time.time() * 1000)

        async with self._lock:
            removed = 0
            for q in (self._outbound_q, self._inbound_q, self._uniswapx_q):
                new_q = [entry for entry in q if entry.expires_at_ms > now_ms]
                removed += len(q) - len(new_q)
                q[:] = new_q
            native_q = cast("list[QueueItem[Any]]", self._native_q)
            new_native_q = [entry for entry in native_q if entry.expires_at_ms > now_ms]
            removed += len(native_q) - len(new_native_q)
            native_q[:] = new_native_q
            return removed

    # -- Snapshots / iteration -------------------------------------------------

    @property
    def outbound(self) -> Sequence[MatchCandidate]:
        return [e.value for e in self._outbound_q]

    @property
    def inbound(self) -> Sequence[MatchCandidate]:
        return [e.value for e in self._inbound_q]

    @property
    def uniswapx(self) -> Sequence[MatchCandidate]:
        return [e.value for e in self._uniswapx_q]

    @property
    def native(self) -> Sequence[Opportunity]:
        return [e.value for e in self._native_q]

    def size(self, name: str | None = None) -> int:
        if name == "outbound":
            return len(self._outbound_q)
        if name == "inbound":
            return len(self._inbound_q)
        if name == "uniswapx":
            return len(self._uniswapx_q)
        if name == "native":
            return len(self._native_q)
        return (
            len(self._outbound_q)
            + len(self._inbound_q)
            + len(self._uniswapx_q)
            + len(self._native_q)
        )

    def __iter__(self) -> Iterator[MatchCandidate]:
        """Iterate matchable candidates (outbound + inbound + uniswapx)."""
        # Note: this returns a snapshot of values
        outbound = [e.value for e in self._outbound_q]
        inbound = [e.value for e in self._inbound_q]
        uniswapx = [e.value for e in self._uniswapx_q]
        return iter(outbound + inbound + uniswapx)

    # -- Internals -------------------------------------------------------------

    def _wrap_candidate(self, c: MatchCandidate) -> QueueItem[MatchCandidate]:
        now = int(time.time() * 1000)
        source_expiry_ms = c.source_expires_at * 1000
        ttl_expiry_ms = now + self._default_candidate_ttl_ms
        expires_at_ms = source_expiry_ms if 0 < source_expiry_ms < ttl_expiry_ms else ttl_expiry_ms
        return QueueItem(value=c, enqueued_at_ms=now, expires_at_ms=expires_at_ms)
