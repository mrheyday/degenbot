"""Unit tests for the ported sandwich sizing logic."""

import pytest
from degenbot.matching.sandwich_math import solve_v2_sandwich

def test_v2_sandwich_solver_profitable():
    # Victim: 10 ETH -> USDC
    # Pool: 1000 ETH, 2,000,000 USDC
    # Slippage: 1% (amountOutMin = baseline * 0.99)
    
    r_in = 1000 * 10**18
    r_out = 2_000_000 * 10**6
    v_in = 10 * 10**18
    
    from degenbot.strategies_coordinator.oracle_sandwich_math import get_amount_out
    baseline = get_amount_out(v_in, r_in, r_out, 30)
    v_min = int(baseline * 0.99)
    
    solution = solve_v2_sandwich(
        victim_amount_in=v_in,
        victim_min_out=v_min,
        reserve_in=r_in,
        reserve_out=r_out,
        fee_bps=30,
    )
    
    assert solution.frontrun_size_wei > 0
    assert solution.net_token_in_wei > 0
    assert solution.victim_actual_out_wei >= v_min
