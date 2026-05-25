"""Verify production delegatee registration on Executor contracts.

Run via ApeWorx:
    cd solver
    uv sync --extra ops
    EXECUTOR_ADDRESS=0x... \
    LIQUIDATOR_ADDRESS=0x... \
    DELEGATEE_ADDRESSES=0x...,0x... \
    OUTPUT_PATH=../docs/runbooks/deployments/mainnet/delegatee-verification.json \
    ape run driver/ops/delegatee_verify.py --network arbitrum:mainnet:alchemy

The script queries both `Executor.delegatees(address)` and
`LiquidationExecutor.delegatees(address)` for every expected hot signer.
It emits non-zero on any missing registration so strict mainnet promotion
cannot silently skip delegatee setup.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")

DELEGATEE_ABI: list[dict[str, object]] = [
    {
        "inputs": [{"internalType": "address", "name": "", "type": "address"}],
        "name": "delegatees",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
]


@dataclass(frozen=True)
class DelegateeFinding:
    """Single delegatee registration check."""

    contract: str
    contract_address: str
    delegatee: str
    expected: str
    actual: str
    ok: bool


class DelegateeReadable(Protocol):
    """Minimal on-chain view used by this verifier."""

    def delegatees(self, address: str) -> bool:
        """Return whether an address is an authorised delegatee."""


def _require_address(value: str | None, label: str) -> str:
    if value is None or not ADDRESS_RE.fullmatch(value):
        msg = f"{label} must be a 20-byte hex address"
        raise ValueError(msg)
    if value.lower() == ZERO_ADDRESS:
        msg = f"{label} must not be the zero address"
        raise ValueError(msg)
    return value


def parse_delegatee_csv(raw: str | None, *, label: str = "DELEGATEE_ADDRESSES") -> tuple[str, ...]:
    """Parse comma-separated delegatee addresses and require at least one."""

    if raw is None or not raw.strip():
        msg = f"{label} must contain at least one address"
        raise ValueError(msg)

    delegatees: list[str] = []
    for item in raw.split(","):
        value = item.strip()
        if value:
            delegatees.append(_require_address(value, label))
    if not delegatees:
        msg = f"{label} must contain at least one address"
        raise ValueError(msg)
    return tuple(delegatees)


def delegatee_csv_from_env(env: Mapping[str, str]) -> tuple[str | None, str]:
    """Return delegatee CSV plus the env label used for validation messages."""

    if env.get("DELEGATEE_ADDRESSES"):
        return env["DELEGATEE_ADDRESSES"], "DELEGATEE_ADDRESSES"
    return env.get("DELEGATEES_INITIAL"), "DELEGATEES_INITIAL"


def collect_delegatee_findings(
    executor_contract: DelegateeReadable,
    liquidation_contract: DelegateeReadable,
    *,
    executor_address: str,
    liquidation_address: str,
    delegatees: Sequence[str],
) -> tuple[DelegateeFinding, ...]:
    """Query both deployed contracts for expected delegatee registrations."""

    findings: list[DelegateeFinding] = []
    targets = (
        ("Executor", executor_address, executor_contract),
        ("LiquidationExecutor", liquidation_address, liquidation_contract),
    )
    for contract_name, contract_address, contract in targets:
        for delegatee in delegatees:
            allowed = bool(contract.delegatees(delegatee))
            findings.append(
                DelegateeFinding(
                    contract=contract_name,
                    contract_address=contract_address,
                    delegatee=delegatee,
                    expected="True",
                    actual=str(allowed),
                    ok=allowed,
                )
            )
    return tuple(findings)


def build_report(
    *,
    executor_address: str,
    liquidation_address: str,
    delegatees: Sequence[str],
    findings: Sequence[DelegateeFinding],
) -> dict[str, object]:
    """Build the JSON-serialisable delegatee verification report."""

    return {
        "schema": "delegatee-registration-verification/v1",
        "chain_id": 42161,
        "executor": executor_address,
        "liquidator": liquidation_address,
        "delegatees": list(delegatees),
        "checks": [
            {
                "contract": finding.contract,
                "contract_address": finding.contract_address,
                "delegatee": finding.delegatee,
                "expected": finding.expected,
                "actual": finding.actual,
                "ok": finding.ok,
            }
            for finding in findings
        ],
        "all_passed": all(finding.ok for finding in findings),
    }


def write_report(path: Path, report: Mapping[str, object]) -> None:
    """Write a pure JSON verification report for downstream readiness gates."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(report, indent=2, sort_keys=True)}\n", encoding="utf-8")


def main() -> None:
    """ApeWorx entrypoint."""

    import ape_arbitrum  # noqa: F401  # pylint: disable=import-outside-toplevel,import-error,unused-import
    from ape import Contract  # pylint: disable=import-outside-toplevel,import-error

    try:
        executor_address = _require_address(os.environ.get("EXECUTOR_ADDRESS"), "EXECUTOR_ADDRESS")
        liquidation_address = _require_address(
            os.environ.get("LIQUIDATOR_ADDRESS") or os.environ.get("LIQUIDATION_EXECUTOR_ADDRESS"),
            "LIQUIDATOR_ADDRESS",
        )
        delegatee_csv, delegatee_label = delegatee_csv_from_env(os.environ)
        delegatees = parse_delegatee_csv(delegatee_csv, label=delegatee_label)
    except ValueError:
        sys.exit(2)

    executor_contract = Contract(executor_address, abi=list(DELEGATEE_ABI))
    liquidation_contract = Contract(liquidation_address, abi=list(DELEGATEE_ABI))
    findings = collect_delegatee_findings(
        executor_contract,
        liquidation_contract,
        executor_address=executor_address,
        liquidation_address=liquidation_address,
        delegatees=delegatees,
    )
    report = build_report(
        executor_address=executor_address,
        liquidation_address=liquidation_address,
        delegatees=delegatees,
        findings=findings,
    )
    if output_path := os.environ.get("OUTPUT_PATH"):
        write_report(Path(output_path), report)

    if not report["all_passed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
