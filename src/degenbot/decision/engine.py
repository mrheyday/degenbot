"""Per-opportunity routing engine for strategy selection."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from degenbot.decision.precedence import DecisionKind, compare_priority
from degenbot.decision.sandoo_ideas import SandooIdeaSignal, evaluate_sandoo_idea
from degenbot.decision.types import AggregatorQuote, DecisionContext, DecisionRoute

if TYPE_CHECKING:
    from collections.abc import Sequence

    from degenbot.adapters.config import Settings
    from degenbot.types_solver.wire import Opportunity

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RoutedDecision:
    kind: DecisionKind
    route: DecisionRoute
    ctx: DecisionContext
    score_wei: int = 0
    enrichment: dict[str, Any] | None = None


@dataclass(frozen=True)
class RouteCandidate:
    kind: DecisionKind
    route: DecisionRoute
    score_wei: int
    ctx: DecisionContext | None = None
    enrichment: dict[str, Any] | None = None


class DecisionEngine:
    """Per-opportunity routing engine."""

    def __init__(self, settings: Settings, queue: Any = None) -> None:
        self._settings = settings
        self._queue = queue

    async def route_opportunity(self, opp: Opportunity, ctx: DecisionContext) -> RoutedDecision:
        candidates: list[RouteCandidate] = []

        if not self._settings.strategies_enabled:
            return RoutedDecision(
                kind="pass",
                route=DecisionRoute(kind="pass", reason="kill_switch_active"),
                ctx=ctx,
            )

        if opp.flash_amount <= 0:
            return RoutedDecision(
                kind="pass",
                route=DecisionRoute(kind="pass", reason="zero_flash_amount"),
                ctx=ctx,
                score_wei=0,
            )

        # TODO: Timeboost economics port
        timeboost_decision = None

        # 1. Pick A — internal match
        if self._settings.strategy_internal_match_enabled and self._queue is not None:
            from degenbot.matching.internal_matcher import find_best_match

            match = find_best_match(
                outbound=self._queue.outbound,
                inbound=self._queue.inbound,
                uniswapx=self._queue.uniswapx,
            )
            if match:
                candidates.append(
                    RouteCandidate(
                        kind="internal_match",
                        route=DecisionRoute(
                            kind="internal_match",
                            pair=match,
                        ),
                        score_wei=match.fill_amount,  # Greedy fill optimization
                        ctx=ctx,
                    )
                )

        # 2. Pick B — four-leg composition
        if self._settings.strategy_four_leg_enabled and opp.morpho_liquidation is None:
            from degenbot.strategies_coordinator.four_leg import FourLegStrategy

            strategy = FourLegStrategy(self._settings)
            plan = strategy.preflight(opp)
            if plan:
                candidates.append(
                    RouteCandidate(
                        kind="four_leg",
                        route=DecisionRoute(
                            kind="four_leg",
                            opportunity_id=opp.id,
                            plan=plan,
                        ),
                        score_wei=opp.estimated_profit_wei,
                        ctx=ctx,
                    )
                )

        # 3. Morpho standard liquidation
        if opp.kind.startswith("MorphoLiquidation"):
            candidates.append(
                RouteCandidate(
                    kind="morpho_liquidation",
                    route=DecisionRoute(kind="morpho_liquidation", opportunity_id=opp.id),
                    score_wei=0,
                    ctx=ctx,
                    enrichment={"timeboost": timeboost_decision} if timeboost_decision else None,
                )
            )

        # Quote enrichment + route scoring for native arb opportunities.
        best_q: AggregatorQuote | None = None
        should_enrich_quote = self._settings.strategy_native_arb_enabled and opp.kind == "NativeArb"
        sandoo_idea: SandooIdeaSignal | None = None

        if should_enrich_quote:
            # TODO: best_quote implementation (DeFiLlamaSwap)
            pass

        if self._settings.strategy_sandoo_ideas_enabled and opp.kind == "NativeArb":
            sandoo_idea = evaluate_sandoo_idea(
                opp=opp,
                best_quote=best_q,
                max_gas_price_gwei=self._settings.max_gas_price_gwei,
                flash_loan_fee_wei=self._settings.flash_loan_fee_wei,
            )

        # 4. Native arb.
        if self._settings.strategy_native_arb_enabled:
            profitable = self._evaluate_native_arb(opp, best_q, sandoo_idea, should_enrich_quote)
            if profitable:
                enrichment = {}
                if best_q:
                    enrichment["best_quote"] = best_q
                if timeboost_decision:
                    enrichment["timeboost"] = timeboost_decision
                if sandoo_idea:
                    enrichment["sandoo_idea"] = sandoo_idea

                candidates.append(
                    RouteCandidate(
                        kind="native_arb",
                        route=DecisionRoute(kind="native_arb", opportunity_id=opp.id),
                        ctx=ctx,
                        score_wei=self._derive_native_arb_score(opp, best_q, sandoo_idea),
                        enrichment=enrichment or None,
                    )
                )

        # 8. Pass.
        if not candidates:
            logger.debug(f"no profitable route for opp {opp.id}; passing")
            return RoutedDecision(
                kind="pass",
                route=DecisionRoute(kind="pass", reason="no_profitable_route"),
                ctx=ctx,
                score_wei=0,
            )

        decision = self._select_best_route(candidates)
        return RoutedDecision(
            kind=decision.kind,
            route=decision.route,
            ctx=ctx,
            enrichment=decision.enrichment,
            score_wei=decision.score_wei,
        )

    def _evaluate_native_arb(
        self,
        opp: Opportunity,
        best_q: AggregatorQuote | None,
        sandoo_idea: SandooIdeaSignal | None,
        require_quote_for_native_arb: bool = False,
    ) -> bool:
        if opp.estimated_profit_wei <= 0:
            return False
        if require_quote_for_native_arb and best_q is None:
            return False

        if self._settings.strategy_sandoo_ideas_enabled and sandoo_idea is not None:
            if not sandoo_idea.eligible:
                return False
            if opp.token_in.lower() != opp.token_out.lower():
                return sandoo_idea.components.net_profit_after_cost_wei > 0
            if best_q is None:
                return sandoo_idea.components.net_profit_after_cost_wei > 0

            best_quote_net_out = (
                best_q.amount_out - opp.amount_in if best_q.amount_out > opp.amount_in else 0
            )
            return sandoo_idea.components.net_profit_after_cost_wei > best_quote_net_out

        if best_q is None:
            return True

        return self._is_native_arb_profit_superior(opp, best_q)

    def _is_native_arb_profit_superior(self, opp: Opportunity, best_q: AggregatorQuote) -> bool:
        if opp.token_in.lower() != opp.token_out.lower():
            return True

        best_quote_net_out = (
            best_q.amount_out - opp.amount_in if best_q.amount_out > opp.amount_in else 0
        )
        return opp.estimated_profit_wei > best_quote_net_out

    def _derive_native_arb_score(
        self,
        opp: Opportunity,
        best_q: AggregatorQuote | None,
        sandoo_idea: SandooIdeaSignal | None,
    ) -> int:
        if sandoo_idea and sandoo_idea.eligible:
            return sandoo_idea.components.net_profit_after_cost_wei

        if best_q and opp.token_in.lower() == opp.token_out.lower():
            best_quote_net_out = (
                best_q.amount_out - opp.amount_in if best_q.amount_out > opp.amount_in else 0
            )
            return opp.estimated_profit_wei - best_quote_net_out

        return opp.estimated_profit_wei

    def _select_best_route(self, candidates: Sequence[RouteCandidate]) -> RouteCandidate:
        best: RouteCandidate | None = None
        for candidate in candidates:
            if (
                best is None
                or compare_priority(candidate.kind, best.kind) < 0
                or (candidate.kind == best.kind and candidate.score_wei > best.score_wei)
            ):
                best = candidate

        if best is None:
            return RouteCandidate(
                kind="pass",
                route=DecisionRoute(kind="pass", reason="no_profitable_route"),
                score_wei=0,
            )
        return best
