"""Unit tests for the ported oracle sandwich strategy (S-5)."""

import pytest
from unittest.mock import MagicMock
from degenbot.strategies_coordinator.oracle_sandwich import (
    OracleSandwichPlan,
    OracleSandwichStrategy,
)
from degenbot.strategies_coordinator.oracle_sandwich_math import (
    estimate_oracle_sandwich_profit,
    v3_virtual_reserves,
)
from degenbot.types_solver.wire import Opportunity
from degenbot.decision.types import Address
from degenbot.adapters.config import Settings

# Mock addresses
_TOKEN_A = "0x" + "a" * 40
_TOKEN_B = "0x" + "b" * 40
_POOL = "0x" + "p" * 40
_ROUTER = "0x" + "r" * 40


@pytest.fixture
def fake_settings() -> Settings:
    settings = MagicMock(spec=Settings)
    settings.executor_address = "0x" + "e" * 40
    settings.estimated_gas_cost_wei = 10**14  # 0.0001 ETH
    settings.aave_v3_pool = "0x794a61358d6845594f94dc1db02a252b5b4814ad"
    settings.morpho_blue = None
    return settings


def test_v3_virtual_reserves():
    # P = 1.0 -> sqrtPriceX96 = 2^96
    # L = 10^18
    # R0 = L/sqrt(P) = 10^18
    # R1 = L*sqrt(P) = 10^18
    Q96 = 1 << 96
    r0, r1 = v3_virtual_reserves(Q96, 10**18)
    assert r0 == 10**18
    assert r1 == 10**18


def test_oracle_sandwich_profit_estimate_profitable(fake_settings):
    # reserves scaled up to avoid integer division to zero
    r_in = 10**24 # 1M A
    r_out = 10**24 # 1M B
    gap_bps = 500 # 5%
    
    estimate = estimate_oracle_sandwich_profit(
        gap_bps=gap_bps,
        pool_address=_POOL,
        reserve_in=r_in,
        reserve_out=r_out,
        fee_bps=30,
        gas_cost_wei=fake_settings.estimated_gas_cost_wei,
    )
    
    assert estimate.expected_profit_wei > 0
    assert estimate.frontrun_size_wei > 0
    assert estimate.backrun_size_wei > 0


def test_oracle_sandwich_preflight_none(fake_settings):
    strategy = OracleSandwichStrategy(fake_settings)
    opp = Opportunity(
        id="test-1",
        kind="NativeArb",
        tokenIn=_TOKEN_A,
        tokenOut=_TOKEN_B,
        amountIn=10**18,
        estimatedProfitWei=0,
        flashToken=_TOKEN_A,
        flashAmount=10**18,
        path=[],
        poolAddresses=[_POOL],
    )
    assert strategy.preflight(opp) is None


def test_oracle_sandwich_preflight_with_enrichment(fake_settings):
    strategy = OracleSandwichStrategy(fake_settings)
    
    r_in = 10**24
    r_out = 10**24
    
    opp = Opportunity(
        id="test-1",
        kind="NativeArb",
        tokenIn=_TOKEN_A,
        tokenOut=_TOKEN_B,
        amountIn=10**18,
        estimatedProfitWei=0,
        flashToken=_TOKEN_A,
        flashAmount=10**18,
        path=[],
        poolAddresses=[_POOL],
        enrichment={
            "ostium_gap": {
                "gap_bps": 500,
                "token_sold": _TOKEN_A,
                "token_bought": _TOKEN_B,
            },
            "pool_state": {
                "kind": "UniswapV2",
                "reserve0": r_in,
                "reserve1": r_out,
                "token0": _TOKEN_A,
                "token1": _TOKEN_B,
                "fee_bps": 30,
                "router": _ROUTER,
            }
        }
    )
    
    plan = strategy.preflight(opp)
    assert plan is not None
    assert plan.frontrun_size_wei > 0
    assert plan.token_sold == _TOKEN_A


def test_oracle_sandwich_build_params(fake_settings):
    strategy = OracleSandwichStrategy(fake_settings)
    plan = OracleSandwichPlan(
        opportunity_id="test-1",
        frontrun_size_wei=10**18,
        backrun_size_wei=10**18,
        expected_profit_wei=10**16,
        flash_token=_TOKEN_A,
        pool_address=_POOL,
        pool_kind="UniswapV2",
        token_sold=_TOKEN_A,
        token_bought=_TOKEN_B,
        router=_ROUTER,
    )
    
    params = strategy.build_params(plan)
    assert len(params.swaps) == 2
    assert params.swaps[0].token_in == _TOKEN_A
    assert params.swaps[1].token_in == _TOKEN_B
    assert params.swaps[1].amount_in == 0 # carry-over
