"""Per-opportunity routing engine for strategy selection."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from degenbot.decision.precedence import DecisionKind, compare_priority
from degenbot.decision.sandoo_ideas import SandooIdeaSignal, evaluate_sandoo_idea
from degenbot.decision.types import AggregatorQuote, DecisionContext, DecisionRoute
from degenbot.simulation import Simulator, parse_seed_pools

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
        self._revm_simulation_required = bool(getattr(settings, "revm_simulation_required", False))
        self._simulator: Simulator | None = self._build_simulator()

    async def route_opportunity(self, opp: Opportunity, ctx: DecisionContext) -> RoutedDecision:
        candidates: list[RouteCandidate] = []
        logger.debug(f"Routing opportunity {opp.id} ({opp.kind}) flow_id={ctx.flow_id}")

        if not self._settings.strategies_enabled:
            return RoutedDecision(
                kind="pass",
                route=DecisionRoute(kind="pass", reason="kill_switch_active"),
                ctx=ctx,
                score_wei=0,
            )

        if opp.flash_amount <= 0:
            return RoutedDecision(
                kind="pass",
                route=DecisionRoute(kind="pass", reason="zero_flash_amount"),
                ctx=ctx,
                score_wei=0,
            )

        # 0. Timeboost economics
        timeboost_decision = None
        if self._settings.strategy_timeboost_enabled:
            from degenbot.decision.timeboost import (
                TimeboostOpportunity,
                TimeboostRoundState,
                decide_timeboost_bid,
            )

            # Sourced from settings / live state
            round_state = TimeboostRoundState(
                current_round_bid=self._settings.timeboost_current_bid_wei,
                round_duration_sec=self._settings.timeboost_round_duration_sec,
                expected_ops_per_round=self._settings.timeboost_expected_ops_per_round,
            )

            timeboost_decision = decide_timeboost_bid(
                TimeboostOpportunity(
                    expected_profit_wei=opp.estimated_profit_wei,
                    non_express_win_probability_bps=self._settings.timeboost_non_express_win_bps,
                    gas_cost_wei=self._settings.estimated_gas_cost_wei,
                    strategy_class=cast("Any", opp.kind),  # Simplified mapping
                ),
                round_state,
            )

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

            four_leg_strategy = FourLegStrategy(self._settings)
            four_leg_plan = four_leg_strategy.preflight(opp)
            if four_leg_plan:
                candidates.append(
                    RouteCandidate(
                        kind="four_leg",
                        route=DecisionRoute(
                            kind="four_leg",
                            opportunity_id=opp.id,
                            plan=four_leg_plan,
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

        # 4. S-5 Oracle sandwich
        if self._settings.strategy_oracle_sandwich_enabled:
            from degenbot.strategies_coordinator.oracle_sandwich import OracleSandwichStrategy

            oracle_sandwich_strategy = OracleSandwichStrategy(self._settings)
            oracle_sandwich_plan = oracle_sandwich_strategy.preflight(opp)
            if oracle_sandwich_plan:
                candidates.append(
                    RouteCandidate(
                        kind="oracle_sandwich",
                        route=DecisionRoute(
                            kind="oracle_sandwich",
                            opportunity_id=opp.id,
                            plan=oracle_sandwich_plan,
                        ),
                        score_wei=oracle_sandwich_plan.expected_profit_wei,
                        ctx=ctx,
                    )
                )

        # 5. Pick S — traditional sandwich
        if self._settings.strategy_sandwich_enabled:
            from degenbot.strategies_coordinator.sandwich import SandwichStrategy

            sandwich_strategy = SandwichStrategy(self._settings)
            sandwich_plan = sandwich_strategy.preflight(opp)
            if sandwich_plan:
                candidates.append(
                    RouteCandidate(
                        kind="sandwich",
                        route=DecisionRoute(
                            kind="sandwich",
                            opportunity_id=opp.id,
                            plan=sandwich_plan,
                        ),
                        score_wei=sandwich_plan.expected_profit_wei,
                        ctx=ctx,
                    )
                )

        # Quote enrichment + route scoring for native arb opportunities.
        best_q: AggregatorQuote | None = None
        should_enrich_quote = self._settings.strategy_native_arb_enabled and opp.kind == "NativeArb"
        sandoo_idea: SandooIdeaSignal | None = None

        if should_enrich_quote:
            logger.debug(
                "native arb quote enrichment adapter not configured; "
                "using sourced opportunity economics"
            )

        if self._settings.strategy_sandoo_ideas_enabled and opp.kind == "NativeArb":
            sandoo_idea = evaluate_sandoo_idea(
                opp=opp,
                best_quote=best_q,
                max_gas_price_gwei=int(self._settings.max_gas_price_gwei),
                flash_loan_fee_wei=self._settings.flash_loan_fee_wei,
            )

        # 4. Native arb.
        if self._settings.strategy_native_arb_enabled:
            profitable = self._evaluate_native_arb(opp, best_q, sandoo_idea)
            if profitable:
                enrichment: dict[str, Any] = {}
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

        decision = self._select_best_route(candidates, opp)
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

    def _select_best_route(
        self, candidates: Sequence[RouteCandidate], opp: Opportunity
    ) -> RouteCandidate:
        best: RouteCandidate | None = None
        for candidate in candidates:
            if candidate.kind == "pass":
                continue

            if not self._candidate_passes_revm(candidate, opp):
                continue

            if (
                best is None
                or compare_priority(candidate.kind, best.kind) < 0
                or (candidate.kind == best.kind and candidate.score_wei > best.score_wei)
            ):
                best = candidate

        if best is None:
            return RouteCandidate(
                kind="pass",
                route=DecisionRoute(kind="pass", reason="no_profitable_route_simulated"),
                score_wei=0,
            )
        return best

    def _build_simulator(self) -> Simulator | None:
        rpc_url = (
            getattr(self._settings, "revm_simulation_rpc_url", None)
            or getattr(self._settings, "arb_rpc_http", None)
            or getattr(self._settings, "rpc_url", None)
        )
        if not rpc_url:
            return None
        return Simulator(
            str(rpc_url),
            seed_pools=parse_seed_pools(
                getattr(self._settings, "revm_simulation_seed_pools", None)
            ),
        )

    def _candidate_passes_revm(self, cand: RouteCandidate, opp: Opportunity) -> bool:
        if self._simulator is None:
            if self._revm_simulation_required:
                logger.warning("REVM simulation required but simulator is not configured")
                return False
            return True

        return self._simulate_candidate(cand, opp)

    def _simulate_candidate(self, cand: RouteCandidate, opp: Opportunity) -> bool:
        """Delegate simulation to the appropriate strategy implementation."""
        if self._simulator is None:
            return not self._revm_simulation_required

        try:
            if cand.kind == "native_arb":
                from degenbot.strategies_coordinator.native_arb import NativeArbStrategy

                native_arb_strategy = NativeArbStrategy(self._settings)
                native_arb_params = native_arb_strategy.build_params(opp)
                return native_arb_strategy.simulate(self._simulator, native_arb_params)

            if cand.kind == "internal_match":
                from degenbot.strategies_coordinator.internal_match import (
                    InternalMatchStrategy,
                )

                if cand.route.pair:
                    internal_match_strategy = InternalMatchStrategy(self._settings)
                    estimated_profit_wei = int(
                        (cand.enrichment or {}).get("estimated_profit_wei", 1)
                    )
                    match_params = internal_match_strategy.build_params_from_pair(
                        cand.route.pair,
                        estimated_profit_wei,
                    )
                    return internal_match_strategy.simulate(self._simulator, match_params)

            if cand.kind == "four_leg":
                from degenbot.strategies_coordinator.four_leg import FourLegStrategy

                if cand.route.plan:
                    four_leg_strategy = FourLegStrategy(self._settings)
                    compose_params = four_leg_strategy.build_params(cand.route.plan)
                    return four_leg_strategy.simulate(self._simulator, compose_params)

            if cand.kind == "morpho_liquidation":
                return self._simulate_enriched_calldata(cand, opp)

            if cand.kind == "oracle_sandwich":
                from degenbot.strategies_coordinator.oracle_sandwich import (
                    OracleSandwichStrategy,
                )

                if cand.route.plan:
                    oracle_sandwich_strategy = OracleSandwichStrategy(self._settings)
                    oracle_sandwich_params = oracle_sandwich_strategy.build_params(cand.route.plan)
                    return oracle_sandwich_strategy.simulate(
                        self._simulator, oracle_sandwich_params
                    )

            if cand.kind == "sandwich":
                from degenbot.strategies_coordinator.sandwich import SandwichStrategy

                if cand.route.plan:
                    sandwich_strategy = SandwichStrategy(self._settings)
                    sandwich_params = sandwich_strategy.build_params(cand.route.plan)
                    return sandwich_strategy.simulate(self._simulator, sandwich_params)

        except Exception as e:
            logger.warning(f"Simulation exception for {cand.kind}: {e}")
            return False

        logger.warning(f"REVM simulation has no exact calldata path for {cand.kind}")
        return False

    def _simulate_enriched_calldata(self, cand: RouteCandidate, opp: Opportunity) -> bool:
        """Simulate routes that already carry exact calldata in enrichment."""
        from degenbot.simulation import simulate_executor_call

        if self._simulator is None:
            return False

        enriched = [cand.enrichment or {}, getattr(opp, "enrichment", {}) or {}]
        for payload in enriched:
            calldata = (
                payload.get("executor_calldata")
                or payload.get("liquidation_executor_calldata")
                or payload.get("calldata")
            )
            if not calldata:
                continue
            target = (
                payload.get("simulation_target")
                or payload.get("target")
                or getattr(self._settings, "liquidation_executor_address", None)
                or getattr(self._settings, "executor_address", None)
            )
            if isinstance(calldata, str):
                raw = calldata.removeprefix("0x").removeprefix("0X")
                data = bytes.fromhex(raw)
            else:
                data = bytes(calldata)
            result = simulate_executor_call(
                simulator=self._simulator,
                settings=self._settings,
                calldata=data,
                to_addr=target,
            )
            return result.success

        logger.warning(f"{cand.kind} rejected: exact simulation calldata is unavailable")
        return False
