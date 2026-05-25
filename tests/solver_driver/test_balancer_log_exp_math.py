"""Tests for the Python port of Balancer V3's LogExpMath.

Reference values are computed via Python's `math.exp/log` and rounded to
18-decimal fixed point, then compared against our integer-only port with
a generous tolerance (1e-12 relative) to absorb the residual error from
the truncated Taylor series + lossy fixed-point divisions.

This is sufficient for the math-port acceptance test; a tighter
cross-check against the on-chain Solidity values lands when we wire fork
fixtures.
"""

from __future__ import annotations

import math

import pytest
from degenbot.execution import balancer_log_exp_math as lem
from degenbot.execution.balancer_log_exp_math import ONE_18

# Relative tolerance for cross-check against `math.exp/log`. The on-chain
# Taylor series targets ~18-decimal precision so 1e-12 is comfortable.
_REL_TOL = 1e-12


def _to_fp(x: float) -> int:
    """Convert a float to 18-decimal fixed point."""
    return round(x * 1e18)


def _from_fp(x: int) -> float:
    """Convert 18-decimal FP back to float for assertion."""
    return x / 1e18


# ---------------------------------------------------------------------------
# exp
# ---------------------------------------------------------------------------


class TestExp:
    @pytest.mark.parametrize("x", [0.0, 0.5, 1.0, 2.0, 5.0, 10.0, 50.0, 100.0])
    def test_positive_argument_matches_math_exp(self, x: float) -> None:
        result = lem.exp(_to_fp(x))
        expected = math.exp(x)
        assert _from_fp(result) == pytest.approx(expected, rel=_REL_TOL)

    @pytest.mark.parametrize("x", [-0.5, -1.0, -5.0, -20.0, -40.0])
    def test_negative_argument_matches_math_exp(self, x: float) -> None:
        result = lem.exp(_to_fp(x))
        expected = math.exp(x)
        assert _from_fp(result) == pytest.approx(expected, rel=_REL_TOL)

    def test_exp_zero_is_one(self) -> None:
        assert lem.exp(0) == ONE_18

    def test_above_max_raises(self) -> None:
        with pytest.raises(OverflowError):
            lem.exp(lem.MAX_NATURAL_EXPONENT + 1)

    def test_below_min_raises(self) -> None:
        with pytest.raises(OverflowError):
            lem.exp(lem.MIN_NATURAL_EXPONENT - 1)


# ---------------------------------------------------------------------------
# ln
# ---------------------------------------------------------------------------


class TestLn:
    @pytest.mark.parametrize("a", [0.5, 0.99, 1.0, 1.01, 2.0, math.e, 10.0, 100.0, 1e6])
    def test_matches_math_log(self, a: float) -> None:
        result = lem.ln(_to_fp(a))
        expected = math.log(a)
        # Log of 1 is exactly 0; absolute tolerance is what matters there.
        if abs(expected) < 1e-9:
            assert abs(_from_fp(result)) < 1e-15
        else:
            assert _from_fp(result) == pytest.approx(expected, rel=_REL_TOL)

    def test_ln_one_is_zero(self) -> None:
        assert lem.ln(ONE_18) == 0

    def test_ln_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="domain"):
            lem.ln(0)

    def test_ln_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="domain"):
            lem.ln(-1)

    def test_ln_close_to_one_uses_high_precision_path(self) -> None:
        # Just below LN_36_UPPER_BOUND — exercises the _ln_36 branch.
        a = ONE_18 + 5 * 10**16  # 1.05
        result = lem.ln(a)
        expected = math.log(1.05)
        assert _from_fp(result) == pytest.approx(expected, rel=_REL_TOL)


# ---------------------------------------------------------------------------
# pow
# ---------------------------------------------------------------------------


class TestPow:
    def test_zero_to_zero_is_one(self) -> None:
        # Solidity convention: 0^0 = 1.
        assert lem.pow(0, 0) == ONE_18

    def test_zero_to_positive_is_zero(self) -> None:
        assert lem.pow(0, 5 * ONE_18) == 0

    def test_x_to_zero_is_one(self) -> None:
        assert lem.pow(5 * ONE_18, 0) == ONE_18

    @pytest.mark.parametrize(
        ("x", "y"),
        [
            (2.0, 0.5),  # sqrt(2)
            (4.0, 0.5),  # = 2
            (2.0, 0.8),  # 80/20 weighted-pool exponent
            (3.0, 1.5),
            (1.5, 2.5),
            (10.0, 0.3),
        ],
    )
    def test_matches_math_pow(self, x: float, y: float) -> None:
        result = lem.pow(_to_fp(x), _to_fp(y))
        expected = math.pow(x, y)
        assert _from_fp(result) == pytest.approx(expected, rel=_REL_TOL)

    def test_50_50_weighted_invariant_factor(self) -> None:
        # x^0.5 — the canonical 50/50 Weighted Pool exponent.
        # 4^0.5 = 2.0
        result = lem.pow(4 * ONE_18, ONE_18 // 2)
        assert _from_fp(result) == pytest.approx(2.0, rel=_REL_TOL)

    def test_80_20_weighted_invariant_factor(self) -> None:
        # x^0.8 / x^0.2 — exponents used in 80/20 pools.
        # 100^0.2 ≈ 2.51188643150958
        result = lem.pow(100 * ONE_18, 2 * ONE_18 // 10)
        assert _from_fp(result) == pytest.approx(math.pow(100, 0.2), rel=_REL_TOL)


# ---------------------------------------------------------------------------
# log (base change)
# ---------------------------------------------------------------------------


class TestLog:
    def test_log10_of_100_is_2(self) -> None:
        # log_10(100) = 2
        result = lem.log(100 * ONE_18, 10 * ONE_18)
        assert _from_fp(result) == pytest.approx(2.0, rel=_REL_TOL)

    def test_log2_of_8_is_3(self) -> None:
        result = lem.log(8 * ONE_18, 2 * ONE_18)
        assert _from_fp(result) == pytest.approx(3.0, rel=_REL_TOL)

    def test_log_e_of_e_is_1(self) -> None:
        e_fp = _to_fp(math.e)
        # log_e(e) = 1
        result = lem.log(e_fp, e_fp)
        assert _from_fp(result) == pytest.approx(1.0, rel=_REL_TOL)


# ---------------------------------------------------------------------------
# Bound enforcement on pow
# ---------------------------------------------------------------------------


class TestPowBounds:
    def test_y_above_mild_bound_raises(self) -> None:
        with pytest.raises(OverflowError):
            lem.pow(2 * ONE_18, lem.MILD_EXPONENT_BOUND)

    def test_product_out_of_natural_range_raises(self) -> None:
        # Choosing x and y such that y * ln(x) overflows the natural-exp range.
        # y * ln(x) > MAX_NATURAL_EXPONENT (130e18) when x ≈ e^200, y = 1
        # That's hard to express directly; use a large x with a large y instead.
        x = 100 * ONE_18  # ln(100) ≈ 4.605
        y = 30 * ONE_18  # 30 * 4.605 ≈ 138 > 130 → ProductOutOfBounds
        with pytest.raises(OverflowError, match="natural-exponent"):
            lem.pow(x, y)
