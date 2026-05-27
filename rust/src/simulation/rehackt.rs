//! Non-dispatchable reHackt adversarial simulation fixtures.
//!
//! This module pins source-backed fixture metadata for future REVM replay
//! work. It deliberately contains no live execution path and no broadcast
//! helper.

/// Promotion state for an adversarial fixture.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FixtureStatus {
    /// Source is classified and awaits simulator/replay implementation.
    SimulatorRequired,
    /// Regression replay exists and is ready to gate strategy promotion.
    RegressionReady,
}

/// Structured quote states expected from rounding-sensitive simulators.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum QuoteOutcome {
    /// Quote produced a deterministic output amount.
    Valid,
    /// Pool state or requested swap is outside the valid math domain.
    InvalidDomain,
    /// Iterative math failed to converge deterministically.
    NumericalNonConvergence,
    /// Fee, scaling, or token-decimal assumptions are inconsistent.
    FeeScalingMismatch,
    /// Quote used stale state and must be discarded.
    StaleState,
}

/// Machine-readable, non-dispatchable adversarial fixture.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct AdversarialFixture {
    pub fixture_id: &'static str,
    pub protocol: &'static str,
    pub source_url: &'static str,
    pub source_commit: &'static str,
    pub source_paths: &'static [&'static str],
    pub status: FixtureStatus,
    pub dispatchable: bool,
    pub chain: &'static str,
    pub fork_block: u64,
    pub pool_addresses: &'static [&'static str],
    pub token_addresses: &'static [&'static str],
    pub required_checks: &'static [&'static str],
    pub forbidden_ports: &'static [&'static str],
    pub simulator_quote_outcomes: &'static [QuoteOutcome],
}

pub const REHACKT_SOURCE_URL: &str = "https://github.com/nonseodion/reHackt.git";
pub const REHACKT_SOURCE_COMMIT: &str = "4fad9644387c0fbd5cd5f7384935dea27362347a";

pub const BALANCER_V2_STABLE_ROUNDING: AdversarialFixture = AdversarialFixture {
    fixture_id: "rehackt-balancer-v2-stable-rounding",
    protocol: "Balancer V2 Composable Stable Pool",
    source_url: REHACKT_SOURCE_URL,
    source_commit: REHACKT_SOURCE_COMMIT,
    source_paths: &[
        "src/Balancer/Hacker.sol",
        "src/Balancer/SwapQuoter.sol",
        "src/Balancer/helpers.sol",
        "src/Balancer/libraries/StableMath.sol",
        "src/Balancer/libraries/FixedPoint.sol",
        "src/Balancer/libraries/ExternalFees.sol",
    ],
    status: FixtureStatus::RegressionReady,
    dispatchable: false,
    chain: "ethereum-mainnet",
    fork_block: 23_717_396,
    pool_addresses: &[
        "0xDACf5Fa19b1f720111609043ac67A9818262850c",
        "0xBA12222222228d8Ba445958a75a0704d566BF2C8",
    ],
    token_addresses: &[
        "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "0xf1C9acDc66974dFB6dEcB12aA385b9cD01190E38",
    ],
    required_checks: &[
        "scaling helpers must match Balancer helpers.sol mutation and rounding semantics",
        "stable-math non-convergence must be surfaced as a structured simulator state",
        "REVM replay must be non-broadcast and must not consume private keys",
        "strategy output must remain disabled until replay matches the pinned vector",
    ],
    forbidden_ports: &[
        "constructor-executed exploit contracts",
        "hardcoded live-mainnet exploit scripts",
        "Solidity 0.7 libraries in contracts/src",
        "live strategy dispatch based on historical exploit reproduction",
    ],
    simulator_quote_outcomes: &[
        QuoteOutcome::Valid,
        QuoteOutcome::InvalidDomain,
        QuoteOutcome::NumericalNonConvergence,
        QuoteOutcome::FeeScalingMismatch,
        QuoteOutcome::StaleState,
    ],
};

pub const COVER_REWARD_ACCOUNTING: AdversarialFixture = AdversarialFixture {
    fixture_id: "rehackt-cover-reward-accounting",
    protocol: "Cover Protocol reward accounting",
    source_url: REHACKT_SOURCE_URL,
    source_commit: REHACKT_SOURCE_COMMIT,
    source_paths: &[
        "test/Cover-Protocol/Hacker.sol",
        "test/Cover-Protocol/Hacker-info.sol",
    ],
    status: FixtureStatus::RegressionReady,
    dispatchable: false,
    chain: "ethereum-mainnet",
    fork_block: 11_542_183,
    pool_addresses: &[],
    token_addresses: &[],
    required_checks: &[
        "reward-index fixtures must prove stake, unstake, claim ordering",
        "off-chain scoring must reject same-balance different-reward-state drift",
        "fixture must stay outside live execution and settlement routing",
    ],
    forbidden_ports: &[
        "historical exploit flow",
        "old Uniswap mainnet setup",
        "reward-claim strategy dispatch without protocol-specific audit",
    ],
    simulator_quote_outcomes: &[],
};

pub const REHACKT_FIXTURES: &[AdversarialFixture] =
    &[BALANCER_V2_STABLE_ROUNDING, COVER_REWARD_ACCOUNTING];

#[must_use]
pub fn fixture_by_id(fixture_id: &str) -> Option<&'static AdversarialFixture> {
    REHACKT_FIXTURES
        .iter()
        .find(|fixture| fixture.fixture_id == fixture_id)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fixture_order_matches_python_catalog() {
        assert_eq!(
            REHACKT_FIXTURES
                .iter()
                .map(|fixture| fixture.fixture_id)
                .collect::<Vec<_>>(),
            vec![
                "rehackt-balancer-v2-stable-rounding",
                "rehackt-cover-reward-accounting",
            ]
        );
    }

    #[test]
    fn balancer_fixture_is_non_dispatchable_and_source_bound() {
        let Some(fixture) = fixture_by_id("rehackt-balancer-v2-stable-rounding") else {
            panic!("fixture exists");
        };

        assert_eq!(fixture.source_url, REHACKT_SOURCE_URL);
        assert_eq!(fixture.source_commit, REHACKT_SOURCE_COMMIT);
        assert_eq!(fixture.status, FixtureStatus::SimulatorRequired);
        assert!(!fixture.dispatchable);
        assert_eq!(fixture.fork_block, 23_717_396);
        assert!(fixture
            .source_paths
            .contains(&"src/Balancer/SwapQuoter.sol"));
    }

    #[test]
    fn quote_outcomes_include_non_convergence() {
        let Some(fixture) = fixture_by_id("rehackt-balancer-v2-stable-rounding") else {
            panic!("fixture exists");
        };

        assert!(fixture
            .simulator_quote_outcomes
            .contains(&QuoteOutcome::NumericalNonConvergence));
        assert!(fixture
            .simulator_quote_outcomes
            .contains(&QuoteOutcome::FeeScalingMismatch));
    }

    #[test]
    fn forbidden_ports_block_live_exploit_logic() {
        let Some(fixture) = fixture_by_id("rehackt-balancer-v2-stable-rounding") else {
            panic!("fixture exists");
        };

        assert!(fixture
            .forbidden_ports
            .contains(&"constructor-executed exploit contracts"));
        assert!(fixture
            .forbidden_ports
            .contains(&"live strategy dispatch based on historical exploit reproduction"));
    }
}
