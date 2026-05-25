"""End-to-end tests for the SolverEngineApp HTTP surface.

Spins up the aiohttp test client and POSTs canonical CoW Solver Engine
payloads to validate the production driver path. No live RPC; the
SolutionBuilder is stubbed so the strategy plane stays orthogonal.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from aiohttp.test_utils import TestClient, TestServer

from degenbot.server import SolverEngineApp
from degenbot.strategies_solver.solver_quality import Solution as StrategySolution

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from aiohttp.web import Application, Request

    from degenbot.protocol import Auction

DATA_DIR = Path(__file__).parent / "data"


# -- stub builders ----------------------------------------------------------


class _BuilderEmpty:
    """No-op builder — the production-degenerate case ('I have nothing')."""

    async def build(self, _auction: Auction) -> StrategySolution | None:
        return None


class _BuilderNotImplemented:
    """Models the scaffold case where build() raises NotImplementedError."""

    async def build(self, _auction: Auction) -> StrategySolution | None:
        msg = "scaffold"
        raise NotImplementedError(msg)


class _BuilderRaises:
    """Models a strategy bug — random exception."""

    async def build(self, _auction: Auction) -> StrategySolution | None:
        msg = "boom"
        raise RuntimeError(msg)


class _BuilderProduces:
    """Returns a Solution with a fully-formed payload."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    async def build(self, _auction: Auction) -> StrategySolution | None:
        return StrategySolution(
            auction_id="x",
            estimated_profit_usd=10.0,
            payload=self._payload,
        )


# -- fixtures ---------------------------------------------------------------


@pytest.fixture
def auction_body() -> dict[str, Any]:
    body: dict[str, Any] = json.loads((DATA_DIR / "auction_minimal.json").read_text())
    return body


@pytest.fixture
async def empty_client() -> AsyncIterator[TestClient[Request, Application]]:
    app = SolverEngineApp(builder=_BuilderEmpty(), build_id="test").make_app()  # type: ignore[arg-type]
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    yield client
    await client.close()


# -- /solve happy path ------------------------------------------------------


class TestSolveHappyPath:
    async def test_no_solution_returns_empty_solutions_array(
        self,
        empty_client: TestClient[Request, Application],
        auction_body: dict[str, Any],
    ) -> None:
        resp = await empty_client.post("/solve", json=auction_body)
        assert resp.status == 200
        body = await resp.json()
        assert body == {"solutions": []}

    async def test_scaffolded_builder_returns_empty_not_500(
        self,
        auction_body: dict[str, Any],
    ) -> None:
        # NotImplementedError must NOT bubble as a 500 — the production
        # path is "stay online with empty solutions" until the strategy
        # plane lands.
        app = SolverEngineApp(builder=_BuilderNotImplemented(), build_id="t").make_app()  # type: ignore[arg-type]
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        try:
            resp = await client.post("/solve", json=auction_body)
            assert resp.status == 200
            body = await resp.json()
            assert body == {"solutions": []}
        finally:
            await client.close()

    async def test_arbitrary_builder_exception_returns_empty_not_500(
        self,
        auction_body: dict[str, Any],
    ) -> None:
        app = SolverEngineApp(builder=_BuilderRaises(), build_id="t").make_app()  # type: ignore[arg-type]
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        try:
            resp = await client.post("/solve", json=auction_body)
            assert resp.status == 200
            body = await resp.json()
            assert body == {"solutions": []}
        finally:
            await client.close()

    async def test_well_formed_solution_round_trips(
        self,
        auction_body: dict[str, Any],
    ) -> None:
        payload = {
            "id": 42,
            "prices": {
                "0x1111111111111111111111111111111111111111": "1000000000000000000",
                "0x2222222222222222222222222222222222222222": "500000000000000000",
            },
            "trades": [],
            "interactions": [],
            "gas": 250_000,
        }
        app = SolverEngineApp(
            builder=_BuilderProduces(payload),  # type: ignore[arg-type]
            build_id="t",
        ).make_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        try:
            resp = await client.post("/solve", json=auction_body)
            assert resp.status == 200
            body = await resp.json()
            assert len(body["solutions"]) == 1
            sol = body["solutions"][0]
            assert sol["id"] == 42
            assert sol["gas"] == 250_000
            # Prices > 2**32 must be emitted as decimal strings.
            assert isinstance(
                sol["prices"]["0x1111111111111111111111111111111111111111"],
                str,
            )
        finally:
            await client.close()


# -- /solve error paths -----------------------------------------------------


class TestSolveErrors:
    async def test_malformed_json_returns_400(
        self, empty_client: TestClient[Request, Application]
    ) -> None:
        resp = await empty_client.post(
            "/solve",
            data="not valid json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status == 400
        body = await resp.json()
        assert body["error"]["code"] == "malformed_json"

    async def test_missing_required_field_returns_400_schema_violation(
        self,
        empty_client: TestClient[Request, Application],
        auction_body: dict[str, Any],
    ) -> None:
        del auction_body["effectiveGasPrice"]
        resp = await empty_client.post("/solve", json=auction_body)
        assert resp.status == 400
        body = await resp.json()
        assert body["error"]["code"] == "schema_violation"

    async def test_invalid_deadline_returns_400(
        self,
        empty_client: TestClient[Request, Application],
        auction_body: dict[str, Any],
    ) -> None:
        auction_body["deadline"] = "not-a-date"
        resp = await empty_client.post("/solve", json=auction_body)
        assert resp.status == 400


# -- /d3/classify -----------------------------------------------------------


class TestD3Classify:
    async def test_d3_classify_accepts_json_safe_order(
        self,
        empty_client: TestClient[Request, Application],
    ) -> None:
        resp = await empty_client.post(
            "/d3/classify",
            json={
                "classification": "amm_routed",
                "reason": "no_price_compatible_opposing_order",
                "order": {
                    "uid": "0x" + "01" * 56,
                    "owner": "0x" + "aa" * 20,
                    "sellToken": "0x" + "11" * 20,
                    "buyToken": "0x" + "22" * 20,
                    "sellAmount": "100",
                    "buyAmount": "90",
                    "feeAmount": "1",
                    "validTo": 2_000_000_000,
                    "kind": "sell",
                    "partiallyFillable": True,
                    "signingScheme": "eip712",
                    "signature": "0x1234",
                    "appData": "0x" + "00" * 32,
                },
            },
        )

        assert resp.status == 200
        body = await resp.json()
        assert body == {
            "status": "accepted",
            "shouldBid": True,
            "reason": "no_price_compatible_opposing_order",
        }

    async def test_d3_classify_rejects_malformed_payload(
        self,
        empty_client: TestClient[Request, Application],
    ) -> None:
        resp = await empty_client.post("/d3/classify", json={"classification": "amm_routed"})

        assert resp.status == 400
        body = await resp.json()
        assert body["error"]["code"] == "schema_violation"


# -- /health and /metrics ---------------------------------------------------


class TestSidecarEndpoints:
    async def test_health_returns_build_id(
        self, empty_client: TestClient[Request, Application]
    ) -> None:
        resp = await empty_client.get("/health")
        assert resp.status == 200
        body = await resp.json()
        assert body == {"status": "ok", "build": "test"}

    async def test_metrics_exposes_prometheus_format(
        self,
        empty_client: TestClient[Request, Application],
        auction_body: dict[str, Any],
    ) -> None:
        # Drive one request so the counter has something to report.
        await empty_client.post("/solve", json=auction_body)
        resp = await empty_client.get("/metrics")
        assert resp.status == 200
        text = await resp.text()
        assert "solver_solve_requests_total" in text
        assert "solver_solve_latency_seconds" in text
