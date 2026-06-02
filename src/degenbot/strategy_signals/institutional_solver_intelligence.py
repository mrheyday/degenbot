"""Institutional Solver Intelligence policy kernel.

This module models a deterministic, auditable control loop for proposal-level
policy updates. It does not execute anything by itself; it classifies candidate
strategy/policy changes as allow/review/block with explicit reasons.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from degenbot.exceptions.base import DegenbotValueError


class InstitutionalSolverDecision(StrEnum):
    """Deterministic action for a candidate adaptive decision."""

    APPROVE = "approve"
    REVIEW = "review"
    BLOCK = "block"


@dataclass(frozen=True, slots=True)
class InstitutionalSolverResponsibilities:
    """Declared behavioral contract for the AI administrator."""

    protect_capital: str
    enforce_determinism: str
    strategic_awareness: str
    adversarial_resilience: str
    governance_discipline: str


@dataclass(frozen=True, slots=True)
class AdaptationCandidate:
    """A deterministic input to the adaptive policy gate."""

    candidate_id: str
    expected_profit_bps: int
    observed_drawdown_bps: int
    confidence_bps: int
    sample_count: int
    required_human_approval: bool = False
    requires_invariant_checks: bool = True
    policy_drift_score: int = 0


@dataclass(frozen=True, slots=True)
class PolicyObservation:
    """Observed outcome for a previously evaluated adaptive candidate."""

    observation_id: str
    candidate_id: str
    realized_profit_bps: int
    realized_drawdown_bps: int
    confidence_bps: int
    policy_drift_score: int = 0


@dataclass(frozen=True, slots=True)
class InstitutionalAction:
    """Result of the policy gate for one candidate."""

    candidate_id: str
    decision: InstitutionalSolverDecision
    policy_id: str
    controls: tuple[str, ...]
    rationale: str


@dataclass(frozen=True, slots=True)
class PolicyCorrectionProposal:
    """Auditable correction proposal emitted by the adaptive control loop."""

    proposal_id: str
    candidate_id: str
    decision: InstitutionalSolverDecision
    policy_id: str
    controls: tuple[str, ...]
    rationale: str
    proposed_min_profit_bps: int
    proposed_min_confidence_bps: int
    requires_human_review: bool


class InstitutionalSolverIntelligence:
    """Deterministic, auditable control policy for self-improving behavior."""

    name = "Institutional Solver Intelligence"

    responsibilities = InstitutionalSolverResponsibilities(
        protect_capital=(
            "Protect capital first, avoid reckless risk and non-deterministic shortcuts."
        ),
        enforce_determinism=(
            "Prioritize correctness and deterministic replay over adaptive volatility."
        ),
        strategic_awareness=(
            "Adapt within approved policy bounds when infrastructure and risks justify it."
        ),
        adversarial_resilience=(
            "Assume hostile environments and reject control loops that create exploitability."
        ),
        governance_discipline=(
            "Hold to incident-ready governance discipline and explicit escalation conditions."
        ),
    )

    ai_principles: tuple[str, ...] = (
        "strategic",
        "disciplined",
        "mathematically_grounded",
        "precise",
        "emotionally_detached",
        "truth_aligned",
        "responsibility_minded",
        "no_assumptions",
    )

    safety_gates: tuple[str, ...] = (
        "fail closed on adverse confidence or sample conditions",
        "bounded drawdown and policy drift enforcement",
        "human approval path for high-impact adaptive changes",
        "invariant-preserving fallback when signals are ambiguous",
    )

    def __init__(
        self,
        *,
        max_drawdown_bps: int = 50,
        min_confidence_bps: int = 7000,
        min_sample_count: int = 30,
        min_profit_bps: int = 20,
        max_policy_drift_score: int = 40,
        policy_id: str = "adaptive_control_loop_v1",
    ) -> None:
        self._max_drawdown_bps = max_drawdown_bps
        self._min_confidence_bps = min_confidence_bps
        self._min_sample_count = min_sample_count
        self._min_profit_bps = min_profit_bps
        self._max_policy_drift_score = max_policy_drift_score
        self._policy_id = policy_id

    def evaluate(self, candidate: AdaptationCandidate) -> InstitutionalAction:
        """Evaluate a candidate and return a deterministic decision."""

        controls: tuple[str, ...]

        if candidate.observed_drawdown_bps > self._max_drawdown_bps:
            return InstitutionalAction(
                candidate_id=candidate.candidate_id,
                decision=InstitutionalSolverDecision.BLOCK,
                policy_id=self._policy_id,
                controls=("drawdown_gate", "kill_switch_required"),
                rationale=(
                    f"reject candidate {candidate.candidate_id}: drawdown "
                    f"{candidate.observed_drawdown_bps} bps exceeds max {self._max_drawdown_bps} bps"
                ),
            )

        if not candidate.requires_invariant_checks:
            return InstitutionalAction(
                candidate_id=candidate.candidate_id,
                decision=InstitutionalSolverDecision.BLOCK,
                policy_id=self._policy_id,
                controls=("invariant_validation", "replay_required"),
                rationale=(
                    f"reject candidate {candidate.candidate_id}: invariant checks are "
                    "required for adaptive reconfiguration"
                ),
            )

        if candidate.sample_count < self._min_sample_count:
            controls = ("sample_reduction_gate", "review_required")
            rationale = (
                f"candidate {candidate.candidate_id}: insufficient samples "
                f"({candidate.sample_count}<{self._min_sample_count}) for stable adaptation"
            )
            return InstitutionalAction(
                candidate_id=candidate.candidate_id,
                decision=InstitutionalSolverDecision.REVIEW,
                policy_id=self._policy_id,
                controls=controls,
                rationale=rationale,
            )

        if candidate.confidence_bps < self._min_confidence_bps:
            controls = ("confidence_gate", "review_required")
            rationale = (
                f"candidate {candidate.candidate_id}: confidence {candidate.confidence_bps} "
                f"below policy floor {self._min_confidence_bps}"
            )
            return InstitutionalAction(
                candidate_id=candidate.candidate_id,
                decision=InstitutionalSolverDecision.REVIEW,
                policy_id=self._policy_id,
                controls=controls,
                rationale=rationale,
            )

        if candidate.policy_drift_score > self._max_policy_drift_score:
            return InstitutionalAction(
                candidate_id=candidate.candidate_id,
                decision=InstitutionalSolverDecision.REVIEW,
                policy_id=self._policy_id,
                controls=("drift_analysis", "governance_review"),
                rationale=(
                    f"candidate {candidate.candidate_id}: policy drift score "
                    f"{candidate.policy_drift_score} exceeds max {self._max_policy_drift_score}"
                ),
            )

        if candidate.expected_profit_bps < self._min_profit_bps:
            return InstitutionalAction(
                candidate_id=candidate.candidate_id,
                decision=InstitutionalSolverDecision.REVIEW,
                policy_id=self._policy_id,
                controls=("min_profit_gate", "simulator_confirmation"),
                rationale=(
                    f"candidate {candidate.candidate_id}: expected profit "
                    f"{candidate.expected_profit_bps} bps below floor {self._min_profit_bps} bps"
                ),
            )

        if candidate.required_human_approval:
            return InstitutionalAction(
                candidate_id=candidate.candidate_id,
                decision=InstitutionalSolverDecision.REVIEW,
                policy_id=self._policy_id,
                controls=("human_approval", "post_change_observability"),
                rationale=(
                    f"candidate {candidate.candidate_id}: human approval required by governance"
                ),
            )

        return InstitutionalAction(
            candidate_id=candidate.candidate_id,
            decision=InstitutionalSolverDecision.APPROVE,
            policy_id=self._policy_id,
            controls=("simulator_replay", "telemetry_logging"),
            rationale=(
                f"candidate {candidate.candidate_id}: all control gates passed"
            ),
        )

    def propose_policy_correction(
        self,
        candidate: AdaptationCandidate,
        observation: PolicyObservation,
    ) -> PolicyCorrectionProposal:
        """Convert observed outcomes into a deterministic correction proposal.

        This method never mutates live thresholds. Callers must route proposals
        through replay and governance before applying any policy changes.
        """

        if observation.candidate_id != candidate.candidate_id:
            msg = (
                "policy observation candidate_id must match adaptation candidate_id "
                f"({observation.candidate_id!r} != {candidate.candidate_id!r})"
            )
            raise DegenbotValueError(msg)

        proposal_id = (
            f"{self._policy_id}:{candidate.candidate_id}:{observation.observation_id}"
        )

        if observation.realized_drawdown_bps > self._max_drawdown_bps:
            return PolicyCorrectionProposal(
                proposal_id=proposal_id,
                candidate_id=candidate.candidate_id,
                decision=InstitutionalSolverDecision.BLOCK,
                policy_id=self._policy_id,
                controls=("post_trade_drawdown_gate", "kill_switch_required", "human_review"),
                rationale=(
                    f"observation {observation.observation_id}: realized drawdown "
                    f"{observation.realized_drawdown_bps} bps exceeds max "
                    f"{self._max_drawdown_bps} bps"
                ),
                proposed_min_profit_bps=self._min_profit_bps,
                proposed_min_confidence_bps=self._min_confidence_bps,
                requires_human_review=True,
            )

        if observation.policy_drift_score > self._max_policy_drift_score:
            return PolicyCorrectionProposal(
                proposal_id=proposal_id,
                candidate_id=candidate.candidate_id,
                decision=InstitutionalSolverDecision.REVIEW,
                policy_id=self._policy_id,
                controls=("drift_correction", "governance_review", "simulator_replay"),
                rationale=(
                    f"observation {observation.observation_id}: policy drift score "
                    f"{observation.policy_drift_score} exceeds max "
                    f"{self._max_policy_drift_score}"
                ),
                proposed_min_profit_bps=self._min_profit_bps,
                proposed_min_confidence_bps=self._min_confidence_bps,
                requires_human_review=True,
            )

        if observation.confidence_bps < self._min_confidence_bps:
            return PolicyCorrectionProposal(
                proposal_id=proposal_id,
                candidate_id=candidate.candidate_id,
                decision=InstitutionalSolverDecision.REVIEW,
                policy_id=self._policy_id,
                controls=("confidence_correction", "sample_expansion", "simulator_replay"),
                rationale=(
                    f"observation {observation.observation_id}: confidence "
                    f"{observation.confidence_bps} below policy floor "
                    f"{self._min_confidence_bps}"
                ),
                proposed_min_profit_bps=self._min_profit_bps,
                proposed_min_confidence_bps=self._min_confidence_bps,
                requires_human_review=True,
            )

        if observation.realized_profit_bps < self._min_profit_bps:
            return PolicyCorrectionProposal(
                proposal_id=proposal_id,
                candidate_id=candidate.candidate_id,
                decision=InstitutionalSolverDecision.REVIEW,
                policy_id=self._policy_id,
                controls=("profit_correction", "simulator_replay", "shadow_execution"),
                rationale=(
                    f"observation {observation.observation_id}: realized profit "
                    f"{observation.realized_profit_bps} bps below floor "
                    f"{self._min_profit_bps} bps"
                ),
                proposed_min_profit_bps=max(
                    self._min_profit_bps,
                    candidate.expected_profit_bps,
                ),
                proposed_min_confidence_bps=self._min_confidence_bps,
                requires_human_review=True,
            )

        return PolicyCorrectionProposal(
            proposal_id=proposal_id,
            candidate_id=candidate.candidate_id,
            decision=InstitutionalSolverDecision.APPROVE,
            policy_id=self._policy_id,
            controls=("retain_policy", "telemetry_logging", "periodic_replay"),
            rationale=(
                f"observation {observation.observation_id}: realized outcome remains "
                "inside approved policy bounds"
            ),
            proposed_min_profit_bps=self._min_profit_bps,
            proposed_min_confidence_bps=self._min_confidence_bps,
            requires_human_review=False,
        )


__all__ = (
    "AdaptationCandidate",
    "InstitutionalAction",
    "InstitutionalSolverDecision",
    "InstitutionalSolverIntelligence",
    "InstitutionalSolverResponsibilities",
    "PolicyCorrectionProposal",
    "PolicyObservation",
)
