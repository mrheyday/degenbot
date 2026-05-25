"""Smoke degenbot V2 reserve override behavior for Arbitrum-style fixtures."""

from __future__ import annotations

import importlib
import sys
from collections import deque
from fractions import Fraction
from threading import Lock
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


ARBITRUM_CHAIN_ID = 42161
POOL = "0x0000000000000000000000000000000000002001"


def _purge_degenbot_modules() -> None:
    for module_name in tuple(sys.modules):
        if module_name == "degenbot" or module_name.startswith("degenbot."):
            del sys.modules[module_name]


def test_degenbot_v2_quote_uses_override_reserves(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if "degenbot" not in sys.modules:
        monkeypatch.setenv("HOME", str(tmp_path))
        _purge_degenbot_modules()

    pytest.importorskip("degenbot")

    pool_module = importlib.import_module("degenbot.uniswap.v2_liquidity_pool")
    types_module = importlib.import_module("degenbot.uniswap.v2_types")
    functions_module = importlib.import_module("degenbot.uniswap.v2_functions")

    uniswap_v2_pool = pool_module.UniswapV2Pool
    uniswap_v2_pool_state = types_module.UniswapV2PoolState
    constant_product_calc_exact_in = functions_module.constant_product_calc_exact_in

    token0 = object()
    token1 = object()
    base_state = uniswap_v2_pool_state(
        address=POOL,
        reserves_token0=1_000_000,
        reserves_token1=1_000_000,
        block=100,
    )
    override_state = uniswap_v2_pool_state(
        address=POOL,
        reserves_token0=2_000_000,
        reserves_token1=1_000_000,
        block=101,
    )

    pool = uniswap_v2_pool.__new__(uniswap_v2_pool)
    pool.token0 = token0
    pool.token1 = token1
    pool.fee_token0 = Fraction(3, 1000)
    pool.fee_token1 = Fraction(3, 1000)
    pool._state_cache = deque([base_state])
    pool._state_lock = Lock()

    amount_in = 100_000
    base_amount_out = pool.calculate_tokens_out_from_tokens_in(
        token_in=token0,
        token_in_quantity=amount_in,
    )
    override_amount_out = pool.calculate_tokens_out_from_tokens_in(
        token_in=token0,
        token_in_quantity=amount_in,
        override_state=override_state,
    )

    assert override_amount_out == constant_product_calc_exact_in(
        amount_in=amount_in,
        reserves_in=override_state.reserves_token0,
        reserves_out=override_state.reserves_token1,
        fee=Fraction(3, 1000),
    )
    assert override_amount_out != base_amount_out

    simulation = pool.simulate_exact_input_swap(
        token_in=token0,
        token_in_quantity=amount_in,
        override_state=override_state,
    )

    assert simulation.initial_state == override_state
    assert simulation.amount0_delta == amount_in
    assert simulation.amount1_delta == -override_amount_out
