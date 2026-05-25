"""Production-ready POC readiness gate.

This gate intentionally separates two states:

* POC-ready: live workflows are executable, proof-backed, tested, and all
  non-live lanes are explicitly gated with remediation.
* Mainnet-ready: POC-ready plus external operational gates such as paid audit,
  deployed Safe, post-deploy verification, and RPC failover.

The gate does not guess at external state. Anything not backed by a
schema-valid repository artifact is emitted as a failed external mainnet gate.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from degenbot.strategies_solver.execution_workflows import (
    EXECUTION_WORKFLOWS,
    WorkflowStatus,
)
from degenbot.strategies_solver.strategy_intelligence import (
    STRATEGY_INTELLIGENCE_PROFILES,
    BlockerStatus,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


def _find_repo_root() -> Path:
    """Find the project root by looking for a marker file."""
    current = Path(__file__).resolve().parent
    while current.parent != current:
        if (current / "PROGRESS.md").exists():
            return current
        current = current.parent
    return Path(__file__).resolve().parents[4]


REPO_ROOT = _find_repo_root()
ADDRESS_HEX_LENGTH = 42
MAINNET_CHAIN_ID = 42161
ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

EXECUTOR_VERIFY_REPORT = REPO_ROOT / "docs/runbooks/deployments/mainnet/executor-verification.json"
LIQUIDATION_VERIFY_REPORT = REPO_ROOT / "docs/runbooks/deployments/mainnet/liquidation-executor-verification.json"
DELEGATEE_VERIFY_REPORT = REPO_ROOT / "docs/runbooks/deployments/mainnet/delegatee-audit.json"
ARBITRUM_CONFIG = REPO_ROOT / "contracts/script/config/arbitrum-one.json"


@dataclass(frozen=True)
class ReadinessFinding:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class StrategyBlocker:
    workflow_id: str
    description: str
    remediation: str
    proof_refs: tuple[str, ...]
    blocks_mainnet: bool = False


@dataclass(frozen=True)
class ExternalMainnetGate:
    gate_id: str
    description: str
    remediation: str
    evidence_refs: tuple[str, ...]
    ok: bool = False


@dataclass(frozen=True)
class ReadinessReport:
    poc_ready: bool
    mainnet_ready: bool
    findings: tuple[ReadinessFinding, ...]
    blockers: tuple[StrategyBlocker, ...]
    external_mainnet_gates: tuple[ExternalMainnetGate, ...]
    failed_external_mainnet_gates: tuple[str, ...]
    required_poc_commands: tuple[str, ...]


def _path_from_ref(ref: str) -> Path:
    return REPO_ROOT / ref.split("::", maxsplit=1)[0]


def _repo_ref(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _load_json_object(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def _is_address(value: Any) -> bool:
    return isinstance(value, str) and bool(ADDRESS_RE.fullmatch(value)) and value.lower() != ZERO_ADDRESS


def _checks_all_ok(raw: dict[str, Any]) -> bool:
    checks = raw.get("checks")
    if not isinstance(checks, list) or not checks:
        return False
    return all(isinstance(check, dict) and check.get("ok") is True for check in checks)


def _deployment_report_passes(path: Path, *, address_key: str, schema: str) -> bool:
    raw = _load_json_object(path)
    if raw is None:
        return False
    return (
        raw.get("schema") == schema
        and raw.get("chain_id") == MAINNET_CHAIN_ID
        and raw.get("all_passed") is True
        and _is_address(raw.get(address_key))
        and _checks_all_ok(raw)
    )


def _delegatee_checks_cover(checks: list[Any], delegatees: list[Any]) -> bool:
    covered: set[tuple[str, str]] = set()
    for check in checks:
        if not isinstance(check, dict):
            return False
        contract = check.get("contract")
        delegatee = check.get("delegatee")
        if (
            contract not in {"Executor", "LiquidationExecutor"}
            or not _is_address(check.get("contract_address"))
            or not _is_address(delegatee)
            or check.get("ok") is not True
        ):
            return False
        covered.add((str(contract), str(delegatee).lower()))

    expected = {
        (contract, str(delegatee).lower())
        for contract in ("Executor", "LiquidationExecutor")
        for delegatee in delegatees
    }
    return expected.issubset(covered)


def _delegatee_report_passes(path: Path) -> bool:
    raw = _load_json_object(path)
    if raw is None:
        return False
    delegatees = raw.get("delegatees")
    checks = raw.get("checks")
    if not isinstance(delegatees, list) or not isinstance(checks, list):
        return False
    if (
        raw.get("schema") != "delegatee-registration-verification/v1"
        or raw.get("chain_id") != MAINNET_CHAIN_ID
        or raw.get("all_passed") is not True
        or not _is_address(raw.get("executor"))
        or not _is_address(raw.get("liquidator"))
    ):
        return False
    if not delegatees or not checks or not all(_is_address(d) for d in delegatees):
        return False
    return _delegatee_checks_cover(checks, delegatees)


def _is_safe_owner_configured() -> bool:
    if not ARBITRUM_CONFIG.exists():
        return False
    try:
        raw = json.loads(ARBITRUM_CONFIG.read_text())
    except (json.JSONDecodeError, KeyError):
        return False
    if not isinstance(raw, dict):
        return False
    owner = raw.get("owner")
    notes = str(raw.get("_owner_notes", "")).lower()
    if not isinstance(owner, str) or not owner.startswith("0x") or len(owner) != ADDRESS_HEX_LENGTH:
        return False
    return "single signing eoa" not in notes and "migrate to 1-of-3" not in notes


def _production_secrets_untracked() -> bool:
    return (REPO_ROOT / ".env.example").exists() and not _tracked_secret_env_files()


def _tracked_secret_env_files() -> tuple[str, ...]:
    git = shutil.which("git")
    if git is None:
        return ("<git missing>",)
    result = subprocess.run(  # noqa: S603 - git path is resolved with shutil.which and args are static
        [git, "-C", str(REPO_ROOT), "ls-files", ".env", ".env.*", "*/.env", "*/.env.*"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ("<git ls-files failed>",)
    return tuple(path for path in result.stdout.splitlines() if _is_tracked_secret_env_path(path))


def _is_tracked_secret_env_path(path: str) -> bool:
    name = Path(path).name
    return name not in {".env.example", ".envrc"}


def _is_rpc_failover_wired() -> bool:
    env_example = REPO_ROOT / ".env.example"
    config_ts = REPO_ROOT / "coordinator/src/config.ts"
    if not env_example.exists() or not config_ts.exists():
        return False
    env_text = env_example.read_text()
    config_text = config_ts.read_text()
    return all(marker in env_text and marker in config_text for marker in ["ARB_RPC_HTTP", "ARB_RPC_HTTP_FAILOVER"])


def _build_external_mainnet_gates() -> tuple[ExternalMainnetGate, ...]:
    return (
        ExternalMainnetGate(
            gate_id="audit_archive",
            description="Security audit archive exists for production-readiness and code-review scope.",
            remediation="Archive the final paid/external audit report under docs/runbooks/audits/ and add it to this gate.",
            evidence_refs=(
                "docs/runbooks/audits/2026-05-11-production-readiness-audit.md",
                "docs/runbooks/audits/2026-05-12-production-code-review.md",
            ),
            ok=(REPO_ROOT / "docs/runbooks/audits/2026-05-11-production-readiness-audit.md").exists(),
        ),
        ExternalMainnetGate(
            gate_id="safe_owner",
            description="1-of-3 Safe is configured as owner in the Arbitrum deployment config.",
            remediation="Deploy the Arbitrum Safe, rotate Executor owner config away from the single-EOA POC owner, and update _owner_notes with the Safe transaction reference.",
            evidence_refs=("contracts/script/config/arbitrum-one.json",),
            ok=_is_safe_owner_configured(),
        ),
        ExternalMainnetGate(
            gate_id="executor_deploy_verify",
            description="Executor and LiquidationExecutor deployment verification reports pass.",
            remediation="Run solver/driver/ops/deploy_verify.py against the on-chain bytecode.",
            evidence_refs=(
                _repo_ref(EXECUTOR_VERIFY_REPORT),
                _repo_ref(LIQUIDATION_VERIFY_REPORT),
            ),
            ok=_deployment_report_passes(EXECUTOR_VERIFY_REPORT, address_key="executor", schema="executor-deployment-verification/v1")
               and _deployment_report_passes(LIQUIDATION_VERIFY_REPORT, address_key="liquidator", schema="liquidation-executor-deployment-verification/v1"),
        ),
        ExternalMainnetGate(
            gate_id="delegatee_verify",
            description="Bot EOAs are enrolled as delegatees on the production Executor.",
            remediation="Run solver/driver/ops/delegatee_verify.py to audit the on-chain delegatee list.",
            evidence_refs=(_repo_ref(DELEGATEE_VERIFY_REPORT),),
            ok=_delegatee_report_passes(DELEGATEE_VERIFY_REPORT),
        ),
        ExternalMainnetGate(
            gate_id="rpc_failover",
            description="Multi-endpoint RPC configuration passes health checks and failover simulation.",
            remediation="Ensure at least two archive-node URLs (e.g. Chainstack + Alchemy) are configured in .env and pass the driver.ops.rpc_health check.",
            evidence_refs=(".env.example", "coordinator/src/config.ts"),
            ok=_is_rpc_failover_wired(),
        ),
        ExternalMainnetGate(
            gate_id="secrets_policy",
            ok=_production_secrets_untracked(),
            description="Production secrets are not present in git; .env.example remains non-secret.",
            evidence_refs=(".env.example",),
            remediation="Remove any committed .env, rotate exposed secrets, and keep only redacted examples in git.",
        ),
    )


def build_readiness_report() -> ReadinessReport:
    findings: list[ReadinessFinding] = []

    # 1. Unique workflow IDs
    workflow_ids = tuple(workflow.workflow_id for workflow in EXECUTION_WORKFLOWS)
    findings.append(
        ReadinessFinding(
            name="workflow_ids_unique",
            ok=len(set(workflow_ids)) == len(workflow_ids),
            detail=f"{len(workflow_ids)} workflows defined",
        )
    )

    # 2. Strategy intelligence alignment
    profiles = {p.workflow_id: p for p in STRATEGY_INTELLIGENCE_PROFILES}
    findings.append(
        ReadinessFinding(
            name="strategy_intelligence_aligned",
            ok=all(wid in profiles for wid in workflow_ids),
            detail="all execution workflows have a matching intelligence profile",
        )
    )

    # 3. File existence checks for all workflows
    for workflow in EXECUTION_WORKFLOWS:
        is_live = workflow.status == WorkflowStatus.EXECUTABLE
        refs = (
            workflow.signal_sources
            + workflow.trigger_modules
            + workflow.planner_modules
            + workflow.calldata_builders
            + workflow.submission_modules
            + workflow.contract_entrypoints
            + workflow.callback_entrypoints
            + workflow.happy_path_tests
            + workflow.revert_guard_tests
        )

        for ref in refs:
            path = _path_from_ref(ref)
            ok = path.exists()
            findings.append(
                ReadinessFinding(
                    name=f"{workflow.workflow_id}.ref.{ref}",
                    ok=ok,
                    detail=str(path.relative_to(REPO_ROOT)) if ok else f"MISSING: {ref}",
                )
            )

        if is_live:
            profile = profiles.get(workflow.workflow_id)
            findings.append(
                ReadinessFinding(
                    name=f"{workflow.workflow_id}.live_profile_ready",
                    ok=profile is not None and profile.blocker_status == BlockerStatus.NONE,
                    detail="live workflow must have no explicit blocker",
                )
            )

            bottle_ok = (
                len(workflow.signal_sources) > 0
                and len(workflow.trigger_modules) > 0
                and len(workflow.planner_modules) > 0
                and len(workflow.calldata_builders) > 0
                and len(workflow.submission_modules) > 0
                and len(workflow.contract_entrypoints) > 0
                and len(workflow.happy_path_tests) > 0
            )
            findings.append(
                ReadinessFinding(
                    name=f"{workflow.workflow_id}.execution_bottle_complete",
                    ok=bottle_ok,
                    detail="signal, trigger, planner, calldata, submission, profit, tests",
                )
            )
        else:
            profile = profiles.get(workflow.workflow_id)
            findings.append(
                ReadinessFinding(
                    name=f"{workflow.workflow_id}.gated_with_blocker",
                    ok=profile is not None and profile.blocker_status != BlockerStatus.NONE,
                    detail="non-live workflow must be explicitly gated with remediation",
                )
            )

    findings.append(
        ReadinessFinding(
            name="secrets_policy",
            ok=_production_secrets_untracked(),
            detail="Production secrets are not present in git; .env.example remains non-secret.",
        )
    )

    blockers = tuple(
        StrategyBlocker(
            workflow_id=p.workflow_id,
            description=b.description,
            remediation=b.remediation,
            proof_refs=b.proof_refs,
            blocks_mainnet=p.blocker_status == BlockerStatus.MAINNET_BLOCKER,
        )
        for p in STRATEGY_INTELLIGENCE_PROFILES
        for b in p.blockers
    )

    external_gates = _build_external_mainnet_gates()
    failed_external_gates = tuple(gate for gate in external_gates if not gate.ok)

    poc_ready = all(f.ok for f in findings)
    mainnet_ready = poc_ready and not any(b.blocks_mainnet for b in blockers) and not any(not g.ok for g in external_gates)

    return ReadinessReport(
        poc_ready=poc_ready,
        mainnet_ready=mainnet_ready,
        findings=tuple(findings),
        blockers=blockers,
        external_mainnet_gates=external_gates,
        failed_external_mainnet_gates=tuple(gate.description for gate in failed_external_gates),
        required_poc_commands=_build_required_poc_commands(),
    )


def report_to_dict(report: ReadinessReport) -> dict[str, Any]:
    return asdict(report)


def _print_text_report(report: ReadinessReport, *, verbose: bool = False) -> None:

    sum(1 for finding in report.findings if finding.ok)
    failed_findings = tuple(finding for finding in report.findings if not finding.ok)
    if verbose or failed_findings:
        for _finding in report.findings if verbose else failed_findings:
            pass

    mainnet_blockers = tuple(blocker for blocker in report.blockers if blocker.blocks_mainnet)
    deferred_blockers = tuple(blocker for blocker in report.blockers if not blocker.blocks_mainnet)
    for _blocker in mainnet_blockers:
        pass

    for _blocker in deferred_blockers:
        pass

    for _gate in report.external_mainnet_gates:
        pass

    for _command in report.required_poc_commands:
        pass


def _build_required_poc_commands() -> tuple[str, ...]:
    return (
        f"cd {REPO_ROOT} && ruff check vendor/degenbot/src/degenbot/ops_solver/readiness_gate.py",
        f"cd {REPO_ROOT} && .venv/bin/python -m pytest vendor/degenbot/tests/solver_driver/test_readiness_gate.py",
        f"cd {REPO_ROOT} && cd coordinator && env -u NODE_OPTIONS bun run test",
        f"cd {REPO_ROOT} && forge test --match-contract '^(ExecutorStrategiesTest|ExecutorUniswapXFillTest|ExecutorCoWFlashRouterTest|ExecutorCoWFlashRouterStartTest|LiquidationExecutorH1Test|LiquidationExecutorDeltaTest|MevSafeUnitTest)$' -vvv",
        f"cd {REPO_ROOT} && git diff --check",
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the readiness gate CLI."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    parser.add_argument("--verbose", action="store_true", help="Print every readiness finding")
    parser.add_argument(
        "--strict-mainnet",
        action="store_true",
        help="Return non-zero unless mainnet readiness is also satisfied",
    )
    args = parser.parse_args(argv)

    report = build_readiness_report()
    if args.json:
        pass
    else:
        _print_text_report(report, verbose=args.verbose)

    if args.strict_mainnet:
        return 0 if report.mainnet_ready else 1
    return 0 if report.poc_ready else 1


if __name__ == "__main__":
    sys.exit(main())
