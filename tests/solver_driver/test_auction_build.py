"""Tests for the CoW auction-build bridge contract."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from degenbot.auction_build import (
    AuctionBuildRequest,
    build_auction_response,
    handle_auction_build_payload,
)
from degenbot.strategies import D3Filter, SolutionBuilder
from pydantic import ValidationError

UID_1 = f"0x{'11' * 56}"
UID_2 = f"0x{'22' * 56}"
OWNER = f"0x{'33' * 20}"
USDC = f"0x{'44' * 20}"
WETH = f"0x{'55' * 20}"


@pytest.fixture
def mock_builder():
    builder = MagicMock(spec=SolutionBuilder)
    builder.build = AsyncMock(return_value=None)
    return builder


def order(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "uid": UID_1,
        "owner": OWNER,
        "sellToken": USDC,
        "buyToken": WETH,
        "sellAmount": "1000000",
        "buyAmount": "400000000000000",
        "feeAmount": "0",
        "validTo": 1_900_000_000,
        "kind": "sell",
        "partiallyFillable": False,
        "signingScheme": "eip712",
        "signature": "0x",
    }
    base.update(overrides)
    return base


def payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "auction": {
            "auctionId": "auction-42",
            "orders": [order()],
            "deadlineMs": int(time.time() * 1000) + 30_000,
        },
        "policy": {
            "chainId": 42161,
            "maxBidFractionBps": 3500,
            "minProfitUsd": 12.5,
            "d3FilterEnabled": True,
        },
    }
    base.update(overrides)
    return base


def test_parses_coordinator_payload_aliases() -> None:
    request = AuctionBuildRequest.model_validate(payload())

    assert request.auction.auction_id == "auction-42"
    assert request.auction.orders[0].uid == UID_1
    assert request.auction.orders[0].sell_amount == 1_000_000
    assert request.policy.chain_id == 42161
    assert request.policy.max_bid_fraction_bps == 3500
    assert request.policy.min_profit_usd == 12.5
    assert request.policy.d3_filter_enabled is True


@pytest.mark.asyncio
async def test_returns_fail_closed_no_bid_response(mock_builder: MagicMock) -> None:
    response = await handle_auction_build_payload(payload(), mock_builder)

    assert response.model_dump(by_alias=True, exclude_none=True) == {
        "auctionId": "auction-42",
        "status": "no_bid",
        "reason": "missing_raw_auction_data",
        "ordersSeen": 1,
        "candidateOrders": 1,
        "filteredOrders": 0,
    }


@pytest.mark.asyncio
async def test_d3_filter_classifies_opposing_price_compatible_orders(
    mock_builder: MagicMock,
) -> None:
    first = order()
    peer = order(
        uid=UID_2,
        sellToken=WETH,
        buyToken=USDC,
        sellAmount="400000000000000",
        buyAmount="1000000",
    )

    assert D3Filter().classify(first, [peer]) == "cow_matchable"
    response = await handle_auction_build_payload(
        payload(
            auction={
                "auctionId": "auction-42",
                "orders": [first, peer],
                "deadlineMs": int(time.time() * 1000) + 30_000,
            }
        ),
        mock_builder,
    )
    assert response.model_dump(by_alias=True, exclude_none=True) == {
        "auctionId": "auction-42",
        "status": "no_bid",
        "reason": "missing_raw_auction_data",
        "ordersSeen": 2,
        "candidateOrders": 0,
        "filteredOrders": 2,
    }


@pytest.mark.asyncio
async def test_d3_policy_can_be_disabled_for_all_orders(mock_builder: MagicMock) -> None:
    first = order()
    peer = order(
        uid=UID_2,
        sellToken=WETH,
        buyToken=USDC,
        sellAmount="400000000000000",
        buyAmount="1000000",
    )

    response = await handle_auction_build_payload(
        payload(
            auction={
                "auctionId": "auction-42",
                "orders": [first, peer],
                "deadlineMs": int(time.time() * 1000) + 30_000,
            },
            policy={
                "chainId": 42161,
                "maxBidFractionBps": 3500,
                "minProfitUsd": 12.5,
                "d3FilterEnabled": False,
            },
        ),
        mock_builder,
    )

    assert response.candidate_orders == 2
    assert response.filtered_orders == 0


def test_rejects_stale_auction() -> None:
    stale = payload(
        auction={
            "auctionId": "auction-42",
            "orders": [order()],
            "deadlineMs": 1,
        }
    )

    with pytest.raises(ValidationError, match="auction deadline elapsed"):
        AuctionBuildRequest.model_validate(stale)


def test_rejects_empty_auction() -> None:
    empty = payload(
        auction={
            "auctionId": "auction-42",
            "orders": [],
            "deadlineMs": int(time.time() * 1000) + 30_000,
        }
    )

    with pytest.raises(ValidationError):
        AuctionBuildRequest.model_validate(empty)


def test_rejects_non_arbitrum_chain_and_invalid_policy_caps() -> None:
    with pytest.raises(ValidationError):
        AuctionBuildRequest.model_validate(
            payload(
                policy={
                    "chainId": 1,
                    "maxBidFractionBps": 3500,
                    "minProfitUsd": 12.5,
                    "d3FilterEnabled": True,
                }
            )
        )

    with pytest.raises(ValidationError):
        AuctionBuildRequest.model_validate(
            payload(
                policy={
                    "chainId": 42161,
                    "maxBidFractionBps": 10_001,
                    "minProfitUsd": 12.5,
                    "d3FilterEnabled": True,
                }
            )
        )


@pytest.mark.asyncio
async def test_response_builder_counts_orders_without_side_effects(mock_builder: MagicMock) -> None:
    request = AuctionBuildRequest.model_validate(
        payload(
            auction={
                "auctionId": "auction-many",
                "orders": [order(), order(uid=UID_2, sellAmount="2000000")],
                "deadlineMs": int(time.time() * 1000) + 30_000,
            }
        )
    )

    response = await build_auction_response(request, mock_builder)

    assert response.auction_id == "auction-many"
    assert response.orders_seen == 2
