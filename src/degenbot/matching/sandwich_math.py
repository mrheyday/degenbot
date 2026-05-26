"""Sandwich frontrun sizing math (Pick S).

Algorithm reference: docs/research/2026-05-11-sandwich-primitive-epic.md
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class V2SandwichSolution:
    frontrun_size_wei: int
    frontrun_out_wei: int
    victim_actual_out_wei: int
    backrun_out_wei: int
    net_token_in_wei: int
    slippage_cap_binding: bool


def solve_v2_sandwich(
    victim_amount_in: int,
    victim_min_out: int,
    reserve_in: int,
    reserve_out: int,
    fee_bps: int,
) -> V2SandwichSolution:
    """Find the optimal frontrun size for a V2 sandwich."""
    from degenbot import (
        v2_optimal_sandwich_size,
        v2_sandwich_max_size,
    )

    # 1. Max size that keeps victim from reverting
    a_max = int(
        v2_sandwich_max_size(
            victim_amount_in,
            victim_min_out,
            reserve_in,
            reserve_out,
            fee_bps,
        )
    )

    if a_max <= 0:
        return _zero_solution()

    # 2. Optimal size by maximizing net profit
    a_opt = int(
        v2_optimal_sandwich_size(
            victim_amount_in,
            reserve_in,
            reserve_out,
            fee_bps,
            a_max,
        )
    )

    frontrun_size = min(a_opt, a_max)
    if frontrun_size <= 0:
        return _zero_solution()

    # 3. Simulate outputs
    from degenbot.strategies_coordinator.oracle_sandwich_math import get_amount_out

    fr_out = get_amount_out(frontrun_size, reserve_in, reserve_out, fee_bps)

    x1 = reserve_in + frontrun_size
    y1 = reserve_out - fr_out

    victim_out = get_amount_out(victim_amount_in, x1, y1, fee_bps)

    x2 = x1 + victim_amount_in
    y2 = y1 - victim_out

    backrun_out = get_amount_out(fr_out, y2, x2, fee_bps)

    return V2SandwichSolution(
        frontrun_size_wei=frontrun_size,
        frontrun_out_wei=fr_out,
        victim_actual_out_wei=victim_out,
        backrun_out_wei=backrun_out,
        net_token_in_wei=backrun_out - frontrun_size,
        slippage_cap_binding=(frontrun_size == a_max),
    )


def _zero_solution() -> V2SandwichSolution:
    return V2SandwichSolution(0, 0, 0, 0, 0, False)
