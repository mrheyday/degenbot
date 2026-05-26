from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from degenbot.ops_solver import deploy_verify as verifier

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from typing import Any


class FakeExecutor:
    def __init__(
        self,
        values: dict[str, str],
        *,
        paused: bool = False,
        delegatees: set[str] | None = None,
    ) -> None:
        self._values = values
        self._paused = paused
        self._delegatees = {addr.lower() for addr in delegatees or set()}

    def __getattr__(self, name: str) -> Callable[[], str]:
        if name in self._values:
            return lambda: self._values[name]
        raise AttributeError(name)

    def paused(self) -> bool:
        return self._paused

    def delegatees(self, address: str) -> bool:
        return address.lower() in self._delegatees


def _write_config(tmp_path: Path, mutator: Callable[[dict[str, Any]], None] | None = None) -> Path:
    data = json.loads(verifier.DEFAULT_CONFIG_PATH.read_text())
    if mutator is not None:
        mutator(data)

    path = tmp_path / "arbitrum-one.json"
    path.write_text(json.dumps(data))
    return path


def test_load_expected_executor_config_reads_all_constructor_pins() -> None:
    expected = {call.getter: call.expected for call in verifier.load_expected_executor_config()}
    config = json.loads(verifier.DEFAULT_CONFIG_PATH.read_text())

    assert len(expected) == 16
    assert expected["owner"] == config["owner"]
    assert expected["ONEINCH_V6_ROUTER"] == "0x111111125421cA6dc452d289314280a0f8842A65"
    assert expected["COW_SETTLEMENT"] == "0x9008D19f58AAbD9eD0D60971565AA8510560ab41"
    assert expected["UNISWAPX_DUTCH_REACTOR"] == "0xB274d5F4b833b61B340b654d600A864fB604a87c"
    assert expected["ACROSS_SPOKEPOOL"] == "0xe35e9842fceaCA96570B734083f4a58e8F7C5f2A"


def test_load_expected_executor_config_rejects_unverified_entries(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path,
        lambda data: data["venues"]["cowSettlement"].__setitem__("_verified", False),
    )

    with pytest.raises(ValueError, match=r"venues\.cowSettlement\._verified.*not verified"):
        verifier.load_expected_executor_config(path)


def test_load_expected_executor_config_rejects_zero_addresses(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path,
        lambda data: data["venues"]["cowSettlement"].__setitem__("address", verifier.ZERO_ADDRESS),
    )

    with pytest.raises(ValueError, match=r"venues\.cowSettlement\.address.*zero address"):
        verifier.load_expected_executor_config(path)


def test_collect_contract_findings_reports_passes_and_delegatees() -> None:
    expected_calls = verifier.load_expected_executor_config()
    values = {call.getter: call.expected.lower() for call in expected_calls}
    delegatee = "0x000000000000000000000000000000000000dEaD"

    findings = verifier.collect_contract_findings(
        FakeExecutor(values, delegatees={delegatee}),
        expected_calls,
        expected_delegatees=(delegatee,),
    )

    assert all(finding.ok for finding in findings)
    assert {finding.name for finding in findings} >= {"owner", "paused", f"delegatees[{delegatee}]"}


def test_collect_contract_findings_reports_address_and_pause_mismatches() -> None:
    expected_calls = (
        verifier.ExpectedCall(
            getter="COW_SETTLEMENT",
            expected="0x9008D19f58AAbD9eD0D60971565AA8510560ab41",
            config_path="venues.cowSettlement.address",
        ),
    )

    findings = verifier.collect_contract_findings(
        FakeExecutor(
            {"COW_SETTLEMENT": "0x000000000000000000000000000000000000dEaD"},
            paused=True,
        ),
        expected_calls,
    )
    report = verifier.build_report(
        "0x000000000000000000000000000000000000bEEF", verifier.DEFAULT_CONFIG_PATH, findings
    )

    assert [finding.ok for finding in findings] == [False, False]
    assert report["all_passed"] is False


def test_parse_delegatee_csv_validates_addresses() -> None:
    assert verifier.parse_delegatee_csv(None) == ()
    assert verifier.parse_delegatee_csv("  ") == ()
    assert verifier.parse_delegatee_csv("0x000000000000000000000000000000000000dEaD") == (
        "0x000000000000000000000000000000000000dEaD",
    )

    with pytest.raises(ValueError, match="DELEGATEE_ADDRESSES"):
        verifier.parse_delegatee_csv("not-an-address")


def test_delegatee_csv_from_env_accepts_deploy_script_alias() -> None:
    delegatee = "0x000000000000000000000000000000000000dEaD"

    assert verifier.delegatee_csv_from_env({"DELEGATEES_INITIAL": delegatee}) == delegatee
    assert verifier.parse_delegatee_csv(
        verifier.delegatee_csv_from_env({"DELEGATEES_INITIAL": delegatee})
    ) == (delegatee,)
