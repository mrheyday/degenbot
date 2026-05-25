from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from numbers import Real
from pathlib import Path

from degenbot.strategies.arbitrum_mev_e2e import (
    E2EAction,
    E2ELane,
    build_master_plan,
    dispatchable_strategy_ids,
    ev_estimate,
    recon_strategy_ids,
    validate_master_plan,
)
from degenbot.strategies.execution_workflows import WorkflowStatus

REPO_ROOT = Path(__file__).resolve().parents[3]


def _assert_no_float(value: object) -> None:
    assert not (isinstance(value, Real) and not isinstance(value, (bool, int))), value
    if isinstance(value, Mapping):
        for nested in value.values():
            _assert_no_float(nested)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            _assert_no_float(nested)


def _path(ref: str) -> Path:
    return REPO_ROOT / ref.split("::", maxsplit=1)[0]


def test_master_plan_validates_and_matches_ranked_sequence() -> None:
    plan = build_master_plan()

    assert validate_master_plan(plan) == ()
    assert [route.strategy_id for route in plan.routes] == [
        "L-2",
        "U-1",
        "A-1",
        "V-1",
        "L-1",
        "J-1",
        "B-1",
        "T-1",
        "S-1",
        "K-1",
    ]


def test_uniswapx_and_cyclic_arb_fail_closed_until_sourced_wrappers_exist() -> None:
    plan = build_master_plan()

    assert dispatchable_strategy_ids() == ()
    assert [route.strategy_id for route in plan.execution_queue()] == []

    u1 = plan.route_for("U-1")
    a1 = plan.route_for("A-1")

    assert u1.workflow_id == "uniswapx_filler"
    assert u1.workflow_status is WorkflowStatus.EXECUTABLE
    assert u1.lane is E2ELane.RECON_ONLY
    assert u1.action is E2EAction.INTEGRATE
    assert not u1.dispatchable

    assert a1.workflow_id == "native_arb"
    assert a1.workflow_status is WorkflowStatus.EXECUTABLE
    assert a1.lane is E2ELane.RECON_ONLY
    assert a1.action is E2EAction.INTEGRATE
    assert not a1.dispatchable


def test_boros_fails_closed_into_recon_and_jit_is_research_only() -> None:
    plan = build_master_plan()

    assert recon_strategy_ids() == ("B-1",)

    b1 = plan.route_for("B-1")
    assert b1.action is E2EAction.RECON
    assert b1.lane is E2ELane.RECON_ONLY
    assert b1.workflow_id is None
    assert not b1.dispatchable
    assert "decode" in " ".join(b1.next_steps).lower()

    j1 = plan.route_for("J-1")
    assert j1.action is E2EAction.RESEARCH_ONLY
    assert j1.workflow_id == "jit_liquidity"
    assert not j1.dispatchable


def test_variational_signal_flow_is_build_ready_but_not_dispatchable() -> None:
    plan = build_master_plan()
    route = plan.route_for("V-1")

    assert route.action is E2EAction.BUILD_NOW
    assert route.lane is E2ELane.KAIROS_ON_DEMAND
    assert route.workflow_id == "native_arb"
    assert route.workflow_status is WorkflowStatus.EXECUTABLE
    assert not route.dispatchable
    assert "OLPToPoolTransfer" in " ".join(route.required_inputs)
    assert "externally liquidatable" in " ".join(route.stop_conditions)


def test_timeboost_is_costed_as_rail_not_alpha() -> None:
    plan = build_master_plan()
    route = plan.route_for("T-1")

    assert route.action is E2EAction.EXECUTION_RAIL
    assert route.lane is E2ELane.KAIROS_ON_DEMAND
    assert not route.dispatchable
    assert route.ev.annual_base_usd_cents == -560_000
    assert plan.timeboost_cost_per_event_usd_cents == 235
    assert plan.timeboost_annual_cost_usd_cents == 560_000


def test_ev_model_is_integer_only_and_pins_user_totals() -> None:
    plan = build_master_plan()

    assert plan.known_vectors_base_usd_cents == 181_111_635
    assert plan.total_base_usd_cents == 181_111_635
    assert plan.total_low_usd_cents == 38_027_581
    assert plan.total_high_usd_cents == 362_041_550
    assert plan.kelp_scale_single_event_usd_cents == 605_000_000

    l1 = ev_estimate("L-1")
    assert l1.captured_events_per_year == 540
    assert l1.derived_annual_base_usd_cents == 221_238_000
    assert l1.annual_base_usd_cents == 59_734_260

    l2 = ev_estimate("L-2")
    assert l2.net_per_event_usd_cents == 21_422

    u1 = ev_estimate("U-1")
    assert u1.net_per_event_usd_cents == 7_500

    v1 = ev_estimate("V-1")
    assert v1.net_per_event_usd_cents == 5_365
    assert v1.annual_base_usd_cents == 9_791_125


def test_evidence_payload_is_json_safe_and_exposes_no_float_values() -> None:
    evidence = build_master_plan().to_evidence()

    _assert_no_float(evidence)
    json.dumps(evidence, sort_keys=True)

    assert set(evidence["routes"][0]["annual_ev_usd_cents"]) == {"low", "base", "high"}


def test_all_e2e_route_references_exist() -> None:
    for route in build_master_plan().routes:
        for ref in (*route.priority.code_refs, *route.priority.proof_refs):
            assert _path(ref).exists(), f"{route.strategy_id}: {ref}"
