from __future__ import annotations

from pathlib import Path

from degenbot.strategies_solver.execution_workflows import (
    EXECUTION_WORKFLOWS,
    WorkflowStatus,
    workflow_for_id,
    workflows_for_decision_kind,
)
from degenbot.strategies_solver.strategy_intelligence import (
    STRATEGY_INTELLIGENCE_PROFILES,
    BlockerStatus,
    profile_for_workflow,
)


def _find_root() -> Path:
    current = Path(__file__).resolve().parent
    while current.parent != current:
        if (current / "PROGRESS.md").exists():
            return current
        current = current.parent
    return Path(__file__).resolve().parents[3]


REPO_ROOT = _find_root()

DECISION_KINDS = frozenset({
    "internal_match",
    "four_leg",
    "morpho_liquidation",
    "native_arb",
    "launch_sniper",
    "cow_user_submit",
    "across_fill",
})

LIVE_WORKFLOW_IDS = frozenset({
    "native_arb",
    "internal_match",
    "four_leg",
    "uniswapx_filler",
    "liquidation",
    "morpho_liquidation_decision",
    "oracle_sandwich",
    "d3_cow_quote",
})


def _path_from_ref(ref: str) -> Path:
    return REPO_ROOT / ref.split("::", maxsplit=1)[0]


def _all_file_refs() -> set[str]:
    refs: set[str] = set()
    for workflow in EXECUTION_WORKFLOWS:
        refs.update(workflow.signal_sources)
        refs.update(workflow.trigger_modules)
        refs.update(workflow.planner_modules)
        refs.update(workflow.calldata_builders)
        refs.update(workflow.submission_modules)
        refs.update(workflow.contract_entrypoints)
        refs.update(workflow.callback_entrypoints)
        refs.update(workflow.happy_path_tests)
        refs.update(workflow.revert_guard_tests)
        for step in workflow.steps:
            refs.update(step.code_refs)

    return refs


def _all_profile_refs() -> set[str]:
    refs: set[str] = set()
    for profile in STRATEGY_INTELLIGENCE_PROFILES:
        refs.update(profile.proof_refs)
        for blocker in profile.blockers:
            refs.update(blocker.owner_refs)
            refs.update(blocker.proof_refs)

    return refs


def test_workflow_ids_are_unique_and_lookupable() -> None:
    workflow_ids = [workflow.workflow_id for workflow in EXECUTION_WORKFLOWS]

    assert len(workflow_ids) == len(set(workflow_ids))
    for workflow_id in workflow_ids:
        assert workflow_for_id(workflow_id).workflow_id == workflow_id


def test_live_workflow_set_is_explicit() -> None:
    assert {
        workflow.workflow_id for workflow in EXECUTION_WORKFLOWS if workflow.is_live
    } == LIVE_WORKFLOW_IDS


def test_all_decision_kinds_are_documented_without_claiming_gated_dispatch_is_live() -> None:
    for decision_kind in DECISION_KINDS:
        workflows = workflows_for_decision_kind(decision_kind)

        assert workflows, decision_kind
        if decision_kind == "launch_sniper":
            assert all(workflow.status is WorkflowStatus.GATED_EXPLICIT for workflow in workflows)


def test_all_referenced_files_exist() -> None:
    for ref in sorted(_all_file_refs()):
        assert _path_from_ref(ref).exists(), ref


def test_live_workflows_have_complete_execution_bottle() -> None:
    for workflow in EXECUTION_WORKFLOWS:
        if not workflow.is_live:
            continue

        assert workflow.signal_sources, workflow.workflow_id
        assert workflow.trigger_modules, workflow.workflow_id
        assert workflow.planner_modules, workflow.workflow_id
        assert workflow.calldata_builders, workflow.workflow_id
        assert workflow.submission_modules, workflow.workflow_id
        assert workflow.profit_extraction, workflow.workflow_id
        assert workflow.no_silent_stop_policy, workflow.workflow_id
        assert workflow.happy_path_tests, workflow.workflow_id
        assert workflow.revert_guard_tests, workflow.workflow_id
        assert len(workflow.steps) >= 4, workflow.workflow_id


def test_contract_workflows_document_callback_encoding_and_revert_guards() -> None:
    for workflow in EXECUTION_WORKFLOWS:
        if not workflow.contract_entrypoints:
            continue

        assert workflow.callback_entrypoints, workflow.workflow_id
        assert workflow.flash_callback_encoding, workflow.workflow_id
        assert workflow.revert_guard_tests, workflow.workflow_id


def test_gated_workflows_are_fail_loud_not_silent_stops() -> None:
    for workflow in EXECUTION_WORKFLOWS:
        if workflow.status is not WorkflowStatus.GATED_EXPLICIT:
            continue

        policy = workflow.no_silent_stop_policy.lower()
        assert any(
            marker in policy for marker in ("log", "revert", "no decisionkind", "dispatcher")
        ), (
            workflow.workflow_id,
            workflow.no_silent_stop_policy,
        )
        assert workflow.happy_path_tests, workflow.workflow_id
        assert workflow.revert_guard_tests, workflow.workflow_id


def test_flash_callback_discriminators_are_documented() -> None:
    assert "uint8(0)" in workflow_for_id("native_arb").flash_callback_encoding
    assert "uint8(1)" in workflow_for_id("internal_match").flash_callback_encoding
    assert "uint8(2)" in workflow_for_id("four_leg").flash_callback_encoding
    assert "strategy id 0" in workflow_for_id("oracle_sandwich").flash_callback_encoding
    assert "round" in workflow_for_id("cow_flash_router").flash_callback_encoding
    assert "uint8(1|2)" in workflow_for_id("cow_flash_router").flash_callback_encoding
    assert (
        "abi.encode(collateral, debt, borrower"
        in workflow_for_id("liquidation").flash_callback_encoding
    )


def test_ordered_steps_are_contiguous_per_workflow() -> None:
    for workflow in EXECUTION_WORKFLOWS:
        assert [step.order for step in workflow.steps] == list(range(1, len(workflow.steps) + 1))
        assert all(step.name for step in workflow.steps)
        assert all(step.validation for step in workflow.steps)


def test_strategy_intelligence_profiles_cover_every_workflow() -> None:
    workflow_ids = {workflow.workflow_id for workflow in EXECUTION_WORKFLOWS}
    profile_ids = {profile.workflow_id for profile in STRATEGY_INTELLIGENCE_PROFILES}

    assert profile_ids == workflow_ids
    for workflow_id in workflow_ids:
        assert profile_for_workflow(workflow_id).workflow_id == workflow_id


def test_strategy_intelligence_profiles_have_competitive_content() -> None:
    for profile in STRATEGY_INTELLIGENCE_PROFILES:
        assert profile.objective, profile.workflow_id
        assert profile.execution_choice, profile.workflow_id
        assert profile.logic, profile.workflow_id
        assert profile.mechanics, profile.workflow_id
        assert profile.competitive_advantage, profile.workflow_id
        assert profile.latency_posture, profile.workflow_id
        assert profile.resource_utilization, profile.workflow_id
        assert profile.profitability_controls, profile.workflow_id
        assert profile.proof_refs, profile.workflow_id


def test_strategy_intelligence_proof_refs_exist() -> None:
    for ref in sorted(_all_profile_refs()):
        assert _path_from_ref(ref).exists(), ref


def test_production_ready_profiles_have_no_blockers_and_gated_profiles_do() -> None:
    workflow_by_id = {workflow.workflow_id: workflow for workflow in EXECUTION_WORKFLOWS}

    for profile in STRATEGY_INTELLIGENCE_PROFILES:
        workflow = workflow_by_id[profile.workflow_id]
        if (
            workflow.status is WorkflowStatus.EXECUTABLE
            or workflow.status is WorkflowStatus.EXTERNAL_FORWARD
        ):
            assert profile.blocker_status is BlockerStatus.NONE, profile.workflow_id
            assert profile.production_ready, profile.workflow_id
            continue

        assert profile.blocker_status is BlockerStatus.EXPLICIT_GATE, profile.workflow_id
        assert not profile.production_ready, profile.workflow_id
        assert profile.blockers, profile.workflow_id
        for blocker in profile.blockers:
            assert blocker.description, profile.workflow_id
            assert blocker.remediation, profile.workflow_id
            assert blocker.owner_refs, profile.workflow_id
            assert blocker.proof_refs, profile.workflow_id
