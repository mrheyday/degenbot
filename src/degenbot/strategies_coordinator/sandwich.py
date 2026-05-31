"""Traditional sandwich strategy (Pick S).

Algorithm reference: docs/research/2026-05-11-sandwich-primitive-epic.md
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from degenbot.decision.types import Address, Hex
from degenbot.flash.source_router import resolve_executor_flash_route
from degenbot.matching.sandwich_math import solve_v2_sandwich
from degenbot.strategies_coordinator.types import (
    DEX_KIND,
    DexKind,
    NativeArbParams,
    SwapStep,
)

if TYPE_CHECKING:
    from degenbot.adapters.config import Settings
    from degenbot.types_solver.wire import Opportunity

logger = logging.getLogger(__name__)

# Min profit buffer (95% of estimate)
MIN_PROFIT_BPS_OF_ESTIMATE = 9500
BPS_DENOMINATOR = 10000


@dataclass(frozen=True)
class SandwichPlan:
    opportunity_id: str
    frontrun_size_wei: int
    backrun_out_wei: int
    expected_profit_wei: int
    flash_token: Address
    pool_address: Address
    pool_kind: str
    token_in: Address
    token_out: Address
    router: Address


class SandwichStrategy:
    """Traditional offensive sandwich strategy."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def preflight(self, opp: Opportunity) -> SandwichPlan | None:
        """Validate and size a traditional sandwich."""
        # Traditional sandwiching expects a 'victim_tx' signal.
        # For now we assume the enrichment contains victim swap details.

        enrichment = opp.enrichment or {}
        victim = enrichment.get("victim_tx")
        if not victim:
            return None

        pool_state = enrichment.get("pool_state")
        if not pool_state or pool_state["kind"] != "UniswapV2":
            # Traditional sandwiching currently focuses on V2 pools.
            # V3 uses numerical search (sizing-v3.ts).
            return None

        # 1. Unpack reserves
        # token_in is what the victim sells (and we frontrun by selling the same)
        token_in = victim["token_in"]
        token_out = victim["token_out"]

        r_in = (
            pool_state["reserve0"]
            if pool_state["token0"].lower() == token_in.lower()
            else pool_state["reserve1"]
        )
        r_out = (
            pool_state["reserve1"]
            if pool_state["token0"].lower() == token_in.lower()
            else pool_state["reserve0"]
        )

        if r_in == 0 or r_out == 0:
            return None

        # 2. Compute optimal sandwich
        solution = solve_v2_sandwich(
            victim_amount_in=victim["amount_in"],
            victim_min_out=victim["amount_out_min"],
            reserve_in=r_in,
            reserve_out=r_out,
            fee_bps=pool_state.get("fee_bps", 30),
        )

        if solution.net_token_in_wei <= 0:
            return None

        return SandwichPlan(
            opportunity_id=opp.id,
            frontrun_size_wei=solution.frontrun_size_wei,
            backrun_out_wei=solution.backrun_out_wei,
            expected_profit_wei=solution.net_token_in_wei,
            flash_token=token_in,
            pool_address=opp.pool_addresses[0],
            pool_kind=pool_state["kind"],
            token_in=token_in,
            token_out=token_out,
            router=pool_state["router"],
        )

    def build_params(self, plan: SandwichPlan) -> NativeArbParams:
        """Convert a SandwichPlan into NativeArbParams (Round-Trip)."""

        flash_route = resolve_executor_flash_route(
            token=plan.flash_token,
            amount=plan.frontrun_size_wei,
            context="SandwichStrategy",
            aave_v3_pool=self._settings.aave_v3_pool,
            morpho_blue=self._settings.morpho_blue,
        )

        min_profit = (plan.expected_profit_wei * MIN_PROFIT_BPS_OF_ESTIMATE) // BPS_DENOMINATOR
        deadline = int(time.time()) + 60

        # Round-trip swaps: sold -> bought -> sold
        swaps = [
            SwapStep(
                dex_kind=cast("DexKind", DEX_KIND.V2),
                router=plan.router,
                call_data=Hex("0x"),
                token_in=plan.token_in,
                token_out=plan.token_out,
                amount_in=plan.frontrun_size_wei,
                amount_out_min=0,
            ),
            SwapStep(
                dex_kind=cast("DexKind", DEX_KIND.V2),
                router=plan.router,
                call_data=Hex("0x"),
                token_in=plan.token_out,
                token_out=plan.token_in,
                amount_in=0,  # carry-over
                amount_out_min=0,
            ),
        ]

        return NativeArbParams(
            flash_lender=flash_route.lender,
            flash_protocol=flash_route.protocol,
            flash_token=plan.flash_token,
            flash_amount=plan.frontrun_size_wei,
            swaps=swaps,
            min_profit=min_profit,
            deadline=deadline,
        )

    def simulate(self, simulator: Any, params: NativeArbParams) -> bool:
        """Simulate the sandwich transaction using REVM."""
        from degenbot.simulation import encode_native_arb_params, simulate_executor_call

        # Atomic sandwich simulation (FR + BR in one tx)
        # Note: the victim's presence in the same block is implied by the signal context.
        # In a real dry-run, we should ideally bundle them.
        result = simulate_executor_call(
            simulator=simulator,
            settings=self._settings,
            calldata=encode_native_arb_params(params),
        )
        return result.success
