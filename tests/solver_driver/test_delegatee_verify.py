from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from degenbot.ops_solver import delegatee_verify as verifier

if TYPE_CHECKING:
    from pathlib import Path


class FakeDelegateeContract:
    def __init__(self, allowed: set[str]) -> None:
        self._allowed = {address.lower() for address in allowed}

    def delegatees(self, address: str) -> bool:
        return address.lower() in self._allowed


def test_parse_delegatee_csv_requires_valid_delegatees() -> None:
    delegatee = "0x000000000000000000000000000000000000dEaD"

    assert verifier.parse_delegatee_csv(f" {delegatee} ") == (delegatee,)

    with pytest.raises(ValueError, match="at least one"):
        verifier.parse_delegatee_csv("")
    with pytest.raises(ValueError, match="20-byte"):
        verifier.parse_delegatee_csv("not-an-address")


def test_delegatee_csv_from_env_accepts_deploy_script_alias() -> None:
    explicit = "0x000000000000000000000000000000000000dEaD"
    deploy_script = "0x000000000000000000000000000000000000bEEF"

    assert verifier.delegatee_csv_from_env({"DELEGATEES_INITIAL": deploy_script}) == (
        deploy_script,
        "DELEGATEES_INITIAL",
    )
    assert verifier.delegatee_csv_from_env(
        {
            "DELEGATEE_ADDRESSES": explicit,
            "DELEGATEES_INITIAL": deploy_script,
        }
    ) == (explicit, "DELEGATEE_ADDRESSES")

    raw, label = verifier.delegatee_csv_from_env({"DELEGATEES_INITIAL": "not-an-address"})
    with pytest.raises(ValueError, match="DELEGATEES_INITIAL"):
        verifier.parse_delegatee_csv(raw, label=label)


def test_collect_delegatee_findings_checks_both_contracts() -> None:
    delegatee = "0x000000000000000000000000000000000000dEaD"
    findings = verifier.collect_delegatee_findings(
        FakeDelegateeContract({delegatee}),
        FakeDelegateeContract(set()),
        executor_address="0x0000000000000000000000000000000000001111",
        liquidation_address="0x0000000000000000000000000000000000002222",
        delegatees=(delegatee,),
    )

    assert [(finding.contract, finding.ok) for finding in findings] == [
        ("Executor", True),
        ("LiquidationExecutor", False),
    ]


def test_delegatee_report_writes_pure_json(tmp_path: Path) -> None:
    delegatee = "0x000000000000000000000000000000000000dEaD"
    findings = verifier.collect_delegatee_findings(
        FakeDelegateeContract({delegatee}),
        FakeDelegateeContract({delegatee}),
        executor_address="0x0000000000000000000000000000000000001111",
        liquidation_address="0x0000000000000000000000000000000000002222",
        delegatees=(delegatee,),
    )
    report = verifier.build_report(
        executor_address="0x0000000000000000000000000000000000001111",
        liquidation_address="0x0000000000000000000000000000000000002222",
        delegatees=(delegatee,),
        findings=findings,
    )
    output_path = tmp_path / "delegatee-verification.json"

    verifier.write_report(output_path, report)

    assert json.loads(output_path.read_text())["all_passed"] is True
