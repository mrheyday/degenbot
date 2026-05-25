"""Shared primitives for solver-side execution adapters.

These helpers are intentionally small. They factor the temporary
solver-side adapter shape while each protocol module keeps ownership of
protocol-specific wire types, math, and stub messages.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final, Protocol, Self, cast

import httpx

if TYPE_CHECKING:
    from collections.abc import Mapping

SUPPORTED_EXECUTOR_STRATEGIES: Final[frozenset[str]] = frozenset(
    {"native_arb", "match_internal", "compose_four_leg"},
)


def configure_execution_logging(level: str) -> None:
    """Configure simple message-only logging for adapter CLI/test use."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", level=log_level)


def validate_executor_strategy(strategy: str) -> None:
    """Reject strategies that are not routed by the Executor calldata builders."""
    if strategy not in SUPPORTED_EXECUTOR_STRATEGIES:
        msg = f"Unsupported strategy {strategy!r}; expected one of {sorted(SUPPORTED_EXECUTOR_STRATEGIES)}"
        raise ValueError(
            msg,
        )


class AdapterLogger(Protocol):
    """Small logger protocol for bound structlog loggers."""

    def bind(self, **new_values: object) -> AdapterLogger:
        """Return a logger with contextual values bound."""
        ...

    def error(self, event: str, **kw: object) -> None:
        """Emit a structured error event."""
        ...


@dataclass(frozen=True)
class GraphqlAdapterConfig:
    """GraphQL adapter logging/error-message configuration."""

    http_error_event: str
    graphql_errors_event: str
    graphql_error_prefix: str
    log: AdapterLogger | None = None
    log_context: Mapping[str, object] | None = None


class AsyncHttpAdapterClient:
    """Common async HTTP client lifecycle for execution adapters."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout_sec: float = 5.0,
        headers: Mapping[str, str] | None = None,
        log: AdapterLogger | None = None,
        log_context: Mapping[str, object] | None = None,
    ) -> None:
        self._url = base_url
        self._timeout = timeout_sec
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout_sec,
            headers=dict(headers) if headers is not None else None,
        )
        self._log = log.bind(**log_context) if log is not None and log_context else log

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()


class AsyncGraphqlAdapterClient(AsyncHttpAdapterClient):
    """Common GraphQL POST helper for read-side planning adapters."""

    def __init__(
        self,
        graphql_url: str,
        *,
        timeout_sec: float = 5.0,
        bearer_token: str | None = None,
        config: GraphqlAdapterConfig,
    ) -> None:
        headers: dict[str, str] = {"content-type": "application/json"}
        if bearer_token:
            headers["authorization"] = f"Bearer {bearer_token}"

        super().__init__(
            graphql_url,
            timeout_sec=timeout_sec,
            headers=headers,
            log=config.log,
            log_context=config.log_context,
        )
        self._http_error_event = config.http_error_event
        self._graphql_errors_event = config.graphql_errors_event
        self._graphql_error_prefix = config.graphql_error_prefix

    async def _query(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        """Issue a raw GraphQL POST and return the `data` field."""
        try:
            resp = await self._client.post(
                "",
                json={"query": query, "variables": variables},
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            if self._log is not None:
                self._log.error(self._http_error_event, err=str(exc))
            raise

        body = resp.json()
        if body.get("errors"):
            if self._log is not None:
                self._log.error(self._graphql_errors_event, errors=body["errors"])
            msg = f"{self._graphql_error_prefix}: {body['errors']}"
            raise RuntimeError(msg)
        data = body.get("data", {})
        return cast("dict[str, Any]", data)
