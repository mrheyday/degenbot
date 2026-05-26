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
import shlex
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, cast

from degenbot.strategies_solver.execution_workflows import (
    EXECUTION_WORKFLOWS,
    WorkflowStatus,
)
from degenbot.strategies_solver.strategy_intelligence import (
    STRATEGY_INTELLIGENCE_PROFILES,
    BlockerStatus,
    StrategyIntelligenceProfile,
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
    # Fallback for unexpected environments
    return Path(__file__).resolve().parents[4]


REPO_ROOT = _find_repo_root()
ADDRESS_HEX_LENGTH = 42
MAINNET_CHAIN_ID = 42161
ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


def _rooted_command(command: str) -> str:
    return f"cd {shlex.quote(str(REPO_ROOT))} && {command}"


def _build_required_poc_commands() -> tuple[str, ...]:
    return tuple(
        _rooted_command(command)
        for command in (
            "ruff check vendor/degenbot/src/degenbot/ops_solver/readiness_gate.py",
            ".venv/bin/python -m pytest vendor/degenbot/tests/ops_solver/test_readiness_gate.py",
            "cd coordinator && env -u NODE_OPTIONS bun run test",
            "forge test --match-contract '^(ExecutorStrategiesTest|ExecutorUniswapXFillTest|ExecutorCoWFlashRouterTest|ExecutorCoWFlashRouterStartTest|LiquidationExecutorH1Test|LiquidationExecutorDeltaTest|MevSafeUnitTest)$' -vvv",
            "git diff --check",
        )
    )


MAINNET_DEPLOYMENT_DIR = REPO_ROOT / "docs/runbooks/deployments/mainnet"
EXECUTOR_VERIFY_REPORT = MAINNET_DEPLOYMENT_DIR / "executor-verification.json"
LIQUIDATION_VERIFY_REPORT = MAINNET_DEPLOYMENT_DIR / "liquidation-executor-verification.json"
DELEGATEE_VERIFY_REPORT = MAINNET_DEPLOYMENT_DIR / "delegatee-verification.json"
ARBITRUM_CONFIG = REPO_ROOT / "contracts/script/config/arbitrum-one.json"


@dataclass(frozen=True, slots=True)
class ReadinessFinding:
    """One readiness assertion."""

    name: str
    ok: bool
    detail: str


@dataclass(frozen=True, slots=True)
class ReadinessBlocker:
    """A documented blocker with remediation."""

    workflow_id: str
    description: str
    remediation: str
    proof_refs: tuple[str, ...]
    blocks_mainnet: bool


@dataclass(frozen=True, slots=True)
class ExternalMainnetGate:
    """One external/operator gate with machine-checkable evidence."""

    gate_id: str
    ok: bool
    description: str
    evidence_refs: tuple[str, ...]
    remediation: str


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    """Deterministic readiness report emitted by the gate."""

    poc_ready: bool
    mainnet_ready: bool
    findings: tuple[ReadinessFinding, ...]
    blockers: tuple[ReadinessBlocker, ...]
    external_mainnet_gates: tuple[ExternalMainnetGate, ...]
    failed_external_mainnet_gates: tuple[str, ...]
    required_poc_commands: tuple[str, ...]


def _path_from_ref(ref: str) -> Path:
    return REPO_ROOT / ref.split("::", maxsplit=1)[0]


def _workflow_ids() -> tuple[str, ...]:
    return tuple(workflow.workflow_id for workflow in EXECUTION_WORKFLOWS)


def _profile_by_id() -> dict[str, StrategyIntelligenceProfile]:
    return {profile.workflow_id: profile for profile in STRATEGY_INTELLIGENCE_PROFILES}


def _all_refs_for_profile(profile: StrategyIntelligenceProfile) -> tuple[str, ...]:
    refs: list[str] = list(profile.proof_refs)
    for blocker in profile.blockers:
        refs.extend(blocker.owner_refs)
        refs.extend(blocker.proof_refs)
    return tuple(refs)


def _build_findings() -> tuple[ReadinessFinding, ...]:
    findings: list[ReadinessFinding] = []
    workflow_ids = _workflow_ids()
    profile_by_id = _profile_by_id()
    profile_ids = tuple(profile_by_id)

    findings.extend((
        ReadinessFinding(
            name="workflow_ids_unique",
            ok=len(workflow_ids) == len(set(workflow_ids)),
            detail=f"{len(workflow_ids)} workflow ids",
        ),
        ReadinessFinding(
            name="strategy_profiles_cover_workflows",
            ok=set(workflow_ids) == set(profile_ids),
            detail=f"{len(profile_ids)} profiles for {len(workflow_ids)} workflows",
        ),
    ))

    for workflow in EXECUTION_WORKFLOWS:
        profile = profile_by_id.get(workflow.workflow_id)
        if profile is None:
            findings.append(
                ReadinessFinding(
                    name=f"{workflow.workflow_id}.profile_exists",
                    ok=False,
                    detail="missing strategy intelligence profile",
                )
            )
            continue

        if workflow.is_live:
            findings.extend((
                ReadinessFinding(
                    name=f"{workflow.workflow_id}.live_profile_ready",
                    ok=profile.production_ready,
                    detail="live workflow must have no explicit blocker",
                ),
                ReadinessFinding(
                    name=f"{workflow.workflow_id}.execution_bottle_complete",
                    ok=all((
                        workflow.signal_sources,
                        workflow.trigger_modules,
                        workflow.planner_modules,
                        workflow.calldata_builders,
                        workflow.submission_modules,
                        workflow.profit_extraction,
                        workflow.happy_path_tests,
                        workflow.revert_guard_tests,
                    )),
                    detail="signal, trigger, planner, calldata, submission, profit, tests",
                ),
            ))
        else:
            findings.append(
                ReadinessFinding(
                    name=f"{workflow.workflow_id}.gated_with_blocker",
                    ok=(
                        profile.blocker_status is BlockerStatus.EXPLICIT_GATE
                        and bool(profile.blockers)
                        and workflow.status is WorkflowStatus.GATED_EXPLICIT
                    ),
                    detail="non-live workflow must be explicitly gated with remediation",
                )
            )

        refs = (
            *workflow.signal_sources,
            *workflow.trigger_modules,
            *workflow.planner_modules,
            *workflow.calldata_builders,
            *workflow.submission_modules,
            *workflow.contract_entrypoints,
            *workflow.callback_entrypoints,
            *workflow.happy_path_tests,
            *workflow.revert_guard_tests,
            *_all_refs_for_profile(profile),
        )
        findings.extend(
            (
                ReadinessFinding(
                    name=f"{workflow.workflow_id}.ref.{ref}",
                    ok=_path_from_ref(ref).exists(),
                    detail=ref,
                )
            )
            for ref in refs
        )

    return tuple(findings)


def _build_blockers() -> tuple[ReadinessBlocker, ...]:
    blockers: list[ReadinessBlocker] = []
    for profile in STRATEGY_INTELLIGENCE_PROFILES:
        blockers.extend(
            (
                ReadinessBlocker(
                    workflow_id=profile.workflow_id,
                    description=blocker.description,
                    remediation=blocker.remediation,
                    proof_refs=blocker.proof_refs,
                    blocks_mainnet=blocker.blocks_mainnet,
                )
            )
            for blocker in profile.blockers
        )
    return tuple(blockers)


def _repo_ref(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _load_json_object(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None
    return cast("dict[str, object]", raw)


def _is_address(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(ADDRESS_RE.fullmatch(value))
        and value.lower() != ZERO_ADDRESS
    )


def _checks_all_ok(raw: dict[str, object]) -> bool:
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


def _delegatee_checks_cover(checks: list[object], delegatees: list[object]) -> bool:
    """Every check entry is well-formed and the set covers all contract/delegatee pairs."""
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


def _audit_archive_present() -> bool:
    required = (
        REPO_ROOT / "docs/runbooks/audits/2026-05-11-production-readiness-audit.md",
        REPO_ROOT / "docs/runbooks/audits/2026-05-12-production-code-review.md",
    )
    return all(path.exists() for path in required)


def _safe_owner_configured() -> bool:
    if not ARBITRUM_CONFIG.exists():
        return False
    try:
        raw = json.loads(ARBITRUM_CONFIG.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
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
    result = subprocess.run(  # noqa: S603 - fixed git argv, no shell, no user-controlled command.
        (
            git,
            "-C",
            str(REPO_ROOT),
            "ls-files",
            ".env",
            ".env.*",
            "*/.env",
            "*/.env.*",
        ),
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


def _rpc_failover_wired() -> bool:
    env_example = REPO_ROOT / ".env.example"
    config_ts = REPO_ROOT / "coordinator/src/config.ts"
    if not env_example.exists() or not config_ts.exists():
        return False
    env_text = env_example.read_text(encoding="utf-8")
    config_text = config_ts.read_text(encoding="utf-8")
    return all(
        marker in env_text and marker in config_text
        for marker in ("ARB_RPC_HTTP_FALLBACK", "ARB_RPC_WS_FALLBACK")
    )


def _build_external_mainnet_gates() -> tuple[ExternalMainnetGate, ...]:
    return (
        ExternalMainnetGate(
            gate_id="audit_archive",
            ok=_audit_archive_present(),
            description="Security audit archive exists for production-readiness and code-review scope.",
            evidence_refs=(
                "docs/runbooks/audits/2026-05-11-production-readiness-audit.md",
                "docs/runbooks/audits/2026-05-12-production-code-review.md",
            ),
            remediation=(
                "Archive the final paid/external audit report under docs/runbooks/audits/ "
                "and add it to this gate."
            ),
        ),
        ExternalMainnetGate(
            gate_id="safe_owner",
            ok=_safe_owner_configured(),
            description="1-of-3 Safe is configured as owner in the Arbitrum deployment config.",
            evidence_refs=("contracts/script/config/arbitrum-one.json",),
            remediation=(
                "Deploy the Arbitrum Safe, rotate Executor owner config away from the single-EOA POC owner, "
                "and update _owner_notes with the Safe transaction reference."
            ),
        ),
        ExternalMainnetGate(
            gate_id="executor_deploy_verify",
            ok=_deployment_report_passes(
                EXECUTOR_VERIFY_REPORT,
                address_key="executor",
                schema="executor-deployment-verification/v1",
            )
            and _deployment_report_passes(
                LIQUIDATION_VERIFY_REPORT,
                address_key="liquidator",
                schema="liquidation-executor-deployment-verification/v1",
            ),
            description="Executor and LiquidationExecutor deployment verification reports pass.",
            evidence_refs=(
                _repo_ref(EXECUTOR_VERIFY_REPORT),
                _repo_ref(LIQUIDATION_VERIFY_REPORT),
            ),
            remediation=(
                "Run solver/driver/ops/deploy_verify.py and the LiquidationExecutor verifier against Arbitrum "
                "mainnet with OUTPUT_PATH set, then archive schema-valid JSON reports under "
                "docs/runbooks/deployments/mainnet/."
            ),
        ),
        ExternalMainnetGate(
            gate_id="delegatee_verify",
            ok=_delegatee_report_passes(DELEGATEE_VERIFY_REPORT),
            description="Delegatee EOAs are registered on-chain and hot keys are excluded from the repository.",
            evidence_refs=(_repo_ref(DELEGATEE_VERIFY_REPORT), ".env.example"),
            remediation=(
                "Register delegatees from the owner Safe, run solver/driver/ops/delegatee_verify.py with "
                "OUTPUT_PATH set, and archive the schema-valid report."
            ),
        ),
        ExternalMainnetGate(
            gate_id="rpc_failover",
            ok=_rpc_failover_wired(),
            description="Archive RPC primary plus warm failover provider config is wired and documented.",
            evidence_refs=(".env.example", "coordinator/src/config.ts"),
            remediation=(
                "Wire coordinator config to explicit ARB_RPC_HTTP_FALLBACK/ARB_RPC_WS_FALLBACK values."
            ),
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
    """Build the current repository readiness report."""

    findings = _build_findings()
    blockers = _build_blockers()
    mainnet_blockers = tuple(blocker for blocker in blockers if blocker.blocks_mainnet)
    external_gates = _build_external_mainnet_gates()
    failed_external_gates = tuple(gate for gate in external_gates if not gate.ok)
    poc_ready = all(finding.ok for finding in findings)
    mainnet_ready = poc_ready and not mainnet_blockers and not failed_external_gates
    return ReadinessReport(
        poc_ready=poc_ready,
        mainnet_ready=mainnet_ready,
        findings=findings,
        blockers=blockers,
        external_mainnet_gates=external_gates,
        failed_external_mainnet_gates=tuple(gate.description for gate in failed_external_gates),
        required_poc_commands=_build_required_poc_commands(),
    )


def report_to_dict(report: ReadinessReport) -> dict[str, object]:
    """Convert a report to JSON-serialisable data."""

    return asdict(report)


def _print_text_report(report: ReadinessReport, *, verbose: bool = False) -> None:
    sys.stdout.write("Production-ready POC readiness report\n")
    sys.stdout.write(f"POC ready:     {report.poc_ready}\n")
    sys.stdout.write(f"Mainnet ready: {report.mainnet_ready}\n")
    sys.stdout.write(f"Repository:    {REPO_ROOT}\n\n")

    passed = sum(1 for finding in report.findings if finding.ok)
    failed_findings = tuple(finding for finding in report.findings if not finding.ok)
    sys.stdout.write(f"Findings: {passed} pass, {len(failed_findings)} fail\n")

    if verbose or failed_findings:
        for finding in report.findings if verbose else failed_findings:
            status = "PASS" if finding.ok else "FAIL"
            sys.stdout.write(f"- {status} {finding.name}: {finding.detail}\n")
    else:
        sys.stdout.write("- all repository-verifiable assertions passed\n")

    sys.stdout.write("\nMainnet code blockers:\n")
    mainnet_blockers = tuple(blocker for blocker in report.blockers if blocker.blocks_mainnet)
    if not mainnet_blockers:
        sys.stdout.write("- none\n")
    for blocker in mainnet_blockers:
        sys.stdout.write(f"- {blocker.workflow_id}: {blocker.description}\n")
        sys.stdout.write(f"  remediation: {blocker.remediation}\n")

    sys.stdout.write("\nDeferred gated surfaces:\n")
    deferred_blockers = tuple(blocker for blocker in report.blockers if not blocker.blocks_mainnet)
    if not deferred_blockers:
        sys.stdout.write("- none\n")
    for blocker in deferred_blockers:
        sys.stdout.write(f"- {blocker.workflow_id}: {blocker.description}\n")
        sys.stdout.write(f"  remediation: {blocker.remediation}\n")

    sys.stdout.write("\nExternal mainnet gates:\n")
    for gate in report.external_mainnet_gates:
        status = "PASS" if gate.ok else "FAIL"
        sys.stdout.write(f"- {status} {gate.gate_id}: {gate.description}\n")
        sys.stdout.write(f"  evidence: {', '.join(gate.evidence_refs)}\n")
        if not gate.ok:
            sys.stdout.write(f"  remediation: {gate.remediation}\n")

    sys.stdout.write("\nRequired POC commands:\n")
    for command in report.required_poc_commands:
        sys.stdout.write(f"- {command}\n")


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
        sys.stdout.write(f"{json.dumps(report_to_dict(report), indent=2, sort_keys=True)}\n")
    else:
        _print_text_report(report, verbose=args.verbose)

    if args.strict_mainnet:
        return 0 if report.mainnet_ready else 1
    return 0 if report.poc_ready else 1


if __name__ == "__main__":
    sys.exit(main())
