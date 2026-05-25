"""Deterministic Rust execution-engine job composition.

This module is the Python convenience layer for the degenbot Rust engine
composer. It normalizes Python-native dicts into JSON-safe values and delegates
all admission logic to `degenbot_rs.compose_engine_job_json`.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, NotRequired, TypedDict

from hexbytes import HexBytes

from degenbot.degenbot_rs import to_checksum_address
from degenbot.utils.bytes import HexBytesLike, to_bytes

try:  # Prefer canonical export from a rebuilt extension.
    from degenbot.degenbot_rs import compose_engine_job_json as _compose_engine_job_json
except ImportError:  # Fallback for local editable builds that expose the PyO3 symbol.
    try:
        from degenbot.degenbot_rs import compose_engine_job_json_py as _compose_engine_job_json
    except ImportError:
        _compose_engine_job_json = None


class ExecutionPlanDict(TypedDict):
    """Python representation of a capital-moving execution plan."""

    trace_id: str
    strategy: str
    chain_id: int
    target: str | bytes
    calldata: HexBytesLike | str
    value: NotRequired[int | bytes | str]
    gas_limit: int
    max_fee_per_gas: int | bytes | str
    max_priority_fee_per_gas: int | bytes | str
    deadline_ms: int
    profit_token: str | bytes
    min_profit_wei: int | bytes | str
    require_preflight: bool
    dry_run: bool
    broadcast_lane: str


class EnginePolicyDict(TypedDict):
    """Python representation of deterministic execution policy."""

    expected_chain_id: int
    min_profit_wei: int | bytes | str
    max_gas_limit: int
    require_preflight: bool
    require_live_sources: bool
    min_gate_count: int
    min_deadline_ms_from_now: int
    allowed_targets: NotRequired[Sequence[str | bytes]]
    allowed_lanes: NotRequired[Sequence[str]]


class SourceArtifactDict(TypedDict):
    """Live source artifact used to build the plan."""

    name: str
    block_number: int
    observed_at_ns: int


class GateArtifactDict(TypedDict):
    """Deterministic gate artifact."""

    name: str
    admitted: bool
    reason: NotRequired[str | None]


class SimulationArtifactDict(TypedDict):
    """Simulation/preflight artifact."""

    success: bool
    expected_profit_wei: int | bytes | str
    gas_used: int
    state_read_count: int
    revert_reason: NotRequired[str | None]


def _normalize_address(value: str | bytes) -> str:
    return to_checksum_address(value)


def _normalize_bytes(value: HexBytesLike | str) -> str:
    if isinstance(value, str):
        return HexBytes(value).hex()
    return "0x" + to_bytes(value).hex()


def _normalize_amount(value: int | bytes | str) -> str:
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return str(int(value, 16) if value.startswith("0x") else int(value, 10))
    return str(int.from_bytes(to_bytes(value), byteorder="big"))


def _normalize_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "trace_id": str(plan["trace_id"]),
        "strategy": str(plan["strategy"]),
        "chain_id": int(plan["chain_id"]),
        "target": _normalize_address(plan["target"]),
        "calldata": _normalize_bytes(plan["calldata"]),
        "value": _normalize_amount(plan.get("value", 0)),
        "gas_limit": int(plan["gas_limit"]),
        "max_fee_per_gas": _normalize_amount(plan["max_fee_per_gas"]),
        "max_priority_fee_per_gas": _normalize_amount(plan["max_priority_fee_per_gas"]),
        "deadline_ms": int(plan["deadline_ms"]),
        "profit_token": _normalize_address(plan["profit_token"]),
        "min_profit_wei": _normalize_amount(plan["min_profit_wei"]),
        "require_preflight": bool(plan["require_preflight"]),
        "dry_run": bool(plan["dry_run"]),
        "broadcast_lane": str(plan["broadcast_lane"]),
    }


def _normalize_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "expected_chain_id": int(policy["expected_chain_id"]),
        "min_profit_wei": _normalize_amount(policy["min_profit_wei"]),
        "max_gas_limit": int(policy["max_gas_limit"]),
        "require_preflight": bool(policy["require_preflight"]),
        "require_live_sources": bool(policy["require_live_sources"]),
        "min_gate_count": int(policy["min_gate_count"]),
        "min_deadline_ms_from_now": int(policy["min_deadline_ms_from_now"]),
        "allowed_targets": [
            _normalize_address(target) for target in policy.get("allowed_targets", [])
        ],
        "allowed_lanes": [str(lane) for lane in policy.get("allowed_lanes", [])],
    }


def _normalize_sources(sources: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "name": str(source["name"]),
            "block_number": int(source["block_number"]),
            "observed_at_ns": int(source["observed_at_ns"]),
        }
        for source in sources
    ]


def _normalize_gates(gates: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "name": str(gate["name"]),
            "admitted": bool(gate["admitted"]),
            "reason": gate.get("reason"),
        }
        for gate in gates
    ]


def _normalize_simulation(simulation: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "success": bool(simulation["success"]),
        "expected_profit_wei": _normalize_amount(simulation["expected_profit_wei"]),
        "gas_used": int(simulation["gas_used"]),
        "state_read_count": int(simulation["state_read_count"]),
        "revert_reason": simulation.get("revert_reason"),
    }


def compose_engine_job(
    plan: Mapping[str, Any],
    policy: Mapping[str, Any],
    sources: Sequence[Mapping[str, Any]],
    gates: Sequence[Mapping[str, Any]],
    simulation: Mapping[str, Any],
    now_ms: int,
) -> dict[str, Any]:
    """Compose and validate a Rust/Alloy execution-engine job.

    Returns a JSON-safe report containing the stable plan hash and broadcast
    decision. Raises `ValueError` if the Rust policy engine rejects the job.
    """

    if _compose_engine_job_json is None:
        raise RuntimeError(
            "degenbot_rs execution-engine bindings are unavailable; rebuild the "
            "Rust extension with maturin before composing execution jobs"
        )

    report_json = _compose_engine_job_json(
        json.dumps(_normalize_plan(plan), sort_keys=True, separators=(",", ":")),
        json.dumps(_normalize_policy(policy), sort_keys=True, separators=(",", ":")),
        json.dumps(_normalize_sources(sources), sort_keys=True, separators=(",", ":")),
        json.dumps(_normalize_gates(gates), sort_keys=True, separators=(",", ":")),
        json.dumps(_normalize_simulation(simulation), sort_keys=True, separators=(",", ":")),
        int(now_ms),
    )
    result = json.loads(report_json)
    assert isinstance(result, dict)
    return result


__all__ = [
    "EnginePolicyDict",
    "ExecutionPlanDict",
    "GateArtifactDict",
    "SimulationArtifactDict",
    "SourceArtifactDict",
    "compose_engine_job",
]
