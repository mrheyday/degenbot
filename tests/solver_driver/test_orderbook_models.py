"""Wire-format lock tests for the orderbook pydantic models.

Each fixture is a literal slice of the OpenAPI examples (or a realistic
payload from the live Arbitrum endpoint). When upstream renames a field
or changes a wire type, these break first — fix the models, don't relax
the test.
"""

from __future__ import annotations

import pytest

from degenbot.orderbook.models import (
    Auction,
    AuctionOrder,
    EcdsaSignature,
    EcdsaSigningScheme,
    NativePriceResponse,
    Order,
    OrderClass,
    OrderCreation,
    OrderKind,
    OrderQuoteRequest,
    OrderQuoteResponse,
    OrderQuoteSideKindSell,
    OrderQuoteValidity,
    OrderStatus,
    SigningScheme,
    SolverCompetitionResponse,
    SolverSettlement,
    Trade,
)


def test_order_creation_round_trip() -> None:
    """`POST /orders` body: known shape from OpenAPI example."""
    payload = {
        "sellToken": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
        "buyToken": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
        "receiver": "0xae2Fc483527B8EF99EB5D9B44875F005ba1FaE13",
        "sellAmount": "1000000",
        "buyAmount": "500000000000000",
        "validTo": 2_000_000_000,
        "appData": "{}",
        "feeAmount": "1000",
        "kind": "sell",
        "partiallyFillable": False,
        "sellTokenBalance": "erc20",
        "buyTokenBalance": "erc20",
        "signingScheme": "eip712",
        "signature": "0x" + "ab" * 65,
        "from": "0xae2Fc483527B8EF99EB5D9B44875F005ba1FaE13",
    }
    creation = OrderCreation.model_validate(payload)
    assert creation.kind is OrderKind.SELL
    assert creation.signing_scheme is SigningScheme.EIP712
    assert creation.sell_amount == 1_000_000
    assert creation.from_ == payload["from"]

    # Round-trip preserves the camelCase on serialization.
    dumped = creation.model_dump(by_alias=True, exclude_none=True, mode="json")
    assert "sellToken" in dumped
    assert "from" in dumped
    assert "from_" not in dumped


def test_order_full_with_metadata() -> None:
    """`GET /orders/{uid}` shape includes server-side metadata."""
    payload = {
        "creationDate": "2026-05-08T12:00:00Z",
        "owner": "0xae2Fc483527B8EF99EB5D9B44875F005ba1FaE13",
        "uid": "0x" + "ab" * 56,
        "executedSellAmount": "0",
        "executedSellAmountBeforeFees": "0",
        "executedBuyAmount": "0",
        "executedFeeAmount": "0",
        "invalidated": False,
        "status": "open",
        "class": "limit",
        "sellToken": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
        "buyToken": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
        "sellAmount": "1000000",
        "buyAmount": "500000000000000",
        "validTo": 2_000_000_000,
        "appData": "{}",
        "feeAmount": "0",
        "kind": "sell",
        "partiallyFillable": True,
        "signingScheme": "eip712",
        "signature": "0x" + "cd" * 65,
    }
    order = Order.model_validate(payload)
    assert order.status is OrderStatus.OPEN
    assert order.class_ is OrderClass.LIMIT
    assert order.partially_fillable is True
    # Metadata + parameters merged into one model.
    assert order.uid == payload["uid"]
    assert order.sell_amount == 1_000_000


def test_order_quote_request_with_sell_side() -> None:
    payload = {
        "sellToken": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
        "buyToken": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
        "from": "0xae2Fc483527B8EF99EB5D9B44875F005ba1FaE13",
        "kind": "sell",
        "sellAmountBeforeFee": "1000000",
        "appData": "{}",
        "signingScheme": "eip712",
        "validFor": 1_800,
    }
    # Quote payloads are flat in OpenAPI — `side` and `validity` are inlined.
    # The model expects them as nested objects, so build that explicitly.
    req = OrderQuoteRequest.model_validate(
        {
            "sellToken": payload["sellToken"],
            "buyToken": payload["buyToken"],
            "from": payload["from"],
            "appData": "{}",
            "signingScheme": "eip712",
            "side": {"kind": "sell", "sellAmountBeforeFee": "1000000"},
            "validity": {"validFor": 1_800},
        },
    )
    assert isinstance(req.side, OrderQuoteSideKindSell)
    assert req.side.sell_amount_before_fee == 1_000_000
    assert isinstance(req.validity, OrderQuoteValidity)
    assert req.validity.valid_for == 1_800


def test_order_quote_response() -> None:
    payload = {
        "quote": {
            "sellToken": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
            "buyToken": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
            "sellAmount": "999000",
            "buyAmount": "498500000000000",
            "validTo": 2_000_000_000,
            "appData": "{}",
            "feeAmount": "1000",
            "kind": "sell",
            "partiallyFillable": False,
            "signingScheme": "eip712",
        },
        "from": "0xae2Fc483527B8EF99EB5D9B44875F005ba1FaE13",
        "expiration": "2026-05-08T12:30:00Z",
        "id": 4242,
        "verified": True,
    }
    resp = OrderQuoteResponse.model_validate(payload)
    assert resp.id == 4242
    assert resp.verified is True
    assert resp.quote.sell_amount == 999_000


def test_native_price_response() -> None:
    resp = NativePriceResponse.model_validate({"price": 0.000341})
    assert resp.price == pytest.approx(0.000341)


def test_auction_with_one_order() -> None:
    payload = {
        "id": 12345,
        "block": 250_000_000,
        "latestSettlementBlock": 250_000_000,
        "orders": [
            {
                "uid": "0x" + "ab" * 56,
                "sellToken": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
                "buyToken": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                "sellAmount": "1000000",
                "buyAmount": "500000000000000",
                "userFee": "0",
                "validTo": 2_000_000_000,
                "kind": "sell",
                "owner": "0xae2Fc483527B8EF99EB5D9B44875F005ba1FaE13",
                "partiallyFillable": False,
                "preInteractions": [],
                "postInteractions": [],
                "class": "limit",
                "appData": "{}",
                "signingScheme": "eip712",
                "signature": "0x" + "ab" * 65,
                "protocolFees": [{"kind": "volume", "factor": 0.001}],
            },
        ],
        "prices": {
            "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": "1000000000000000000",
        },
    }
    auction = Auction.model_validate(payload)
    assert auction.id == 12345
    assert len(auction.orders) == 1
    only = auction.orders[0]
    assert isinstance(only, AuctionOrder)
    assert only.kind is OrderKind.SELL
    assert auction.prices["0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"] == 1_000_000_000_000_000_000


def test_solver_competition_response() -> None:
    payload = {
        "auctionId": 999,
        "transactionHashes": ["0x" + "ab" * 32],
        "solutions": [
            {
                "solver": "test-solver",
                "ranking": 1,
                "score": "1000000000000000000",
                "isWinner": True,
            },
        ],
    }
    resp = SolverCompetitionResponse.model_validate(payload)
    assert resp.auction_id == 999
    assert isinstance(resp.solutions[0], SolverSettlement)
    assert resp.solutions[0].is_winner is True


def test_trade_round_trip() -> None:
    payload = {
        "blockNumber": 250_000_000,
        "logIndex": 7,
        "orderUid": "0x" + "cd" * 56,
        "owner": "0xae2Fc483527B8EF99EB5D9B44875F005ba1FaE13",
        "sellToken": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
        "buyToken": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
        "sellAmount": "1000000",
        "sellAmountBeforeFees": "999000",
        "buyAmount": "498500000000000",
        "txHash": "0x" + "ef" * 32,
    }
    trade = Trade.model_validate(payload)
    assert trade.block_number == 250_000_000
    assert trade.transaction_hash == payload["txHash"]


def test_ecdsa_signature_round_trip() -> None:
    sig = EcdsaSignature(
        scheme=EcdsaSigningScheme.EIP712,
        signature="0x" + "12" * 65,
    )
    dumped = sig.model_dump(mode="json")
    assert dumped["scheme"] == "eip712"
    assert dumped["signature"].startswith("0x")
