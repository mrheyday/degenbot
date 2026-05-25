"""Verify a deployed Executor against the canonical Arbitrum config.

Run via ApeWorx:
    cd solver
    uv sync --extra ops
    EXECUTOR_ADDRESS=0x... ape run driver/ops/deploy_verify.py --network arbitrum:mainnet:alchemy

The verifier loads the deployed `Executor`, queries every constructor-pinned
address exposed by public getters, and asserts it matches
`contracts/script/config/arbitrum-one.json` (or `CONFIG_PATH`). It exits
non-zero on any mismatch so post-deploy CI can gate release promotion.

Foundry remains the canonical contract dev framework per PROGRESS.md; this is a
Python-side post-deploy assertion only.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast


def _find_repo_root() -> Path:
    """Find the mev-arbitrum project root from a vendored degenbot checkout."""

    current = Path(__file__).resolve().parent
    while current.parent != current:
        if (current / "PROGRESS.md").exists() and (current / "contracts").exists():
            return current
        current = current.parent
    return Path(__file__).resolve().parents[5]


REPO_ROOT = _find_repo_root()
DEFAULT_CONFIG_PATH = REPO_ROOT / "contracts/script/config/arbitrum-one.json"
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


@dataclass(frozen=True)
class ConfigBinding:
    """Mapping between an Executor getter and a JSON config address path."""

    getter: str
    address_path: str
    verified_path: str


@dataclass(frozen=True)
class ExpectedCall:
    """Expected address returned by a deployed Executor getter."""

    getter: str
    expected: str
    config_path: str


@dataclass(frozen=True)
class Finding:
    """Single verification result emitted in the JSON report."""

    name: str
    expected: str
    actual: str
    ok: bool


CONFIG_BINDINGS: tuple[ConfigBinding, ...] = (
    ConfigBinding("owner", "owner", "_owner_verified"),
    ConfigBinding(
        "ONEINCH_V6_ROUTER",
        "aggregators.oneInchV6Router.address",
        "aggregators.oneInchV6Router._verified",
    ),
    ConfigBinding(
        "ZEROX_EXCHANGE_PROXY",
        "aggregators.zeroExExchangeProxy.address",
        "aggregators.zeroExExchangeProxy._verified",
    ),
    ConfigBinding(
        "PARASWAP_AUGUSTUS",
        "aggregators.paraswapAugustus.address",
        "aggregators.paraswapAugustus._verified",
    ),
    ConfigBinding(
        "ODOS_ROUTER", "aggregators.odosRouter.address", "aggregators.odosRouter._verified"
    ),
    ConfigBinding(
        "KYBER_META_AGGREGATION",
        "aggregators.kyberMetaAggregation.address",
        "aggregators.kyberMetaAggregation._verified",
    ),
    ConfigBinding(
        "OPENOCEAN_EXCHANGE",
        "aggregators.openOceanExchange.address",
        "aggregators.openOceanExchange._verified",
    ),
    ConfigBinding("AAVE_V3_POOL", "lenders.aaveV3Pool.address", "lenders.aaveV3Pool._verified"),
    ConfigBinding("MORPHO_BLUE", "lenders.morphoBlue.address", "lenders.morphoBlue._verified"),
    ConfigBinding(
        "COW_SETTLEMENT", "venues.cowSettlement.address", "venues.cowSettlement._verified"
    ),
    ConfigBinding(
        "COW_FLASH_LOAN_ROUTER",
        "venues.cowFlashLoanRouter.address",
        "venues.cowFlashLoanRouter._verified",
    ),
    ConfigBinding(
        "UNISWAPX_DUTCH_REACTOR",
        "venues.uniswapxDutchReactor.address",
        "venues.uniswapxDutchReactor._verified",
    ),
    ConfigBinding(
        "ACROSS_SPOKEPOOL", "venues.acrossSpokePool.address", "venues.acrossSpokePool._verified"
    ),
    ConfigBinding("WETH", "tokens.weth.address", "tokens.weth._verified"),
    ConfigBinding("USDC", "tokens.usdc.address", "tokens.usdc._verified"),
    ConfigBinding("USDT", "tokens.usdt.address", "tokens.usdt._verified"),
)


def _address_view(name: str) -> dict[str, object]:
    return {
        "inputs": [],
        "name": name,
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    }


def _bool_view(name: str) -> dict[str, object]:
    return {
        "inputs": [],
        "name": name,
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    }


EXECUTOR_ABI: list[dict[str, object]] = [
    *[_address_view(binding.getter) for binding in CONFIG_BINDINGS],
    _bool_view("paused"),
    {
        "inputs": [{"internalType": "address", "name": "", "type": "address"}],
        "name": "delegatees",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
]


def _node_at(config: Mapping[str, object], path: str) -> object:
    node: object = config
    for part in path.split("."):
        if not isinstance(node, Mapping):
            msg = f"config path {path!r} crosses non-object node at {part!r}"
            raise ValueError(msg)
        mapping = cast("Mapping[str, object]", node)
        if part not in mapping:
            msg = f"config path {path!r} missing key {part!r}"
            raise ValueError(msg)
        node = mapping[part]
    return node


def _require_verified(config: Mapping[str, object], binding: ConfigBinding) -> None:
    verified = _node_at(config, binding.verified_path)
    if verified is not True:
        msg = f"config path {binding.verified_path!r} is not verified"
        raise ValueError(msg)


def _require_address(value: object, label: str) -> str:
    if not isinstance(value, str) or not ADDRESS_RE.fullmatch(value):
        msg = f"{label} must be a 20-byte hex address"
        raise ValueError(msg)
    if value.lower() == ZERO_ADDRESS:
        msg = f"{label} must not be the zero address"
        raise ValueError(msg)
    return value


def _same_address(a: str, b: str) -> bool:
    return a.lower() == b.lower()


def load_expected_executor_config(
    config_path: Path = DEFAULT_CONFIG_PATH,
) -> tuple[ExpectedCall, ...]:
    """Load and validate the canonical Executor address bundle."""

    raw = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        msg = f"{config_path} must contain a JSON object"
        raise ValueError(msg)
    config = cast("Mapping[str, object]", raw)

    expected: list[ExpectedCall] = []
    for binding in CONFIG_BINDINGS:
        _require_verified(config, binding)
        address = _require_address(_node_at(config, binding.address_path), binding.address_path)
        expected.append(
            ExpectedCall(getter=binding.getter, expected=address, config_path=binding.address_path)
        )
    return tuple(expected)


def parse_delegatee_csv(raw: str | None, *, label: str = "DELEGATEE_ADDRESSES") -> tuple[str, ...]:
    """Parse optional comma-separated delegatee assertions."""

    if raw is None or not raw.strip():
        return ()

    delegatees: list[str] = []
    for item in raw.split(","):
        value = item.strip()
        if not value:
            continue
        delegatees.append(_require_address(value, label))
    return tuple(delegatees)


def delegatee_csv_from_env(env: Mapping[str, str]) -> str | None:
    """Return the explicit delegatee verifier env, falling back to deploy-script env."""

    return env.get("DELEGATEE_ADDRESSES") or env.get("DELEGATEES_INITIAL")


def collect_contract_findings(
    contract: object,
    expected_calls: Sequence[ExpectedCall],
    expected_delegatees: Sequence[str] = (),
) -> tuple[Finding, ...]:
    """Query the live contract object and build deterministic verification findings."""

    findings: list[Finding] = []
    for expected in expected_calls:
        actual = str(getattr(contract, expected.getter)())
        findings.append(
            Finding(
                name=expected.getter,
                expected=expected.expected,
                actual=actual,
                ok=_same_address(actual, expected.expected),
            )
        )

    paused = bool(contract.paused())
    findings.append(
        Finding(name="paused", expected="False", actual=str(paused), ok=paused is False)
    )

    for delegatee in expected_delegatees:
        allowed = bool(contract.delegatees(delegatee))
        findings.append(
            Finding(
                name=f"delegatees[{delegatee}]",
                expected="True",
                actual=str(allowed),
                ok=allowed,
            )
        )

    return tuple(findings)


def build_report(
    executor_address: str, config_path: Path, findings: Sequence[Finding]
) -> dict[str, object]:
    """Build the JSON-serialisable deployment verification report."""

    return {
        "schema": "executor-deployment-verification/v1",
        "chain_id": 42161,
        "executor": executor_address,
        "config_path": str(config_path),
        "checks": [
            {
                "name": finding.name,
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

    # Lazy import so the main solver loop never pulls Ape into its env.
    import ape_arbitrum  # noqa: F401  # pylint: disable=import-outside-toplevel,import-error,unused-import
    from ape import Contract  # pylint: disable=import-outside-toplevel,import-error

    raw_executor_address = os.environ.get("EXECUTOR_ADDRESS")
    if raw_executor_address is None:
        sys.stderr.write("[deploy-verify] EXECUTOR_ADDRESS must be set\n")
        sys.exit(2)

    executor_address = _require_address(raw_executor_address, "EXECUTOR_ADDRESS")
    raw_config_path = os.environ.get("CONFIG_PATH")
    config_path = Path(raw_config_path) if raw_config_path else DEFAULT_CONFIG_PATH
    expected_calls = load_expected_executor_config(config_path)
    expected_delegatees = parse_delegatee_csv(delegatee_csv_from_env(os.environ))

    contract = Contract(executor_address, abi=list(EXECUTOR_ABI))
    findings = collect_contract_findings(contract, expected_calls, expected_delegatees)
    report = build_report(executor_address, config_path, findings)
    if output_path := os.environ.get("OUTPUT_PATH"):
        write_report(Path(output_path), report)
    sys.stdout.write(f"{json.dumps(report, indent=2, sort_keys=True)}\n")

    if not report["all_passed"]:
        sys.stderr.write("[deploy-verify] FAILED - see report above\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
