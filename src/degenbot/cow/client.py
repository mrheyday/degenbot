"""Async HTTP client for the CoW Protocol orderbook REST API.

See `solver/driver/orderbook/__init__.py` for the API surface; spec at
[`cowprotocol/services::crates/orderbook/openapi.yml`](
https://github.com/cowprotocol/services/blob/main/crates/orderbook/openapi.yml).

All methods are `async` and return typed pydantic models. HTTP errors
surface as [`OrderbookError`] with the response body parsed into the
appropriate error model when possible.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

import httpx
from pydantic import TypeAdapter
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from degenbot.orderbook.models import (
    Auction,
    CompetitionSolution,
    NativePriceResponse,
    Order,
    OrderCreation,
    OrderPostError,
    OrderQuoteRequest,
    OrderQuoteResponse,
    PriceEstimationError,
    SolverCompetitionResponse,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from types import TracebackType

DEFAULT_BASE_URL = "https://api.cow.fi/arbitrum_one"
DEFAULT_TIMEOUT_SEC = 10.0
"""Conservative — most reads return < 100 ms; quote can spike to 3-5 s under load."""

_RETRYABLE_STATUS = frozenset({429, 502, 503, 504})


class OrderbookError(Exception):
    """Wraps any non-2xx response or transport failure.

    Carries the HTTP status, raw body, and (when parseable) the typed
    error model from the OpenAPI spec.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        body: str | None = None,
        parsed: OrderPostError | PriceEstimationError | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body
        self.parsed = parsed

    def __repr__(self) -> str:  # pragma: no cover — debugging only
        return (
            f"OrderbookError({self.args[0]!r}, status={self.status_code}, parsed={self.parsed!r})"
        )


_ORDER_LIST = TypeAdapter(list[Order])


class OrderbookClient:
    """Async client for the CoW Protocol orderbook.

    Use as an async context manager:

        async with OrderbookClient(base_url=...) as cow:
            quote = await cow.post_quote(req)
    """

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout_sec: float = DEFAULT_TIMEOUT_SEC,
        api_key: str | None = None,
        # Allow injecting a transport for tests (httpx.MockTransport).
        transport: httpx.AsyncBaseTransport | None = None,
        max_retries: int = 3,
    ) -> None:
        headers: dict[str, str] = {
            "accept": "application/json",
            "content-type": "application/json",
        }
        if api_key:
            headers["x-api-key"] = api_key
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout_sec,
            headers=headers,
            transport=transport,
        )
        self._max_retries = max_retries

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    # ─── Auction / batch ────────────────────────────────────────────────

    async def get_auction(self) -> Auction:
        """`GET /api/v1/auction`. Permissioned (solver-only)."""
        resp = await self._request("GET", "/api/v1/auction")
        return Auction.model_validate(resp.json())

    # ─── Orders ─────────────────────────────────────────────────────────

    async def post_order(self, creation: OrderCreation) -> str:
        """`POST /api/v1/orders` — create order. Returns the new order UID."""
        body = creation.model_dump(by_alias=True, exclude_none=True, mode="json")
        resp = await self._request("POST", "/api/v1/orders", json=body)
        # Body is just the UID string with surrounding quotes.
        return resp.json()  # type: ignore[no-any-return]

    async def get_order(self, uid: str) -> Order:
        """`GET /api/v1/orders/{UID}`."""
        resp = await self._request("GET", f"/api/v1/orders/{uid}")
        return Order.model_validate(resp.json())

    async def get_orders_by_uids(self, uids: Sequence[str]) -> list[Order]:
        """`POST /api/v1/orders/by_uids`. Up to 128 UIDs per call."""
        if len(uids) > 128:
            msg = "get_orders_by_uids: max 128 UIDs per call"
            raise ValueError(msg)
        resp = await self._request(
            "POST",
            "/api/v1/orders/by_uids",
            json={"uids": list(uids)},
        )
        return _ORDER_LIST.validate_python(resp.json())

    # ─── Quote ──────────────────────────────────────────────────────────

    async def post_quote(self, req: OrderQuoteRequest) -> OrderQuoteResponse:
        """`POST /api/v1/quote` — price + fee quote for prospective order."""
        body = req.model_dump(by_alias=True, exclude_none=True, mode="json")
        resp = await self._request("POST", "/api/v1/quote", json=body)
        return OrderQuoteResponse.model_validate(resp.json())

    # ─── Native price ───────────────────────────────────────────────────

    async def get_native_price(self, token: str) -> NativePriceResponse:
        """`GET /api/v1/token/{token}/native_price`."""
        resp = await self._request("GET", f"/api/v1/token/{token}/native_price")
        return NativePriceResponse.model_validate(resp.json())

    # ─── Solver competition ─────────────────────────────────────────────

    async def post_competition_solution(self, solution: CompetitionSolution) -> str:
        """`POST /api/v1/competition/solutions`. External solver submission."""
        body = solution.model_dump_wire()
        resp = await self._request("POST", "/api/v1/competition/solutions", json=body)
        return resp.text

    async def get_latest_competition(self) -> SolverCompetitionResponse:
        """`GET /api/v2/solver_competition/latest`."""
        resp = await self._request("GET", "/api/v2/solver_competition/latest")
        return SolverCompetitionResponse.model_validate(resp.json())

    async def get_competition_by_tx(self, tx_hash: str) -> SolverCompetitionResponse:
        """`GET /api/v2/solver_competition/by_tx_hash/{tx_hash}`."""
        resp = await self._request(
            "GET",
            f"/api/v2/solver_competition/by_tx_hash/{tx_hash}",
        )
        return SolverCompetitionResponse.model_validate(resp.json())

    # ─── Internal: HTTP with retry + typed error handling ───────────────

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Mapping[str, object] | Sequence[object] | None = None,
    ) -> httpx.Response:
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self._max_retries),
                wait=wait_exponential(multiplier=0.25, min=0.25, max=4.0),
                retry=retry_if_exception_type(_RetryableTransportError),
                reraise=True,
            ):
                with attempt:
                    resp = await self._client.request(method, path, json=json)
                    if resp.status_code in _RETRYABLE_STATUS:
                        raise _RetryableTransportError(resp.status_code, resp.text)
                    if resp.status_code >= 400:
                        raise _to_orderbook_error(resp)
                    return resp
        except _RetryableTransportError as exhausted:
            msg = f"{method} {path} -> HTTP {exhausted.status} (retries exhausted)"
            raise OrderbookError(
                msg,
                status_code=exhausted.status,
                body=exhausted.body,
            ) from exhausted
        # Unreachable: AsyncRetrying always either returns inside the loop
        # or raises on exhaustion (handled above).
        msg = "retry loop exited without response"
        raise OrderbookError(msg)  # pragma: no cover


class _RetryableTransportError(Exception):
    """Internal sentinel — not exposed to callers."""

    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"retryable HTTP {status}")
        self.status = status
        self.body = body


def _to_orderbook_error(resp: httpx.Response) -> OrderbookError:
    body = resp.text
    parsed: OrderPostError | PriceEstimationError | None = None
    try:
        data = resp.json()
        if isinstance(data, dict) and "errorType" in data:
            # Both schemas share the same wire shape; pick by path semantic.
            if "/quote" in str(resp.url):
                parsed = PriceEstimationError.model_validate(data)
            else:
                parsed = OrderPostError.model_validate(data)
    except (ValueError, KeyError, TypeError):  # JSON or schema mismatch — leave parsed None
        pass
    return OrderbookError(
        f"{resp.request.method} {resp.url.path} -> HTTP {resp.status_code}",
        status_code=resp.status_code,
        body=body,
        parsed=parsed,
    )
