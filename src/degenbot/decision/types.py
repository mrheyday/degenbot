"""Core domain types for the strategy routing engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Any, Sequence

Address = str
Hex = str
Bytes32 = str
ChainId = int

Strategy = Literal[
    "internal_match",
    "four_leg",
    "morpho_liquidation",
    "dolomite_liquidation",
    "native_arb",
    "launch_sniper",
    "d3_filter",
    "cow_quoter",
    "filler_bid",
    "cow_user_submit",
    "across_destination_fill",
    "sandwich_s1_timeboost",
    "sandwich_s2_cow_prebatch",
    "sandwich_s3_uniswapx_filler",
    "sandwich_s4_cross_pool_flash",
    "oracle_sandwich",
]

AggregatorSource = Literal[
    "1inch",
    "0x",
    "paraswap",
    "odos",
    "kyberswap",
    "openocean",
    "defillamaswap",
    "uniswap",
    "woofi",
    "native",
    "hashflow",
    "dodo",
    "dexscreener",
    "cow",
]


@dataclass(frozen=True)
class PathfinderPath:
    source: AggregatorSource
    provider: str
    amount_out: int
    executable: bool
    protocols: Sequence[str]
    router: Address | None = None
    calldata: Hex | None = None
    estimated_gas: int | None = None
    fee_bps: int | None = None
    expires_at: int | None = None


@dataclass(frozen=True)
class AggregatorQuote:
    source: AggregatorSource
    amount_out: int
    router: Address
    calldata: Hex
    estimated_gas: int
    fee_bps: int
    timestamp_ms: int
    expires_at: int
    provider: str | None = None
    paths: Sequence[PathfinderPath] | None = None


@dataclass(frozen=True)
class CowOrderSummary:
    uid: Hex
    owner: Address
    sell_token: Address
    buy_token: Address
    sell_amount: int
    buy_amount: int
    fee_amount: int
    valid_to: int
    kind: Literal["buy", "sell"]
    partially_fillable: bool
    signing_scheme: Literal["eip712", "ethsign", "presign", "eip1271"]
    signature: Hex
    app_data: Bytes32


UniswapXOrderType = Literal["Dutch", "Dutch_V2", "Dutch_V3", "Priority", "Unknown"]


@dataclass(frozen=True)
class UniswapXOrderSummary:
    order_hash: Hex
    reactor: Address
    swapper: Address
    input_token: Address
    output_token: Address
    input_amount: int
    output_amount_min: int
    deadline: int
    encoded_order: Hex
    signature: Hex
    chain_id: int | None = None
    order_type: UniswapXOrderType | None = None


@dataclass(frozen=True)
class MatchCandidate:
    id: str
    side: Literal["outbound", "inbound", "uniswapx", "native"]
    pair_sell: Address
    pair_buy: Address
    amount_sell: int
    amount_buy_min: int
    source_id: str
    source_venue: Literal["native", "cow", "cow-competition", "uniswapx", "across", "eco"]
    source_expires_at: int
    received_at_ms: int
    cow_order: CowOrderSummary | None = None
    uniswapx_order: UniswapXOrderSummary | None = None


@dataclass(frozen=True)
class MatchPair:
    o: MatchCandidate
    c: MatchCandidate
    fill_amount: int
    clearing_price: int


@dataclass(frozen=True)
class DecisionContext:
    flow_id: str
    detected_at_ns: int
    block_number: int
    chain_id: int


@dataclass(frozen=True)
class DecisionRoute:
    kind: Literal[
        "internal_match",
        "four_leg",
        "morpho_liquidation",
        "dolomite_liquidation",
        "native_arb",
        "launch_sniper",
        "cow_user_submit",
        "across_fill",
        "pass",
    ]
    reason: str | None = None
    pair: MatchPair | None = None
    opportunity_id: str | None = None
    token_address: str | None = None
    pool_address: str | None = None
    signal_score: float | None = None
    order_id: Bytes32 | None = None
    # Add four_leg plan when ported
    plan: Any | None = None
