from __future__ import annotations

from pathlib import Path

from degenbot.strategies_solver.jaredbot_poc_catalog import (
    JAREDBOT_POCS,
    CapitalMode,
    PocStatus,
    executable_pocs,
    poc_for_skill,
    pocs_for_status,
    workflow_required_pocs,
)

REPO_ROOT = Path(__file__).resolve().parents[3]

REQUESTED_SKILLS = frozenset(
    {
        "jaredbot-crypto-bot-security",
        "jaredbot-defi-adjacent-context",
        "jaredbot-mev-amm-economics",
        "jaredbot-mev-bot-engineering",
        "jaredbot-mev-flash-arbitrage",
        "jaredbot-mev-frontrun",
        "jaredbot-mev-jit-v4",
        "jaredbot-mev-launch-sniper",
        "jaredbot-mev-liquidations",
        "jaredbot-mev-mempool-relay",
        "jaredbot-mev-ostium-oracle-gap",
        "jaredbot-mev-protection",
    }
)

EXPECTED_EXECUTABLE = frozenset(
    {
        "jaredbot-mev-flash-arbitrage",
        "jaredbot-mev-liquidations",
    }
)

EXPECTED_NEEDS_WORKFLOW = frozenset(
    {
        "jaredbot-mev-jit-v4",
        "jaredbot-mev-launch-sniper",
        "jaredbot-mev-ostium-oracle-gap",
    }
)


def _path(ref: str) -> Path:
    return REPO_ROOT / ref


def test_requested_jaredbot_skills_are_all_implemented_as_pocs() -> None:
    assert {poc.skill_name for poc in JAREDBOT_POCS} == REQUESTED_SKILLS
    assert len(JAREDBOT_POCS) == len(REQUESTED_SKILLS)

    for skill_name in REQUESTED_SKILLS:
        assert poc_for_skill(skill_name).skill_name == skill_name


def test_skill_paths_and_code_refs_exist() -> None:
    for poc in JAREDBOT_POCS:
        assert _path(poc.skill_path).exists(), poc.skill_path

        for ref in (*poc.code_refs, *poc.proof_refs):
            assert _path(ref).exists(), f"{poc.skill_name}: {ref}"

        for stage in poc.stages:
            for ref in stage.code_refs:
                assert _path(ref).exists(), f"{poc.skill_name} stage {stage.order}: {ref}"


def test_poc_stages_are_ordered_and_auditable() -> None:
    for poc in JAREDBOT_POCS:
        assert [stage.order for stage in poc.stages] == list(range(1, len(poc.stages) + 1))
        assert len(poc.stages) >= 4, poc.skill_name
        assert poc.module.startswith("JB-"), poc.skill_name
        assert poc.strategy_surface, poc.skill_name
        assert poc.allowed_use, poc.skill_name
        assert poc.scope_note, poc.skill_name
        assert poc.workflow_requirement, poc.skill_name
        assert poc.required_signals, poc.skill_name
        assert poc.safety_invariants, poc.skill_name
        assert poc.proof_refs, poc.skill_name

        for stage in poc.stages:
            assert stage.name, poc.skill_name
            assert stage.code_refs, poc.skill_name
            assert stage.validation, poc.skill_name


def test_only_existing_capital_moving_paths_are_marked_executable() -> None:
    assert {poc.skill_name for poc in executable_pocs()} == EXPECTED_EXECUTABLE

    for poc in executable_pocs():
        assert poc.status is PocStatus.EXECUTABLE
        assert poc.capital_mode is CapitalMode.LIVE_TX
        joined_refs = " ".join(
            (*poc.code_refs, *poc.proof_refs, *(ref for stage in poc.stages for ref in stage.code_refs))
        )
        assert "contracts/" in joined_refs, poc.skill_name
        assert any("test" in ref for ref in poc.proof_refs), poc.skill_name


def test_strategy_pocs_with_missing_components_require_workflows() -> None:
    assert {poc.skill_name for poc in pocs_for_status(PocStatus.NEEDS_WORKFLOW)} == EXPECTED_NEEDS_WORKFLOW

    for poc in pocs_for_status(PocStatus.NEEDS_WORKFLOW):
        assert poc.capital_mode is CapitalMode.WORKFLOW_REQUIRED
        requirement = poc.workflow_requirement.lower()
        assert any(marker in requirement for marker in ("builder", "executor", "simulation", "tests")), (
            poc.skill_name,
            poc.workflow_requirement,
        )

    assert poc_for_skill("jaredbot-mev-launch-sniper") in workflow_required_pocs()
    assert poc_for_skill("jaredbot-mev-jit-v4") in workflow_required_pocs()


def test_launch_sniper_code_path_still_awaits_executor_workflow() -> None:
    source = _path("coordinator/src/strategies/launch-sniper.ts").read_text()

    assert "launch_sniper_execution_disabled_pending_audited_executor" in source
    assert "return null" in source
    assert poc_for_skill("jaredbot-mev-launch-sniper").capital_mode is CapitalMode.WORKFLOW_REQUIRED


def test_defensive_pocs_do_not_emit_transactions() -> None:
    defensive_names = {poc.skill_name for poc in JAREDBOT_POCS if poc.status is PocStatus.DEFENSIVE}

    assert defensive_names == {
        "jaredbot-crypto-bot-security",
        "jaredbot-defi-adjacent-context",
        "jaredbot-mev-amm-economics",
        "jaredbot-mev-protection",
    }
    for name in defensive_names:
        assert poc_for_skill(name).capital_mode in {CapitalMode.NO_TX, CapitalMode.READ_ONLY}


def test_infrastructure_pocs_are_not_strategy_transaction_builders() -> None:
    infra_names = {poc.skill_name for poc in pocs_for_status(PocStatus.INFRASTRUCTURE)}

    assert infra_names == {
        "jaredbot-mev-bot-engineering",
        "jaredbot-mev-frontrun",
        "jaredbot-mev-mempool-relay",
    }
    for name in infra_names:
        poc = poc_for_skill(name)
        assert poc.capital_mode is CapitalMode.READ_ONLY
        assert not poc.can_emit_transaction
