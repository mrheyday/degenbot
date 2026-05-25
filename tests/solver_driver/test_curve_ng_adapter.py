"""Unit tests for CurveNGPool (Curve new-gen StableSwap).

Covers the degenbot pool-class interface + canonical Curve V1 StableSwap
behaviour on a 2-token NG pool (the most common shape). Math is the
self-contained `_curve_ng_get_d` + `_curve_ng_get_y` solver; tests
exercise inputs, not the math itself (Curve's reference Brownie tests
own correctness).
"""

from __future__ import annotations

import pytest
from degenbot.execution.curve_ng_adapter import CurveNGPool, CurveNGPoolState

_USDC = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
_USDT = "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9"
_POOL = "0x0000000000000000000000000000000000000099"


def _make_pool(**overrides: object) -> CurveNGPool:
    """Realistic USDC/USDT Curve NG pool — both 6 decimals."""
    defaults: dict[str, object] = {
        "address": _POOL,
        "token0": _USDC,
        "token1": _USDT,
        "balances": (10_000_000_000_000, 10_000_000_000_000),  # 10M each
        # 6-decimal tokens need a 10^30 rate (10^18 multiplied by 10^12) to normalise to 18-dec
        # for the StableSwap solver — this is the Curve NG `stored_rates()` form.
        "rates": (10**30, 10**30),
        "amp": 200,
        "fee_bps": 4_000_000,  # 0.04%
        "state_block": 1_000,
    }
    defaults.update(overrides)
    return CurveNGPool(**defaults)  # type: ignore[arg-type]


class TestCurveNGPoolConstructor:
    def test_constructs_with_realistic_inputs(self) -> None:
        p = _make_pool()
        assert p.address.lower() == _POOL.lower()
        assert isinstance(p.state, CurveNGPoolState)
        assert "CurveNGPool" in p.name
        assert "A=200" in p.name

    def test_state_cache_seeded(self) -> None:
        p = _make_pool()
        assert len(p._state_cache) == 1

    def test_rejects_negative_balance(self) -> None:
        with pytest.raises(ValueError, match="balances"):
            _make_pool(balances=(-1, 10_000_000_000_000))

    def test_rejects_zero_rate(self) -> None:
        with pytest.raises(ValueError, match="rates"):
            _make_pool(rates=(0, 10**30))

    def test_rejects_non_positive_amp(self) -> None:
        with pytest.raises(ValueError, match="amp"):
            _make_pool(amp=0)

    def test_rejects_out_of_range_fee_bps(self) -> None:
        with pytest.raises(ValueError, match="fee_bps"):
            _make_pool(fee_bps=10**10)
        with pytest.raises(ValueError, match="fee_bps"):
            _make_pool(fee_bps=-1)


class TestCurveNGPoolSimulation:
    def test_stable_swap_near_parity(self) -> None:
        # USDC ↔ USDT at 1:1 ratio. 1000 USDC in should yield ~1000 USDT
        # (less ~0.04% fee + tiny curve drift on a balanced pool).
        p = _make_pool()
        amount_in = 1_000_000_000  # 1000 USDC (6 decimals)
        out = p.calculate_tokens_out_from_tokens_in(_USDC, amount_in)
        # Expect ~999.6 USDT (1000 minus 0.04% fee = 0.4 USDT).
        assert 999_000_000 <= out <= 1_000_000_000

    def test_rejects_zero_quantity(self) -> None:
        p = _make_pool()
        with pytest.raises(ValueError, match="must be positive"):
            p.calculate_tokens_out_from_tokens_in(_USDC, 0)

    def test_rejects_unknown_token(self) -> None:
        p = _make_pool()
        with pytest.raises(ValueError, match="matches neither"):
            p.calculate_tokens_out_from_tokens_in(
                "0x0000000000000000000000000000000000000001",
                1_000_000,
            )

    def test_both_directions_work(self) -> None:
        p = _make_pool()
        out0 = p.calculate_tokens_out_from_tokens_in(_USDC, 1_000_000_000)
        out1 = p.calculate_tokens_out_from_tokens_in(_USDT, 1_000_000_000)
        # Balanced pool — outputs should be symmetric to within rounding.
        assert abs(out0 - out1) <= 10  # ≤ 10 micro-units of drift

    def test_override_state_does_not_mutate_pool(self) -> None:
        p = _make_pool()
        override = CurveNGPoolState(
            address=p.address,
            block=p.state.block,
            balances=(p.state.balances[0] * 10, p.state.balances[1] * 10),
            rates=p.state.rates,
            amp=p.state.amp,
            fee_bps=p.state.fee_bps,
        )
        out_default = p.calculate_tokens_out_from_tokens_in(_USDC, 1_000_000_000)
        out_override = p.calculate_tokens_out_from_tokens_in(
            _USDC,
            1_000_000_000,
            override_state=override,
        )
        # 10x deeper pool ⇒ less slippage ⇒ at least as much out.
        assert out_override >= out_default
        # State unchanged.
        assert p.state.balances == (10_000_000_000_000, 10_000_000_000_000)


class TestCurveNGPoolUpdate:
    def test_update_state_advances_cache(self) -> None:
        p = _make_pool()
        block = p.state.block
        assert block is not None
        new_state = p.update_state(
            balances=(p.state.balances[0] + 1, p.state.balances[1]),
            block=block + 1,
        )
        assert p.state == new_state
        assert len(p._state_cache) == 2

    def test_carry_forward_amp_and_fee(self) -> None:
        p = _make_pool()
        block = p.state.block
        assert block is not None
        new_state = p.update_state(
            balances=(p.state.balances[0] + 1, p.state.balances[1]),
            block=block + 1,
        )
        assert new_state.amp == 200
        assert new_state.fee_bps == 4_000_000

    def test_explicit_amp_update_applies(self) -> None:
        p = _make_pool()
        block = p.state.block
        assert block is not None
        new_state = p.update_state(
            balances=p.state.balances,
            amp=400,
            block=block + 1,
        )
        assert new_state.amp == 400

    def test_past_block_update_rejected(self) -> None:
        p = _make_pool()
        with pytest.raises(ValueError, match="predates"):
            p.update_state(
                balances=p.state.balances,
                block=(p.state.block or 0) - 1,
            )
