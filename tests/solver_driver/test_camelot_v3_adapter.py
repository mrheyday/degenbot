"""Unit tests for CamelotV3Pool (Algebra single-tick swap).

Full implementation supersedes the prior forward-stub test set. Covers
the degenbot pool-class interface contract (state, mutation, simulation)
plus the single-tick boundary that distinguishes Algebra from a generic
UniV3 simulation.
"""

from __future__ import annotations

import dataclasses

import pytest
from degenbot.execution.camelot_v3_adapter import (
    CamelotV3Pool,
    CamelotV3PoolState,
    MultiTickCrossingNotSupportedError,
)

# Seed WETH/USDC AMMv3 pool from
# `docs/research/camelot-v3-degenbot-adapter-design-2026-05-05.md` Q-5.
_POOL_ADDR = "0xB1026b8e7276e7AC75410F1fcbbe21796e8f7526"
_USDC = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
_WETH = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"

# Realistic Algebra globalState() at probe block 459756918 (rough WETH/USDC
# region around $3500). sqrt_price_x96 chosen for a $3500 quote.
_REALISTIC_SQRT_PRICE_X96 = 1_396_972_269_637_064_528_146_046_058_500_000_000
_REALISTIC_TICK = 196_257
_REALISTIC_LIQUIDITY = 1_500_000_000_000_000_000_000  # 1500 units in-range liquidity
_REALISTIC_FEE_PIPS = 500  # 0.05% (Algebra static-fee plugin)
_REALISTIC_TICK_SPACING = 60


def _make_pool(**overrides: object) -> CamelotV3Pool:
    """Construct a CamelotV3Pool with the realistic baseline; allow overrides."""
    defaults: dict[str, object] = {
        "address": _POOL_ADDR,
        "token0": _USDC,
        "token1": _WETH,
        "sqrt_price_x96": _REALISTIC_SQRT_PRICE_X96,
        "tick": _REALISTIC_TICK,
        "liquidity": _REALISTIC_LIQUIDITY,
        "fee_pips": _REALISTIC_FEE_PIPS,
        "tick_spacing": _REALISTIC_TICK_SPACING,
        "state_block": 459_756_918,
    }
    defaults.update(overrides)
    return CamelotV3Pool(**defaults)  # type: ignore[arg-type]


class TestCamelotV3PoolConstructor:
    def test_constructs_with_realistic_inputs(self) -> None:
        p = _make_pool()
        assert p.address.lower() == _POOL_ADDR.lower()
        assert p.token0.lower() == _USDC.lower()
        assert p.token1.lower() == _WETH.lower()
        assert p.tick_spacing == _REALISTIC_TICK_SPACING
        assert "CamelotV3Pool" in p.name
        assert "0.0500%" in p.name

    def test_state_is_a_frozen_dataclass(self) -> None:
        p = _make_pool()
        assert isinstance(p.state, CamelotV3PoolState)
        # `@dataclass(frozen=True)` raises FrozenInstanceError on field assignment.
        with pytest.raises(dataclasses.FrozenInstanceError):
            p.state.sqrt_price_x96 = 0  # type: ignore[misc]

    def test_state_cache_seeded_with_initial(self) -> None:
        p = _make_pool()
        assert len(p._state_cache) == 1
        assert p._state_cache[0] is p.state

    def test_rejects_invalid_sqrt_price(self) -> None:
        with pytest.raises(ValueError, match="sqrt_price_x96"):
            _make_pool(sqrt_price_x96=0)

    def test_rejects_negative_liquidity(self) -> None:
        with pytest.raises(ValueError, match="liquidity"):
            _make_pool(liquidity=-1)

    def test_rejects_out_of_range_fee_pips(self) -> None:
        with pytest.raises(ValueError, match="fee_pips"):
            _make_pool(fee_pips=1_000_000)
        with pytest.raises(ValueError, match="fee_pips"):
            _make_pool(fee_pips=-1)

    def test_rejects_non_positive_tick_spacing(self) -> None:
        with pytest.raises(ValueError, match="tick_spacing"):
            _make_pool(tick_spacing=0)


class TestCamelotV3PoolSimulation:
    def test_small_swap_within_tick_succeeds(self) -> None:
        # Small input that won't exhaust the current tick range.
        p = _make_pool()
        out = p.calculate_tokens_out_from_tokens_in(_USDC, 100_000_000)  # 100 USDC
        assert out > 0

    def test_rejects_zero_quantity(self) -> None:
        p = _make_pool()
        with pytest.raises(ValueError, match="must be positive"):
            p.calculate_tokens_out_from_tokens_in(_USDC, 0)

    def test_rejects_unknown_token(self) -> None:
        p = _make_pool()
        with pytest.raises(ValueError, match="matches neither"):
            p.calculate_tokens_out_from_tokens_in(
                "0x0000000000000000000000000000000000000001",
                1_000,
            )

    def test_zero_liquidity_raises(self) -> None:
        p = _make_pool(liquidity=0)
        with pytest.raises(ValueError, match="zero liquidity"):
            p.calculate_tokens_out_from_tokens_in(_USDC, 100_000_000)

    def test_huge_swap_raises_multi_tick(self) -> None:
        # Push enough input that the tick range exhausts.
        p = _make_pool()
        with pytest.raises(MultiTickCrossingNotSupportedError):
            p.calculate_tokens_out_from_tokens_in(
                _USDC,
                10**18,  # 1 trillion USDC — definitely crosses
            )

    def test_override_state_does_not_mutate_pool(self) -> None:
        p = _make_pool()
        override = CamelotV3PoolState(
            address=p.address,
            block=p.state.block,
            sqrt_price_x96=p.state.sqrt_price_x96,
            tick=p.state.tick,
            liquidity=p.state.liquidity * 2,
            fee_pips=p.state.fee_pips,
            tick_spacing=p.state.tick_spacing,
        )
        out_default = p.calculate_tokens_out_from_tokens_in(_USDC, 100_000_000)
        out_override = p.calculate_tokens_out_from_tokens_in(
            _USDC,
            100_000_000,
            override_state=override,
        )
        # Higher liquidity ⇒ lower price impact ⇒ at least as much out.
        assert out_override >= out_default
        # State unchanged.
        assert p.state.liquidity == _REALISTIC_LIQUIDITY


class TestCamelotV3PoolUpdate:
    def test_update_state_advances_cache(self) -> None:
        p = _make_pool()
        starting_block = p.state.block
        assert starting_block is not None
        new_state = p.update_state(
            sqrt_price_x96=p.state.sqrt_price_x96 + 1,
            tick=p.state.tick,
            liquidity=p.state.liquidity,
            block=starting_block + 1,
        )
        assert p.state == new_state
        assert len(p._state_cache) == 2

    def test_same_block_replays_replace_head(self) -> None:
        p = _make_pool()
        block = p.state.block
        assert block is not None
        p.update_state(
            sqrt_price_x96=p.state.sqrt_price_x96 + 1,
            tick=p.state.tick,
            liquidity=p.state.liquidity,
            block=block,
        )
        # Cache still only has one entry (dedup'd).
        assert len(p._state_cache) == 1

    def test_past_block_update_rejected(self) -> None:
        p = _make_pool()
        with pytest.raises(ValueError, match="predates"):
            p.update_state(
                sqrt_price_x96=p.state.sqrt_price_x96,
                tick=p.state.tick,
                liquidity=p.state.liquidity,
                block=(p.state.block or 0) - 1,
            )
