"""Tests for the `GET /quote` route on SolverEngineApp.

Validates the CoW Driver OpenAPI contract:
<https://github.com/cowprotocol/services/blob/main/crates/driver/openapi.yml>.

* Query params: `sellToken`, `buyToken`, `kind`, `amount`, `deadline`.
* 200 success returns the JIT-aware `QuoteResponse` shape
  (`clearingPrices` + `solver` required).
* 400 failures return the spec's `Error` envelope (`kind` + `description`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from aiohttp.test_utils import TestClient, TestServer
from degenbot.protocol import Auction  # noqa: TC002 — runtime stub use
from degenbot.quote_engine import AggregatorQuote, QuoteRequest
from degenbot.server import SolverEngineApp

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from aiohttp.web import Application, Request
    from degenbot.strategies_solver.solver_quality import Solution as StrategySolution


SOLVER_ADDRESS = "0x" + "ab" * 20
SELL_TOKEN = "0x" + "11" * 20
BUY_TOKEN = "0x" + "22" * 20


class _BuilderEmpty:
    async def build(self, _auction: Auction) -> StrategySolution | None:
        return None


class _StubQuoteEngine:
    """Test double for `QuoteEngineClient` — captures the last request."""

    def __init__(
        self,
        result: AggregatorQuote | None = None,
        exc: Exception | None = None,
    ) -> None:
        self._result = result
        self._exc = exc
        self.last_request: QuoteRequest | None = None

    async def quote(self, request: QuoteRequest) -> AggregatorQuote:
        self.last_request = request
        if self._exc is not None:
            raise self._exc
        assert self._result is not None
        return self._result


def _make_client(
    quote_engine: _StubQuoteEngine | None,
) -> tuple[TestClient[Request, Application], _StubQuoteEngine | None]:
    app = SolverEngineApp(
        builder=_BuilderEmpty(),  # type: ignore[arg-type]
        build_id="test",
        solver_address=SOLVER_ADDRESS,
        quote_engine=quote_engine,  # type: ignore[arg-type]
    ).make_app()
    return TestClient(TestServer(app)), quote_engine


@pytest.fixture
async def quote_client() -> AsyncIterator[TestClient[Request, Application]]:
    # Happy-path fixture used by the simple 400-validation tests below.
    # Returns a 1:1 quote so existing assertions stay valid.
    stub = _StubQuoteEngine(
        result=AggregatorQuote(
            source="oneinch",
            sellAmount="1000000000000000000",
            buyAmount="1000000000000000000",
            router="0x" + "cc" * 20,
            calldata="0xdeadbeef",
            estimatedGas=210000,
        ),
    )
    client, _ = _make_client(stub)
    await client.start_server()
    yield client
    await client.close()


def _valid_params(**overrides: Any) -> dict[str, str]:
    params: dict[str, str] = {
        "sellToken": SELL_TOKEN,
        "buyToken": BUY_TOKEN,
        "kind": "sell",
        "amount": "1000000000000000000",
        "deadline": "2030-01-01T00:00:00Z",
    }
    params.update(overrides)
    return params


class TestQuoteHappyPath:
    async def test_sell_kind_maps_aggregator_quote_to_clearing_prices(
        self,
    ) -> None:
        stub = _StubQuoteEngine(
            result=AggregatorQuote(
                source="oneinch",
                sellAmount="1000000000000000000",
                buyAmount="2500000000",
                router="0x" + "cc" * 20,
                calldata="0xdeadbeef",
                estimatedGas=210000,
            ),
        )
        client, _ = _make_client(stub)
        await client.start_server()
        try:
            resp = await client.get("/quote", params=_valid_params())
            assert resp.status == 200
            body = await resp.json()
            assert body["solver"] == SOLVER_ADDRESS
            # Uniform-price form: sellToken priced in buy units, vice versa.
            # `_to_wire` keeps ints below 2**32 as numbers; large ints as
            # decimal strings. 2_500_000_000 is below the cutoff.
            assert int(body["clearingPrices"][SELL_TOKEN]) == 2_500_000_000
            assert body["clearingPrices"][BUY_TOKEN] == "1000000000000000000"
            assert body["gas"] == 210000
            # Coordinator request shape carried through unchanged.
            assert stub.last_request is not None
            assert stub.last_request.kind == "sell"
            assert stub.last_request.sell_amount == "1000000000000000000"
        finally:
            await client.close()

    async def test_buy_kind_anchors_buy_amount_to_request(self) -> None:
        # In buy-kind the user fixes buyAmount; aggregator returns the
        # sell side. The handler must respect the request's anchor and
        # project the spec's uniform-price mapping accordingly.
        stub = _StubQuoteEngine(
            result=AggregatorQuote(
                source="zerox",
                sellAmount="500000000000000000",
                buyAmount="1000000000",  # ignored — buy-kind anchors on request
                router="0x" + "cc" * 20,
                calldata="0xfeed",
                estimatedGas=180000,
            ),
        )
        client, _ = _make_client(stub)
        await client.start_server()
        try:
            resp = await client.get(
                "/quote",
                params=_valid_params(kind="buy", amount="2500000000"),
            )
            assert resp.status == 200
            body = await resp.json()
            # Anchor: buyAmount = request.amount = 2_500_000_000.
            # clearingPrices[sellToken] = buyAmount, [buyToken] = sellAmount.
            assert int(body["clearingPrices"][SELL_TOKEN]) == 2_500_000_000
            assert int(body["clearingPrices"][BUY_TOKEN]) == 500_000_000_000_000_000
            assert body["gas"] == 180000
            assert stub.last_request is not None
            assert stub.last_request.kind == "buy"
        finally:
            await client.close()

    async def test_quote_engine_raises_returns_quote_not_possible(self) -> None:
        stub = _StubQuoteEngine(exc=RuntimeError("no liquidity"))
        client, _ = _make_client(stub)
        await client.start_server()
        try:
            resp = await client.get("/quote", params=_valid_params())
            assert resp.status == 400
            body = await resp.json()
            assert body["kind"] == "QuoteNotPossible"
            assert "no liquidity" in body["description"]
        finally:
            await client.close()

    async def test_missing_quote_engine_returns_quote_not_possible(self) -> None:
        client, _ = _make_client(None)
        await client.start_server()
        try:
            resp = await client.get("/quote", params=_valid_params())
            assert resp.status == 400
            body = await resp.json()
            assert body["kind"] == "QuoteNotPossible"
        finally:
            await client.close()

    async def test_zero_buy_amount_returns_quote_not_possible(self) -> None:
        stub = _StubQuoteEngine(
            result=AggregatorQuote(
                source="oneinch",
                sellAmount="1000000000000000000",
                buyAmount="0",
                router="0x" + "cc" * 20,
                calldata="0x",
                estimatedGas=0,
            ),
        )
        client, _ = _make_client(stub)
        await client.start_server()
        try:
            resp = await client.get("/quote", params=_valid_params())
            assert resp.status == 400
            body = await resp.json()
            assert body["kind"] == "QuoteNotPossible"
        finally:
            await client.close()


class TestQuoteErrors:
    async def test_missing_sell_token_returns_400_invalid_query(
        self,
        quote_client: TestClient[Request, Application],
    ) -> None:
        params = _valid_params()
        del params["sellToken"]
        resp = await quote_client.get("/quote", params=params)
        assert resp.status == 400
        body = await resp.json()
        assert body["kind"] == "InvalidQuery"
        assert "sellToken" in body["description"] or "sell_token" in body["description"]

    async def test_bad_kind_returns_400_invalid_query(
        self,
        quote_client: TestClient[Request, Application],
    ) -> None:
        resp = await quote_client.get("/quote", params=_valid_params(kind="swap"))
        assert resp.status == 400
        body = await resp.json()
        assert body["kind"] == "InvalidQuery"

    async def test_non_numeric_amount_returns_400_invalid_query(
        self,
        quote_client: TestClient[Request, Application],
    ) -> None:
        resp = await quote_client.get("/quote", params=_valid_params(amount="abc"))
        assert resp.status == 400
        body = await resp.json()
        assert body["kind"] == "InvalidQuery"

    async def test_bad_deadline_returns_400_invalid_query(
        self,
        quote_client: TestClient[Request, Application],
    ) -> None:
        resp = await quote_client.get("/quote", params=_valid_params(deadline="not-a-date"))
        assert resp.status == 400
        body = await resp.json()
        assert body["kind"] == "InvalidQuery"
