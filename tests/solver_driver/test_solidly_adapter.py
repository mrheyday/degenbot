"""Unit tests for SolidlyV1Pool (Ramses / Chronos / Solidlizard).

Covers the degenbot pool-class interface contract + both Solidly
families (volatile = x·y=k, stable = y·x³+x·y³≥k). Math primitives
are degenbot's `solidly_functions` — the tests verify our adapter
correctly routes inputs into them, not the math correctness itself
(degenbot's own test suite locks the math).
"""

from __future__ import annotations

from fractions import Fraction

import pytest
from degenbot.execution.solidly_adapter import SolidlyV1Pool, SolidlyV1PoolState

# Test tokens — checksum addresses required by ChecksumAddress validation.
_USDC = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
_WETH = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"
_USDT = "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9"
_POOL = "0x0000000000000000000000000000000000000099"


def _make_volatile_pool(**overrides: object) -> SolidlyV1Pool:
    """Realistic Ramses USDC/WETH volatile pool."""
    defaults: dict[str, object] = {
        "address": _POOL,
        "token0": _USDC,
        "token1": _WETH,
        # USDC has 6 decimals; WETH has 18. Use ~$3500 price ratio:
        # 3.5M USDC ↔ 1000 WETH ⇒ 1 WETH ≈ 3500 USDC.
        "reserves_token0": 3_500_000_000_000,  # 3.5M USDC (6 decimals)
        "reserves_token1": 1_000 * 10**18,  # 1000 WETH
        "decimals_token0": 10**6,
        "decimals_token1": 10**18,
        "fee": Fraction(1, 10_000),  # 1 bp (Ramses-default volatile)
        "stable": False,
        "state_block": 1_000,
    }
    defaults.update(overrides)
    return SolidlyV1Pool(**defaults)  # type: ignore[arg-type]


def _make_stable_pool(**overrides: object) -> SolidlyV1Pool:
    """Realistic Ramses USDC/USDT stable pool — both 6-decimal."""
    defaults: dict[str, object] = {
        "address": _POOL,
        "token0": _USDC,
        "token1": _USDT,
        "reserves_token0": 10_000_000_000_000,  # 10M USDC
        "reserves_token1": 10_000_000_000_000,  # 10M USDT
        "decimals_token0": 10**6,
        "decimals_token1": 10**6,
        "fee": Fraction(5, 100_000),  # 0.5 bp (Ramses-default stable)
        "stable": True,
        "state_block": 1_000,
    }
    defaults.update(overrides)
    return SolidlyV1Pool(**defaults)  # type: ignore[arg-type]


class TestSolidlyV1PoolConstructor:
    def test_constructs_volatile(self) -> None:
        p = _make_volatile_pool()
        assert p.address.lower() == _POOL.lower()
        assert not p.stable
        assert "volatile" in p.name
        assert isinstance(p.state, SolidlyV1PoolState)

    def test_constructs_stable(self) -> None:
        p = _make_stable_pool()
        assert p.stable
        assert "stable" in p.name

    def test_rejects_negative_reserves(self) -> None:
        with pytest.raises(ValueError, match="reserves"):
            _make_volatile_pool(reserves_token0=-1)

    def test_rejects_non_positive_decimals(self) -> None:
        with pytest.raises(ValueError, match="decimals"):
            _make_volatile_pool(decimals_token0=0)

    def test_rejects_out_of_range_fee(self) -> None:
        with pytest.raises(ValueError, match="fee"):
            _make_volatile_pool(fee=Fraction(2, 1))


class TestSolidlyV1PoolVolatileSwap:
    def test_xy_invariant_holds_within_rounding(self) -> None:
        # UniV2-style x·y=k: small input, output should roughly preserve k.
        p = _make_volatile_pool()
        amount_in = 1_000_000_000  # 1000 USDC
        out = p.calculate_tokens_out_from_tokens_in(_USDC, amount_in)
        assert out > 0
        # Output WETH for 1000 USDC at ~3500 USDC/WETH should be ~0.285 WETH.
        # With 1bp fee + slippage, expect 0.27..0.286.
        assert 270_000_000_000_000_000 <= out <= 286_000_000_000_000_000

    def test_rejects_zero_quantity(self) -> None:
        p = _make_volatile_pool()
        with pytest.raises(ValueError, match="must be positive"):
            p.calculate_tokens_out_from_tokens_in(_USDC, 0)

    def test_rejects_unknown_token(self) -> None:
        p = _make_volatile_pool()
        with pytest.raises(ValueError, match="matches neither"):
            p.calculate_tokens_out_from_tokens_in(
                "0x0000000000000000000000000000000000000001",
                1_000_000,
            )

    def test_both_directions_work(self) -> None:
        p = _make_volatile_pool()
        # USDC → WETH
        out0 = p.calculate_tokens_out_from_tokens_in(_USDC, 1_000_000_000)
        # WETH → USDC
        out1 = p.calculate_tokens_out_from_tokens_in(_WETH, 10**18)
        assert out0 > 0
        assert out1 > 0


class TestSolidlyV1PoolStableSwap:
    def test_stable_swap_near_parity(self) -> None:
        # USDC ↔ USDT stable pool at 1:1 ratio. 1000 USDC in should
        # yield ~1000 USDT out (less the 0.5bp fee + minor curve drift).
        p = _make_stable_pool()
        amount_in = 1_000_000_000  # 1000 USDC
        out = p.calculate_tokens_out_from_tokens_in(_USDC, amount_in)
        # Expect ~999.95 USDT (1000 minus 0.5bp = 0.05 USDT).
        assert 999_000_000 <= out <= 1_000_000_000

    def test_override_state_does_not_mutate_pool(self) -> None:
        p = _make_stable_pool()
        override = SolidlyV1PoolState(
            address=p.address,
            block=p.state.block,
            reserves_token0=p.state.reserves_token0 * 2,
            reserves_token1=p.state.reserves_token1 * 2,
        )
        out_default = p.calculate_tokens_out_from_tokens_in(_USDC, 1_000_000_000)
        out_override = p.calculate_tokens_out_from_tokens_in(
            _USDC,
            1_000_000_000,
            override_state=override,
        )
        assert out_override >= out_default
        # State unchanged.
        assert p.state.reserves_token0 == 10_000_000_000_000


class TestSolidlyV1PoolUpdate:
    def test_update_state_advances_cache(self) -> None:
        p = _make_volatile_pool()
        block = p.state.block
        assert block is not None
        new_state = p.update_state(
            reserves_token0=p.state.reserves_token0 + 1,
            reserves_token1=p.state.reserves_token1,
            block=block + 1,
        )
        assert p.state == new_state
        assert len(p._state_cache) == 2

    def test_past_block_update_rejected(self) -> None:
        p = _make_volatile_pool()
        with pytest.raises(ValueError, match="predates"):
            p.update_state(
                reserves_token0=p.state.reserves_token0,
                reserves_token1=p.state.reserves_token1,
                block=(p.state.block or 0) - 1,
            )
