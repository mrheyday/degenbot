from __future__ import annotations

import pytest

from degenbot.ops_solver.execution_policy import (
    ExecutionPolicyContext,
    StrictExecutionPolicyError,
    enforce_execution_policy,
    execution_policy_context_from_plan,
    validate_execution_policy,
)


def _admitted_context(**overrides: object) -> ExecutionPolicyContext:
    values: dict[str, object] = {
        "trace_id": "trace-strict-1",
        "chain_id": 42161,
        "execute_with_sig": True,
        "flash_amount_wei": 10**18,
        "min_profit_wei": 100,
        "require_preflight": True,
        "transport": "private_relay",
        "private_submission": True,
        "sponsored_execution": True,
    }
    values.update(overrides)
    return ExecutionPolicyContext(**values)  # type: ignore[arg-type]


def test_strict_execution_policy_accepts_private_sponsored_flash_execution() -> None:
    context = _admitted_context()

    assert validate_execution_policy(context) == ()
    enforce_execution_policy(context)


def test_strict_execution_policy_reports_stable_violation_codes() -> None:
    context = _admitted_context(
        execute_with_sig=False,
        flash_amount_wei=0,
        min_profit_wei=0,
        require_preflight=False,
        transport="default",
        private_submission=False,
        sponsored_execution=False,
    )

    violations = validate_execution_policy(context)

    assert tuple(violation.code for violation in violations) == (
        "missing_eip7702_delegation",
        "missing_flash_liquidity",
        "missing_profit_floor",
        "missing_preflight",
        "unsupported_transport",
        "public_submission",
        "unsponsored_execution",
    )


def test_enforce_execution_policy_raises_with_all_violations() -> None:
    context = _admitted_context(execute_with_sig=False, transport="default")

    with pytest.raises(StrictExecutionPolicyError) as excinfo:
        enforce_execution_policy(context)

    assert excinfo.value.trace_id == "trace-strict-1"
    assert tuple(violation.code for violation in excinfo.value.violations) == (
        "missing_eip7702_delegation",
        "unsupported_transport",
    )
    assert "trace-strict-1" in str(excinfo.value)
    assert "unsupported_transport" in str(excinfo.value)


def test_execution_policy_context_from_plan_normalizes_wire_amounts() -> None:
    plan = {
        "trace_id": "trace-plan-1",
        "chain_id": 42161,
        "min_profit_wei": "0x64",
        "require_preflight": True,
        "broadcast_lane": "PrivateRelay",
    }

    context = execution_policy_context_from_plan(
        plan,
        execute_with_sig=True,
        flash_amount_wei="0xde0b6b3a7640000",
        sponsored_execution=True,
        private_submission=True,
    )

    assert context.trace_id == "trace-plan-1"
    assert context.min_profit_wei == 100
    assert context.flash_amount_wei == 10**18
    assert context.transport == "private_relay"
    assert validate_execution_policy(context) == ()
