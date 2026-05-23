"""Degenbot-owned dispatch envelope composition.

TypeScript strategy modules may supply exact calldata, but the capital-moving
dispatch boundary is degenbot: this module composes the Rust-admitted execution
job into the envelope that signing and broadcast adapters consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict

from hexbytes import HexBytes

from degenbot.degenbot_rs import to_checksum_address
from degenbot.execution_engine import compose_engine_job
from degenbot.utils.bytes import HexBytesLike, to_bytes

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


class DispatchEnvelopeDict(TypedDict):
    """JSON-safe dispatch envelope accepted by degenbot execution adapters."""

    plan_hash: str
    trace_id: str
    strategy: str
    chain_id: int
    target: str
    calldata: str
    value: str
    gas_limit: int
    max_fee_per_gas: str
    max_priority_fee_per_gas: str
    deadline_ms: int
    profit_token: str
    min_profit_wei: str
    broadcast_lane: str
    submit: bool
    private_submission: bool
    require_preflight: bool
    dry_run: bool
    engine_report: dict[str, Any]


def _normalize_address(value: str | bytes) -> str:
    return to_checksum_address(value)


def _normalize_bytes(value: HexBytesLike | str) -> str:
    if isinstance(value, str):
        normalized = HexBytes(value).hex()
        return normalized if normalized.startswith("0x") else f"0x{normalized}"
    return "0x" + to_bytes(value).hex()


def _normalize_amount(value: int | bytes | str) -> str:
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return str(int(value, 16) if value.startswith("0x") else int(value, 10))
    return str(int.from_bytes(to_bytes(value), byteorder="big"))


def compose_dispatch_envelope(  # noqa: PLR0917
    plan: Mapping[str, Any],
    policy: Mapping[str, Any],
    sources: Sequence[Mapping[str, Any]],
    gates: Sequence[Mapping[str, Any]],
    simulation: Mapping[str, Any],
    now_ms: int,
) -> DispatchEnvelopeDict:
    """Validate a plan and return the degenbot execution dispatch envelope.

    The returned envelope intentionally carries the exact calldata and fee
    fields alongside the Rust admission report. Side-effecting sign/broadcast
    adapters consume this envelope; they do not rebuild calldata.
    """

    report = compose_engine_job(plan, policy, sources, gates, simulation, now_ms)
    envelope: DispatchEnvelopeDict = {
        "plan_hash": str(report["plan_hash"]),
        "trace_id": str(report["trace_id"]),
        "strategy": str(report["strategy"]),
        "chain_id": int(report["chain_id"]),
        "target": _normalize_address(plan["target"]),
        "calldata": _normalize_bytes(plan["calldata"]),
        "value": _normalize_amount(plan.get("value", 0)),
        "gas_limit": int(report["gas_limit"]),
        "max_fee_per_gas": _normalize_amount(plan["max_fee_per_gas"]),
        "max_priority_fee_per_gas": _normalize_amount(plan["max_priority_fee_per_gas"]),
        "deadline_ms": int(report["deadline_ms"]),
        "profit_token": _normalize_address(plan["profit_token"]),
        "min_profit_wei": _normalize_amount(plan["min_profit_wei"]),
        "broadcast_lane": str(report["broadcast_lane"]),
        "submit": bool(report["submit"]),
        "private_submission": bool(report["private_submission"]),
        "require_preflight": bool(report["require_preflight"]),
        "dry_run": bool(report["dry_run"]),
        "engine_report": report,
    }
    return envelope


__all__ = [
    "DispatchEnvelopeDict",
    "compose_dispatch_envelope",
]
