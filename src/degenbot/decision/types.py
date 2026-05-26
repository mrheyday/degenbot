"""Core domain types for the strategy routing engine."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from collections.abc import Sequence

Address = str
Hex = str
Bytes32 = str
ChainId = int

AggregatorSource = str


class PathfinderPath(BaseModel):
    model_config = ConfigDict(frozen=True)
    source: AggregatorSource
    provider: str
    amount_out: int = Field(alias="amountOut")
    executable: bool
    protocols: Sequence[str]
    router: Address | None = None
    calldata: Hex | None = Field(default=None, alias="callData")
    estimated_gas: int | None = Field(default=None, alias="estimatedGas")
    fee_bps: int | None = Field(default=None, alias="feeBps")
    expires_at: int | None = Field(default=None, alias="expiresAt")


class AggregatorQuote(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)
    source: AggregatorSource
    amount_out: int = Field(alias="amountOut")
    router: Address
    calldata: Hex = Field(alias="callData")
    estimated_gas: int = Field(alias="estimatedGas")
    fee_bps: int = Field(alias="feeBps")
    timestamp_ms: int = Field(alias="timestampMs")
    expires_at: int = Field(alias="expiresAt")
    provider: str | None = None
    paths: Sequence[PathfinderPath] | None = None


class CowOrderSummary(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)
    uid: Hex
    owner: Address
    sell_token: Address = Field(alias="sellToken")
    buy_token: Address = Field(alias="buyToken")
    sell_amount: int = Field(alias="sellAmount")
    buy_amount: int = Field(alias="buyAmount")
    fee_amount: int = Field(alias="feeAmount")
    valid_to: int = Field(alias="validTo")
    kind: Literal["buy", "sell"]
    partially_fillable: bool = Field(alias="partiallyFillable")
    signing_scheme: Literal["eip712", "ethsign", "presign", "eip1271"] = Field(
        alias="signingScheme"
    )
    signature: Hex
    app_data: Bytes32 = Field(alias="appData")


UniswapXOrderType = Literal["Dutch", "Dutch_V2", "Dutch_V3", "Priority", "Unknown"]


class UniswapXOrderSummary(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)
    order_hash: Hex = Field(alias="orderHash")
    reactor: Address
    swapper: Address
    input_token: Address = Field(alias="inputToken")
    output_token: Address = Field(alias="outputToken")
    input_amount: int = Field(alias="inputAmount")
    output_amount_min: int = Field(alias="outputAmountMin")
    deadline: int
    encoded_order: Hex = Field(alias="encodedOrder")
    signature: Hex
    chain_id: int | None = Field(default=None, alias="chainId")
    order_type: UniswapXOrderType | None = Field(default=None, alias="orderType")


class ERC7683IntentSummary(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)
    order_id: Hex = Field(alias="orderId")
    origin_chain_id: int = Field(alias="originChainId")
    destination_chain_id: int = Field(alias="destinationChainId")
    user: Address
    input_token: Address = Field(alias="inputToken")
    output_token: Address = Field(alias="outputToken")
    input_amount: int = Field(alias="inputAmount")
    output_amount: int = Field(alias="outputAmount")
    fill_deadline: int = Field(alias="fillDeadline")
    origin_data: Hex = Field(alias="originData")
    destination_data: Hex = Field(alias="destinationData")


class MatchCandidate(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)
    id: str
    side: Literal["outbound", "inbound", "uniswapx", "native"]
    pair_sell: Address = Field(alias="pairSell")
    pair_buy: Address = Field(alias="pairBuy")
    pair_sell_decimals: int = Field(default=18, ge=0, le=255, alias="pairSellDecimals")
    pair_buy_decimals: int = Field(default=18, ge=0, le=255, alias="pairBuyDecimals")
    amount_sell: int = Field(alias="amountSell")
    amount_buy_min: int = Field(alias="amountBuyMin")
    source_id: str = Field(alias="sourceId")
    source_venue: Literal["native", "cow", "cow-competition", "uniswapx", "across", "eco"] = Field(
        alias="sourceVenue"
    )
    source_expires_at: int = Field(alias="sourceExpiresAt")
    received_at_ms: int = Field(alias="receivedAtMs")
    cow_order: CowOrderSummary | None = Field(default=None, alias="cowOrder")
    uniswapx_order: UniswapXOrderSummary | None = Field(default=None, alias="uniswapxOrder")


class MatchPair(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)
    o: MatchCandidate
    c: MatchCandidate
    fill_amount: int = Field(alias="fillAmount")
    clearing_price: int = Field(alias="clearingPrice")


class DecisionContext(BaseModel):
    model_config = ConfigDict(frozen=True)
    flow_id: str = Field(alias="flowId")
    detected_at_ns: int = Field(alias="detectedAtNs")
    block_number: int = Field(alias="blockNumber")
    chain_id: int = Field(alias="chainId")


class DecisionRoute(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)
    kind: Literal[
        "internal_match",
        "four_leg",
        "morpho_liquidation",
        "dolomite_liquidation",
        "native_arb",
        "launch_sniper",
        "oracle_sandwich",
        "cow_user_submit",
        "across_fill",
        "pass",
    ]
    reason: str | None = None
    pair: MatchPair | None = None
    opportunity_id: str | None = Field(default=None, alias="opportunityId")
    token_address: str | None = Field(default=None, alias="tokenAddress")
    pool_address: str | None = Field(default=None, alias="poolAddress")
    signal_score: float | None = Field(default=None, alias="signalScore")
    order_id: Bytes32 | None = Field(default=None, alias="orderId")
    # Add four_leg plan when ported
    plan: Any | None = None
