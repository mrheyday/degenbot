"""Unit tests for MaverickV2Client + MaverickV2Pool (forward stub).

Forward stub — full integration lands in degenbot upstream PR per Q-5.
These tests cover the dataclass surface + lifecycle + stub-message
anchoring so that the post-PR rewire keeps the interface stable.
"""

from __future__ import annotations

import pytest
from degenbot.execution.maverick_v2_adapter import (
    MaverickV2Client,
    MaverickV2Pool,
)

_RPC_URL = "https://arb1.arbitrum.io/rpc"
_POOL_ADDR = "0x0000000000000000000000000000000000000abc"
_USDC = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
_WETH = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"


class TestMaverickV2Pool:
    def test_pool_holds_payload_unchanged(self) -> None:
        p = MaverickV2Pool(
            address=_POOL_ADDR,
            token0=_USDC,
            token1=_WETH,
            current_bin=42,
            sqrt_price_x96=79228162514264337593543950336,  # 1.0 in Q64.96
            fee_bps=30,
        )
        assert p.address == _POOL_ADDR
        assert p.current_bin == 42
        assert p.fee_bps == 30
        # sqrt_price_x96 must round-trip exactly (uint160 max is ~1.46e48)
        assert p.sqrt_price_x96 == 79228162514264337593543950336

    def test_pool_handles_negative_bin_index(self) -> None:
        # Maverick uses signed bin deltas — make sure dataclass doesn't reject.
        p = MaverickV2Pool(
            address=_POOL_ADDR,
            token0=_USDC,
            token1=_WETH,
            current_bin=-100,
            sqrt_price_x96=1,
            fee_bps=5,
        )
        assert p.current_bin == -100


class TestMaverickV2ClientLifecycle:
    async def test_async_context_manager_closes_httpx(self) -> None:
        async with MaverickV2Client(_RPC_URL) as client:
            assert client is not None

    async def test_close_is_idempotent(self) -> None:
        client = MaverickV2Client(_RPC_URL)
        await client.close()
        # second close should not raise
        await client.close()


class TestMaverickV2ClientUnimplemented:
    """Stub methods raise NotImplementedError until degenbot Q-5 PR lands."""

    async def test_list_pools_anchors_message_to_q5(self) -> None:
        async with MaverickV2Client(_RPC_URL) as client:
            with pytest.raises(NotImplementedError, match="Q-5"):
                await client.list_pools()

    async def test_get_pool_anchors_message_to_q5(self) -> None:
        async with MaverickV2Client(_RPC_URL) as client:
            with pytest.raises(NotImplementedError, match="Q-5"):
                await client.get_pool(_POOL_ADDR)

    async def test_simulate_swap_anchors_message_to_bin_shift(self) -> None:
        async with MaverickV2Client(_RPC_URL) as client:
            with pytest.raises(NotImplementedError, match="Bin-shift"):
                await client.simulate_swap(_POOL_ADDR, 1_000_000, zero_for_one=True)
