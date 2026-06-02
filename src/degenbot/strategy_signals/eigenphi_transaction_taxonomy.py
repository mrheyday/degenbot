"""EigenPhi-inspired DeFi transaction-structure taxonomy.

This module converts the Head First DeFi case-study index into conservative,
machine-readable strategy intelligence. It is descriptive only: historical
transaction patterns are not permission to emit live transactions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class EigenPhiPatternFamily(StrEnum):
    """High-level family for a DeFi transaction structure."""

    ARBITRAGE = "arbitrage"
    SANDWICH = "sandwich"
    LIQUIDITY = "liquidity"
    LIQUIDATION = "liquidation"
    CROSS_CHAIN = "cross_chain"
    ORACLE = "oracle"
    ADVERSARIAL = "adversarial"


class PatternOperationalMode(StrEnum):
    """How degenbot may use a transaction pattern."""

    ANALYSIS_ONLY = "analysis_only"
    DEFENSIVE = "defensive"
    WORKFLOW_REQUIRED = "workflow_required"
    OFFENSIVE = "offensive"
    EXECUTABLE = "executable"


@dataclass(frozen=True, slots=True)
class EigenPhiTransactionPattern:
    """One transaction-structure pattern from the EigenPhi case-study set."""

    slug: str
    title: str
    family: EigenPhiPatternFamily
    operational_mode: PatternOperationalMode
    source_url: str
    structural_signals: tuple[str, ...]
    required_validations: tuple[str, ...]
    safety_invariants: tuple[str, ...]
    engine_use: str


_BASE_URL = "https://eigenphi-1.gitbook.io/head-first-defi"
_MEDIUM_EIGENPHI_BASE = "https://medium.com/@eigenphi"
_SUBSTACK_EIGENPHI_BASE = "https://eigenphi.substack.com/p"
_SUBSTACK_AGENTICREVIEW_BASE = "https://theagenticreview.substack.com/p"
_THOUGHTS_JOCKPL_BASE = "https://thoughts.jock.pl"


def _pattern(
    slug: str,
    title: str,
    family: EigenPhiPatternFamily,
    operational_mode: PatternOperationalMode,
    source_path: str,
    structural_signals: tuple[str, ...],
    required_validations: tuple[str, ...],
    safety_invariants: tuple[str, ...],
    engine_use: str,
) -> EigenPhiTransactionPattern:
    return EigenPhiTransactionPattern(
        slug=slug,
        title=title,
        family=family,
        operational_mode=operational_mode,
        source_url=f"{_BASE_URL}/{source_path}",
        structural_signals=structural_signals,
        required_validations=required_validations,
        safety_invariants=safety_invariants,
        engine_use=engine_use,
    )


def _medium_pattern(
    slug: str,
    title: str,
    family: EigenPhiPatternFamily,
    operational_mode: PatternOperationalMode,
    medium_path: str,
    structural_signals: tuple[str, ...],
    required_validations: tuple[str, ...],
    safety_invariants: tuple[str, ...],
    engine_use: str,
) -> EigenPhiTransactionPattern:
    return EigenPhiTransactionPattern(
        slug=slug,
        title=title,
        family=family,
        operational_mode=operational_mode,
        source_url=f"{_MEDIUM_EIGENPHI_BASE}/{medium_path}",
        structural_signals=structural_signals,
        required_validations=required_validations,
        safety_invariants=safety_invariants,
        engine_use=engine_use,
    )


def _substack_pattern(
    slug: str,
    title: str,
    family: EigenPhiPatternFamily,
    operational_mode: PatternOperationalMode,
    substack_slug: str,
    structural_signals: tuple[str, ...],
    required_validations: tuple[str, ...],
    safety_invariants: tuple[str, ...],
    engine_use: str,
) -> EigenPhiTransactionPattern:
    return EigenPhiTransactionPattern(
        slug=slug,
        title=title,
        family=family,
        operational_mode=operational_mode,
        source_url=f"{_SUBSTACK_EIGENPHI_BASE}/{substack_slug}",
        structural_signals=structural_signals,
        required_validations=required_validations,
        safety_invariants=safety_invariants,
        engine_use=engine_use,
    )


def _theagenticreview_substack_pattern(
    slug: str,
    title: str,
    family: EigenPhiPatternFamily,
    operational_mode: PatternOperationalMode,
    substack_slug: str,
    structural_signals: tuple[str, ...],
    required_validations: tuple[str, ...],
    safety_invariants: tuple[str, ...],
    engine_use: str,
) -> EigenPhiTransactionPattern:
    return EigenPhiTransactionPattern(
        slug=slug,
        title=title,
        family=family,
        operational_mode=operational_mode,
        source_url=f"{_SUBSTACK_AGENTICREVIEW_BASE}/{substack_slug}",
        structural_signals=structural_signals,
        required_validations=required_validations,
        safety_invariants=safety_invariants,
        engine_use=engine_use,
    )


def _thoughts_jockpl_pattern(
    slug: str,
    title: str,
    family: EigenPhiPatternFamily,
    operational_mode: PatternOperationalMode,
    thought_slug: str,
    structural_signals: tuple[str, ...],
    required_validations: tuple[str, ...],
    safety_invariants: tuple[str, ...],
    engine_use: str,
) -> EigenPhiTransactionPattern:
    return EigenPhiTransactionPattern(
        slug=slug,
        title=title,
        family=family,
        operational_mode=operational_mode,
        source_url=f"{_THOUGHTS_JOCKPL_BASE}/{thought_slug}",
        structural_signals=structural_signals,
        required_validations=required_validations,
        safety_invariants=safety_invariants,
        engine_use=engine_use,
    )


EIGENPHI_TRANSACTION_PATTERNS: tuple[EigenPhiTransactionPattern, ...] = (
    _pattern(
        "backrun-arbitrage",
        "Back-run arbitrage",
        EigenPhiPatternFamily.ARBITRAGE,
        PatternOperationalMode.OFFENSIVE,
        "mev-transaction-and-strategy-101/understand-back-run-arbitrages-and-their-signals-and-join-the-mev-game.",
        (
            "victim swap or state-moving transaction",
            "post-transaction pool imbalance",
            "same-block reversal opportunity",
            "profit token and gas cost delta",
        ),
        (
            "fork-simulate after victim state transition",
            "prove positive integer-denominated profit after gas and fees",
            "verify private bundle ordering before submission",
        ),
        (
            "fail closed when victim transaction is missing or reordered",
            "never assume mempool visibility is executable state",
            "amountOutMin and profit floors are mandatory",
        ),
        "Candidate generator for post-state arbitrage workflows.",
    ),
    _pattern(
        "sandwich-attack",
        "Sandwich attack",
        EigenPhiPatternFamily.SANDWICH,
        PatternOperationalMode.OFFENSIVE,
        "dont-let-your-trading-become-the-recipe-of-someones-sandwich",
        (
            "victim swap with measurable slippage",
            "attacker front-run before victim",
            "attacker back-run after victim",
            "same asset path around the victim",
        ),
        (
            "detect vulnerable outbound user flow before routing",
            "measure user price impact and slippage exposure",
            "prefer private routing or intent settlement for protected flow",
        ),
        (
            "fail closed for user-facing flow with excessive slippage",
            "do not emit victimizing front-run/back-run transactions",
            "route protection takes priority over extractive execution",
        ),
        "MEV-protection classifier for vulnerable user order flow.",
    ),
    _pattern(
        "flashloan-sandwich",
        "Flash-loan-enabled sandwich",
        EigenPhiPatternFamily.SANDWICH,
        PatternOperationalMode.OFFENSIVE,
        "dont-let-your-trading-become-the-recipe-of-someones-sandwich/combined-with-flash-loan-this-leveraged-sandwich-launched-the-attack-with-millions-of-volumes",
        (
            "flash loan borrow",
            "leveraged front-run",
            "victim execution",
            "back-run repayment sequence",
        ),
        (
            "identify flash-liquidity-funded price movement",
            "bound user loss under private and public routing",
            "verify protection lane does not leak intent contents",
        ),
        (
            "fail closed on high slippage public flow",
            "never treat flash-loan capacity as permission to attack users",
            "protected settlement overrides public mempool routing",
        ),
        "Risk signal for leveraged sandwich exposure and private-route enforcement.",
    ),
    _pattern(
        "liquidity-provider-sandwich",
        "Liquidity-provider sandwich exposure",
        EigenPhiPatternFamily.SANDWICH,
        PatternOperationalMode.OFFENSIVE,
        "dont-let-your-trading-become-the-recipe-of-someones-sandwich/sandwich-targeting-liquidity-providers",
        (
            "liquidity add or remove",
            "adverse price movement around the LP action",
            "fee accrual versus inventory loss",
        ),
        (
            "simulate LP action with adjacent swap ordering",
            "measure reserve and fee deltas",
            "require private execution for sensitive LP changes",
        ),
        (
            "fail closed when LP inventory loss exceeds configured bound",
            "protect treasury LP actions from public pre-positioning",
            "do not expose deterministic rebalance timing publicly",
        ),
        "Defensive classifier for LP-management and treasury-rebalance flow.",
    ),
    _pattern(
        "jit-liquidity",
        "Just-in-time liquidity",
        EigenPhiPatternFamily.LIQUIDITY,
        PatternOperationalMode.OFFENSIVE,
        "unlocking-the-power-of-advanced-defi-transactions-and-becoming-a-defi-sleuth/just-in-time-an-mev-type-that-benefits-traders-in-the-same-trading-venue",
        (
            "liquidity mint before swap",
            "target swap execution",
            "liquidity burn after swap",
            "fee capture and inventory unwind",
        ),
        (
            "simulate exact tick range and fee capture",
            "verify inventory exposure after burn",
            "prove swap price improvement or neutral user outcome",
        ),
        (
            "fail closed when user price worsens",
            "JIT workflow needs simulator tests before live tx output",
            "inventory and fee accounting must be deterministic",
        ),
        "Workflow-required liquidity lane for fee-capture analysis.",
    ),
    _pattern(
        "liquidation-internal-accounting",
        "Liquidation internal accounting",
        EigenPhiPatternFamily.LIQUIDATION,
        PatternOperationalMode.OFFENSIVE,
        "under-the-hood-of-the-defi-lego/liquidation-a-good-entry-point-to-comprehend-internal-accounting-used-by-many-defi-protocols.",
        (
            "borrower collateral and debt state",
            "oracle price and health factor",
            "liquidation bonus and close factor",
            "repay asset and seize asset path",
        ),
        (
            "read protocol-specific accounting at the same block",
            "verify post-liquidation health factor and seized collateral",
            "include flash-loan fee and swap unwind costs",
        ),
        (
            "fail closed on stale oracle or stale reserve data",
            "never liquidate without protocol-specific close-factor checks",
            "profit must be denominated in raw integer token units",
        ),
        "Liquidation candidate gating checklist.",
    ),
    _pattern(
        "cross-chain-arbitrage",
        "Cross-chain arbitrage",
        EigenPhiPatternFamily.CROSS_CHAIN,
        PatternOperationalMode.OFFENSIVE,
        "under-the-hood-of-the-defi-lego/a-cross-chain-arbitrage-the-art-of-arbitraging-banana-cross-bsc-and-polygon-chains",
        (
            "same asset market on multiple chains",
            "bridge or transfer leg",
            "settlement latency",
            "per-chain liquidity and gas cost",
        ),
        (
            "model bridge finality and failure path",
            "discount profit by latency and inventory risk",
            "verify independent per-chain execution states",
        ),
        (
            "fail closed when bridge state or finality is uncertain",
            "do not assume atomicity across independent chains",
            "inventory exposure must be explicitly bounded",
        ),
        "Research-only signal for non-atomic cross-chain spreads.",
    ),
    _pattern(
        "liquidity-rebalancing",
        "Liquidity rebalancing",
        EigenPhiPatternFamily.LIQUIDITY,
        PatternOperationalMode.OFFENSIVE,
        "under-the-hood-of-the-defi-lego/liquidity-rebalancing-moving-around-usd9.4-million-for-more-fee-revenues.",
        (
            "LP position range",
            "fee APR versus inventory drift",
            "rebalance transaction cost",
            "target pool depth",
        ),
        (
            "simulate remove-add sequence",
            "measure fee gain against slippage and gas",
            "verify treasury authorization before any movement",
        ),
        (
            "fail closed for treasury movement without Safe approval",
            "rebalance timing must not be publicly predictable",
            "inventory bounds take priority over fee revenue",
        ),
        "Treasury and LP analytics pattern, not an autonomous executor lane.",
    ),
    _pattern(
        "aave-flashloan-rebalancing",
        "Aave flash-loan rebalancing",
        EigenPhiPatternFamily.LIQUIDITY,
        PatternOperationalMode.OFFENSIVE,
        "under-the-hood-of-the-defi-lego/rebalancing-loan-positions-utilizing-aave-flash-loan",
        (
            "flash-loan borrow",
            "debt repay or collateral swap",
            "position migration",
            "flash-loan repayment",
        ),
        (
            "simulate full flash-loan callback",
            "verify account health factor before and after",
            "include premium, slippage, and repay exactness",
        ),
        (
            "fail closed if repayment exactness is not proven",
            "health factor must improve or remain within policy",
            "position-owner authorization is mandatory",
        ),
        "Aave position-management workflow checklist.",
    ),
    _pattern(
        "synthetic-mint-burn-arbitrage",
        "Synthetic mint/burn arbitrage",
        EigenPhiPatternFamily.ARBITRAGE,
        PatternOperationalMode.OFFENSIVE,
        "unlocking-the-power-of-advanced-defi-transactions-and-becoming-a-defi-sleuth/a-bot-devised-arbitrage-strategies-centered-on-autonomous-minting-and-burning-of-synthetic-tokens",
        (
            "mint leg",
            "secondary-market swap",
            "burn or redeem leg",
            "synthetic backing and fee state",
        ),
        (
            "verify mint and redeem invariants",
            "simulate full cycle at one block",
            "bound protocol fee and backing-risk changes",
        ),
        (
            "fail closed when backing state is stale",
            "mint/burn permission and cap checks are mandatory",
            "do not rely on off-chain price alone",
        ),
        "Workflow-required cyclic arb lane for synthetic assets.",
    ),
    _pattern(
        "oracle-defect-exploit",
        "Oracle defect exploit",
        EigenPhiPatternFamily.ORACLE,
        PatternOperationalMode.OFFENSIVE,
        "unlocking-the-power-of-advanced-defi-transactions-and-becoming-a-defi-sleuth/the-defect-in-a-lending-protocols-oracle-module-was-exploited-by-a-bot-to-generate-a-usd110k-profit",
        (
            "stale or manipulable oracle price",
            "borrow or liquidation action",
            "protocol accounting dependent on bad price",
        ),
        (
            "compare oracle price to independent references",
            "detect deviation, staleness, and update authority",
            "block execution when accounting depends on defective price",
        ),
        (
            "fail closed on oracle discrepancy",
            "do not exploit defective user-facing accounting",
            "independent price quorum is required for capital movement",
        ),
        "Defensive oracle-risk gate for lending and liquidation candidates.",
    ),
    _pattern(
        "mev-bot-bait",
        "MEV bot bait",
        EigenPhiPatternFamily.ADVERSARIAL,
        PatternOperationalMode.OFFENSIVE,
        "unlocking-the-power-of-advanced-defi-transactions-and-becoming-a-defi-sleuth/an-attacker-baited-mev-arbitrage-bots-and-emptied-their-wallets",
        (
            "apparently profitable bait transaction",
            "untrusted callback or token behavior",
            "wallet-draining approval or transfer path",
        ),
        (
            "simulate with adversarial token and callback assumptions",
            "inspect approvals, permits, and arbitrary external calls",
            "reject opportunities requiring wallet custody exposure",
        ),
        (
            "fail closed on unknown token behavior",
            "never grant unbounded approvals from strategy wallets",
            "profit signal must not bypass security review",
        ),
        "Adversarial bait filter for opportunity intake.",
    ),
    _medium_pattern(
        "jared-2-0-layered-sandwich",
        "Jared 2.0 layered sandwich profile",
        EigenPhiPatternFamily.SANDWICH,
        PatternOperationalMode.OFFENSIVE,
        "metamorphosis-of-jaredfromsubway-eth-cunninger-jared-2-0-with-more-layers-81a3f900c71a",
        (
            "same-pool block-level cluster with >4 attacker legs",
            "front and back legs include liquidity mutations",
            "multiple victim swaps between attacker legs",
            "private and public submission mix",
        ),
        (
            "segment multi-leg clusters by block/order",
            "confirm attacker wallet continuity across legs",
            "classify LP mutations as sandwich support, not routine LP intent",
            "validate profit path after fee and slippage floors",
        ),
        (
            "fail closed when cluster membership is ambiguous",
            "do not classify LP mutation clusters as neutral",
            "new multi-layer patterns must pass conservative false-positive control",
        ),
        "Defense-oriented classifier for advanced layered sandwich variants.",
    ),
    _substack_pattern(
        "myth-buster-no-trade-is-too-small",
        "Myth Buster: no trade is too small",
        EigenPhiPatternFamily.SANDWICH,
        PatternOperationalMode.OFFENSIVE,
        "myth-buster-4-no-trade-is-too-small",
        (
            "very small swap notional with measurable slippage",
            "rapid orderbook depth decay or reserve imbalance",
            "front-run/back-run sequencing with low confidence profit",
            "micro-profit opportunities in volatile pools",
        ),
        (
            "simulate minimum profitable notional under worst-case gas",
            "bound MEV capture by confidence-adjusted simulation only",
            "verify victim ordering and anti-sandwich controls remain intact",
        ),
        (
            "fail closed when post-simulation profit confidence is below threshold",
            "reject non-atomic opportunities below deterministic minimum notional",
            "do not permit dust-size extraction unless governance policy explicitly allows",
        ),
        "Sandwich viability classifier for micro-size orders and no-trade-size myths.",
    ),
    _theagenticreview_substack_pattern(
        "self-improving-agent-ops-framework",
        "Self-improving agent ops framework",
        EigenPhiPatternFamily.ADVERSARIAL,
        PatternOperationalMode.OFFENSIVE,
        "how-to-build-a-self-improving-agent",
        (
            "model-guided strategy iteration loop",
            "feedback signals changing execution preference",
            "policy-adjusted risk posture over time",
            "governance-like control flow with bounded autonomy",
        ),
        (
            "simulate policy updates before deployment",
            "prove safety invariants remain closed under adaptation",
            "require human or hard policy review gate for strategy reconfiguration",
        ),
        (
            "fail closed when learned policy drifts from hard risk bounds",
            "do not permit model-originated privilege escalation",
            "log all adaptation events for replay and attribution",
        ),
        "Control-loop risk pattern for self-improving agent execution governance.",
    ),
    _thoughts_jockpl_pattern(
        "self-improving-agent-corrections-loop",
        "Self-improving agent corrections loop",
        EigenPhiPatternFamily.ADVERSARIAL,
        PatternOperationalMode.OFFENSIVE,
        "p/i-built-a-self-improving-ai-agent",
        (
            "model-generated policy adjustments with explicit correction traces",
            "rollback-capable feedback channels after detected drift",
            "explicit failure/incident logging as control input",
        ),
        (
            "replay correction traces before adaptation acceptance",
            "verify control limits are unchanged by adaptation output",
            "require deterministic guardrails around any policy mutation",
        ),
        (
            "fail closed when correction confidence is below required floor",
            "do not allow strategy control to grant unbounded execution privileges",
            "mandatory telemetry on every adaptation and rejection event",
        ),
        "Adversarial adaptation pattern for closed-loop self-correction governance.",
    ),
)


def pattern_for_slug(slug: str) -> EigenPhiTransactionPattern:
    """Return a taxonomy pattern by slug."""
    for pattern in EIGENPHI_TRANSACTION_PATTERNS:
        if pattern.slug == slug:
            return pattern
    msg = f"unknown EigenPhi transaction pattern: {slug}"
    raise KeyError(msg)


def patterns_for_family(
    family: EigenPhiPatternFamily,
) -> tuple[EigenPhiTransactionPattern, ...]:
    """Return all patterns in a transaction family."""
    return tuple(pattern for pattern in EIGENPHI_TRANSACTION_PATTERNS if pattern.family is family)


def high_risk_patterns() -> tuple[EigenPhiTransactionPattern, ...]:
    """Return all non-executable patterns requiring policy gating."""
    return tuple(
        pattern
        for pattern in EIGENPHI_TRANSACTION_PATTERNS
        if pattern.operational_mode is not PatternOperationalMode.EXECUTABLE
    )
