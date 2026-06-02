from __future__ import annotations

from degenbot.strategy_signals.eigenphi_transaction_taxonomy import (
    EIGENPHI_TRANSACTION_PATTERNS,
    EigenPhiPatternFamily,
    PatternOperationalMode,
    high_risk_patterns,
    pattern_for_slug,
    patterns_for_family,
)

EXPECTED_PATTERN_SLUGS = frozenset(
    {
        "backrun-arbitrage",
        "sandwich-attack",
        "flashloan-sandwich",
        "liquidity-provider-sandwich",
        "jit-liquidity",
        "liquidation-internal-accounting",
        "cross-chain-arbitrage",
        "liquidity-rebalancing",
        "aave-flashloan-rebalancing",
        "synthetic-mint-burn-arbitrage",
        "oracle-defect-exploit",
        "mev-bot-bait",
        "jared-2-0-layered-sandwich",
        "myth-buster-no-trade-is-too-small",
        "self-improving-agent-ops-framework",
        "self-improving-agent-corrections-loop",
    }
)


def test_eigenphi_taxonomy_covers_core_transaction_structures() -> None:
    assert {pattern.slug for pattern in EIGENPHI_TRANSACTION_PATTERNS} == EXPECTED_PATTERN_SLUGS

    for pattern in EIGENPHI_TRANSACTION_PATTERNS:
        assert pattern.title
        assert pattern.source_url.startswith(
            (
                "https://eigenphi-1.gitbook.io/head-first-defi/",
                "https://medium.com/",
                "https://eigenphi.substack.com/p/",
                "https://theagenticreview.substack.com/p/",
                "https://experiments.jock.pl/thoughts/",
                "https://thoughts.jock.pl/",
            )
        )
        assert pattern.structural_signals
        assert pattern.required_validations
        assert pattern.safety_invariants
        assert pattern.engine_use


def test_eigenphi_taxonomy_keeps_attack_patterns_non_executable() -> None:
    high_risk_slugs = {pattern.slug for pattern in high_risk_patterns()}

    assert high_risk_slugs == EXPECTED_PATTERN_SLUGS
    assert all(
        pattern.operational_mode is not PatternOperationalMode.EXECUTABLE
        for pattern in high_risk_patterns()
    )
    assert all(
        any("fail closed" in invariant.lower() for invariant in pattern.safety_invariants)
        for pattern in high_risk_patterns()
    )


def test_eigenphi_pattern_lookup_and_family_filters_are_total() -> None:
    assert pattern_for_slug("jit-liquidity").family is EigenPhiPatternFamily.LIQUIDITY
    assert pattern_for_slug("oracle-defect-exploit").family is EigenPhiPatternFamily.ORACLE
    assert pattern_for_slug("mev-bot-bait").operational_mode is PatternOperationalMode.OFFENSIVE
    assert (
        pattern_for_slug("self-improving-agent-ops-framework").family
        is EigenPhiPatternFamily.ADVERSARIAL
    )

    sandwich_slugs = {
        pattern.slug for pattern in patterns_for_family(EigenPhiPatternFamily.SANDWICH)
    }
    assert sandwich_slugs == {
        "sandwich-attack",
        "flashloan-sandwich",
        "jared-2-0-layered-sandwich",
        "liquidity-provider-sandwich",
        "myth-buster-no-trade-is-too-small",
    }


def test_eigenphi_offensive_patterns_are_intentional() -> None:
    offensive_slugs = {
        pattern.slug
        for pattern in EIGENPHI_TRANSACTION_PATTERNS
        if pattern.operational_mode is PatternOperationalMode.OFFENSIVE
    }
    assert offensive_slugs == EXPECTED_PATTERN_SLUGS
