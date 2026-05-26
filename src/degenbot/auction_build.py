"""Compatibility import for the CoW auction-build bridge."""

from degenbot.cow.auction_build import (
    AuctionBuildRequest,
    AuctionBuildResponse,
    AuctionOrderRef,
    AuctionQuotePolicy,
    AuctionRef,
    build_auction_response,
    handle_auction_build_payload,
)

__all__ = [
    "AuctionBuildRequest",
    "AuctionBuildResponse",
    "AuctionOrderRef",
    "AuctionQuotePolicy",
    "AuctionRef",
    "build_auction_response",
    "handle_auction_build_payload",
]
