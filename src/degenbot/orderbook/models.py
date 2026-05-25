"""Pydantic models for the CoW Protocol orderbook REST API."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from degenbot.cow.models import (
    BigIntStr,
    BuyTokenBalance,
    CompetitionSolution,
    OrderClass,
    OrderKind,
    SigningScheme,
    SellTokenBalance,
)

__all__ = [
    "Address",
    "Auction",
    "AuctionOrder",
    "AuctionPrices",
    "BuyTokenDestination",
    "CompetitionSolution",
    "EcdsaSignature",
    "EcdsaSigningScheme",
    "ExecutedProtocolFee",
    "FeePolicy",
    "FeePolicyPriceImprovement",
    "FeePolicySurplus",
    "FeePolicyVolume",
    "HexBytes",
    "InteractionData",
    "NativePriceResponse",
    "Order",
    "OrderClass",
    "OrderCreation",
    "OrderKind",
    "OrderMetaData",
    "OrderParameters",
    "OrderPostError",
    "OrderQuoteRequest",
    "OrderQuoteResponse",
    "OrderQuoteSide",
    "OrderQuoteSideKindBuy",
    "OrderQuoteSideKindSell",
    "OrderQuoteValidity",
    "OrderStatus",
    "OrderUid",
    "PriceEstimationError",
    "PriceImprovement",
    "PriceQuality",
    "SellTokenSource",
    "Signature",
    "SigningScheme",
    "SolverCompetitionResponse",
    "SolverSettlement",
    "Surplus",
    "Trade",
    "TransactionHash",
    "Volume",
]

OrderUid = Annotated[str, Field(pattern=r"^0x[0-9a-fA-F]{112}$")]
Address = Annotated[str, Field(pattern=r"^0x[0-9a-fA-F]{40}$")]
TransactionHash = Annotated[str, Field(pattern=r"^0x[0-9a-fA-F]{64}$")]
HexBytes = Annotated[str, Field(pattern=r"^0x([0-9a-fA-F]{2})*$")]

SellTokenSource = SellTokenBalance
BuyTokenDestination = BuyTokenBalance


class OrderStatus(StrEnum):
    """Orderbook status of an order."""

    PRESIGNATURE_PENDING = "presignaturePending"
    OPEN = "open"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class PriceQuality(StrEnum):
    """How aggressively the orderbook should price an order."""

    FAST = "fast"
    OPTIMAL = "optimal"
    VERIFIED = "verified"


class EcdsaSigningScheme(StrEnum):
    """The two ECDSA-shaped signing schemes."""

    EIP712 = "eip712"
    ETH_SIGN = "ethsign"


class EcdsaSignature(BaseModel):
    """65-byte ECDSA signature."""

    model_config = ConfigDict(populate_by_name=True)

    scheme: EcdsaSigningScheme
    signature: HexBytes


class PreSignature(BaseModel):
    """Marker for Settlement.setPreSignature signatures."""

    model_config = ConfigDict(populate_by_name=True)

    scheme: Literal[SigningScheme.PRESIGN] = SigningScheme.PRESIGN
    signature: HexBytes | None = None


class Eip1271Signature(BaseModel):
    """Smart-contract-wallet signature."""

    model_config = ConfigDict(populate_by_name=True)

    scheme: Literal[SigningScheme.EIP1271] = SigningScheme.EIP1271
    signature: HexBytes


Signature = EcdsaSignature | PreSignature | Eip1271Signature


class InteractionData(BaseModel):
    """A pre-/post-interaction call attached via CoW Hooks."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    target: Address
    value: BigIntStr
    call_data: HexBytes = Field(alias="callData")


class OrderParameters(BaseModel):
    """User-signed order data."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    sell_token: Address = Field(alias="sellToken")
    buy_token: Address = Field(alias="buyToken")
    receiver: Address | None = None
    sell_amount: BigIntStr = Field(alias="sellAmount")
    buy_amount: BigIntStr = Field(alias="buyAmount")
    valid_to: int = Field(alias="validTo")
    app_data: str = Field(alias="appData")
    fee_amount: BigIntStr = Field(alias="feeAmount")
    kind: OrderKind
    partially_fillable: bool = Field(alias="partiallyFillable")
    sell_token_balance: SellTokenSource = Field(
        alias="sellTokenBalance",
        default=SellTokenSource.ERC20,
    )
    buy_token_balance: BuyTokenDestination = Field(
        alias="buyTokenBalance",
        default=BuyTokenDestination.ERC20,
    )
    signing_scheme: SigningScheme = Field(alias="signingScheme")


class OrderCreation(OrderParameters):
    """POST /orders body."""

    signature: HexBytes
    quote_id: int | None = Field(default=None, alias="quoteId")
    app_data_hash: str | None = Field(default=None, alias="appDataHash")
    from_: Address | None = Field(default=None, alias="from")


class FeePolicySurplus(BaseModel):
    """Take a fraction of surplus, capped at a fraction of volume."""

    model_config = ConfigDict(populate_by_name=True)

    kind: Literal["surplus"] = "surplus"
    factor: float
    max_volume_factor: float = Field(alias="maxVolumeFactor")


class FeePolicyVolume(BaseModel):
    """Flat fraction of trade volume."""

    model_config = ConfigDict(populate_by_name=True)

    kind: Literal["volume"] = "volume"
    factor: float


class FeePolicyPriceImprovement(BaseModel):
    """Take a fraction of price improvement vs. a quote reference."""

    model_config = ConfigDict(populate_by_name=True)

    kind: Literal["priceImprovement"] = "priceImprovement"
    factor: float
    max_volume_factor: float = Field(alias="maxVolumeFactor")
    quote: dict[str, Any] | None = None


FeePolicy = FeePolicySurplus | FeePolicyVolume | FeePolicyPriceImprovement


class ExecutedProtocolFee(BaseModel):
    """How a fee policy realised on settlement."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    policy: FeePolicy
    amount: BigIntStr
    token: Address


class Surplus(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    factor: float
    max_volume_factor: float = Field(alias="maxVolumeFactor")


class Volume(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    factor: float


class PriceImprovement(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    factor: float
    max_volume_factor: float = Field(alias="maxVolumeFactor")


class OrderMetaData(BaseModel):
    """Server-side fields appended by the orderbook."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    creation_date: datetime = Field(alias="creationDate")
    owner: Address
    uid: OrderUid
    available_balance: BigIntStr | None = Field(default=None, alias="availableBalance")
    executed_sell_amount: BigIntStr = Field(alias="executedSellAmount")
    executed_sell_amount_before_fees: BigIntStr = Field(
        alias="executedSellAmountBeforeFees",
    )
    executed_buy_amount: BigIntStr = Field(alias="executedBuyAmount")
    executed_fee_amount: BigIntStr = Field(alias="executedFeeAmount")
    invalidated: bool
    status: OrderStatus
    class_: OrderClass = Field(alias="class")
    settlement_contract: Address | None = Field(default=None, alias="settlementContract")
    full_fee_amount: BigIntStr | None = Field(default=None, alias="fullFeeAmount")
    is_liquidity_order: bool | None = Field(default=None, alias="isLiquidityOrder")
    executed_protocol_fees: list[ExecutedProtocolFee] = Field(
        default_factory=list,
        alias="executedProtocolFees",
    )


class Order(OrderParameters, OrderMetaData):
    """Full order = signed parameters + server metadata + signature."""

    signature: HexBytes


class AuctionOrder(BaseModel):
    """Order shape inside the orderbook auction endpoint."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    uid: OrderUid
    sell_token: Address = Field(alias="sellToken")
    buy_token: Address = Field(alias="buyToken")
    sell_amount: BigIntStr = Field(alias="sellAmount")
    buy_amount: BigIntStr = Field(alias="buyAmount")
    user_fee: BigIntStr = Field(alias="userFee")
    valid_to: int = Field(alias="validTo")
    kind: OrderKind
    receiver: Address | None = None
    owner: Address
    partially_fillable: bool = Field(alias="partiallyFillable")
    executed: BigIntStr | None = None
    pre_interactions: list[InteractionData] = Field(
        default_factory=list,
        alias="preInteractions",
    )
    post_interactions: list[InteractionData] = Field(
        default_factory=list,
        alias="postInteractions",
    )
    sell_token_balance: SellTokenSource = Field(
        alias="sellTokenBalance",
        default=SellTokenSource.ERC20,
    )
    buy_token_balance: BuyTokenDestination = Field(
        alias="buyTokenBalance",
        default=BuyTokenDestination.ERC20,
    )
    class_: OrderClass = Field(alias="class")
    app_data: str = Field(alias="appData")
    signing_scheme: SigningScheme = Field(alias="signingScheme")
    signature: HexBytes
    protocol_fees: list[FeePolicy] = Field(default_factory=list, alias="protocolFees")
    quote: dict[str, Any] | None = None


AuctionPrices = dict[Address, BigIntStr]


class Auction(BaseModel):
    """Current batch auction snapshot from the orderbook."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: int | None = None
    block: int | None = None
    latest_settlement_block: int | None = Field(default=None, alias="latestSettlementBlock")
    orders: list[AuctionOrder] = Field(default_factory=list)
    prices: AuctionPrices = Field(default_factory=dict)
    surplus_capturing_jit_order_owners: list[Address] = Field(
        default_factory=list,
        alias="surplusCapturingJitOrderOwners",
    )


class OrderQuoteSideKindSell(BaseModel):
    """Sell-amount-fixed quote variant."""

    model_config = ConfigDict(populate_by_name=True)

    kind: Literal["sell"] = "sell"
    sell_amount_before_fee: BigIntStr | None = Field(default=None, alias="sellAmountBeforeFee")
    sell_amount_after_fee: BigIntStr | None = Field(default=None, alias="sellAmountAfterFee")


class OrderQuoteSideKindBuy(BaseModel):
    """Buy-amount-fixed quote variant."""

    model_config = ConfigDict(populate_by_name=True)

    kind: Literal["buy"] = "buy"
    buy_amount_after_fee: BigIntStr = Field(alias="buyAmountAfterFee")


OrderQuoteSide = OrderQuoteSideKindSell | OrderQuoteSideKindBuy


class OrderQuoteValidity(BaseModel):
    """Either an absolute deadline or relative valid-for seconds."""

    model_config = ConfigDict(populate_by_name=True)

    valid_to: int | None = Field(default=None, alias="validTo")
    valid_for: int | None = Field(default=None, alias="validFor")


class OrderQuoteRequest(BaseModel):
    """POST /quote body."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    sell_token: Address = Field(alias="sellToken")
    buy_token: Address = Field(alias="buyToken")
    receiver: Address | None = None
    app_data: str = Field(alias="appData")
    app_data_hash: str | None = Field(default=None, alias="appDataHash")
    sell_token_balance: SellTokenSource = Field(
        alias="sellTokenBalance",
        default=SellTokenSource.ERC20,
    )
    buy_token_balance: BuyTokenDestination = Field(
        alias="buyTokenBalance",
        default=BuyTokenDestination.ERC20,
    )
    from_: Address | None = Field(default=None, alias="from")
    price_quality: PriceQuality | None = Field(default=None, alias="priceQuality")
    signing_scheme: SigningScheme = Field(alias="signingScheme")
    on_chain_order: bool | None = Field(default=None, alias="onchainOrder")
    side: OrderQuoteSide
    validity: OrderQuoteValidity


class OrderQuoteResponse(BaseModel):
    """POST /quote response. Embeds an unsigned executable order."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    quote: OrderParameters
    from_: Address | None = Field(default=None, alias="from")
    expiration: datetime
    id: int | None = None
    verified: bool | None = None


class NativePriceResponse(BaseModel):
    """GET /token/{token}/native_price."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    price: float


class SolverSettlement(BaseModel):
    """One row in a solver-competition response."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    solver: str
    solver_address: Address | None = Field(default=None, alias="solverAddress")
    score: BigIntStr | None = None
    ranking: int | None = None
    objective: dict[str, Any] | None = None
    clearing_prices: dict[Address, BigIntStr] = Field(default_factory=dict, alias="clearingPrices")
    orders: list[dict[str, Any]] = Field(default_factory=list)
    call_data: HexBytes | None = Field(default=None, alias="callData")
    uninternalized_call_data: HexBytes | None = Field(
        default=None,
        alias="uninternalizedCallData",
    )
    is_winner: bool | None = Field(default=None, alias="isWinner")
    filtered_out: bool | None = Field(default=None, alias="filteredOut")


class SolverCompetitionResponse(BaseModel):
    """GET /v2/solver_competition/* response."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    auction_id: int = Field(alias="auctionId")
    transaction_hashes: list[TransactionHash] = Field(
        default_factory=list,
        alias="transactionHashes",
    )
    reference_score: BigIntStr | None = Field(default=None, alias="referenceScore")
    auction: dict[str, Any] | None = None
    solutions: list[SolverSettlement] = Field(default_factory=list)


class Trade(BaseModel):
    """One settled orderbook trade."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    block_number: int = Field(alias="blockNumber")
    log_index: int = Field(alias="logIndex")
    order_uid: OrderUid = Field(alias="orderUid")
    owner: Address
    sell_token: Address = Field(alias="sellToken")
    buy_token: Address = Field(alias="buyToken")
    sell_amount: BigIntStr = Field(alias="sellAmount")
    sell_amount_before_fees: BigIntStr = Field(alias="sellAmountBeforeFees")
    buy_amount: BigIntStr = Field(alias="buyAmount")
    transaction_hash: TransactionHash = Field(alias="txHash")


class OrderPostError(BaseModel):
    """Body of a 4xx response from POST /orders."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    error_type: str = Field(alias="errorType")
    description: str | None = None


class PriceEstimationError(BaseModel):
    """Body of a 4xx response from POST /quote."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    error_type: str = Field(alias="errorType")
    description: str | None = None
