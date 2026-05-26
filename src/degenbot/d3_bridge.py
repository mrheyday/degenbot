"""Compatibility import for the D3 classifier bridge."""

from degenbot.strategies_solver.d3_bridge import (
    D3ClassifyRequest,
    D3ClassifyResponse,
    D3OrderRef,
    handle_d3_classify_payload,
)

__all__ = [
    "D3ClassifyRequest",
    "D3ClassifyResponse",
    "D3OrderRef",
    "handle_d3_classify_payload",
]
