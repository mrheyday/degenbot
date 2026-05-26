"""Oracle sandwich strategy (S-5).

Algorithm reference: docs/architecture/03-LOCKED-STRATEGIES.md#s-5
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from eth_abi import encode as abi_encode
from eth_utils.crypto import keccak

from degenbot.decision.types import Address, Hex
from degenbot.flash.source_router import resolve_executor_flash_route
from degenbot.strategies_coordinator.oracle_sandwich_math import (
    estimate_oracle_sandwich_profit,
    v3_virtual_reserves,
)
from degenbot.strategies_coordinator.types import (
    DEX_KIND,
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
DEFAULT_DEADLINE_BUFFER_S = 60
V2_SWAP_EXACT_TOKENS_FOR_TOKENS = (
    "swapExactTokensForTokens(uint256,uint256,address[],address,uint256)"
)
V3_EXACT_INPUT_SINGLE = (
    "exactInputSingle((address,address,uint24,address,uint256,uint256,uint256,uint160))"
)


@dataclass(frozen=True)
class OracleSandwichPlan:
    opportunity_id: str
    frontrun_size_wei: int
    backrun_size_wei: int
    expected_profit_wei: int
    flash_token: Address
    pool_address: Address
    pool_kind: str
    token_sold: Address
    token_bought: Address
    router: Address
    v3_fee_tier: int | None = None
    frontrun_call_data: Hex | None = None
    backrun_call_data: Hex | None = None


class OracleSandwichStrategy:
    """S-5 Oracle-update sandwich strategy."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def preflight(self, opp: Opportunity) -> OracleSandwichPlan | None:
        """Validate and size the oracle sandwich."""
        enrichment = opp.enrichment or {}
        gap = enrichment.get("ostium_gap")
        pool_state = enrichment.get("pool_state")
        if not gap or not pool_state or not opp.pool_addresses:
            return None

        token_sold = gap.get("token_sold")
        token_bought = gap.get("token_bought")
        if not token_sold or not token_bought:
            return None

        reserve_in, reserve_out = self._align_reserves(pool_state, token_sold)
        if reserve_in == 0 or reserve_out == 0:
            return None

        estimate = estimate_oracle_sandwich_profit(
            gap_bps=gap["gap_bps"],
            pool_address=opp.pool_addresses[0],
            reserve_in=reserve_in,
            reserve_out=reserve_out,
            fee_bps=pool_state.get("fee_bps", 30),
            gas_cost_wei=self._settings.estimated_gas_cost_wei,
        )

        if estimate.expected_profit_wei <= 0:
            return None

        pool_kind = str(pool_state.get("kind", ""))
        if pool_kind not in {"UniswapV2", "UniswapV3", "UniswapV4"}:
            return None

        router = pool_state.get("router")
        frontrun_call_data = pool_state.get("frontrun_call_data") or pool_state.get(
            "frontrunCallData"
        )
        backrun_call_data = pool_state.get("backrun_call_data") or pool_state.get("backrunCallData")
        if pool_kind == "UniswapV3" and pool_state.get("v3_fee_tier") is None:
            return None
        if pool_kind == "UniswapV4":
            router = (
                pool_state.get("universal_router") or pool_state.get("universalRouter") or router
            )
            if not frontrun_call_data or not backrun_call_data:
                return None
        if not router:
            return None

        return OracleSandwichPlan(
            opportunity_id=opp.id,
            frontrun_size_wei=estimate.frontrun_size_wei,
            backrun_size_wei=estimate.backrun_size_wei,
            expected_profit_wei=estimate.expected_profit_wei,
            flash_token=token_sold,
            pool_address=opp.pool_addresses[0],
            pool_kind=pool_state["kind"],
            token_sold=token_sold,
            token_bought=token_bought,
            router=router,
            v3_fee_tier=pool_state.get("v3_fee_tier"),
            frontrun_call_data=frontrun_call_data,
            backrun_call_data=backrun_call_data,
        )

    def build_params(self, plan: OracleSandwichPlan) -> NativeArbParams:
        """Convert an OracleSandwichPlan into NativeArbParams."""
        flash_route = resolve_executor_flash_route(
            token=plan.flash_token,
            amount=plan.frontrun_size_wei,
            context="OracleSandwichStrategy",
            aave_v3_pool=self._settings.aave_v3_pool,
            morpho_blue=self._settings.morpho_blue,
        )

        min_profit = (plan.expected_profit_wei * MIN_PROFIT_BPS_OF_ESTIMATE) // BPS_DENOMINATOR
        deadline = int(time.time()) + DEFAULT_DEADLINE_BUFFER_S

        frontrun_call_data = self._build_leg_call_data(plan, deadline, backrun=False)
        backrun_call_data = self._build_leg_call_data(plan, deadline, backrun=True)
        dex_kind = self._kind_to_dex_kind(plan.pool_kind)
        swaps = [
            SwapStep(
                dex_kind=dex_kind,
                router=plan.router,
                call_data=frontrun_call_data,
                token_in=plan.token_sold,
                token_out=plan.token_bought,
                amount_in=plan.frontrun_size_wei,
                amount_out_min=0,
            ),
            SwapStep(
                dex_kind=dex_kind,
                router=plan.router,
                call_data=backrun_call_data,
                token_in=plan.token_bought,
                token_out=plan.token_sold,
                amount_in=0,
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

    def _align_reserves(self, state: dict[str, Any], token_sold: Address) -> tuple[int, int]:
        if state["kind"] == "UniswapV2":
            r0, r1 = state["reserve0"], state["reserve1"]
            return (r0, r1) if state["token0"].lower() == token_sold.lower() else (r1, r0)

        if state["kind"] in {"UniswapV3", "UniswapV4"}:
            r0, r1 = v3_virtual_reserves(state["sqrt_price_x96"], state["liquidity"])
            return (r0, r1) if state["token0"].lower() == token_sold.lower() else (r1, r0)

        return 0, 0

    def _build_leg_call_data(
        self, plan: OracleSandwichPlan, deadline: int, *, backrun: bool
    ) -> Hex:
        token_in = plan.token_bought if backrun else plan.token_sold
        token_out = plan.token_sold if backrun else plan.token_bought
        amount_in = plan.backrun_size_wei if backrun else plan.frontrun_size_wei

        if backrun and plan.backrun_call_data:
            return plan.backrun_call_data
        if not backrun and plan.frontrun_call_data:
            return plan.frontrun_call_data
        if plan.pool_kind == "UniswapV2":
            return _encode_v2_swap_exact_tokens_for_tokens(
                amount_in=amount_in,
                token_in=token_in,
                token_out=token_out,
                recipient=self._settings.executor_address,
                deadline=deadline,
            )
        if plan.pool_kind == "UniswapV3":
            if plan.v3_fee_tier is None:
                msg = "OracleSandwichStrategy: v3_fee_tier required for V3 call encoding"
                raise ValueError(msg)
            return _encode_v3_exact_input_single(
                amount_in=amount_in,
                token_in=token_in,
                token_out=token_out,
                fee_tier=plan.v3_fee_tier,
                recipient=self._settings.executor_address,
                deadline=deadline,
            )
        msg = "OracleSandwichStrategy: V4 requires prebuilt Universal Router calldata"
        raise ValueError(msg)

    def _kind_to_dex_kind(self, kind: str) -> int:
        if kind in {"UniswapV2", "UniswapV3", "UniswapV4"}:
            return DEX_KIND.V2
        return DEX_KIND.V2


def _encode_v2_swap_exact_tokens_for_tokens(
    *,
    amount_in: int,
    token_in: Address,
    token_out: Address,
    recipient: Address,
    deadline: int,
) -> Hex:
    selector = keccak(text=V2_SWAP_EXACT_TOKENS_FOR_TOKENS)[:4]
    args = abi_encode(
        ["uint256", "uint256", "address[]", "address", "uint256"],
        [amount_in, 0, [token_in, token_out], recipient, deadline],
    )
    return Hex(f"0x{(selector + args).hex()}")


def _encode_v3_exact_input_single(
    *,
    amount_in: int,
    token_in: Address,
    token_out: Address,
    fee_tier: int,
    recipient: Address,
    deadline: int,
) -> Hex:
    selector = keccak(text=V3_EXACT_INPUT_SINGLE)[:4]
    args = abi_encode(
        ["(address,address,uint24,address,uint256,uint256,uint256,uint160)"],
        [(token_in, token_out, fee_tier, recipient, deadline, amount_in, 0, 0)],
    )
    return Hex(f"0x{(selector + args).hex()}")
