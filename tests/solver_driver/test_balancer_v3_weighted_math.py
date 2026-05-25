"""Tests for the Python port of Balancer V3's WeightedMath.

Reference values are computed via `math.pow` and rounded to 18-decimal
fixed point, then compared against the integer-only port at rel-tol=1e-12
(matches the Taylor-series precision target inherited from LogExpMath).

Round-trip tests confirm `compute_in_given_exact_out` and
`compute_out_given_exact_in` are mutually consistent within fudge tolerance.
"""

from __future__ import annotations

import math

import pytest
from degenbot.execution import balancer_v3_weighted_math as wm
from degenbot.execution.balancer_fixed_point import ONE

_REL_TOL = 1e-12


def _to_fp(x: float) -> int:
    return round(x * 1e18)


def _from_fp(x: int) -> float:
    return x / 1e18


# ---------------------------------------------------------------------------
# Invariant
# ---------------------------------------------------------------------------


class TestInvariant:
    def test_50_50_pool_invariant_matches_geometric_mean(self) -> None:
        # 50/50 pool with balances [100, 200]:
        # I = 100^0.5 * 200^0.5 = sqrt(100 * 200) ≈ 141.42135623730951
        balances = (100 * ONE, 200 * ONE)
        weights = (ONE // 2, ONE // 2)
        result = wm.compute_invariant_down(weights, balances)
        expected = math.sqrt(100 * 200)
        assert _from_fp(result) == pytest.approx(expected, rel=_REL_TOL)

    def test_80_20_pool_invariant(self) -> None:
        # 80/20 pool with balances [1000, 100]:
        # I = 1000^0.8 * 100^0.2 ≈ 251.1886431509...
        balances = (1000 * ONE, 100 * ONE)
        weights = (8 * ONE // 10, 2 * ONE // 10)
        result = wm.compute_invariant_down(weights, balances)
        expected = (1000**0.8) * (100**0.2)
        assert _from_fp(result) == pytest.approx(expected, rel=_REL_TOL)

    def test_three_token_invariant(self) -> None:
        # 33/33/34 pool with balances [100, 200, 300]
        balances = (100 * ONE, 200 * ONE, 300 * ONE)
        weights = (333_333_333_333_333_333, 333_333_333_333_333_333, 333_333_333_333_333_334)
        result = wm.compute_invariant_down(weights, balances)
        expected = (
            math.pow(100, 0.333_333_333_333_333_333)
            * math.pow(
                200,
                0.333_333_333_333_333_333,
            )
            * math.pow(300, 0.333_333_333_333_333_334)
        )
        assert _from_fp(result) == pytest.approx(expected, rel=_REL_TOL)

    def test_invariant_up_geq_invariant_down(self) -> None:
        # Up rounding should be ≥ down rounding for the same inputs.
        balances = (1000 * ONE, 100 * ONE)
        weights = (8 * ONE // 10, 2 * ONE // 10)
        down = wm.compute_invariant_down(weights, balances)
        up = wm.compute_invariant_up(weights, balances)
        assert up >= down

    def test_zero_balance_raises(self) -> None:
        balances = (0, 100 * ONE)
        weights = (ONE // 2, ONE // 2)
        with pytest.raises(wm.ZeroInvariantError):
            wm.compute_invariant_down(weights, balances)

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="length mismatch"):
            wm.compute_invariant_down((ONE,), (100 * ONE, 200 * ONE))

    def test_empty_inputs_raise(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            wm.compute_invariant_down((), ())


# ---------------------------------------------------------------------------
# ExactIn swap (the hot path)
# ---------------------------------------------------------------------------


class TestComputeOutGivenExactIn:
    def test_50_50_swap_matches_constant_product(self) -> None:
        # For a 50/50 pool, the weighted formula reduces to constant product
        # x*y=k. Balances 100/100, swap 10 in → out = 100 - 100*100/(100+10)
        # = 100 - 9090.909.../1000 ... wait, let's redo.
        # k = 100 * 100 = 10_000.
        # newBalanceOut = k / (100 + 10) = 10000/110 = 90.909090909...
        # amountOut = 100 - 90.909... = 9.0909...
        b_in = 100 * ONE
        b_out = 100 * ONE
        w = ONE // 2
        amt_in = 10 * ONE
        result = wm.compute_out_given_exact_in(b_in, w, b_out, w, amt_in)
        expected = 100 - (100 * 100 / (100 + 10))
        # FixedPoint pow rounding adds ~1e-14 error; loosen tol slightly.
        assert _from_fp(result) == pytest.approx(expected, rel=1e-10)

    def test_80_20_swap(self) -> None:
        # 80/20 pool: ETH-heavy side. Real-world Balancer use case.
        # balance_in = 1000 (high-weight 0.8), balance_out = 100 (low-weight 0.2)
        # amountIn = 50
        # amountOut = 100 * (1 - (1000/(1000+50))^(0.8/0.2))
        #           = 100 * (1 - (1000/1050)^4)
        b_in = 1000 * ONE
        b_out = 100 * ONE
        w_in = 8 * ONE // 10
        w_out = 2 * ONE // 10
        amt_in = 50 * ONE
        result = wm.compute_out_given_exact_in(b_in, w_in, b_out, w_out, amt_in)
        expected = 100 * (1 - (1000 / (1000 + 50)) ** (0.8 / 0.2))
        assert _from_fp(result) == pytest.approx(expected, rel=1e-10)

    def test_max_in_ratio_enforced(self) -> None:
        # MAX_IN_RATIO is 30% of balance_in.
        b_in = 100 * ONE
        b_out = 100 * ONE
        w = ONE // 2
        amt_in = 31 * ONE  # 31% — should revert
        with pytest.raises(wm.MaxInRatioError):
            wm.compute_out_given_exact_in(b_in, w, b_out, w, amt_in)

    def test_at_max_in_ratio_succeeds(self) -> None:
        # Exactly 30% should be accepted.
        b_in = 100 * ONE
        b_out = 100 * ONE
        w = ONE // 2
        amt_in = 30 * ONE
        # Should not raise.
        result = wm.compute_out_given_exact_in(b_in, w, b_out, w, amt_in)
        assert result > 0


class TestComputeInGivenExactOut:
    def test_50_50_swap_round_trip(self) -> None:
        # For a 50/50 pool, swap 10 in → x out, then x out → ~10 in
        # (modulo rounding fudge).
        b_in = 100 * ONE
        b_out = 100 * ONE
        w = ONE // 2
        amt_in = 10 * ONE
        amt_out = wm.compute_out_given_exact_in(b_in, w, b_out, w, amt_in)
        amt_in_recomputed = wm.compute_in_given_exact_out(b_in, w, b_out, w, amt_out)
        # Round trip should be close to the original. mul_up + power-up
        # rounding can drift by a few wei but not materially.
        assert _from_fp(amt_in_recomputed) == pytest.approx(_from_fp(amt_in), rel=1e-10)

    def test_max_out_ratio_enforced(self) -> None:
        b_in = 100 * ONE
        b_out = 100 * ONE
        w = ONE // 2
        amt_out = 31 * ONE  # > 30%
        with pytest.raises(wm.MaxOutRatioError):
            wm.compute_in_given_exact_out(b_in, w, b_out, w, amt_out)


# ---------------------------------------------------------------------------
# Inverse invariant
# ---------------------------------------------------------------------------


class TestComputeBalanceOutGivenInvariant:
    def test_invariant_ratio_one_returns_current_balance(self) -> None:
        # If invariant_ratio = 1.0, the balance is unchanged.
        # (Modulo rounding-up of 1^x = 1 path.)
        result = wm.compute_balance_out_given_invariant(100 * ONE, ONE // 2, ONE)
        assert _from_fp(result) == pytest.approx(100.0, rel=1e-15)

    def test_invariant_ratio_above_one_grows_balance(self) -> None:
        # invariant_ratio = 1.5 with weight = 0.5 → balance_ratio = 1.5^2 = 2.25
        # new_balance = 100 * 2.25 = 225
        result = wm.compute_balance_out_given_invariant(
            100 * ONE,
            ONE // 2,
            3 * ONE // 2,
        )
        assert _from_fp(result) == pytest.approx(225.0, rel=1e-10)

    def test_invariant_ratio_below_one_shrinks_balance(self) -> None:
        # invariant_ratio = 0.8 with weight = 0.5 → balance_ratio = 0.8^2 = 0.64
        # new_balance = 100 * 0.64 = 64
        result = wm.compute_balance_out_given_invariant(
            100 * ONE,
            ONE // 2,
            8 * ONE // 10,
        )
        assert _from_fp(result) == pytest.approx(64.0, rel=1e-10)
