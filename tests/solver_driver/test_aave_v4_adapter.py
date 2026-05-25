"""Unit tests for AaveV4Client + dataclass shape.

V4 adapter is read-only per §07 §1.1a; full GraphQL wiring is TODO. These
tests cover the dataclass surface + Decimal/string handling that's critical
for the off-chain planning path (no on-chain decisions made here).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from degenbot.execution.aave_v4_adapter import (
    AaveV4Client,
    AaveV4Reserve,
    AaveV4SwapQuote,
    AaveV4UserHealth,
    quote_intent_path,
)


class TestAaveV4Reserve:
    def test_decimal_passthrough_preserves_full_precision(self) -> None:
        # 1e-18-precision values must round-trip exactly per §07 §1.1a decimal note.
        r = AaveV4Reserve(
            spoke_address="0x0000000000000000000000000000000000000abc",
            underlying="0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
            symbol="USDC",
            decimals=6,
            supply_apy_str="0.043512345678901234",
            borrow_apy_str="0.063412345678901234",
            liquidity_index_str="1.000000123456789012",
            debt_index_str="1.000001234567890123",
            oracle_price_usd_str="1.000099876543210987",
        )
        assert r.supply_apy == Decimal("0.043512345678901234")
        assert r.borrow_apy == Decimal("0.063412345678901234")
        assert r.oracle_price_usd == Decimal("1.000099876543210987")
        # Critical: NO float conversion in the chain
        assert isinstance(r.supply_apy, Decimal)


class TestAaveV4UserHealth:
    def test_health_factor_below_one_signals_liquidatable(self) -> None:
        h = AaveV4UserHealth(
            user_address="0xdead0000000000000000000000000000000000ad",
            hub_address="0xbeef0000000000000000000000000000000000ef",
            health_factor_str="0.97",
            total_collateral_usd_str="1000",
            total_debt_usd_str="980",
            available_borrows_usd_str="0",
        )
        assert h.health_factor < Decimal("1")


class TestAaveV4SwapQuote:
    def test_swap_quote_shape(self) -> None:
        q = AaveV4SwapQuote(
            src_asset="0xaf88d065e77c8cC2239327C5EDb3A432268e5831",  # USDC
            dst_asset="0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",  # WETH
            src_amount_str="1000000",
            dst_amount_str="500000000000000",
            slippage_bps=10,
            route_kind="cow",
        )
        # Per §07 §1.1a CoW-backed path is the AaveKit default
        assert q.route_kind == "cow"
        assert q.slippage_bps == 10


class TestAaveV4ClientLifecycle:
    @pytest.mark.asyncio
    async def test_async_context_manager_closes_httpx(self) -> None:
        async with AaveV4Client("https://api.v4.aave.com/graphql") as client:
            assert client is not None
        # post-close: client._client is closed; subsequent ops would raise

    @pytest.mark.asyncio
    async def test_close_is_idempotent(self) -> None:
        client = AaveV4Client("https://api.v4.aave.com/graphql")
        await client.close()
        # second close should not raise
        await client.close()


class TestAaveV4ClientUnimplemented:
    """Stub methods raise NotImplementedError until full GraphQL wiring lands."""

    @pytest.mark.asyncio
    async def test_list_reserves_raises_until_wired(self) -> None:
        async with AaveV4Client("https://api.v4.aave.com/graphql") as client:
            with pytest.raises(NotImplementedError, match="reserves"):
                await client.list_reserves("0x0000000000000000000000000000000000000abc")

    @pytest.mark.asyncio
    async def test_get_user_health_raises_until_wired(self) -> None:
        async with AaveV4Client("https://api.v4.aave.com/graphql") as client:
            with pytest.raises(NotImplementedError, match="userPosition"):
                await client.get_user_health(
                    "0x0000000000000000000000000000000000000abc",
                    "0xdead0000000000000000000000000000000000ad",
                )

    @pytest.mark.asyncio
    async def test_quote_intent_path_propagates_not_implemented(self) -> None:
        async with AaveV4Client("https://api.v4.aave.com/graphql") as client:
            with pytest.raises(NotImplementedError):
                await quote_intent_path(
                    client,
                    intent_src="0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
                    intent_dst="0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
                    intent_src_amount=1_000_000,
                )
