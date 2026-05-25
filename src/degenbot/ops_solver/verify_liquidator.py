"""Verify the deployed `LiquidationExecutor.sol` against expected config.

Run via ApeWorx:
    cd solver
    uv sync --extra ops
    ape run driver/ops/verify_liquidator.py --network arbitrum:mainnet:alchemy

Required env vars:
    LIQUIDATOR_ADDRESS  - the contract under verification
    SAFE_ADDRESS        - expected owner (1-of-3 Safe per ADR-020)

Optional env vars:
    DELEGATEE_ADDRESSES - comma-separated EOAs we expect to find whitelisted

The script asserts the contract's hard-coded constants match the
verified-live anchors and exits non-zero on any mismatch so this can
be wired into a post-deploy CI gate.

Foundry remains the canonical contract dev framework per PROGRESS.md;
this is a Python-side post-deploy assertion only.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

# Verified live at block 460,140,172 (2026-05-06) per
# docs/research/2026-05-06-defillama-arbitrum-liquidator-build.pdf.
EXPECTED_AAVE_V3_POOL = "0x794a61358D6845594F94dc1DB02A252b5b4814aD"
EXPECTED_BALANCER_VAULT = "0xBA12222222228d8Ba445958a75a0704d566BF2C8"
EXPECTED_UNIV3_ROUTER = "0x68b3465833fB72A70ecDF485E0e4C7bD8665Fc45"


# Minimal ABI — only the views the verifier needs. Avoids pulling in the
# Foundry build artifact, so this script stays self-contained.
LIQUIDATOR_ABI: list[dict[str, object]] = [
    {
        "inputs": [],
        "name": "AAVE_V3_POOL",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "BALANCER_VAULT",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "UNIV3_ROUTER",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
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
    {
        "inputs": [{"internalType": "address", "name": "", "type": "address"}],
        "name": "delegatees",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
]


@dataclass
class Finding:
    name: str
    expected: str
    actual: str
    ok: bool


def _checksum(addr: str) -> str:
    """Lower-case canonicalisation; ape returns checksummed addresses."""
    return addr.lower()


def liquidator_address_from_env(env: Mapping[str, str]) -> str | None:
    """Return the LiquidationExecutor address from canonical or legacy env."""

    return env.get("LIQUIDATOR_ADDRESS") or env.get("LIQUIDATION_EXECUTOR_ADDRESS")


def delegatee_csv_from_env(env: Mapping[str, str]) -> str:
    """Return delegatee verifier env, falling back to deploy-script env."""

    return env.get("DELEGATEE_ADDRESSES") or env.get("DELEGATEES_INITIAL") or ""


def build_report(liquidator_address: str, findings: list[Finding]) -> dict[str, object]:
    """Build the JSON-serialisable LiquidationExecutor verification report."""

    return {
        "schema": "liquidation-executor-deployment-verification/v1",
        "chain_id": 42161,
        "liquidator": liquidator_address,
        "checks": [
            {
                "name": f.name,
                "expected": f.expected,
                "actual": f.actual,
                "ok": f.ok,
            }
            for f in findings
        ],
        "all_passed": all(f.ok for f in findings),
    }


def write_report(path: Path, report: Mapping[str, object]) -> None:
    """Write a pure JSON verification report for downstream readiness gates."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(report, indent=2, sort_keys=True)}\n", encoding="utf-8")


# pylint: disable=too-many-locals
def main() -> None:
    """ApeWorx entrypoint."""
    # Lazy import so the main solver loop never pulls Ape into its env.
    import ape_arbitrum  # noqa: F401  # pylint: disable=import-outside-toplevel,import-error,unused-import
    from ape import Contract  # pylint: disable=import-outside-toplevel,import-error

    liq_addr = liquidator_address_from_env(os.environ)
    safe_addr = os.environ.get("SAFE_ADDRESS")
    if not liq_addr or not safe_addr:
        sys.exit(2)

    # Connect to whichever network ape was invoked with.

    contract = Contract(liq_addr, abi=list(LIQUIDATOR_ABI))

    aave = contract.AAVE_V3_POOL()
    balancer = contract.BALANCER_VAULT()
    uniswap = contract.UNIV3_ROUTER()
    owner = contract.owner()
    paused = bool(contract.paused())

    findings = [
        Finding(
            name="AAVE_V3_POOL",
            expected=EXPECTED_AAVE_V3_POOL,
            actual=aave,
            ok=_checksum(aave) == _checksum(EXPECTED_AAVE_V3_POOL),
        ),
        Finding(
            name="BALANCER_VAULT",
            expected=EXPECTED_BALANCER_VAULT,
            actual=balancer,
            ok=_checksum(balancer) == _checksum(EXPECTED_BALANCER_VAULT),
        ),
        Finding(
            name="UNIV3_ROUTER",
            expected=EXPECTED_UNIV3_ROUTER,
            actual=uniswap,
            ok=_checksum(uniswap) == _checksum(EXPECTED_UNIV3_ROUTER),
        ),
        Finding(
            name="owner",
            expected=safe_addr,
            actual=owner,
            ok=_checksum(owner) == _checksum(safe_addr),
        ),
        Finding(
            name="paused",
            expected="False",
            actual=str(paused),
            ok=paused is False,
        ),
    ]

    delegatee_csv = delegatee_csv_from_env(os.environ).strip()
    if delegatee_csv:
        for d in (a.strip() for a in delegatee_csv.split(",") if a.strip()):
            allowed = bool(contract.delegatees(d))
            findings.append(
                Finding(
                    name=f"delegatees[{d}]",
                    expected="True",
                    actual=str(allowed),
                    ok=allowed,
                )
            )

    report = build_report(liq_addr, findings)
    if output_path := os.environ.get("OUTPUT_PATH"):
        write_report(Path(output_path), report)

    if not report["all_passed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
