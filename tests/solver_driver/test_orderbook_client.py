"""Async tests for OrderbookClient using httpx.MockTransport.

No real network calls. Each test pins one endpoint's request shape
(method + path + body) and response decoding (parsed pydantic model).
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from degenbot.orderbook import (
    Auction,
    NativePriceResponse,
    OrderbookClient,
    OrderbookError,
    OrderQuoteRequest,
    OrderQuoteResponse,
    SolverCompetitionResponse,
)
from degenbot.orderbook.models import OrderQuoteSideKindSell, OrderQuoteValidity

_BASE = "https://api.cow.fi/arbitrum_one"
_QUOTE_REQ = OrderQuoteRequest(
    sellToken="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",  # type: ignore[call-arg]
    buyToken="0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",  # type: ignore[call-arg]
    appData="{}",  # type: ignore[call-arg]
    signingScheme="eip712",  # type: ignore[call-arg]
    side=OrderQuoteSideKindSell(sellAmountBeforeFee="1000000"),  # type: ignore[call-arg]
    validity=OrderQuoteValidity(validFor=1800),  # type: ignore[call-arg]
)


def _ok_handler(payload: dict[str, Any] | list[Any]) -> httpx.MockTransport:
    def h(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    return httpx.MockTransport(h)


def _status_handler(status: int, body: dict[str, Any] | None = None) -> httpx.MockTransport:
    def h(_req: httpx.Request) -> httpx.Response:
        if body is None:
            return httpx.Response(status, text="oops")
        return httpx.Response(status, json=body)

    return httpx.MockTransport(h)


@pytest.mark.asyncio
async def test_get_auction_decodes() -> None:
    payload = {
        "id": 1,
        "block": 100,
        "orders": [],
        "prices": {},
    }
    transport = _ok_handler(payload)
    async with OrderbookClient(base_url=_BASE, transport=transport) as cow:
        auction = await cow.get_auction()
    assert isinstance(auction, Auction)
    assert auction.id == 1


@pytest.mark.asyncio
async def test_get_native_price_decodes() -> None:
    transport = _ok_handler({"price": 0.000341})
    async with OrderbookClient(base_url=_BASE, transport=transport) as cow:
        out = await cow.get_native_price("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2")
    assert isinstance(out, NativePriceResponse)
    assert out.price == pytest.approx(0.000341)


@pytest.mark.asyncio
async def test_post_quote_round_trips_request_body() -> None:
    captured: dict[str, Any] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["method"] = req.method
        captured["path"] = req.url.path
        captured["body"] = json.loads(req.content)
        return httpx.Response(
            200,
            json={
                "quote": {
                    "sellToken": _QUOTE_REQ.sell_token,
                    "buyToken": _QUOTE_REQ.buy_token,
                    "sellAmount": "999000",
                    "buyAmount": "498500000000000",
                    "validTo": 2_000_000_000,
                    "appData": "{}",
                    "feeAmount": "1000",
                    "kind": "sell",
                    "partiallyFillable": False,
                    "signingScheme": "eip712",
                },
                "expiration": "2026-05-08T12:30:00Z",
                "id": 7,
            },
        )

    async with OrderbookClient(
        base_url=_BASE,
        transport=httpx.MockTransport(handler),
    ) as cow:
        resp = await cow.post_quote(_QUOTE_REQ)

    assert isinstance(resp, OrderQuoteResponse)
    assert resp.id == 7
    assert captured["method"] == "POST"
    # base_url's path component (`/arbitrum_one`) prefixes the captured URL.
    assert captured["path"] == "/arbitrum_one/api/v1/quote"
    assert captured["body"]["side"] == {"kind": "sell", "sellAmountBeforeFee": "1000000"}
    assert captured["body"]["validity"] == {"validFor": 1800}


@pytest.mark.asyncio
async def test_get_latest_competition_decodes() -> None:
    transport = _ok_handler(
        {
            "auctionId": 42,
            "transactionHashes": ["0x" + "ab" * 32],
            "solutions": [
                {
                    "solver": "test-solver",
                    "ranking": 1,
                    "isWinner": True,
                },
            ],
        },
    )
    async with OrderbookClient(base_url=_BASE, transport=transport) as cow:
        comp = await cow.get_latest_competition()
    assert isinstance(comp, SolverCompetitionResponse)
    assert comp.auction_id == 42
    assert comp.solutions[0].is_winner is True


@pytest.mark.asyncio
async def test_4xx_surface_as_orderbook_error_with_parsed_body() -> None:
    transport = _status_handler(
        400,
        {"errorType": "InsufficientBalance", "description": "balance too low"},
    )
    async with OrderbookClient(base_url=_BASE, transport=transport) as cow:
        with pytest.raises(OrderbookError) as ei:
            await cow.post_quote(_QUOTE_REQ)
    err = ei.value
    assert err.status_code == 400
    # Quote endpoint -> PriceEstimationError parsed.
    assert err.parsed is not None
    assert err.parsed.error_type == "InsufficientBalance"


@pytest.mark.asyncio
async def test_5xx_surface_as_error_after_retry_exhausted() -> None:
    call_count = 0

    def handler(_req: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(503)

    async with OrderbookClient(
        base_url=_BASE,
        transport=httpx.MockTransport(handler),
        max_retries=2,
    ) as cow:
        with pytest.raises(OrderbookError) as ei:
            await cow.get_auction()

    # max_retries=2 means 2 attempts total before reraise.
    assert call_count == 2
    assert ei.value.status_code == 503
    assert "retries exhausted" in str(ei.value)


@pytest.mark.asyncio
async def test_by_uids_rejects_oversized_batch() -> None:
    async with OrderbookClient(base_url=_BASE) as cow:
        too_many = ["0x" + "ab" * 56] * 129
        with pytest.raises(ValueError, match="max 128"):
            await cow.get_orders_by_uids(too_many)
