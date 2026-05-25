"""Per-solution P&L recorder.

Emits structured logs (structlog) and Prometheus counters for every
auction outcome. The Prometheus surface mirrors the conventions in
spec §4.4: `pnl_wei_total{strategy}`, `opportunities_dispatched_total{...}`.
"""

from __future__ import annotations

from typing import Any

import structlog
from prometheus_client import Counter

# Counters are module-level so they share a single registry across the
# process. `strategy` is always one of {"C", "C+D3"} for this driver.
_PNL_USD_TOTAL = Counter(
    "solver_pnl_usd_total",
    "Cumulative solver P&L in USD by strategy and outcome.",
    labelnames=("strategy", "outcome"),
)
_AUCTIONS_TOTAL = Counter(
    "solver_auctions_total",
    "Auctions observed and processed by the solver driver.",
    labelnames=("strategy", "outcome"),
)


class PnLTracker:
    """Records per-solution outcomes to Prometheus + structlog.

    Stateless wrt persistence — we lean on Prometheus for time series
    storage and structured logs for the audit trail.
    """

    def __init__(self) -> None:
        self._log = structlog.get_logger(__name__).bind(
            service="solver",
            component="driver.pnl",
        )

    def record(self, auction: Any, solution: Any) -> None:  # noqa: ANN401 -- scaffold: typed when Auction/Solution land
        """Record a submitted solution.

        Args:
            auction: The auction we built against (carries id/batch info).
            solution: The Solution we submitted (carries estimated profit).
        """
        # TODO(scaffold): pull strategy label from solution context (C vs C+D3),
        #                 outcome from CoW competition feedback (won/lost/invalid),
        #                 and increment the right counter. For the scaffold we
        #                 just route a structured log line.
        self._log.info(
            "solution_submitted",
            auction_id=getattr(auction, "id", None),
            estimated_profit_usd=getattr(solution, "estimated_profit_usd", None),
        )

    def record_outcome(self, *, strategy: str, outcome: str, profit_usd: float) -> None:
        """Increment Prometheus counters once we know the auction outcome."""
        # TODO(scaffold): bind to the same flow_id as the build/submit log lines.
        _AUCTIONS_TOTAL.labels(strategy=strategy, outcome=outcome).inc()
        _PNL_USD_TOTAL.labels(strategy=strategy, outcome=outcome).inc(profit_usd)
