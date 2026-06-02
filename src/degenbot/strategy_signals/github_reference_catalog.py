"""Ranked GitHub reference repos for degenbot integration work.

These records preserve the useful surfaces found in the operator's GitHub
account. They are planning inputs, not vendored dependencies or executable
strategy code.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class GithubReferenceRisk(StrEnum):
    """Reuse posture for one external reference repo."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class GithubReferenceRepo:
    """One ranked repo and the precise surfaces worth inspecting."""

    repo_id: str
    rank: int
    full_name: str
    url: str
    primary_use: str
    risk: GithubReferenceRisk
    import_surfaces: tuple[str, ...]
    inspected_refs: tuple[str, ...]
    guardrails: tuple[str, ...]
    next_steps: tuple[str, ...]


TOP_GITHUB_REFERENCE_REPOS: tuple[GithubReferenceRepo, ...] = (
    GithubReferenceRepo(
        repo_id="cowprotocol-solvers-dto-alloy",
        rank=1,
        full_name="mrheyday/cowprotocol-solvers-dto-alloy",
        url="https://github.com/mrheyday/cowprotocol-solvers-dto-alloy",
        primary_use="Alloy-native CoW auction, order, notification, and solution DTO parity.",
        risk=GithubReferenceRisk.LOW,
        import_surfaces=("cow", "alloy_dto", "solution_wire"),
        inspected_refs=(
            "src/auction.rs",
            "src/order_uid.rs",
            "src/solution.rs",
            "src/notification.rs",
            "resources/response_auction.json",
        ),
        guardrails=(
            "keep Python wire models integer-only for amount fields",
            "preserve camelCase/alias parity with CoW Solver Engine payloads",
            "do not replace existing fail-closed no-bond quote posture",
        ),
        next_steps=(
            "add CoW DTO parity fixtures from resources/response_auction.json",
            "tighten Python Solution interaction shapes where current models are extra-allow",
        ),
    ),
    GithubReferenceRepo(
        repo_id="swap-path",
        rank=2,
        full_name="mrheyday/swap-path",
        url="https://github.com/mrheyday/swap-path",
        primary_use="Typed route identity, path hashing, and duplicate path suppression.",
        risk=GithubReferenceRisk.LOW,
        import_surfaces=("pathfinding", "route_hash", "graph"),
        inspected_refs=(
            "src/swap_path.rs",
            "src/swap_path_hash.rs",
            "src/swap_path_set.rs",
            "src/graph/token_graph.rs",
            "examples/build_swap_path.rs",
        ),
        guardrails=(
            "adapt only deterministic hashing/container semantics",
            "keep degenbot database-backed graph as the source of truth",
            "avoid importing pool abstractions that conflict with existing calculators",
        ),
        next_steps=(
            "add a stable path-hash helper for PathStep sequences",
            "deduplicate pathfinding outputs before strategy scoring",
        ),
    ),
    GithubReferenceRepo(
        repo_id="phantom-filler",
        rank=3,
        full_name="mrheyday/phantom-filler",
        url="https://github.com/mrheyday/phantom-filler",
        primary_use="Rust intent-filler architecture for discovery, strategy, execution, pricing, settlement.",
        risk=GithubReferenceRisk.MEDIUM,
        import_surfaces=("intent_filler", "execution_pipeline", "private_relay"),
        inspected_refs=(
            "crates/phantom-discovery/src/orderbook.rs",
            "crates/phantom-strategy/src/pipeline.rs",
            "crates/phantom-execution/src/relay.rs",
            "crates/phantom-execution/src/nonce.rs",
            "crates/phantom-settlement/src/retry.rs",
        ),
        guardrails=(
            "use architecture as reference only, not a wholesale engine replacement",
            "bind every fill decision to degenbot preflight and profit floors",
            "private relay support must preserve existing lane/deadline semantics",
        ),
        next_steps=(
            "port the bounded strategy-pipeline scoring concept into degenbot planning metadata",
            "compare relay request types against rust/src/executor/lane.rs and inclusion watcher",
        ),
    ),
    GithubReferenceRepo(
        repo_id="compass",
        rank=4,
        full_name="mrheyday/compass",
        url="https://github.com/mrheyday/compass",
        primary_use="Adjacent live MEV engine patterns for retries, Flashblocks, strategy modules, and monitors.",
        risk=GithubReferenceRisk.MEDIUM,
        import_surfaces=("rpc_retry", "flashblocks", "strategy_catalog", "monitoring"),
        inspected_refs=(
            "engine/src/rpc_retry.rs",
            "engine/src/rpc_rate_limit.rs",
            "engine/src/monitor/flashblocks.rs",
            "engine/src/strategy/uniswapx_filler.rs",
            "src/UniswapXFiller.sol",
        ),
        guardrails=(
            "secret-scan before copying from private checkout",
            "treat live-trading reports as historical, not proof of current readiness",
            "port tested primitives only after reconciling with degenbot's Alchemy provider",
        ),
        next_steps=(
            "adapt retry/backoff parsing for provider log reads",
            "compare Flashblocks monitor behavior with current provider interfaces",
        ),
    ),
    GithubReferenceRepo(
        repo_id="mev-kernel-final",
        rank=5,
        full_name="mrheyday/MEV-KERNEL-FINAL",
        url="https://github.com/mrheyday/MEV-KERNEL-FINAL",
        primary_use="Strict policy, intents, guards, flashloan adapters, and settlement architecture reference.",
        risk=GithubReferenceRisk.HIGH,
        import_surfaces=("execution_policy", "guards", "intents", "flashloan", "settlement"),
        inspected_refs=(
            "offchain/src/bots/execution_policy.py",
            "offchain/src/intents/models.py",
            "offchain/src/execution/strict_executor.py",
            "onchain/src/IntentSettlement.sol",
            "onchain/src/SolverRegistry.sol",
            "onchain/src/flash/BaseFlashLoanAggregator.sol",
        ),
        guardrails=(
            "use as doctrine/reference, not as deployable code without audit",
            "do not import broad onchain modules into degenbot",
            "translate policy checks into fail-closed offchain gates first",
        ),
        next_steps=(
            "map strict execution constraints into readiness-gate findings",
            "compare flashloan adapter inventory against degenbot execution_adapters",
        ),
    ),
)

_REFERENCES_BY_ID = {repo.repo_id: repo for repo in TOP_GITHUB_REFERENCE_REPOS}


def ranked_github_reference_repos() -> tuple[GithubReferenceRepo, ...]:
    """Return useful GitHub references in import priority order."""

    return tuple(sorted(TOP_GITHUB_REFERENCE_REPOS, key=lambda repo: repo.rank))


def github_reference_repo(repo_id: str) -> GithubReferenceRepo:
    """Return a GitHub reference repo by stable id."""

    try:
        return _REFERENCES_BY_ID[repo_id]
    except KeyError as exc:
        msg = f"unknown GitHub reference repo: {repo_id}"
        raise KeyError(msg) from exc


def references_for_import_surface(surface: str) -> tuple[GithubReferenceRepo, ...]:
    """Return references that mention an import surface."""

    return tuple(
        repo for repo in ranked_github_reference_repos() if surface in repo.import_surfaces
    )
