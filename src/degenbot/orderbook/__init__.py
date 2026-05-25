"""CoW Protocol orderbook client and typed REST models."""

from degenbot.orderbook.models import (
    Address,
    Auction,
    AuctionOrder,
    AuctionPrices,
    BuyTokenDestination,
    CompetitionSolution,
    EcdsaSignature,
    EcdsaSigningScheme,
    ExecutedProtocolFee,
    FeePolicy,
    FeePolicyPriceImprovement,
    FeePolicySurplus,
    FeePolicyVolume,
    HexBytes,
    InteractionData,
    NativePriceResponse,
    Order,
    OrderClass,
    OrderCreation,
    OrderKind,
    OrderMetaData,
    OrderParameters,
    OrderPostError,
    OrderQuoteRequest,
    OrderQuoteResponse,
    OrderQuoteSide,
    OrderQuoteSideKindBuy,
    OrderQuoteSideKindSell,
    OrderQuoteValidity,
    OrderStatus,
    OrderUid,
    PriceEstimationError,
    PriceImprovement,
    PriceQuality,
    SellTokenSource,
    Signature,
    SigningScheme,
    SolverCompetitionResponse,
    SolverSettlement,
    Surplus,
    Trade,
    TransactionHash,
    Volume,
)

_CLIENT_EXPORTS = {"DEFAULT_BASE_URL", "DEFAULT_TIMEOUT_SEC", "OrderbookClient", "OrderbookError"}


def __getattr__(name: str) -> object:
    """Lazily expose the HTTP client without creating an import cycle."""

    if name in _CLIENT_EXPORTS:
        from degenbot.orderbook.client import (  # noqa: PLC0415
            DEFAULT_BASE_URL,
            DEFAULT_TIMEOUT_SEC,
            OrderbookClient,
            OrderbookError,
        )

        exports: dict[str, object] = {
            "DEFAULT_BASE_URL": DEFAULT_BASE_URL,
            "DEFAULT_TIMEOUT_SEC": DEFAULT_TIMEOUT_SEC,
            "OrderbookClient": OrderbookClient,
            "OrderbookError": OrderbookError,
        }
        return exports[name]
    raise AttributeError(name)


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
