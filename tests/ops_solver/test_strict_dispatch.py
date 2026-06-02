from __future__ import annotations

import pytest

from degenbot.ops_solver import (
    StrictExecutionPolicyError,
    compose_strict_dispatch_envelope,
)


def _admitted_inputs() -> tuple[
    dict[str, object],
    dict[str, object],
    list[dict[str, object]],
    list[dict[str, object]],
    dict[str, object],
]:
    plan = {
        "trace_id": "trace-strict-dispatch-1",
        "strategy": "native_arb",
        "chain_id": 42161,
        "target": "0x000000000000000000000000000000000000beef",
        "calldata": "0x12345678",
        "value": 0,
        "gas_limit": 500_000,
        "max_fee_per_gas": 1_000_000_000,
        "max_priority_fee_per_gas": 100_000_000,
        "deadline_ms": 10_000,
        "profit_token": "0x0000000000000000000000000000000000000001",
        "min_profit_wei": 100,
        "require_preflight": True,
        "dry_run": False,
        "broadcast_lane": "private_relay",
    }
    policy = {
        "expected_chain_id": 42161,
        "min_profit_wei": 50,
        "max_gas_limit": 1_000_000,
        "require_preflight": True,
        "require_live_sources": True,
        "min_gate_count": 1,
        "min_deadline_ms_from_now": 1_000,
        "allowed_targets": [plan["target"]],
        "allowed_lanes": ["private_relay"],
    }
    sources = [{"name": "same-block-pool-state", "block_number": 123, "observed_at_ns": 456}]
    gates = [{"name": "min-profit", "admitted": True}]
    simulation = {
        "success": True,
        "expected_profit_wei": 150,
        "gas_used": 250_000,
        "state_read_count": 8,
    }
    return plan, policy, sources, gates, simulation


def test_compose_strict_dispatch_envelope_returns_admitted_private_envelope() -> None:
    plan, policy, sources, gates, simulation = _admitted_inputs()

    envelope = compose_strict_dispatch_envelope(
        plan,
        policy,
        sources,
        gates,
        simulation,
        now_ms=8_000,
        execute_with_sig=True,
        flash_amount_wei=10**18,
        sponsored_execution=True,
    )

    assert envelope["trace_id"] == "trace-strict-dispatch-1"
    assert envelope["broadcast_lane"] == "private_relay"
    assert envelope["private_submission"] is True
    assert envelope["submit"] is True
    assert envelope["calldata"] == "0x12345678"


def test_compose_strict_dispatch_envelope_rejects_missing_delegation() -> None:
    plan, policy, sources, gates, simulation = _admitted_inputs()

    with pytest.raises(StrictExecutionPolicyError) as excinfo:
        compose_strict_dispatch_envelope(
            plan,
            policy,
            sources,
            gates,
            simulation,
            now_ms=8_000,
            execute_with_sig=False,
            flash_amount_wei=10**18,
            sponsored_execution=True,
        )

    assert excinfo.value.trace_id == "trace-strict-dispatch-1"
    assert tuple(violation.code for violation in excinfo.value.violations) == (
        "missing_eip7702_delegation",
    )


def test_compose_strict_dispatch_envelope_rejects_public_override() -> None:
    plan, policy, sources, gates, simulation = _admitted_inputs()

    with pytest.raises(StrictExecutionPolicyError) as excinfo:
        compose_strict_dispatch_envelope(
            plan,
            policy,
            sources,
            gates,
            simulation,
            now_ms=8_000,
            execute_with_sig=True,
            flash_amount_wei=10**18,
            sponsored_execution=True,
            private_submission=False,
        )

    assert tuple(violation.code for violation in excinfo.value.violations) == (
        "public_submission",
    )
