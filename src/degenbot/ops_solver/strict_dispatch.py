"""Strict dispatch composition for capital-moving solver operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from degenbot.dispatch import DispatchEnvelopeDict, compose_dispatch_envelope
from degenbot.ops_solver.execution_policy import (
    enforce_execution_policy,
    execution_policy_context_from_plan,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


def compose_strict_dispatch_envelope(
    plan: Mapping[str, Any],
    policy: Mapping[str, Any],
    sources: Sequence[Mapping[str, Any]],
    gates: Sequence[Mapping[str, Any]],
    simulation: Mapping[str, Any],
    now_ms: int,
    *,
    execute_with_sig: bool,
    flash_amount_wei: int | bytes | str,
    sponsored_execution: bool,
    private_submission: bool | None = None,
    transport: str | None = None,
) -> DispatchEnvelopeDict:
    """Compose a Rust-admitted envelope and enforce strict execution policy.

    This helper keeps the existing Rust engine admission as the first gate and
    applies the ops doctrine as the second gate before a signer/broadcaster can
    receive the envelope.
    """

    envelope = compose_dispatch_envelope(plan, policy, sources, gates, simulation, now_ms)
    context = execution_policy_context_from_plan(
        envelope,
        execute_with_sig=execute_with_sig,
        flash_amount_wei=flash_amount_wei,
        sponsored_execution=sponsored_execution,
        private_submission=(
            envelope["private_submission"]
            if private_submission is None
            else private_submission
        ),
        transport=envelope["broadcast_lane"] if transport is None else transport,
    )
    enforce_execution_policy(context)
    return envelope


__all__ = [
    "compose_strict_dispatch_envelope",
]
