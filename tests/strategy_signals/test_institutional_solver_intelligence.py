from __future__ import annotations

from degenbot.strategy_signals.institutional_solver_intelligence import (
    AdaptationCandidate,
    InstitutionalSolverDecision,
    InstitutionalSolverIntelligence,
    PolicyObservation,
)


def test_institutional_solver_identity_and_principles() -> None:
    agent = InstitutionalSolverIntelligence()

    assert agent.name == "Institutional Solver Intelligence"
    assert agent.responsibilities.protect_capital
    assert "deterministic" in agent.responsibilities.enforce_determinism.lower()
    assert "disciplined" in agent.ai_principles


def test_block_on_high_drawdown_candidate() -> None:
    agent = InstitutionalSolverIntelligence()
    decision = agent.evaluate(
        AdaptationCandidate(
            candidate_id="high-drawdown-adapt",
            expected_profit_bps=100,
            observed_drawdown_bps=agent._max_drawdown_bps + 1,
            confidence_bps=agent._min_confidence_bps + 200,
            sample_count=agent._min_sample_count,
        )
    )

    assert decision.decision is InstitutionalSolverDecision.BLOCK
    assert decision.candidate_id == "high-drawdown-adapt"
    assert "drawdown" in decision.rationale
    assert "kill_switch_required" in decision.controls


def test_review_on_low_confidence_or_insufficient_samples() -> None:
    agent = InstitutionalSolverIntelligence()

    low_confidence = agent.evaluate(
        AdaptationCandidate(
            candidate_id="low-confidence",
            expected_profit_bps=200,
            observed_drawdown_bps=0,
            confidence_bps=agent._min_confidence_bps - 1,
            sample_count=agent._min_sample_count,
        )
    )
    assert low_confidence.decision is InstitutionalSolverDecision.REVIEW
    assert "confidence" in low_confidence.rationale

    insufficient_samples = agent.evaluate(
        AdaptationCandidate(
            candidate_id="few-samples",
            expected_profit_bps=200,
            observed_drawdown_bps=0,
            confidence_bps=agent._min_confidence_bps + 1,
            sample_count=agent._min_sample_count - 1,
        )
    )
    assert insufficient_samples.decision is InstitutionalSolverDecision.REVIEW
    assert "samples" in insufficient_samples.rationale


def test_approve_when_controls_pass() -> None:
    agent = InstitutionalSolverIntelligence()

    decision = agent.evaluate(
        AdaptationCandidate(
            candidate_id="stable-gate-pass",
            expected_profit_bps=agent._min_profit_bps + 5,
            observed_drawdown_bps=0,
            confidence_bps=agent._min_confidence_bps,
            sample_count=agent._min_sample_count,
            required_human_approval=False,
        )
    )

    assert decision.decision is InstitutionalSolverDecision.APPROVE
    assert decision.candidate_id == "stable-gate-pass"
    assert "simulator_replay" in decision.controls


def test_policy_correction_reviews_underperformance_without_mutating_thresholds() -> None:
    agent = InstitutionalSolverIntelligence()
    candidate = AdaptationCandidate(
        candidate_id="profit-underperformed",
        expected_profit_bps=agent._min_profit_bps + 20,
        observed_drawdown_bps=0,
        confidence_bps=agent._min_confidence_bps,
        sample_count=agent._min_sample_count,
    )

    proposal = agent.propose_policy_correction(
        candidate,
        PolicyObservation(
            observation_id="obs-1",
            candidate_id="profit-underperformed",
            realized_profit_bps=agent._min_profit_bps - 1,
            realized_drawdown_bps=0,
            confidence_bps=agent._min_confidence_bps,
        ),
    )

    assert proposal.decision is InstitutionalSolverDecision.REVIEW
    assert proposal.proposed_min_profit_bps == candidate.expected_profit_bps
    assert proposal.requires_human_review is True
    assert "profit_correction" in proposal.controls
    assert agent._min_profit_bps == 20


def test_policy_correction_blocks_realized_drawdown() -> None:
    agent = InstitutionalSolverIntelligence()
    candidate = AdaptationCandidate(
        candidate_id="drawdown-observed",
        expected_profit_bps=agent._min_profit_bps + 20,
        observed_drawdown_bps=0,
        confidence_bps=agent._min_confidence_bps,
        sample_count=agent._min_sample_count,
    )

    proposal = agent.propose_policy_correction(
        candidate,
        PolicyObservation(
            observation_id="obs-2",
            candidate_id="drawdown-observed",
            realized_profit_bps=agent._min_profit_bps + 5,
            realized_drawdown_bps=agent._max_drawdown_bps + 1,
            confidence_bps=agent._min_confidence_bps,
        ),
    )

    assert proposal.decision is InstitutionalSolverDecision.BLOCK
    assert "kill_switch_required" in proposal.controls
    assert proposal.requires_human_review is True
