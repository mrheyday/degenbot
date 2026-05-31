"""Regression tests for production-readiness blockers found in review."""

from __future__ import annotations

from degenbot.decision.precedence import compare_priority
from degenbot.decision.types import DecisionRoute
from degenbot.flash.source_router import FlashRouteCandidate, resolve_executor_flash_route
from degenbot.strategies_coordinator.types import FLASH_PROTOCOL

_WETH = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"


def test_sandwich_decision_route_is_a_first_class_kind() -> None:
    route = DecisionRoute(kind="sandwich", opportunityId="opp-1")

    assert route.kind == "sandwich"
    assert compare_priority("oracle_sandwich", "sandwich") < 0
    assert compare_priority("sandwich", "native_arb") > 0


def test_flash_route_wrap_defaults_do_not_crash_when_units_omitted() -> None:
    route = resolve_executor_flash_route(
        token=_WETH,
        amount=1_000_000,
        candidates=[
            FlashRouteCandidate(
                protocol=FLASH_PROTOCOL.AAVE_V3,
                wrap_native=True,
                unwrap_native=True,
                gas_price_wei=2,
            )
        ],
    )

    assert route.wrapping_cost_wei == (30_000 + 35_000) * 2
    assert route.total_cost_in_borrow_token >= route.wrapping_cost_wei
