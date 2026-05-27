"""Native arbitrage strategy implementation."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from degenbot.decision.types import Address, Hex
from degenbot.flash.source_router import resolve_executor_flash_route
from degenbot.strategies_coordinator.types import (
    NativeArbParams,
)
from degenbot.strategies_coordinator.types import (
    SwapStep as ContractSwapStep,
)

if TYPE_CHECKING:
    from degenbot.adapters.config import Settings
    from degenbot.strategies_coordinator.types import DexKind
    from degenbot.types_solver.wire import EngineSwapStep, Opportunity

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
            msg = "NativeArbStrategy: flashAmount must be > 0"
            raise ValueError(msg)

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

        swaps = [self._map_engine_swap_to_contract(step, recipient, deadline) for step in opp.path]

        return NativeArbParams(
            flash_lender=flash_route.lender,
            flash_protocol=flash_route.protocol,
            flash_token=opp.flash_token,
            flash_amount=opp.flash_amount,
            swaps=swaps,
            min_profit=min_profit,
            deadline=deadline,
        )

    def simulate(self, simulator: Any, params: NativeArbParams) -> bool:
        """Simulate the arbitrage transaction using REVM."""
        from degenbot.simulation import encode_native_arb_params, simulate_executor_call

        result = simulate_executor_call(
            simulator=simulator,
            settings=self._settings,
            calldata=encode_native_arb_params(params),
        )
        return result.success

    def _map_engine_swap_to_contract(
        self, step: EngineSwapStep, recipient: Address, deadline: int
    ) -> ContractSwapStep:
        """Translate one engine SwapStep into a contract SwapStep."""
        from degenbot.strategies_coordinator.types import DEX_KIND

        _ = recipient, deadline
        dex_map = {
            "UniswapV2": DEX_KIND.V2,
            "UniswapV3": DEX_KIND.V3,
            "UniswapV4": DEX_KIND.V4,
            "Curve": DEX_KIND.CURVE,
            "CurveNG": DEX_KIND.CURVE_NG,
            "Aerodrome": DEX_KIND.SOLIDLY,
            "Solidly": DEX_KIND.SOLIDLY,
            "Algebra": DEX_KIND.ALGEBRA,
            "MaverickV2": DEX_KIND.MAVERICK_V2,
            "DodoPmm": DEX_KIND.DODO_PMM,
            "FluidDex": DEX_KIND.FLUID_DEX,
            "KyberElastic": DEX_KIND.KYBER_ELASTIC,
            "LFJLiquidityBook": DEX_KIND.LFJ_LIQUIDITY_BOOK,
            "GMXV2": DEX_KIND.GMX_V2,
            "Native": DEX_KIND.NATIVE,
        }
        raw_dex_kind = getattr(step, "dex_kind", None)
        if raw_dex_kind is not None:
            dex_kind = cast("DexKind", int(raw_dex_kind))
        else:
            raw_dex = getattr(step, "dex", None)
            if raw_dex not in dex_map:
                msg = f"NativeArbStrategy: unsupported swap dex kind {raw_dex!r}"
                raise ValueError(msg)
            dex_kind = cast("DexKind", dex_map[raw_dex])

        router = getattr(step, "pool", None) or getattr(step, "router", None)
        if not router:
            msg = "NativeArbStrategy: swap step missing pool/router"
            raise ValueError(msg)

        return ContractSwapStep(
            dex_kind=dex_kind,
            router=router,
            call_data=getattr(step, "call_data", None) or Hex("0x"),
            token_in=step.token_in,
            token_out=step.token_out,
            amount_in=step.amount_in,
            amount_out_min=step.amount_out_min,
        )
