from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from degenbot.ops_solver import anomaly_response as ar

if TYPE_CHECKING:
    from pathlib import Path


EXECUTOR = "0x000000000000000000000000000000000000bEEF"
SAFE = "0x000000000000000000000000000000000000dEaD"


def test_build_pause_transaction_uses_locked_selector() -> None:
    tx = ar.build_pause_transaction(EXECUTOR)

    assert tx["to"] == EXECUTOR
    assert tx["value"] == "0"
    assert tx["data"] == "0x8456cb59"
    assert tx["operation"] == "CALL"
    assert tx["contractMethod"] == {"name": "pause", "payable": False, "inputs": []}
    assert tx["contractInputsValues"] == {}


def test_build_pause_payload_requires_safe_signature_when_owner_matches_and_unpaused() -> None:
    readiness = ar.PauseReadiness(executor_owner=SAFE.lower(), expected_safe=SAFE, executor_paused=False)

    payload = ar.build_pause_payload(
        ar.PausePayloadRequest(
            executor_address=EXECUTOR,
            safe_address=SAFE,
            chain_id=42161,
            readiness=readiness,
            incident_id="incident-1",
            reason="pnl deviation",
            created_at="2026-05-14T00:00:00+00:00",
        )
    )

    assert payload["status"] == "needs_safe_signature"
    assert payload["action_required"] is True
    assert payload["checks"]["owner_matches"] is True
    assert payload["transactions"] == [ar.build_pause_transaction(EXECUTOR)]
    assert ar.payload_exit_code(payload) == 0


def test_build_pause_payload_blocks_owner_mismatch() -> None:
    readiness = ar.PauseReadiness(
        executor_owner="0x0000000000000000000000000000000000000001",
        expected_safe=SAFE,
        executor_paused=False,
    )

    payload = ar.build_pause_payload(
        ar.PausePayloadRequest(
            executor_address=EXECUTOR,
            safe_address=SAFE,
            chain_id=42161,
            readiness=readiness,
            incident_id="incident-1",
            reason="pnl deviation",
            created_at="2026-05-14T00:00:00+00:00",
        )
    )

    assert payload["status"] == "blocked_owner_mismatch"
    assert payload["action_required"] is False
    assert payload["transactions"] == []
    assert ar.payload_exit_code(payload) == 1


def test_build_pause_payload_noops_when_already_paused() -> None:
    readiness = ar.PauseReadiness(executor_owner=SAFE, expected_safe=SAFE, executor_paused=True)

    payload = ar.build_pause_payload(
        ar.PausePayloadRequest(
            executor_address=EXECUTOR,
            safe_address=SAFE,
            chain_id=42161,
            readiness=readiness,
            incident_id="incident-1",
            reason="pnl deviation",
            created_at="2026-05-14T00:00:00+00:00",
        )
    )

    assert payload["status"] == "already_paused"
    assert payload["action_required"] is False
    assert payload["transactions"] == []
    assert ar.payload_exit_code(payload) == 0


def test_parse_chain_id_defaults_to_arbitrum_one() -> None:
    assert ar.parse_chain_id(None) == 42161
    assert ar.parse_chain_id("  ") == 42161
    assert ar.parse_chain_id("421614") == 421614

    with pytest.raises(ValueError, match="CHAIN_ID"):
        ar.parse_chain_id("0")


def test_require_address_rejects_invalid_and_zero_values() -> None:
    assert ar.require_address(EXECUTOR, "EXECUTOR_ADDRESS") == EXECUTOR

    with pytest.raises(ValueError, match="20-byte"):
        ar.require_address("not-an-address", "EXECUTOR_ADDRESS")

    with pytest.raises(ValueError, match="zero address"):
        ar.require_address(ar.ZERO_ADDRESS, "EXECUTOR_ADDRESS")


def test_write_payload_writes_sorted_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    output_path = tmp_path / "pause-plan.json"
    payload = {"schema": "test", "status": "already_paused", "action_required": False}

    ar.write_payload(payload, str(output_path))

    written = json.loads(output_path.read_text())
    printed = json.loads(capsys.readouterr().out)
    assert written == payload
    assert printed == payload
