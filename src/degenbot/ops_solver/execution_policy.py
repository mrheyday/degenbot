"""Strict pre-dispatch policy for zero-capital solver execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from degenbot.exceptions.base import DegenbotValueError
from degenbot.utils.bytes import to_bytes

if TYPE_CHECKING:
    from collections.abc import Mapping


ALLOWED_STRICT_TRANSPORTS = frozenset({
    "cow_private_settlement",
    "erc4337_paymaster",
    "flashblocks",
    "flashblocks_bundle",
    "flashbots_bundle",
    "flashbots_private",
    "fusion_private_execution",
    "gasless_paymaster",
    "kairos",
    "paymaster_base",
    "paymaster_sponsored",
    "private_relay",
    "timeboost",
})

_TRANSPORT_ALIASES = {
    "cow": "cow_private_settlement",
    "cow_private": "cow_private_settlement",
    "cow_settlement": "cow_private_settlement",
    "erc4337": "erc4337_paymaster",
    "flashbots": "flashbots_private",
    "flashbots-private": "flashbots_private",
    "flashbots_private_relay": "flashbots_private",
    "fusion": "fusion_private_execution",
    "fusion_private": "fusion_private_execution",
    "gas_manager": "paymaster_sponsored",
    "paymaster": "paymaster_sponsored",
    "private": "private_relay",
    "privaterelay": "private_relay",
    "private-relay": "private_relay",
    "privateRelay": "private_relay",
}


@dataclass(frozen=True, slots=True)
class ExecutionPolicyViolation:
    """One failed strict execution-policy assertion."""

    code: str
    detail: str


@dataclass(frozen=True, slots=True)
class ExecutionPolicyContext:
    """Capital-moving execution facts checked before signing or broadcast."""

    trace_id: str
    chain_id: int
    execute_with_sig: bool
    flash_amount_wei: int
    min_profit_wei: int
    require_preflight: bool
    transport: str
    private_submission: bool
    sponsored_execution: bool


class StrictExecutionPolicyError(DegenbotValueError):
    """Raised when a dispatch candidate violates strict execution policy."""

    trace_id: str
    violations: tuple[ExecutionPolicyViolation, ...]

    def __init__(self, trace_id: str, violations: tuple[ExecutionPolicyViolation, ...]) -> None:
        self.trace_id = trace_id
        self.violations = violations
        codes = ", ".join(violation.code for violation in violations)
        super().__init__(message=f"strict execution policy rejected {trace_id}: {codes}")


def normalize_transport(transport: str) -> str:
    """Normalize transport names into stable strict-policy identifiers."""

    normalized = transport.strip()
    if normalized in _TRANSPORT_ALIASES:
        return _TRANSPORT_ALIASES[normalized]
    normalized = normalized.replace("-", "_").lower()
    return _TRANSPORT_ALIASES.get(normalized, normalized)


def execution_policy_context_from_plan(
    plan: Mapping[str, Any],
    *,
    execute_with_sig: bool,
    flash_amount_wei: int | bytes | str,
    sponsored_execution: bool,
    private_submission: bool | None = None,
    transport: str | None = None,
) -> ExecutionPolicyContext:
    """Build strict-policy context from an engine plan or dispatch envelope."""

    resolved_transport = normalize_transport(
        str(transport if transport is not None else plan["broadcast_lane"])
    )
    return ExecutionPolicyContext(
        trace_id=str(plan["trace_id"]),
        chain_id=int(plan["chain_id"]),
        execute_with_sig=bool(execute_with_sig),
        flash_amount_wei=_amount_to_int(flash_amount_wei),
        min_profit_wei=_amount_to_int(plan["min_profit_wei"]),
        require_preflight=bool(plan["require_preflight"]),
        transport=resolved_transport,
        private_submission=(
            bool(private_submission)
            if private_submission is not None
            else resolved_transport in ALLOWED_STRICT_TRANSPORTS
        ),
        sponsored_execution=bool(sponsored_execution),
    )


def validate_execution_policy(
    context: ExecutionPolicyContext,
) -> tuple[ExecutionPolicyViolation, ...]:
    """Return every strict execution-policy violation for a dispatch candidate."""

    violations: list[ExecutionPolicyViolation] = []
    transport = normalize_transport(context.transport)

    if not context.execute_with_sig:
        violations.append(
            ExecutionPolicyViolation(
                code="missing_eip7702_delegation",
                detail="capital-moving execution must be authorized through executeWithSig",
            )
        )

    if context.flash_amount_wei <= 0:
        violations.append(
            ExecutionPolicyViolation(
                code="missing_flash_liquidity",
                detail="zero-capital execution requires a positive flash-liquidity amount",
            )
        )

    if context.min_profit_wei <= 0:
        violations.append(
            ExecutionPolicyViolation(
                code="missing_profit_floor",
                detail="execution must carry a positive deterministic profit floor",
            )
        )

    if not context.require_preflight:
        violations.append(
            ExecutionPolicyViolation(
                code="missing_preflight",
                detail="execution must require deterministic simulation before dispatch",
            )
        )

    if transport not in ALLOWED_STRICT_TRANSPORTS:
        violations.append(
            ExecutionPolicyViolation(
                code="unsupported_transport",
                detail=f"transport {context.transport!r} is outside strict-policy allowlist",
            )
        )

    if not context.private_submission:
        violations.append(
            ExecutionPolicyViolation(
                code="public_submission",
                detail="strict policy requires private or protected submission",
            )
        )

    if not context.sponsored_execution:
        violations.append(
            ExecutionPolicyViolation(
                code="unsponsored_execution",
                detail="strict policy requires sponsored, paymaster, or profit-funded execution",
            )
        )

    return tuple(violations)


def enforce_execution_policy(context: ExecutionPolicyContext) -> None:
    """Raise if a dispatch candidate violates strict execution policy."""

    violations = validate_execution_policy(context)
    if violations:
        raise StrictExecutionPolicyError(context.trace_id, violations)


def _amount_to_int(value: int | bytes | str) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 16) if value.startswith("0x") else int(value, 10)
    return int.from_bytes(to_bytes(value), byteorder="big")


__all__ = [
    "ALLOWED_STRICT_TRANSPORTS",
    "ExecutionPolicyContext",
    "ExecutionPolicyViolation",
    "StrictExecutionPolicyError",
    "enforce_execution_policy",
    "execution_policy_context_from_plan",
    "normalize_transport",
    "validate_execution_policy",
]
