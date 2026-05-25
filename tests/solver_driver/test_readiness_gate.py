from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

from degenbot.ops_solver import readiness_gate
from degenbot.strategies_solver.execution_workflows import EXECUTION_WORKFLOWS
from degenbot.strategies_solver.strategy_intelligence import STRATEGY_INTELLIGENCE_PROFILES

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any

    import pytest


def test_poc_readiness_gate_passes_current_repository_state() -> None:
    report = readiness_gate.build_readiness_report()

    assert report.poc_ready is True
    assert all(finding.ok for finding in report.findings)


def test_mainnet_readiness_remains_blocked_by_explicit_gates() -> None:
    report = readiness_gate.build_readiness_report()

    assert report.mainnet_ready is False
    assert not any(blocker.blocks_mainnet for blocker in report.blockers)
    assert report.failed_external_mainnet_gates
    assert {gate.gate_id for gate in report.external_mainnet_gates if not gate.ok} == {
        "executor_deploy_verify",
        "delegatee_verify",
    }


def test_readiness_gate_blockers_match_strategy_profiles() -> None:
    report = readiness_gate.build_readiness_report()
    expected = {
        (profile.workflow_id, blocker.description, blocker.blocks_mainnet)
        for profile in STRATEGY_INTELLIGENCE_PROFILES
        for blocker in profile.blockers
    }
    actual = {
        (blocker.workflow_id, blocker.description, blocker.blocks_mainnet)
        for blocker in report.blockers
    }

    assert actual == expected


def test_required_poc_commands_cover_all_stacks() -> None:
    report = readiness_gate.build_readiness_report()
    commands = "\n".join(report.required_poc_commands)

    assert "ruff check" in commands
    assert "pytest" in commands
    assert "bun run test" in commands
    assert "forge test" in commands
    assert "git diff --check" in commands
    assert all(command.startswith("cd ") for command in report.required_poc_commands)
    assert "cd coordinator && env -u NODE_OPTIONS bun run test" in commands


def test_readiness_gate_covers_every_workflow_and_profile() -> None:
    report = readiness_gate.build_readiness_report()
    finding_names = {finding.name for finding in report.findings}

    for workflow in EXECUTION_WORKFLOWS:
        assert any(name.startswith(f"{workflow.workflow_id}.") for name in finding_names)
    for profile in STRATEGY_INTELLIGENCE_PROFILES:
        assert profile.workflow_id in {workflow.workflow_id for workflow in EXECUTION_WORKFLOWS}


def test_json_report_is_serialisable() -> None:
    report = readiness_gate.build_readiness_report()
    encoded = json.dumps(readiness_gate.report_to_dict(report), sort_keys=True)

    assert '"poc_ready": true' in encoded


def test_secrets_policy_allows_ignored_local_env_files() -> None:
    assert readiness_gate._production_secrets_untracked() is True


def test_secrets_policy_rejects_tracked_env_files(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=("git", "ls-files"),
            returncode=0,
            stdout=".env.example\ncontracts/.env\ncoordinator/.env.local\n",
            stderr="",
        )

    monkeypatch.setattr(readiness_gate.subprocess, "run", fake_run)

    assert readiness_gate._tracked_secret_env_files() == (
        "contracts/.env",
        "coordinator/.env.local",
    )
    assert readiness_gate._production_secrets_untracked() is False


def test_deployment_report_validation_rejects_weak_evidence(tmp_path: Path) -> None:
    report_path = tmp_path / "executor-verification.json"
    report_path.write_text('{"all_passed": true}')

    assert (
        readiness_gate._deployment_report_passes(
            report_path,
            address_key="executor",
            schema="executor-deployment-verification/v1",
        )
        is False
    )

    report_path.write_text(
        json.dumps(
            {
                "schema": "executor-deployment-verification/v1",
                "chain_id": 42161,
                "executor": "0x0000000000000000000000000000000000001111",
                "checks": [{"name": "paused", "ok": True}],
                "all_passed": True,
            }
        )
    )

    assert readiness_gate._deployment_report_passes(
        report_path,
        address_key="executor",
        schema="executor-deployment-verification/v1",
    )


def test_delegatee_report_validation_requires_both_contracts(tmp_path: Path) -> None:
    delegatee = "0x000000000000000000000000000000000000dEaD"
    report_path = tmp_path / "delegatee-verification.json"
    base_report: dict[str, Any] = {
        "schema": "delegatee-registration-verification/v1",
        "chain_id": 42161,
        "executor": "0x0000000000000000000000000000000000001111",
        "liquidator": "0x0000000000000000000000000000000000002222",
        "delegatees": [delegatee],
        "checks": [
            {
                "contract": "Executor",
                "contract_address": "0x0000000000000000000000000000000000001111",
                "delegatee": delegatee,
                "ok": True,
            }
        ],
        "all_passed": True,
    }
    report_path.write_text(json.dumps(base_report))

    assert readiness_gate._delegatee_report_passes(report_path) is False

    base_report["checks"].append(
        {
            "contract": "LiquidationExecutor",
            "contract_address": "0x0000000000000000000000000000000000002222",
            "delegatee": delegatee,
            "ok": True,
        }
    )
    report_path.write_text(json.dumps(base_report))

    assert readiness_gate._delegatee_report_passes(report_path)


def test_cli_exit_codes_reflect_poc_vs_mainnet_modes(capsys: pytest.CaptureFixture[str]) -> None:
    assert readiness_gate.main(["--json"]) == 0
    output = capsys.readouterr().out
    assert '"poc_ready": true' in output

    assert readiness_gate.main(["--strict-mainnet"]) == 1
