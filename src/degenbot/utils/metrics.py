"""Prometheus metrics for the CoW solver driver."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from prometheus_client import REGISTRY, Counter, Histogram

if TYPE_CHECKING:
    from collections.abc import Callable


def _collector(name: str, factory: Callable[[], Any]) -> Any:
    names_to_collectors = getattr(REGISTRY, "_names_to_collectors", {})
    existing = names_to_collectors.get(name.removesuffix("_total")) or names_to_collectors.get(name)
    if existing is not None:
        return existing
    return factory()


# -- Solver Engine (/solve) --------------------------------------------------
SOLVE_REQUESTS = _collector(
    "solver_solve_requests_total",
    lambda: Counter(
        "solver_solve_requests_total",
        "Number of /solve requests received, labelled by outcome.",
        ("outcome",),
    ),
)
SOLVE_LATENCY = _collector(
    "solver_solve_latency_seconds",
    lambda: Histogram(
        "solver_solve_latency_seconds",
        "Wall-clock latency of /solve handler.",
    ),
)

# -- Competition Submission (Push) -------------------------------------------
SUBMISSION_REQUESTS = _collector(
    "solver_submission_requests_total",
    lambda: Counter(
        "solver_submission_requests_total",
        "Number of competition submission attempts, labelled by outcome.",
        ("outcome",),
    ),
)
SUBMISSION_LATENCY = _collector(
    "solver_submission_latency_seconds",
    lambda: Histogram(
        "solver_submission_latency_seconds",
        "Wall-clock latency of competition submission POST.",
    ),
)
