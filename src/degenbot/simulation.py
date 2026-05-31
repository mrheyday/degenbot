"""REVM-backed simulation for the Python solver.

The strategy layer uses this module only for exact, same-calldata preflight
checks. It deliberately stays thin: calldata construction remains owned by the
executor encoders, while REVM execution is delegated to the Rust extension.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence

    from degenbot.adapters.config import Settings

ZERO_ADDRESS = "0x" + "0" * 40


class SwapStepLike(Protocol):
    """Structural type for Executor swap-step mirrors."""

    @property
    def dex_kind(self) -> Any: ...

    @property
    def router(self) -> Any: ...

    @property
    def call_data(self) -> Any: ...

    @property
    def token_in(self) -> Any: ...

    @property
    def token_out(self) -> Any: ...

    @property
    def amount_in(self) -> Any: ...

    @property
    def amount_out_min(self) -> Any: ...


class NativeArbParamsLike(Protocol):
    """Structural type for `executeNativeArb` mirrors."""

    @property
    def flash_lender(self) -> Any: ...

    @property
    def flash_protocol(self) -> Any: ...

    @property
    def flash_token(self) -> Any: ...

    @property
    def flash_amount(self) -> Any: ...

    @property
    def swaps(self) -> Sequence[SwapStepLike]: ...

    @property
    def min_profit(self) -> Any: ...

    @property
    def deadline(self) -> Any: ...


class MatchParamsLike(Protocol):
    """Structural type for `matchInternal` mirrors."""

    @property
    def cow_settlement_calldata(self) -> Any: ...

    @property
    def uniswapx_batch_calldata(self) -> Any: ...

    @property
    def expected_token_inflows(self) -> Sequence[Any]: ...

    @property
    def expected_token_inflow_min(self) -> Sequence[Any]: ...

    @property
    def flash_lender(self) -> Any: ...

    @property
    def flash_protocol(self) -> Any: ...

    @property
    def flash_token(self) -> Any: ...

    @property
    def flash_amount(self) -> Any: ...

    @property
    def min_profit(self) -> Any: ...

    @property
    def deadline(self) -> Any: ...


class ComposeParamsLike(Protocol):
    """Structural type for `composeFourLeg` mirrors."""

    @property
    def across_fill_calldata(self) -> Any: ...

    @property
    def arb_swaps(self) -> Sequence[SwapStepLike]: ...

    @property
    def cow_fill_calldata(self) -> Any: ...

    @property
    def uniswapx_rebalance_calldata(self) -> Any: ...

    @property
    def flash_lender(self) -> Any: ...

    @property
    def flash_protocol(self) -> Any: ...

    @property
    def flash_token(self) -> Any: ...

    @property
    def flash_amount(self) -> Any: ...

    @property
    def min_profit(self) -> Any: ...

    @property
    def deadline(self) -> Any: ...


@dataclass(frozen=True, slots=True)
class SimulationResult:
    """Result of a REVM simulation."""

    success: bool
    output: bytes
    revert_reason: str | None = None


class Simulator:
    """Pythonic wrapper around the Rust RevmDb extension."""

    def __init__(self, rpc_url: str, seed_pools: Sequence[str] | None = None) -> None:
        from degenbot.degenbot_rs import RevmDb

        self._db = RevmDb(rpc_url, list(seed_pools) if seed_pools else None)

    def call(
        self,
        from_addr: str,
        to_addr: str,
        calldata: bytes,
        value: int = 0,
    ) -> SimulationResult:
        """Execute a call against the warm cache."""
        try:
            output = self._db.call(from_addr, to_addr, calldata, value)
            return SimulationResult(success=True, output=output)
        except RuntimeError as e:
            return SimulationResult(success=False, output=b"", revert_reason=str(e))


def parse_seed_pools(raw: str | Sequence[str] | None) -> tuple[str, ...]:
    """Normalize configured seed-pool addresses."""
    if raw is None:
        return ()
    if isinstance(raw, str):
        return tuple(part.strip() for part in raw.split(",") if part.strip())
    return tuple(str(part).strip() for part in raw if str(part).strip())


def is_zero_address(value: str | None) -> bool:
    """Return true when `value` is unset or the all-zero EVM address."""
    if not value:
        return True
    return value.lower() == ZERO_ADDRESS


def resolve_simulation_sender(settings: Settings) -> str:
    """Resolve the caller used for REVM `eth_call`-style strategy checks."""
    for attr in (
        "revm_simulation_from_address",
        "executor_delegatee_address",
        "delegatee_address",
        "cow_solver_address",
    ):
        value = getattr(settings, attr, None)
        if isinstance(value, str) and not is_zero_address(value):
            return value

    delegatees_initial = getattr(settings, "delegatees_initial", None)
    if delegatees_initial:
        for value in str(delegatees_initial).split(","):
            candidate = value.strip()
            if not is_zero_address(candidate):
                return candidate

    executor = getattr(settings, "executor_address", None)
    if isinstance(executor, str) and not is_zero_address(executor):
        return executor

    msg = "REVM simulation requires a configured caller or non-zero executor address"
    raise ValueError(msg)


def simulate_executor_call(
    simulator: Simulator,
    settings: Settings,
    calldata: bytes,
    *,
    to_addr: str | None = None,
    value: int = 0,
) -> SimulationResult:
    """Simulate an exact executor calldata payload."""
    target = to_addr or getattr(settings, "executor_address", None)
    if is_zero_address(str(target) if target else None):
        return SimulationResult(
            success=False,
            output=b"",
            revert_reason="REVM simulation target address is unset",
        )
    return simulator.call(
        from_addr=resolve_simulation_sender(settings),
        to_addr=str(target),
        calldata=calldata,
        value=value,
    )


def swap_step_to_execution_dict(step: SwapStepLike) -> dict[str, Any]:
    """Convert a strategy SwapStep-like object into the encoder dict shape."""
    return {
        "dex_kind": step.dex_kind,
        "router": step.router,
        "call_data": step.call_data,
        "token_in": step.token_in,
        "token_out": step.token_out,
        "amount_in": step.amount_in,
        "amount_out_min": step.amount_out_min,
    }


def encode_native_arb_params(params: NativeArbParamsLike) -> bytes:
    """Encode a NativeArbParams-like object for exact REVM preflight."""
    from degenbot.execution import encode_native_arb_calldata

    return encode_native_arb_calldata(
        flash_lender=params.flash_lender,
        flash_protocol=params.flash_protocol,
        flash_token=params.flash_token,
        flash_amount=params.flash_amount,
        swaps=[swap_step_to_execution_dict(step) for step in params.swaps],
        min_profit=params.min_profit,
        deadline=params.deadline,
    )


def encode_match_params(params: MatchParamsLike) -> bytes:
    """Encode a MatchParams-like object for exact REVM preflight."""
    from degenbot.execution import encode_match_internal_calldata

    return encode_match_internal_calldata(
        cow_settlement_calldata=params.cow_settlement_calldata,
        uniswapx_batch_calldata=params.uniswapx_batch_calldata,
        expected_token_inflows=params.expected_token_inflows,
        expected_token_inflow_min=params.expected_token_inflow_min,
        flash_lender=params.flash_lender,
        flash_protocol=params.flash_protocol,
        flash_token=params.flash_token,
        flash_amount=params.flash_amount,
        min_profit=params.min_profit,
        deadline=params.deadline,
    )


def encode_compose_params(params: ComposeParamsLike) -> bytes:
    """Encode a ComposeParams-like object for exact REVM preflight."""
    from degenbot.execution import encode_compose_four_leg_calldata

    return encode_compose_four_leg_calldata(
        across_fill_calldata=params.across_fill_calldata,
        arb_swaps=[swap_step_to_execution_dict(step) for step in params.arb_swaps],
        cow_fill_calldata=params.cow_fill_calldata,
        uniswapx_rebalance_calldata=params.uniswapx_rebalance_calldata,
        flash_lender=params.flash_lender,
        flash_protocol=params.flash_protocol,
        flash_token=params.flash_token,
        flash_amount=params.flash_amount,
        min_profit=params.min_profit,
        deadline=params.deadline,
    )
