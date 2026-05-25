"""Prepare the incident-response `Executor.pause()` Safe action.

Run via ApeWorx:
    cd solver
    uv sync --extra ops
    EXECUTOR_ADDRESS=0x... SAFE_ADDRESS=0x... ape run driver/ops/anomaly_response.py --network arbitrum:mainnet:alchemy

This is the on-chain half of the kill switch documented in the architecture:
the off-chain coordinator must stop dispatch first, then the owner Safe signs
`Executor.pause()`. This script does not hold a hot signing key and does not
broadcast. It verifies the deployed Executor owner/pause state and emits a
deterministic action payload for Safe signers or downstream Safe-service tooling.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
PAUSE_SELECTOR = "0x8456cb59"
DEFAULT_CHAIN_ID = 42161

EXECUTOR_GUARD_ABI: list[dict[str, object]] = [
    {
        "inputs": [],
        "name": "owner",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "paused",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
]


@dataclass(frozen=True)
class PauseReadiness:
    """Read-only state needed before asking the owner Safe to pause."""

    executor_owner: str
    expected_safe: str
    executor_paused: bool

    @property
    def owner_matches(self) -> bool:
        return same_address(self.executor_owner, self.expected_safe)

    @property
    def needs_pause(self) -> bool:
        return self.owner_matches and not self.executor_paused


@dataclass(frozen=True)
class PausePayloadRequest:
    """Inputs required to build the incident action payload."""

    executor_address: str
    safe_address: str
    chain_id: int
    readiness: PauseReadiness
    incident_id: str
    reason: str
    created_at: str


def require_address(value: object, label: str) -> str:
    """Validate a nonzero EVM address string."""

    if not isinstance(value, str) or not ADDRESS_RE.fullmatch(value):
        raise ValueError(f"{label} must be a 20-byte hex address")
    if value.lower() == ZERO_ADDRESS:
        raise ValueError(f"{label} must not be the zero address")
    return value


def same_address(a: str, b: str) -> bool:
    """Case-insensitive address comparison."""

    return a.lower() == b.lower()


def parse_chain_id(raw: str | None) -> int:
    """Parse CHAIN_ID with Arbitrum One as the locked default."""

    if raw is None or not raw.strip():
        return DEFAULT_CHAIN_ID

    chain_id = int(raw, 10)
    if chain_id <= 0:
        raise ValueError("CHAIN_ID must be positive")
    return chain_id


def build_pause_transaction(executor_address: str) -> dict[str, Any]:
    """Build the single Safe call required to pause Executor dispatch."""

    return {
        "to": executor_address,
        "value": "0",
        "data": PAUSE_SELECTOR,
        "operation": "CALL",
        "contractMethod": {
            "name": "pause",
            "payable": False,
            "inputs": [],
        },
        "contractInputsValues": {},
    }


def build_pause_payload(request: PausePayloadRequest) -> dict[str, Any]:
    """Build a deterministic incident action payload for Safe signers."""

    readiness = request.readiness
    action_required = readiness.needs_pause
    status = "needs_safe_signature"
    if not readiness.owner_matches:
        status = "blocked_owner_mismatch"
    elif readiness.executor_paused:
        status = "already_paused"

    transactions = [build_pause_transaction(request.executor_address)] if action_required else []

    return {
        "schema": "mev-arbitrum.ops.anomaly-response.v1",
        "status": status,
        "action_required": action_required,
        "chain_id": request.chain_id,
        "safe_address": request.safe_address,
        "executor_address": request.executor_address,
        "incident": {
            "id": request.incident_id,
            "reason": request.reason,
            "created_at": request.created_at,
        },
        "checks": {
            "executor_owner": readiness.executor_owner,
            "expected_safe": readiness.expected_safe,
            "owner_matches": readiness.owner_matches,
            "executor_paused": readiness.executor_paused,
        },
        "transactions": transactions,
        "operator_instructions": [
            "Confirm coordinator dispatch is disabled before signing.",
            "Have the owner Safe sign and execute Executor.pause().",
            "Record the executed transaction hash in the incident log.",
        ],
    }


def payload_exit_code(payload: dict[str, Any]) -> int:
    """Translate payload status into shell exit semantics."""

    if payload["status"] == "blocked_owner_mismatch":
        return 1
    return 0


def write_payload(payload: dict[str, Any], output_path: str | None) -> None:
    """Emit the JSON payload to stdout and optionally persist it."""

    text = json.dumps(payload, indent=2, sort_keys=True)
    print(text)
    if output_path:
        Path(output_path).write_text(f"{text}\n")


def main() -> None:
    """ApeWorx entrypoint."""

    # Lazy import so the solver hot path never imports Ape.
    import ape_arbitrum  # noqa: F401  # pylint: disable=import-outside-toplevel,import-error,unused-import
    from ape import Contract, networks  # pylint: disable=import-outside-toplevel,import-error

    try:
        executor_address = require_address(os.environ.get("EXECUTOR_ADDRESS"), "EXECUTOR_ADDRESS")
        safe_address = require_address(os.environ.get("SAFE_ADDRESS"), "SAFE_ADDRESS")
        chain_id = parse_chain_id(os.environ.get("CHAIN_ID"))
    except ValueError as exc:
        print(f"[anomaly-response] {exc}", file=sys.stderr)
        sys.exit(2)

    reason = os.environ.get("ANOMALY_REASON", "operator-requested pause")
    incident_id = os.environ.get("INCIDENT_ID", "manual")
    created_at = datetime.now(UTC).isoformat()

    print(f"[anomaly-response] network: {networks.active_provider.name}", file=sys.stderr)
    print(f"[anomaly-response] executor: {executor_address}", file=sys.stderr)
    print(f"[anomaly-response] safe:     {safe_address}", file=sys.stderr)

    contract = Contract(executor_address, abi=list(EXECUTOR_GUARD_ABI))
    readiness = PauseReadiness(
        executor_owner=str(contract.owner()),
        expected_safe=safe_address,
        executor_paused=bool(contract.paused()),
    )
    payload = build_pause_payload(
        PausePayloadRequest(
            executor_address=executor_address,
            safe_address=safe_address,
            chain_id=chain_id,
            readiness=readiness,
            incident_id=incident_id,
            reason=reason,
            created_at=created_at,
        )
    )
    write_payload(payload, os.environ.get("OUTPUT_PATH"))
    sys.exit(payload_exit_code(payload))


if __name__ == "__main__":
    main()
