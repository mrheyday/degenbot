"""Python convenience wrappers for Executor calldata encoding.

This module normalizes plain Python dicts, lists, addresses, and bytes-like
inputs before delegating to the Rust-backed `degenbot.degenbot_rs` bindings.
The Rust layer remains the source of truth for validation and encoding.
"""

import sys as _sys
from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

from hexbytes import HexBytes

from degenbot.cow import submitter as _competition_submitter
from degenbot.degenbot_rs import to_checksum_address
from degenbot.utils.bytes import HexBytesLike, to_bytes

try:  # Prefer canonical exports from a rebuilt extension.
    from degenbot.degenbot_rs import (
        encode_compose_four_leg_calldata as _encode_compose_four_leg_calldata,
    )
    from degenbot.degenbot_rs import (
        encode_match_internal_calldata as _encode_match_internal_calldata,
    )
    from degenbot.degenbot_rs import (
        encode_native_arb_calldata as _encode_native_arb_calldata,
    )
except ImportError:  # Fallback for the currently installed binary surface.
    from degenbot.degenbot_rs import (
        encode_compose_four_leg_calldata_py as _encode_compose_four_leg_calldata,
    )
    from degenbot.degenbot_rs import (
        encode_match_internal_calldata_py as _encode_match_internal_calldata,
    )
    from degenbot.degenbot_rs import (
        encode_native_arb_calldata_py as _encode_native_arb_calldata,
    )


class SwapStepDict(TypedDict):
    """Python representation of a single swap step."""

    dex_kind: str
    router: str | bytes
    call_data: HexBytesLike
    token_in: str | bytes
    token_out: str | bytes
    amount_in: int | bytes
    amount_out_min: int | bytes


def _normalize_address(value: str | bytes) -> str:
    return to_checksum_address(value)


def _normalize_bytes(value: bytes | HexBytesLike | str) -> bytes:
    if isinstance(value, str):
        return bytes(HexBytes(value))
    return to_bytes(value)


def _normalize_amount(value: int | bytes) -> int | bytes:
    if isinstance(value, int):
        return value
    return to_bytes(value)


def _normalize_swap_step(step: Mapping[str, Any]) -> SwapStepDict:
    return {
        "dex_kind": str(step["dex_kind"]),
        "router": _normalize_address(step["router"]),
        "call_data": _normalize_bytes(step["call_data"]),
        "token_in": _normalize_address(step["token_in"]),
        "token_out": _normalize_address(step["token_out"]),
        "amount_in": _normalize_amount(step["amount_in"]),
        "amount_out_min": _normalize_amount(step["amount_out_min"]),
    }


def _normalize_swap_steps(swaps: Sequence[Mapping[str, Any]]) -> list[SwapStepDict]:
    return [_normalize_swap_step(step) for step in swaps]


def encode_native_arb_calldata(
    flash_lender: str | bytes,
    flash_protocol: str,
    flash_token: str | bytes,
    flash_amount: int | bytes,
    swaps: Sequence[Mapping[str, Any]],
    min_profit: int | bytes,
    deadline: int | bytes,
) -> bytes:
    """Encode calldata for `Executor.executeNativeArb` from Python objects."""

    return _encode_native_arb_calldata(
        _normalize_address(flash_lender),
        flash_protocol,
        _normalize_address(flash_token),
        _normalize_amount(flash_amount),
        _normalize_swap_steps(swaps),
        _normalize_amount(min_profit),
        _normalize_amount(deadline),
    )


def encode_match_internal_calldata(
    cow_settlement_calldata: bytes | HexBytesLike,
    uniswapx_batch_calldata: bytes | HexBytesLike,
    expected_token_inflows: Sequence[str | bytes],
    expected_token_inflow_min: Sequence[int | bytes],
    flash_lender: str | bytes,
    flash_protocol: str,
    flash_token: str | bytes,
    flash_amount: int | bytes,
    min_profit: int | bytes,
    deadline: int | bytes,
) -> bytes:
    """Encode calldata for `Executor.matchInternal` from Python objects."""

    return _encode_match_internal_calldata(
        _normalize_bytes(cow_settlement_calldata),
        _normalize_bytes(uniswapx_batch_calldata),
        [_normalize_address(token) for token in expected_token_inflows],
        [_normalize_amount(amount) for amount in expected_token_inflow_min],
        _normalize_address(flash_lender),
        flash_protocol,
        _normalize_address(flash_token),
        _normalize_amount(flash_amount),
        _normalize_amount(min_profit),
        _normalize_amount(deadline),
    )


def encode_compose_four_leg_calldata(
    across_fill_calldata: bytes | HexBytesLike,
    arb_swaps: Sequence[Mapping[str, Any]],
    cow_fill_calldata: bytes | HexBytesLike,
    uniswapx_rebalance_calldata: bytes | HexBytesLike,
    flash_lender: str | bytes,
    flash_protocol: str,
    flash_token: str | bytes,
    flash_amount: int | bytes,
    min_profit: int | bytes,
    deadline: int | bytes,
) -> bytes:
    """Encode calldata for `Executor.composeFourLeg` from Python objects."""

    return _encode_compose_four_leg_calldata(
        _normalize_bytes(across_fill_calldata),
        _normalize_swap_steps(arb_swaps),
        _normalize_bytes(cow_fill_calldata),
        _normalize_bytes(uniswapx_rebalance_calldata),
        _normalize_address(flash_lender),
        flash_protocol,
        _normalize_address(flash_token),
        _normalize_amount(flash_amount),
        _normalize_amount(min_profit),
        _normalize_amount(deadline),
    )


__all__ = [
    "SwapStepDict",
    "encode_compose_four_leg_calldata",
    "encode_match_internal_calldata",
    "encode_native_arb_calldata",
]

# Compatibility for the migrated solver-driver import path. `execution.py`
# remains the calldata-encoding module, but legacy code imported
# `degenbot.execution.competition_submitter` before the CoW submitter moved to
# `degenbot.cow.submitter`.
__path__ = []  # type: ignore[var-annotated]
_sys.modules[__name__ + ".competition_submitter"] = _competition_submitter
