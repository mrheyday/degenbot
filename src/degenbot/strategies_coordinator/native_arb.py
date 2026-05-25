"""Native arbitrage strategy implementation."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Sequence, TYPE_CHECKING

from degenbot.decision.types import Address, Hex
from degenbot.types_solver.wire import Opportunity, SwapStep as EngineSwapStep
from degenbot.strategies_coordinator.types import (
    FLASH_PROTOCOL,
    DEX_KIND,
    NativeArbParams,
    SwapStep as ContractSwapStep,
)
from degenbot.flash.source_router import resolve_executor_flash_route

if TYPE_CHECKING:
    from degenbot.adapters.config import Settings

logger = logging.getLogger(__name__)

MIN_PROFIT_BPS_OF_ESTIMATE = 9500
BPS_DENOMINATOR = 10000
DEFAULT_DEADLINE_BUFFER_S = 60


@dataclass(frozen=True)
class PreparedNativeArbTx:
    params: NativeArbParams
    direct_tx: dict[str, Any]


class NativeArbStrategy:
    """Native arbitrage strategy."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def build_params(self, opp: Opportunity) -> NativeArbParams:
        """Build NativeArbParams from an engine Opportunity."""
        if opp.flash_amount <= 0:
            raise ValueError("NativeArbStrategy: flashAmount must be > 0")

        recipient = self._settings.executor_address
        min_profit = (opp.estimated_profit_wei * MIN_PROFIT_BPS_OF_ESTIMATE) // BPS_DENOMINATOR
        
        flash_route = resolve_executor_flash_route(
            token=opp.flash_token,
            amount=opp.flash_amount,
            context="NativeArbStrategy",
            aave_v3_pool=self._settings.aave_v3_pool,
            morpho_blue=self._settings.morpho_blue,
        )
        
        deadline = int(time.time()) + DEFAULT_DEADLINE_BUFFER_S
        
        # TODO: Implement full engine-to-contract swap mapping
        swaps = [
            self._map_engine_swap_to_contract(step, recipient, deadline)
            for step in opp.path
        ]

        return NativeArbParams(
            flash_lender=flash_route.lender,
            flash_protocol=flash_route.protocol,
            flash_token=opp.flash_token,
            flash_amount=opp.flash_amount,
            swaps=swaps,
            min_profit=min_profit,
            deadline=deadline,
        )

    def _map_engine_swap_to_contract(
        self, step: EngineSwapStep, recipient: Address, deadline: int
    ) -> ContractSwapStep:
        """Translate one engine SwapStep into a contract SwapStep."""
        # This is a stub. Real implementation needs degenbot_rs or custom encoders.
        return ContractSwapStep(
            dex_kind=DEX_KIND.V2, # Placeholder
            router=step.pool,
            call_data=Hex("0x"),
            token_in=step.token_in,
            token_out=step.token_out,
            amount_in=step.amount_in,
            amount_out_min=step.amount_out_min,
        )
