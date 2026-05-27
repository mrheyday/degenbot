"""Non-dispatchable adversarial fixtures derived from nonseodion/reHackt.

These records preserve source-backed simulator work items without placing
historical exploit logic on any live execution path.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FixtureStatus(StrEnum):
    """Promotion state for an adversarial source fixture."""

    SIMULATOR_REQUIRED = "simulator_required"
    REGRESSION_READY = "regression_ready"


class QuoteOutcome(StrEnum):
    """Structured simulator quote states required by the reHackt review."""

    VALID = "valid"
    INVALID_DOMAIN = "invalid_domain"
    NUMERICAL_NON_CONVERGENCE = "numerical_non_convergence"
    FEE_SCALING_MISMATCH = "fee_scaling_mismatch"
    STALE_STATE = "stale_state"


@dataclass(frozen=True, slots=True)
class AdversarialFixture:
    """Machine-readable non-dispatchable adversarial fixture."""

    fixture_id: str
    protocol: str
    source_url: str
    source_commit: str
    source_paths: tuple[str, ...]
    status: FixtureStatus
    dispatchable: bool
    chain: str
    fork_block: int
    pool_addresses: tuple[str, ...]
    token_addresses: tuple[str, ...]
    implementation_targets: tuple[str, ...]
    simulator_quote_outcomes: tuple[QuoteOutcome, ...]
    required_checks: tuple[str, ...]
    forbidden_ports: tuple[str, ...]
    proof_refs: tuple[str, ...]


REHACKT_SOURCE_URL = "https://github.com/nonseodion/reHackt.git"
REHACKT_SOURCE_COMMIT = "4fad9644387c0fbd5cd5f7384935dea27362347a"


REHACKT_FIXTURES: tuple[AdversarialFixture, ...] = (
    AdversarialFixture(
        fixture_id="rehackt-balancer-v2-stable-rounding",
        protocol="Balancer V2 Composable Stable Pool",
        source_url=REHACKT_SOURCE_URL,
        source_commit=REHACKT_SOURCE_COMMIT,
        source_paths=(
            "src/Balancer/Hacker.sol",
            "src/Balancer/SwapQuoter.sol",
            "src/Balancer/helpers.sol",
            "src/Balancer/libraries/StableMath.sol",
            "src/Balancer/libraries/FixedPoint.sol",
            "src/Balancer/libraries/ExternalFees.sol",
        ),
        status=FixtureStatus.REGRESSION_READY,
        dispatchable=False,
        chain="ethereum-mainnet",
        fork_block=23_717_396,
        pool_addresses=(
            "0xDACf5Fa19b1f720111609043ac67A9818262850c",
            "0xBA12222222228d8Ba445958a75a0704d566BF2C8",
        ),
        token_addresses=(
            "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "0xf1C9acDc66974dFB6dEcB12aA385b9cD01190E38",
        ),
        implementation_targets=(
            "vendor/degenbot/src/degenbot/balancer/libraries/scaling_helpers.py",
            "vendor/degenbot/src/degenbot/balancer/libraries/stable_math.py",
            "vendor/degenbot/src/degenbot/balancer/stable_pools.py",
            "vendor/degenbot/src/degenbot/balancer/composable_stable_pools.py",
            "vendor/degenbot/tests/balancer/libraries/test_scaling_helpers.py",
            "vendor/degenbot/tests/balancer/libraries/test_stable_math.py",
            "vendor/degenbot/tests/balancer/test_rehackt_balancer_exploit.py",
            "vendor/degenbot/rust/src/simulation/",
        ),
        simulator_quote_outcomes=(
            QuoteOutcome.VALID,
            QuoteOutcome.INVALID_DOMAIN,
            QuoteOutcome.NUMERICAL_NON_CONVERGENCE,
            QuoteOutcome.FEE_SCALING_MISMATCH,
            QuoteOutcome.STALE_STATE,
        ),
        required_checks=(
            "scale-up and scale-down rounding vectors must be pinned before Balancer routes dispatch",
            "stable-math non-convergence must be surfaced as a structured simulator state",
            "revm replay fixtures must be non-broadcast and must not consume private keys",
            "strategy output must remain disabled until fork/revm replay matches the pinned vector",
        ),
        forbidden_ports=(
            "constructor-executed exploit contracts",
            "hardcoded live-mainnet exploit scripts",
            "Solidity 0.7 libraries in contracts/src",
            "live strategy dispatch based on historical exploit reproduction",
        ),
        proof_refs=(
            "docs/research/nonseodion-repo-port-evaluation-2026-05-27.md",
            "docs/research/balancer/rehackt-balancer-rounding-fixture-2026-05-27.md",
            "vendor/degenbot/tests/balancer/libraries/test_scaling_helpers.py",
            "vendor/degenbot/tests/balancer/libraries/test_stable_math.py",
            "vendor/degenbot/tests/balancer/test_rehackt_balancer_exploit.py",
            "vendor/degenbot/tests/strategy_signals/test_rehackt_adversarial_fixtures.py",
        ),
    ),
    AdversarialFixture(
        fixture_id="rehackt-cover-reward-accounting",
        protocol="Cover Protocol reward accounting",
        source_url=REHACKT_SOURCE_URL,
        source_commit=REHACKT_SOURCE_COMMIT,
        source_paths=(
            "test/Cover-Protocol/Hacker.sol",
            "test/Cover-Protocol/Hacker-info.sol",
        ),
        status=FixtureStatus.REGRESSION_READY,
        dispatchable=False,
        chain="ethereum-mainnet",
        fork_block=11_542_183,
        pool_addresses=(),
        token_addresses=(),
        implementation_targets=(
            "vendor/degenbot/src/degenbot/cover/blacksmith_simulator.py",
            "vendor/degenbot/tests/cover/test_rehackt_cover_exploit.py",
            "vendor/degenbot/tests/strategy_signals/",
            "vendor/degenbot/tests/solver_driver/",
        ),
        simulator_quote_outcomes=(),
        required_checks=(
            "reward-index fixtures must prove stake, unstake, claim ordering",
            "off-chain scoring must reject same-balance different-reward-state drift",
            "fixture must stay outside live execution and settlement routing",
        ),
        forbidden_ports=(
            "historical exploit flow",
            "old Uniswap mainnet setup",
            "reward-claim strategy dispatch without protocol-specific audit",
        ),
        proof_refs=(
            "docs/research/nonseodion-repo-port-evaluation-2026-05-27.md",
            "vendor/degenbot/src/degenbot/cover/blacksmith_simulator.py",
            "vendor/degenbot/tests/cover/test_rehackt_cover_exploit.py",
            "vendor/degenbot/tests/strategy_signals/test_rehackt_adversarial_fixtures.py",
        ),
    ),
)

_FIXTURES_BY_ID = {fixture.fixture_id: fixture for fixture in REHACKT_FIXTURES}


def rehackt_fixtures() -> tuple[AdversarialFixture, ...]:
    """Return all reHackt-derived fixtures in review priority order."""

    return REHACKT_FIXTURES


def rehackt_fixture(fixture_id: str) -> AdversarialFixture:
    """Return one reHackt-derived fixture by id."""

    return _FIXTURES_BY_ID[fixture_id]
