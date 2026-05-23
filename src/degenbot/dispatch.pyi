from collections.abc import Mapping, Sequence
from typing import Any, NotRequired, Protocol, TypedDict

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

class DispatchReceiptDict(TypedDict):
    plan_hash: str
    trace_id: str
    adapter: str
    target: str
    calldata: str
    submitted: bool
    dry_run: bool
    private_submission: bool
    broadcast_lane: str
    tx_hash: NotRequired[str]
    raw_transaction: NotRequired[str]

class DispatchAdapter(Protocol):
    @property
    def name(self) -> str: ...
    async def submit(self, envelope: DispatchEnvelopeDict) -> Mapping[str, Any]: ...

def compose_dispatch_envelope(
    plan: Mapping[str, Any],
    policy: Mapping[str, Any],
    sources: Sequence[Mapping[str, Any]],
    gates: Sequence[Mapping[str, Any]],
    simulation: Mapping[str, Any],
    now_ms: int,
) -> DispatchEnvelopeDict: ...

async def submit_dispatch_envelope(
    envelope: DispatchEnvelopeDict,
    adapter: DispatchAdapter,
) -> DispatchReceiptDict: ...

__all__ = [
    "DispatchAdapter",
    "DispatchEnvelopeDict",
    "DispatchReceiptDict",
    "compose_dispatch_envelope",
    "submit_dispatch_envelope",
]
