"""Typed mirror of the locked Solidity struct ABI for Executor.sol."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

from degenbot.decision.types import Address, Hex

FlashProtocol = Literal[0, 1, 2, 3]

DexKind = Literal[
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28
]


class FlashProtocolEnum:
    AAVE_V3 = 0
    MORPHO = 1
    ERC3156 = 2
    UNI_V3 = 3


class DexKindEnum:
    V2 = 0
    V3 = 1
    V4 = 2
    CURVE = 3
    RESERVED = 4
    AGGREGATOR_V6 = 5
    MORPHO_BLUE_ACTION = 6
    ALGEBRA = 7
    SOLIDLY = 8
    CURVE_NG = 9
    BALANCER_V2 = 10
    MAVERICK_V2 = 11
    DODO_PMM = 12
    FLUID_DEX = 13
    BALANCER_V3 = 14
    KYBER_ELASTIC = 15
    LFJ_LIQUIDITY_BOOK = 16
    GMX_V2 = 17
    WOMBAT = 18
    BEBOP = 19
    HASHFLOW = 20
    WOOFI = 21
    OKX_DEX = 22
    ENSO = 23
    SQUID = 24
    LIFI = 25
    RANGO = 26
    RUBIC = 27
    NATIVE = 28


@dataclass(frozen=True)
class SwapStep:
    dex_kind: DexKind
    router: Address
    call_data: Hex
    token_in: Address
    token_out: Address
    amount_in: int
    amount_out_min: int


@dataclass(frozen=True)
class NativeArbParams:
    flash_lender: Address
    flash_protocol: FlashProtocol
    flash_token: Address
    flash_amount: int
    swaps: Sequence[SwapStep]
    min_profit: int
    deadline: int


@dataclass(frozen=True)
class MatchParams:
    cow_settlement_calldata: Hex
    uniswapx_batch_calldata: Hex
    expected_token_inflows: Sequence[Address]
    expected_token_inflow_min: Sequence[int]
    flash_lender: Address
    flash_protocol: FlashProtocol
    flash_token: Address
    flash_amount: int
    min_profit: int
    deadline: int


@dataclass(frozen=True)
class ComposeParams:
    across_fill_calldata: Hex
    arb_swaps: Sequence[SwapStep]
    cow_fill_calldata: Hex
    uniswapx_rebalance_calldata: Hex
    flash_lender: Address
    flash_protocol: FlashProtocol
    flash_token: Address
    flash_amount: int
    min_profit: int
    deadline: int
