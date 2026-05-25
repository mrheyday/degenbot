"""Unit tests for BalancerV3Client + BalancerV3Pool (forward stub).

Forward stub — full integration lands in degenbot upstream PR per Q-6.
These tests cover the dataclass surface + lifecycle + stub-message
anchoring so that the post-PR rewire keeps the interface stable.
"""

from __future__ import annotations

import pytest
from degenbot.execution.balancer_v3_adapter import (
    BalancerV3Client,
    BalancerV3Pool,
    BalancerV3PoolType,
    simulate_weighted_swap_from_snapshot,
)

_RPC_URL = "https://arb1.arbitrum.io/rpc"
_POOL_ADDR = "0x0000000000000000000000000000000000000abc"
_VAULT = "0xbA1333333333a1BA1108E8412f11850A5C319bA9"
_USDC = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
_WETH = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"


class TestBalancerV3Pool:
    def test_pool_holds_payload_unchanged(self) -> None:
        p = BalancerV3Pool(
            address=_POOL_ADDR,
            block=297810187,  # design doc: Arbitrum V3 Vault fromBlock
            vault=_VAULT,
            pool_type=BalancerV3PoolType.WEIGHTED,
            tokens=(_USDC, _WETH),
            balances_raw=(1_000_000_000_000, 250_000_000_000_000_000_000),
            scaling_factors=(10**12, 1),
            static_swap_fee_bps=30,
            aggregate_swap_fee_bps=27,
        )
        assert p.address == _POOL_ADDR
        assert p.vault == _VAULT
        assert p.pool_type is BalancerV3PoolType.WEIGHTED
        assert p.tokens == (_USDC, _WETH)
        # balance values must round-trip exactly (uint256 precision)
        assert p.balances_raw[1] == 250_000_000_000_000_000_000
        assert p.static_swap_fee_bps == 30
        # aggregate fee may diverge from static under dynamic-fee hooks
        assert p.aggregate_swap_fee_bps == 27

    def test_pool_supports_stable_pool_type(self) -> None:
        p = BalancerV3Pool(
            address=_POOL_ADDR,
            block=297810187,
            vault=_VAULT,
            pool_type=BalancerV3PoolType.STABLE,
            tokens=(_USDC, _WETH),
            balances_raw=(0, 0),
            scaling_factors=(1, 1),
            static_swap_fee_bps=1,
            aggregate_swap_fee_bps=1,
        )
        assert p.pool_type is BalancerV3PoolType.STABLE

    def test_pool_handles_three_token_pool_shape(self) -> None:
        # Balancer Weighted/Stable pools support n-asset pools; tuples of
        # different lengths must round-trip without coercion.
        p = BalancerV3Pool(
            address=_POOL_ADDR,
            block=297810187,
            vault=_VAULT,
            pool_type=BalancerV3PoolType.WEIGHTED,
            tokens=(_USDC, _WETH, "0x912CE59144191C1204E64559FE8253a0e49E6548"),
            balances_raw=(1, 2, 3),
            scaling_factors=(1, 1, 1),
            static_swap_fee_bps=10,
            aggregate_swap_fee_bps=10,
        )
        assert len(p.tokens) == 3
        assert len(p.balances_raw) == 3


class TestBalancerV3ClientLifecycle:
    async def test_async_context_manager_closes_httpx(self) -> None:
        async with BalancerV3Client(_RPC_URL) as client:
            assert client is not None

    async def test_close_is_idempotent(self) -> None:
        client = BalancerV3Client(_RPC_URL)
        await client.close()
        # second close should not raise
        await client.close()


class TestBalancerV3ClientUnimplemented:
    """Stub methods raise NotImplementedError until degenbot Q-6 PR lands."""

    async def test_list_pools_anchors_message_to_q6(self) -> None:
        async with BalancerV3Client(_RPC_URL) as client:
            with pytest.raises(NotImplementedError, match="Q-6"):
                await client.list_pools()

    async def test_get_pool_anchors_message_to_q6(self) -> None:
        async with BalancerV3Client(_RPC_URL) as client:
            with pytest.raises(NotImplementedError, match="Q-6"):
                await client.get_pool(_POOL_ADDR)

    async def test_simulate_swap_propagates_get_pool_not_implemented(self) -> None:
        # simulate_swap now delegates get_pool → swap-math; the NotImplementedError
        # comes from the underlying get_pool stub until that's wired.
        async with BalancerV3Client(_RPC_URL) as client:
            with pytest.raises(NotImplementedError, match="Q-6"):
                await client.simulate_swap(_POOL_ADDR, 1_000_000, zero_for_one=True)


# ---------------------------------------------------------------------------
# Pure-math swap simulation (no RPC) — exercises the WeightedMath wiring
# ---------------------------------------------------------------------------


class TestSimulateWeightedSwapFromSnapshot:
    @staticmethod
    def _make_50_50_pool() -> BalancerV3Pool:
        # Standard 50/50 USDC-WETH-style WEIGHTED pool with 100/100 balances.
        return BalancerV3Pool(
            address=_POOL_ADDR,
            block=297810187,
            vault=_VAULT,
            pool_type=BalancerV3PoolType.WEIGHTED,
            tokens=(_USDC, _WETH),
            balances_raw=(100 * 10**18, 100 * 10**18),
            scaling_factors=(1, 1),
            static_swap_fee_bps=0,  # zero fee for clean math
            aggregate_swap_fee_bps=0,
            normalized_weights=(5 * 10**17, 5 * 10**17),  # 0.5 / 0.5
        )

    def test_50_50_zero_fee_swap_matches_constant_product(self) -> None:
        pool = self._make_50_50_pool()
        amt_in = 10 * 10**18  # 10 tokens in
        result = simulate_weighted_swap_from_snapshot(
            pool,
            token_in_index=0,
            token_out_index=1,
            amount_in=amt_in,
        )
        # 50/50 pool reduces to x*y=k. amountOut ≈ 100 - 10000/110 ≈ 9.0909...
        expected = 100 - (100 * 100 / 110)
        assert result / 1e18 == pytest.approx(expected, rel=1e-10)

    def test_static_swap_fee_reduces_amount_out(self) -> None:
        pool_zero_fee = self._make_50_50_pool()
        # Same pool with 30 bps fee.
        pool_with_fee = BalancerV3Pool(
            address=pool_zero_fee.address,
            block=pool_zero_fee.block,
            vault=pool_zero_fee.vault,
            pool_type=pool_zero_fee.pool_type,
            tokens=pool_zero_fee.tokens,
            balances_raw=pool_zero_fee.balances_raw,
            scaling_factors=pool_zero_fee.scaling_factors,
            static_swap_fee_bps=30,
            aggregate_swap_fee_bps=30,
            normalized_weights=pool_zero_fee.normalized_weights,
        )
        amt_in = 10 * 10**18
        out_no_fee = simulate_weighted_swap_from_snapshot(
            pool_zero_fee,
            0,
            1,
            amt_in,
        )
        out_with_fee = simulate_weighted_swap_from_snapshot(
            pool_with_fee,
            0,
            1,
            amt_in,
        )
        # Fee reduces effective amount_in → smaller amount_out.
        assert out_with_fee < out_no_fee

    def test_stable_pool_raises(self) -> None:
        # Build a STABLE pool — math helper must reject.
        pool = BalancerV3Pool(
            address=_POOL_ADDR,
            block=297810187,
            vault=_VAULT,
            pool_type=BalancerV3PoolType.STABLE,
            tokens=(_USDC, _WETH),
            balances_raw=(100 * 10**18, 100 * 10**18),
            scaling_factors=(1, 1),
            static_swap_fee_bps=0,
            aggregate_swap_fee_bps=0,
        )
        with pytest.raises(ValueError, match="WEIGHTED"):
            simulate_weighted_swap_from_snapshot(pool, 0, 1, 10**18)

    def test_missing_weights_raises(self) -> None:
        # WEIGHTED pool with normalized_weights=None — must reject.
        pool = BalancerV3Pool(
            address=_POOL_ADDR,
            block=297810187,
            vault=_VAULT,
            pool_type=BalancerV3PoolType.WEIGHTED,
            tokens=(_USDC, _WETH),
            balances_raw=(100 * 10**18, 100 * 10**18),
            scaling_factors=(1, 1),
            static_swap_fee_bps=0,
            aggregate_swap_fee_bps=0,
            # normalized_weights left at default None
        )
        with pytest.raises(ValueError, match="normalized_weights"):
            simulate_weighted_swap_from_snapshot(pool, 0, 1, 10**18)

    def test_same_index_raises(self) -> None:
        pool = self._make_50_50_pool()
        with pytest.raises(ValueError, match="differ"):
            simulate_weighted_swap_from_snapshot(pool, 0, 0, 10**18)

    def test_out_of_range_index_raises(self) -> None:
        pool = self._make_50_50_pool()
        with pytest.raises(ValueError, match="out of range"):
            simulate_weighted_swap_from_snapshot(pool, 0, 5, 10**18)
