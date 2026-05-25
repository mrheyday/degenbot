"""Unit tests for FluidDexClient + FluidPool (forward stub).

Forward stub — full integration lands in degenbot upstream PR per Q-7.
These tests cover the dataclass surface (with Decimal lending-position
preservation) + lifecycle + stub-message anchoring so that the post-PR
rewire keeps the interface stable.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from degenbot.execution.fluid_dex_adapter import (
    FluidDexClient,
    FluidPool,
)

_RPC_URL = "https://arb1.arbitrum.io/rpc"
_POOL_ADDR = "0x0000000000000000000000000000000000000abc"
_USDC = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
_WETH = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"


class TestFluidPool:
    def test_decimal_passthrough_preserves_full_precision(self) -> None:
        # Lending positions are decimal strings — exact preservation matters.
        p = FluidPool(
            address=_POOL_ADDR,
            token0=_USDC,
            token1=_WETH,
            lending_position_token0_str="123456.789012345678",
            lending_position_token1_str="0.000000000000000001",
            rebalance_threshold_bps=100,
        )
        assert p.lending_position_token0 == Decimal("123456.789012345678")
        assert p.lending_position_token1 == Decimal("0.000000000000000001")
        assert isinstance(p.lending_position_token0, Decimal)

    def test_pool_rebalance_threshold_int(self) -> None:
        p = FluidPool(
            address=_POOL_ADDR,
            token0=_USDC,
            token1=_WETH,
            lending_position_token0_str="0",
            lending_position_token1_str="0",
            rebalance_threshold_bps=50,
        )
        assert p.rebalance_threshold_bps == 50

    def test_zero_string_decimals_still_pass(self) -> None:
        p = FluidPool(
            address=_POOL_ADDR,
            token0=_USDC,
            token1=_WETH,
            lending_position_token0_str="0",
            lending_position_token1_str="0",
            rebalance_threshold_bps=0,
        )
        assert p.lending_position_token0 == Decimal(0)
        assert p.lending_position_token1 == Decimal(0)


class TestFluidDexClientLifecycle:
    async def test_async_context_manager_closes_httpx(self) -> None:
        async with FluidDexClient(_RPC_URL) as client:
            assert client is not None

    async def test_close_is_idempotent(self) -> None:
        client = FluidDexClient(_RPC_URL)
        await client.close()
        # second close should not raise
        await client.close()


class TestFluidDexClientUnimplemented:
    """Stub methods raise NotImplementedError until degenbot Q-7 PR lands."""

    async def test_list_pools_anchors_message_to_q7(self) -> None:
        async with FluidDexClient(_RPC_URL) as client:
            with pytest.raises(NotImplementedError, match="Q-7"):
                await client.list_pools()

    async def test_get_pool_anchors_message_to_q7(self) -> None:
        async with FluidDexClient(_RPC_URL) as client:
            with pytest.raises(NotImplementedError, match="Q-7"):
                await client.get_pool(_POOL_ADDR)

    async def test_simulate_swap_warns_about_naive_drift(self) -> None:
        async with FluidDexClient(_RPC_URL) as client:
            with pytest.raises(NotImplementedError, match="drift"):
                await client.simulate_swap(_POOL_ADDR, 1_000_000, zero_for_one=True)
