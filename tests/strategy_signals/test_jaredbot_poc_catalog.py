from __future__ import annotations

from degenbot.strategy_signals.jaredbot_poc_catalog import (
    JAREDBOT_POCS,
    CapitalMode,
    PocStatus,
    executable_pocs,
    poc_for_skill,
    pocs_for_status,
    workflow_required_pocs,
)

EXPECTED_EXECUTABLE = frozenset({
    "jaredbot-mev-flash-arbitrage",
    "jaredbot-mev-liquidations",
})

EXPECTED_NEEDS_WORKFLOW = frozenset({
    "jaredbot-mev-jit-v4",
    "jaredbot-mev-launch-sniper",
    "jaredbot-mev-ostium-oracle-gap",
})


def test_catalog_owns_all_jaredbot_strategy_signal_lanes() -> None:
    skill_names = {poc.skill_name for poc in JAREDBOT_POCS}

    assert len(JAREDBOT_POCS) == 12
    assert all(name.startswith("jaredbot-") for name in skill_names)
    assert all(poc.required_signals for poc in JAREDBOT_POCS)
    assert all(poc.stages for poc in JAREDBOT_POCS)


def test_executable_lanes_are_live_tx_lanes() -> None:
    assert {poc.skill_name for poc in executable_pocs()} == EXPECTED_EXECUTABLE
    assert all(poc.status is PocStatus.EXECUTABLE for poc in executable_pocs())
    assert all(poc.capital_mode is CapitalMode.LIVE_TX for poc in executable_pocs())


def test_workflow_required_lanes_are_explicit_strategy_workflows() -> None:
    workflow_names = {poc.skill_name for poc in workflow_required_pocs()}

    assert workflow_names == EXPECTED_NEEDS_WORKFLOW
    assert workflow_names == {poc.skill_name for poc in pocs_for_status(PocStatus.NEEDS_WORKFLOW)}
    for poc in workflow_required_pocs():
        assert poc.capital_mode is CapitalMode.WORKFLOW_REQUIRED
        assert any(
            marker in poc.workflow_requirement.lower()
            for marker in ("builder", "executor", "simulation", "tests")
        )


def test_skill_lookup_is_total_for_catalog_members() -> None:
    for poc in JAREDBOT_POCS:
        assert poc_for_skill(poc.skill_name) is poc
