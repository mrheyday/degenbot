from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

from degenbot.utils.bytes import HexBytesLike

class SwapStepDict(TypedDict):
    dex_kind: str
    router: str | bytes
    call_data: HexBytesLike | str
    token_in: str | bytes
    token_out: str | bytes
    amount_in: int | bytes
    amount_out_min: int | bytes

def encode_native_arb_calldata(
    flash_lender: str | bytes,
    flash_protocol: Any,
    flash_token: str | bytes,
    flash_amount: int | bytes,
    swaps: Sequence[Mapping[str, Any]],
    min_profit: int | bytes,
    deadline: int | bytes,
) -> bytes: ...
def encode_match_internal_calldata(
    cow_settlement_calldata: bytes | HexBytesLike | str,
    uniswapx_batch_calldata: bytes | HexBytesLike | str,
    expected_token_inflows: Sequence[str | bytes],
    expected_token_inflow_min: Sequence[int | bytes],
    flash_lender: str | bytes,
    flash_protocol: Any,
    flash_token: str | bytes,
    flash_amount: int | bytes,
    min_profit: int | bytes,
    deadline: int | bytes,
) -> bytes: ...
def encode_compose_four_leg_calldata(
    across_fill_calldata: bytes | HexBytesLike | str,
    arb_swaps: Sequence[Mapping[str, Any]],
    cow_fill_calldata: bytes | HexBytesLike | str,
    uniswapx_rebalance_calldata: bytes | HexBytesLike | str,
    flash_lender: str | bytes,
    flash_protocol: Any,
    flash_token: str | bytes,
    flash_amount: int | bytes,
    min_profit: int | bytes,
    deadline: int | bytes,
) -> bytes: ...

__all__ = [
    "SwapStepDict",
    "encode_compose_four_leg_calldata",
    "encode_match_internal_calldata",
    "encode_native_arb_calldata",
]
