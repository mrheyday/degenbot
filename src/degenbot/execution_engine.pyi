from collections.abc import Mapping, Sequence
from typing import Any, NotRequired, TypedDict

from degenbot.utils.bytes import HexBytesLike

class ExecutionPlanDict(TypedDict):
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
    name: str
    block_number: int
    observed_at_ns: int

class GateArtifactDict(TypedDict):
    name: str
    admitted: bool
    reason: NotRequired[str | None]

class SimulationArtifactDict(TypedDict):
    success: bool
    expected_profit_wei: int | bytes | str
    gas_used: int
    state_read_count: int
    revert_reason: NotRequired[str | None]

def compose_engine_job(
    plan: Mapping[str, Any],
    policy: Mapping[str, Any],
    sources: Sequence[Mapping[str, Any]],
    gates: Sequence[Mapping[str, Any]],
    simulation: Mapping[str, Any],
    now_ms: int,
) -> dict[str, Any]: ...

__all__ = [
    "EnginePolicyDict",
    "ExecutionPlanDict",
    "GateArtifactDict",
    "SimulationArtifactDict",
    "SourceArtifactDict",
    "compose_engine_job",
]
