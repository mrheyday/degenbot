"""Deterministic Sandoo-style candidate idea scoring for opportunities."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass

from degenbot.decision.types import AggregatorQuote
from degenbot.types_solver.wire import Opportunity

try:
    from degenbot.degenbot_rs import evaluate_sandoo_idea_json
    HAS_RUST_ACCEL = True
except ImportError:
    HAS_RUST_ACCEL = False

SANDOOSCORE_SCALE = 1_000_000
GWEI_IN_WEI = 1_000_000_000
HUNDRED_PERCENT_BPS = 10_000


@dataclass(frozen=True)
class SandooIdeaComponents:
    estimated_profit_wei: int
    safe_size_wei: int
    quote_amount_out: int
    quote_amount_net_out: int
    route_gas_wei: int
    quote_fee_wei: int
    flash_loan_fee_wei: int
    net_profit_after_cost_wei: int
    size_vs_flash_ratio_bps: int
    quote_profit_gap_wei: int
    score_scale: int


@dataclass(frozen=True)
class SandooIdeaSignal:
    eligible: bool
    score: int
    reasons: Sequence[str]
    components: SandooIdeaComponents


def evaluate_sandoo_idea(
    opp: Opportunity,
    best_quote: AggregatorQuote | None,
    max_gas_price_gwei: int,
    flash_loan_fee_wei: int,
) -> SandooIdeaSignal:
    """Deterministic Sandoo-style candidate idea scoring for opportunities."""
    if HAS_RUST_ACCEL:
        try:
            # Opportunity is a Pydantic model
            opp_json = opp.model_dump_json(by_alias=True)
            quote_json = best_quote.model_dump_json(by_alias=True) if best_quote else None

            res_json = evaluate_sandoo_idea_json(
                opp_json,
                quote_json,
                max_gas_price_gwei,
                str(flash_loan_fee_wei)
            )
            data = json.loads(res_json)
            # Reconstruct the SandooIdeaSignal dataclass
            return SandooIdeaSignal(
                eligible=data["eligible"],
                score=int(data["score"]),
                reasons=data["reasons"],
                components=SandooIdeaComponents(
                    estimated_profit_wei=int(data["components"]["estimated_profit_wei"]),
                    safe_size_wei=int(data["components"]["safe_size_wei"]),
                    quote_amount_out=int(data["components"]["quote_amount_out"]),
                    quote_amount_net_out=int(data["components"]["quote_amount_net_out"]),
                    route_gas_wei=int(data["components"]["route_gas_wei"]),
                    quote_fee_wei=int(data["components"]["quote_fee_wei"]),
                    flash_loan_fee_wei=int(data["components"]["flash_loan_fee_wei"]),
                    net_profit_after_cost_wei=int(data["components"]["net_profit_after_cost_wei"]),
                    size_vs_flash_ratio_bps=int(data["components"]["size_vs_flash_ratio_bps"]),
                    quote_profit_gap_wei=int(data["components"]["quote_profit_gap_wei"]),
                    score_scale=int(data["components"]["score_scale"]),
                )
            )
        except Exception:
            # Fallback to Python on any error
            pass

    reason: list[str] = []

    if opp.flash_amount <= 0:
        return _build_negative_signal(
            opp,
            best_quote,
            0,
            "zero_flash_amount",
            max_gas_price_gwei,
            flash_loan_fee_wei,
            0,
        )

    safe_size_wei = min(opp.amount_in, opp.flash_amount)
    if safe_size_wei == 0:
        return _build_negative_signal(
            opp,
            best_quote,
            safe_size_wei,
            "safe_size_zero",
            max_gas_price_gwei,
            flash_loan_fee_wei,
            0,
        )

    if opp.estimated_profit_wei <= 0:
        return _build_negative_signal(
            opp,
            best_quote,
            safe_size_wei,
            "non_positive_estimated_profit",
            max_gas_price_gwei,
            flash_loan_fee_wei,
            0,
        )

    quote_amount_out = best_quote.amount_out if best_quote else 0
    quote_amount_net_out = (
        quote_amount_out - opp.amount_in if quote_amount_out > opp.amount_in else 0
    )

    max_gas_fee_wei = max_gas_price_gwei * GWEI_IN_WEI
    route_gas_wei = (
        best_quote.estimated_gas * max_gas_fee_wei if best_quote and best_quote.estimated_gas else 0
    )
    quote_fee_wei = (
        (opp.amount_in * best_quote.fee_bps) // HUNDRED_PERCENT_BPS if best_quote else 0
    )

    net_profit_after_cost_wei = max(
        opp.estimated_profit_wei - (route_gas_wei + quote_fee_wei + flash_loan_fee_wei),
        0,
    )

    if net_profit_after_cost_wei <= 0:
        return _build_negative_signal(
            opp,
            best_quote,
            safe_size_wei,
            "cost_after_profit_not_positive",
            max_gas_price_gwei,
            flash_loan_fee_wei,
            net_profit_after_cost_wei,
        )

    size_vs_flash_ratio_bps = (
        (safe_size_wei * HUNDRED_PERCENT_BPS) // opp.amount_in if opp.amount_in > 0 else 0
    )
    if size_vs_flash_ratio_bps < HUNDRED_PERCENT_BPS:
        reason.append("flash_amount_caps_execution_size")

    quote_profit_gap_wei = 0
    if best_quote and opp.token_in.lower() == opp.token_out.lower():
        quote_profit_gap_wei = max(quote_amount_net_out - opp.estimated_profit_wei, 0)

    if quote_profit_gap_wei > 0:
        reason.append("quote_outperforms_candidate_profit")

    score = (net_profit_after_cost_wei * SANDOOSCORE_SCALE) // safe_size_wei
    if size_vs_flash_ratio_bps > 0 and score == 0:
        reason.append("positive_profit_lost_to_size_rounding")
    elif score > 0:
        reason.append("candidate_has_positive_adj_profit")

    return SandooIdeaSignal(
        eligible=True,
        score=score,
        reasons=reason,
        components=SandooIdeaComponents(
            estimated_profit_wei=opp.estimated_profit_wei,
            safe_size_wei=safe_size_wei,
            quote_amount_out=quote_amount_out,
            quote_amount_net_out=quote_amount_net_out,
            route_gas_wei=route_gas_wei,
            quote_fee_wei=quote_fee_wei,
            flash_loan_fee_wei=flash_loan_fee_wei,
            net_profit_after_cost_wei=net_profit_after_cost_wei,
            size_vs_flash_ratio_bps=size_vs_flash_ratio_bps,
            quote_profit_gap_wei=quote_profit_gap_wei,
            score_scale=SANDOOSCORE_SCALE,
        ),
    )


def _build_negative_signal(
    opp: Opportunity,
    best_quote: AggregatorQuote | None,
    safe_size_wei: int,
    reason: str,
    max_gas_price_gwei: int,
    flash_loan_fee_wei: int,
    net_profit_after_cost_wei: int,
) -> SandooIdeaSignal:
    max_gas_fee_wei = max_gas_price_gwei * GWEI_IN_WEI
    route_gas_wei = (
        best_quote.estimated_gas * max_gas_fee_wei if best_quote and best_quote.estimated_gas else 0
    )
    quote_fee_wei = (
        (opp.amount_in * best_quote.fee_bps) // HUNDRED_PERCENT_BPS if best_quote else 0
    )

    quote_amount_out = best_quote.amount_out if best_quote else 0
    quote_amount_net_out = (
        quote_amount_out - opp.amount_in if quote_amount_out > opp.amount_in else 0
    )

    size_vs_flash_ratio_bps = (
        (safe_size_wei * HUNDRED_PERCENT_BPS) // opp.amount_in if opp.amount_in > 0 else 0
    )

    return SandooIdeaSignal(
        eligible=False,
        score=0,
        reasons=[reason],
        components=SandooIdeaComponents(
            estimated_profit_wei=opp.estimated_profit_wei,
            safe_size_wei=safe_size_wei,
            quote_amount_out=quote_amount_out,
            quote_amount_net_out=quote_amount_net_out,
            route_gas_wei=route_gas_wei,
            quote_fee_wei=quote_fee_wei,
            flash_loan_fee_wei=flash_loan_fee_wei,
            net_profit_after_cost_wei=net_profit_after_cost_wei,
            size_vs_flash_ratio_bps=size_vs_flash_ratio_bps,
            quote_profit_gap_wei=0,
            score_scale=SANDOOSCORE_SCALE,
        ),
    )
