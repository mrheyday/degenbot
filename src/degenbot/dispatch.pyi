from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

class DispatchEnvelopeDict(TypedDict):
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

def compose_dispatch_envelope(
    plan: Mapping[str, Any],
    policy: Mapping[str, Any],
    sources: Sequence[Mapping[str, Any]],
    gates: Sequence[Mapping[str, Any]],
    simulation: Mapping[str, Any],
    now_ms: int,
) -> DispatchEnvelopeDict: ...

__all__ = [
    "DispatchEnvelopeDict",
    "compose_dispatch_envelope",
]
