"""Prometheus metrics for the CoW solver driver."""

from __future__ import annotations

from prometheus_client import Counter, Histogram

# -- Solver Engine (/solve) --------------------------------------------------
SOLVE_REQUESTS = Counter(
    "solver_solve_requests_total",
    "Number of /solve requests received, labelled by outcome.",
    ("outcome",),
)
SOLVE_LATENCY = Histogram(
    "solver_solve_latency_seconds",
    "Wall-clock latency of /solve handler.",
)

# -- Competition Submission (Push) -------------------------------------------
SUBMISSION_REQUESTS = Counter(
    "solver_submission_requests_total",
    "Number of competition submission attempts, labelled by outcome.",
    ("outcome",),
)
SUBMISSION_LATENCY = Histogram(
    "solver_submission_latency_seconds",
    "Wall-clock latency of competition submission POST.",
)
