"""HTTP client to the TS coordinator's quote engine.

The coordinator owns the 6-way aggregator fanout (1inch, 0x, Paraswap,
Odos, Kyber, OpenOcean) per spec §2.4 and ADR-010. The solver driver
asks the coordinator for the best quote rather than maintaining a
parallel set of API keys here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

import httpx
from pydantic import BaseModel, ConfigDict, Field
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

if TYPE_CHECKING:
    from types import TracebackType


class QuoteRequest(BaseModel):
    """Quote request payload."""

    chain_id: int = Field(default=42161, description="Arbitrum One.")
    sell_token: str = Field(..., description="Checksum address of the sell token.")
    buy_token: str = Field(..., description="Checksum address of the buy token.")
    sell_amount: str = Field(..., description="Sell amount as base-10 wei string.")
    # CoW supports both kinds; default to sell-amount-fixed.
    kind: str = Field(default="sell", description="`sell` (fixed sell) or `buy`.")


class AggregatorQuote(BaseModel):
    """Quote response payload returned by the coordinator."""

    model_config = ConfigDict(populate_by_name=True)

    source: str = Field(..., description="Aggregator that won the fanout.")
    sell_amount: str = Field(
        ..., alias="sellAmount", description="Sell amount as base-10 wei string."
    )
    buy_amount: str = Field(..., alias="buyAmount", description="Buy amount as base-10 wei string.")
    # Encoded calldata + router that the executor would call to realise the swap.
    router: str = Field(..., description="Aggregator router address.")
    calldata: str = Field(..., description="0x-prefixed calldata.")
    estimated_gas: int = Field(..., alias="estimatedGas", description="Estimated gas units.")


class QuoteEngineClient:
    """Async client for the coordinator's `/quote` endpoint."""

    def __init__(
        self,
        coordinator_url: str,
        timeout_seconds: float = 1.0,
        max_retries: int = 3,
    ) -> None:
        self._url = coordinator_url
        self._timeout = httpx.Timeout(timeout_seconds)
        self._max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> Self:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def quote(self, request: QuoteRequest) -> AggregatorQuote:
        """Fetch the best aggregator quote from the coordinator.

        Retries transient HTTP errors with exponential backoff via
        `tenacity`. Non-retryable errors (4xx) bubble up as-is.
        """
        if self._client is None:
            msg = "QuoteEngineClient used outside of `async with` block"
            raise RuntimeError(msg)

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=0.05, max=0.5),
            retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
            reraise=True,
        ):
            with attempt:
                response = await self._client.post(
                    self._url,
                    json=request.model_dump(exclude_none=True),
                )
                response.raise_for_status()
                return AggregatorQuote.model_validate(response.json())
        # unreachable but appeases mypy --strict
        msg = "unreachable"
        raise RuntimeError(msg)
