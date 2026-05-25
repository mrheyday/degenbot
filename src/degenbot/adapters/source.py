"""Sourcify/source-verification helpers for adapter-bound contracts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal, Protocol, cast
from urllib.request import urlopen

from degenbot.adapters.templates import SOURCIFY_SERVER, AdapterTemplate, ContractBinding

type SourcifyMatch = Literal["match", "exact_match", "partial_match"] | None


class SourceVerificationError(RuntimeError):
    """Raised when source-verification metadata cannot be fetched or parsed."""


class _HttpResponse(Protocol):
    def read(self) -> bytes: ...
    def __enter__(self) -> _HttpResponse: ...
    def __exit__(self, exc_type: object, exc: object, traceback: object) -> object: ...


@dataclass(frozen=True, slots=True)
class SourceVerificationRequest:
    """One source-verification request for a contract binding."""

    chain_id: int
    address: str
    url: str
    source_ref: str
    role: str


@dataclass(frozen=True, slots=True)
class SourcifyStatus:
    """Parsed Sourcify v2 contract status."""

    match: SourcifyMatch
    creation_match: SourcifyMatch
    runtime_match: SourcifyMatch
    chain_id: str
    address: str
    match_id: str | None = None
    verified_at: str | None = None

    @property
    def verified(self) -> bool:
        """True iff Sourcify reports any verified match."""
        return self.match is not None


def source_verification_request(
    binding: ContractBinding,
    *,
    server: str = SOURCIFY_SERVER,
) -> SourceVerificationRequest:
    """Build the Sourcify request metadata for a contract binding."""
    normalized_server = server.rstrip("/")
    return SourceVerificationRequest(
        chain_id=binding.chain_id,
        address=binding.address,
        url=f"{normalized_server}/v2/contract/{binding.chain_id}/{binding.address}",
        source_ref=binding.source_ref,
        role=binding.role,
    )


def source_verification_requests(adapter: AdapterTemplate) -> tuple[SourceVerificationRequest, ...]:
    """Return Sourcify request metadata for every contract on an adapter."""
    return tuple(source_verification_request(binding) for binding in adapter.contracts)


def parse_sourcify_status(payload: object) -> SourcifyStatus:
    """Parse a Sourcify v2 JSON payload."""
    if not isinstance(payload, dict):
        raise SourceVerificationError("Sourcify status must be a JSON object")
    raw = cast("dict[str, object]", payload)
    return SourcifyStatus(
        match=_parse_match(raw.get("match")),
        creation_match=_parse_match(raw.get("creationMatch")),
        runtime_match=_parse_match(raw.get("runtimeMatch")),
        chain_id=_required_str(raw, "chainId"),
        address=_required_str(raw, "address"),
        match_id=_optional_str(raw.get("matchId")),
        verified_at=_optional_str(raw.get("verifiedAt")),
    )


def fetch_sourcify_status(
    request: SourceVerificationRequest,
    *,
    timeout_sec: float = 8.0,
) -> SourcifyStatus:
    """Fetch and parse Sourcify status for a prepared request.

    This is for one-shot verification tooling, not the hot path.
    """
    try:
        with urlopen(request.url, timeout=timeout_sec) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise SourceVerificationError(f"Sourcify fetch failed for {request.source_ref}: {exc}") from exc
    return parse_sourcify_status(payload)


def _parse_match(value: object) -> SourcifyMatch:
    if value is None:
        return None
    if value in {"match", "exact_match", "partial_match"}:
        return cast("SourcifyMatch", value)
    raise SourceVerificationError(f"unknown Sourcify match value: {value!r}")


def _required_str(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or value == "":
        raise SourceVerificationError(f"Sourcify status missing string field {key}")
    return value


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or value == "":
        raise SourceVerificationError("optional Sourcify string field must be non-empty when present")
    return value
