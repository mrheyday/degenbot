"""HTTP server for the CoW Solver Engine API.

Production-grade server-side driver per CoW protocol
openapi.yml:
<https://github.com/cowprotocol/services/blob/main/crates/solvers/openapi.yml>.
The CoW driver POSTs an `Auction` to `/solve`; we validate, dispatch
to `SolutionBuilder`, and return a `SolveResponse`.

## Endpoints

| Method | Path        | Handler                              |
|--------|-------------|--------------------------------------|
| POST   | `/solve`       | [`SolverEngineApp.handle_solve`]        |
| POST   | `/auction/build` | coordinator auction-build bridge      |
| POST   | `/d3/classify` | coordinator D3 classifier bridge        |
| GET    | `/health`      | liveness — returns 200 with build id    |
| GET    | `/metrics`     | Prometheus exposition                   |

## Architectural notes

* This module is pure protocol — knows nothing about strategy. All
  solving lives behind the injected `SolutionBuilder.build`.
* The aiohttp app is constructed with `CSRF/auth not yet wired` because
  CoW solvers run on a private network reachable only by the driver in
  the canonical deployment. Operators must enforce network ACLs.
* The legacy polling client (`CowSolverClient` in `main.py`) is
  deprecated by this server-side architecture — kept only as a stub
  reference until the next compaction removes it.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import structlog
from aiohttp import web
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    generate_latest,
)
from pydantic import ValidationError

from degenbot.auction_build import handle_auction_build_payload
from degenbot.cow.models import (
    Auction,
    DriverQuoteRequest,
    DriverQuoteResponse,
    Solution,
    SolveResponse,
)
from degenbot.d3_bridge import handle_d3_classify_payload
from degenbot.quote_engine.http_client import QuoteRequest
from degenbot.utils.metrics import SOLVE_LATENCY, SOLVE_REQUESTS

if TYPE_CHECKING:
    from degenbot.cow.submitter import CompetitionSubmitter
    from degenbot.quote_engine import QuoteEngineClient
    from degenbot.strategies_solver.solver_quality import Solution as StrategySolution
    from degenbot.strategies_solver.solver_quality import SolutionBuilder

log = structlog.get_logger(__name__).bind(service="solver", component="server")


SolutionAdapter = Callable[[Auction, "StrategySolution"], dict[str, Any]]
"""Adapter that converts the strategy's `Solution` into a wire dict
matching the `Solution` schema. Defaults to a passthrough when the
strategy emits a model with the right shape; production strategies that
emit a richer internal `Solution` use this hook to project to the wire.

The hook keeps the strategy free of CoW protocol details and the server
free of strategy details.
"""


def default_solution_adapter(
    _auction: Auction,
    solution: StrategySolution,
) -> dict[str, Any]:
    """Convert the strategy's Solution to a wire dict.

    The strategy's `Solution` carries a pre-built `protocol_solution`
    model which we project to a wire dict.
    """
    wire = SolveResponse(solutions=[solution.protocol_solution]).model_dump_wire()
    solutions = wire.get("solutions")
    if not isinstance(solutions, list) or not solutions or not isinstance(solutions[0], dict):
        msg = "strategy solution serialized to an invalid wire shape"
        raise ValueError(msg)
    return solutions[0]


class SolverEngineApp:
    """aiohttp Application wrapping the Solver Engine API surface.

    Construction is dep-injection-friendly: pass the `SolutionBuilder`
    and (optionally) a custom `SolutionAdapter`. Tests inject stubs.
    Production wires `SolutionBuilder` from `main._run_loop`.
    """

    def __init__(
        self,
        builder: SolutionBuilder,
        submitter: CompetitionSubmitter | None = None,
        *,
        solution_adapter: SolutionAdapter = default_solution_adapter,
        build_id: str = "dev",
        quote_engine: QuoteEngineClient | None = None,
        solver_address: str = "0x0000000000000000000000000000000000000000",
    ) -> None:
        self._builder = builder
        self._submitter = submitter
        self._solution_adapter = solution_adapter
        self._build_id = build_id
        self._quote_engine = quote_engine
        self._solver_address = solver_address

    def make_app(self) -> web.Application:
        """Build the aiohttp Application with all routes registered."""
        app = web.Application()
        app.router.add_get("/quote", self.handle_quote)
        app.router.add_post("/solve", self.handle_solve)
        app.router.add_post("/auction/build", self.handle_auction_build)
        app.router.add_post("/d3/classify", self.handle_d3_classify)
        app.router.add_get("/health", self.handle_health)
        app.router.add_get("/metrics", self.handle_metrics)
        return app

    # -- Handlers ----------------------------------------------------------

    async def handle_quote(self, request: web.Request) -> web.Response:
        """GET /quote — price-estimation per CoW Driver OpenAPI.

        Query params: `sellToken`, `buyToken`, `kind`, `amount`, `deadline`.
        Returns the JIT-aware `QuoteResponse` shape on success, or the
        `Error` shape (`kind` + `description`) with HTTP 400 on
        validation failure or unfulfillable quote.

        Dispatches the validated request through `QuoteEngineClient` to
        the coordinator's aggregator fanout. The aggregator's filled
        sell/buy amounts are projected into CoW's uniform-price form:

            clearingPrices[sellToken] = buyAmount
            clearingPrices[buyToken]  = sellAmount

        Per-route interactions, JIT orders, pre/post-interactions,
        `txOrigin` are left unset — those describe richer plans we
        don't synthesise here. Only `clearingPrices` and `solver` are
        required by the spec.
        """
        try:
            params = DriverQuoteRequest.model_validate(dict(request.query))
        except ValidationError as err:
            return _quote_error(400, "InvalidQuery", _describe_validation_error(err))

        log.info(
            "quote_received",
            sell_token=params.sell_token,
            buy_token=params.buy_token,
            kind=params.kind,
            amount=str(params.amount),
        )

        if self._quote_engine is None:
            return _quote_error(
                400,
                "QuoteNotPossible",
                "quote engine not configured",
            )

        qe_request = QuoteRequest(
            sell_token=params.sell_token,
            buy_token=params.buy_token,
            sell_amount=str(params.amount),
            kind=params.kind,
        )
        try:
            quote = await self._quote_engine.quote(qe_request)
        except Exception as err:  # pylint: disable=broad-exception-caught
            log.warning(
                "quote_engine_failed",
                error=str(err),
                sell_token=params.sell_token,
                buy_token=params.buy_token,
            )
            return _quote_error(400, "QuoteNotPossible", str(err) or "quote engine failed")

        try:
            sell_amount = int(quote.sell_amount)
            buy_amount = int(quote.buy_amount)
        except (TypeError, ValueError) as err:
            return _quote_error(400, "QuoteNotPossible", f"invalid quote amounts: {err}")

        # For sell-kind the user fixes the sell side; for buy-kind the user
        # fixes the buy side. Honour the request's anchor exactly so the
        # CoW driver's surplus math lines up with the auctioneer's view.
        if params.kind == "sell":
            sell_amount = int(params.amount)
        else:
            buy_amount = int(params.amount)

        if sell_amount <= 0 or buy_amount <= 0:
            return _quote_error(
                400,
                "QuoteNotPossible",
                "non-positive clearing amounts",
            )

        response = DriverQuoteResponse(
            clearing_prices={
                params.sell_token: buy_amount,
                params.buy_token: sell_amount,
            },
            solver=self._solver_address,
            gas=quote.estimated_gas or None,
        )
        return web.json_response(response.model_dump_wire())

    async def handle_d3_classify(self, request: web.Request) -> web.Response:
        """POST /d3/classify — coordinator D3 classifier bridge."""
        try:
            raw = await request.json()
        except (TypeError, ValueError, json.JSONDecodeError) as err:
            return _error_response(400, "malformed_json", str(err))

        try:
            response = handle_d3_classify_payload(raw)
            return web.json_response(response.model_dump(by_alias=True))
        except ValidationError as err:
            return _error_response(400, "schema_violation", err.errors())

    async def handle_auction_build(self, request: web.Request) -> web.Response:
        """POST /auction/build — coordinator-bridge entrypoint."""
        try:
            raw = await request.json()
        except (TypeError, ValueError, json.JSONDecodeError) as err:
            return _error_response(400, "malformed_json", str(err))

        try:
            response = await handle_auction_build_payload(raw, self._builder, self._submitter)
            return web.json_response(response.model_dump(by_alias=True, exclude_none=True))
        except ValidationError as err:
            return _error_response(400, "schema_violation", err.errors())
        except Exception as err:  # pylint: disable=broad-exception-caught
            log.exception("auction_build_failed", error=str(err))
            return _error_response(500, "internal_error", str(err))

    async def handle_solve(self, request: web.Request) -> web.Response:
        """POST /solve — validate Auction, dispatch, return SolveResponse.

        Outcome counters: every exit increments `SOLVE_REQUESTS` exactly
        once via the `outcome` label. The label values are stable contract
        for the operator dashboard.
        """
        with SOLVE_LATENCY.time():
            return await self._handle_solve_inner(request)

    async def _handle_solve_inner(self, request: web.Request) -> web.Response:
        # Stage 1: parse JSON
        try:
            raw = await request.json()
        except (TypeError, ValueError, json.JSONDecodeError) as err:
            SOLVE_REQUESTS.labels(outcome="malformed_json").inc()
            log.warning("solve_malformed_json", error=str(err))
            return _error_response(400, "malformed_json", str(err))

        # Stage 2: schema-validate the auction body
        try:
            auction = Auction.model_validate(raw)
        except ValidationError as err:
            SOLVE_REQUESTS.labels(outcome="schema_violation").inc()
            log.warning(
                "solve_schema_violation",
                errors=err.errors(),
                auction_id=raw.get("id") if isinstance(raw, dict) else None,
            )
            return _error_response(400, "schema_violation", err.errors())

        log.info(
            "solve_received",
            auction_id=auction.id,
            order_count=len(auction.orders),
            liquidity_count=len(auction.liquidity),
            deadline=auction.deadline.isoformat(),
        )

        # Stage 3: produce the strategy-side Solution (or None)
        strategy_solution = await self._build_strategy_solution(auction)
        if strategy_solution is None:
            return _solve_response(SolveResponse(solutions=[]))

        # Stage 4: convert + validate outbound
        validated = self._project_outbound(auction, strategy_solution)
        if validated is None:
            return _solve_response(SolveResponse(solutions=[]))

        SOLVE_REQUESTS.labels(outcome="ok").inc()
        return _solve_response(SolveResponse(solutions=[validated]))

    async def _build_strategy_solution(
        self,
        auction: Auction,
    ) -> StrategySolution | None:
        """Run the SolutionBuilder. Returns None on any failure (logged)."""
        try:
            return await self._builder.build(auction)
        except NotImplementedError:
            # Scaffolded builder — return empty solutions, NOT 500. This
            # is the production-correct degenerate path: a solver that's
            # online but has no solving logic yet.
            SOLVE_REQUESTS.labels(outcome="empty_no_builder").inc()
            return None
        # pylint: disable=broad-exception-caught
        except Exception as err:
            # Strategy threw — return empty (better than 500 because the
            # CoW driver retries empty cleanly; 500 accumulates as
            # solver-error and may trigger blacklist).
            SOLVE_REQUESTS.labels(outcome="builder_error").inc()
            log.exception(
                "solve_builder_error",
                auction_id=auction.id,
                error=str(err),
            )
            return None

    def _project_outbound(
        self,
        auction: Auction,
        strategy_solution: StrategySolution,
    ) -> Solution | None:
        """Adapt the strategy result to a wire Solution. None on failure."""
        try:
            wire_solution = self._solution_adapter(auction, strategy_solution)
        except (KeyError, OverflowError, ValueError, TypeError) as err:
            SOLVE_REQUESTS.labels(outcome="adapter_error").inc()
            log.exception(
                "solve_adapter_error",
                auction_id=auction.id,
                error=str(err),
            )
            return None

        try:
            return _validate_outbound(wire_solution)
        except ValidationError as err:
            # Strategy produced something we can't ship — refuse rather
            # than risk submitting malformed work.
            SOLVE_REQUESTS.labels(outcome="invalid_outbound").inc()
            log.exception(
                "solve_invalid_outbound",
                auction_id=auction.id,
                errors=err.errors(),
            )
            return None

    async def handle_health(self, _request: web.Request) -> web.Response:
        """GET /health — liveness probe."""
        return web.json_response({"status": "ok", "build": self._build_id})

    async def handle_metrics(self, _request: web.Request) -> web.Response:
        """GET /metrics — Prometheus exposition."""
        body = generate_latest()
        content_type = CONTENT_TYPE_LATEST.split(";", maxsplit=1)[0]
        return web.Response(body=body, content_type=content_type)

    # -- Lifecycle ---------------------------------------------------------

    async def serve(self, host: str, port: int) -> None:
        """Run the server forever.

        Cancellation cleanly shuts the runner down. Use this from
        `main._run_loop` rather than `web.run_app` so the caller keeps
        control over the asyncio event loop and can multiplex other
        services (e.g. a degenbot IPC adapter).
        """
        app = self.make_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=host, port=port)
        await site.start()
        log.info("solver_engine_listening", host=host, port=port)
        try:
            # Block forever. Caller cancels to shut down.
            await _forever()
        finally:
            await runner.cleanup()
            log.info("solver_engine_shutdown")


# -- Internal helpers --------------------------------------------------------


async def _forever() -> None:
    """Sleep forever; cancellable."""
    await asyncio.Event().wait()


def _solve_response(body: SolveResponse) -> web.Response:
    """Serialize a SolveResponse to camelCase JSON with bigint→str."""
    return web.json_response(body.model_dump_wire())


def _error_response(status: int, code: str, detail: object) -> web.Response:
    """Standard error envelope."""
    return web.json_response(
        {"error": {"code": code, "detail": detail}},
        status=status,
    )


def _validate_outbound(wire_solution: dict[str, Any]) -> Solution:
    """Validate the strategy's wire dict against the Solution schema."""
    return Solution.model_validate(wire_solution)


def _quote_error(status: int, kind: str, description: str) -> web.Response:
    """`Error` envelope per CoW Driver spec (`kind` + `description`)."""
    return web.json_response({"kind": kind, "description": description}, status=status)


def _describe_validation_error(err: ValidationError) -> str:
    """Compress a pydantic ValidationError to a single human-readable line."""
    parts: list[str] = []
    for e in err.errors():
        loc = ".".join(str(p) for p in e.get("loc", ()))
        msg = e.get("msg", "invalid")
        parts.append(f"{loc}: {msg}" if loc else msg)
    return "; ".join(parts) or "validation failed"
