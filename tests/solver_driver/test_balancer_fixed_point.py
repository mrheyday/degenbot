"""Tests for the Python port of Balancer V3's FixedPoint library.

These tests compare the Python operations against hand-computed values
that mirror the on-chain Solidity FixedPoint behavior. The reference
identity for each operation is documented in the test docstring so a
future Solidity-fixture cross-check can target the same values.
"""

from __future__ import annotations

import pytest
from degenbot.execution import balancer_fixed_point as fp
from degenbot.execution.balancer_fixed_point import FOUR, ONE, TWO

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_one_is_1e18(self) -> None:
        assert ONE == 10**18

    def test_two_is_2e18(self) -> None:
        assert TWO == 2 * 10**18

    def test_four_is_4e18(self) -> None:
        assert FOUR == 4 * 10**18


# ---------------------------------------------------------------------------
# mul_down / mul_up — rounding direction is the whole point
# ---------------------------------------------------------------------------


class TestMulDown:
    def test_one_times_one_is_one(self) -> None:
        # 1.0 * 1.0 = 1.0
        assert fp.mul_down(ONE, ONE) == ONE

    def test_two_times_three_is_six(self) -> None:
        assert fp.mul_down(2 * ONE, 3 * ONE) == 6 * ONE

    def test_zero_propagates(self) -> None:
        assert fp.mul_down(0, ONE) == 0
        assert fp.mul_down(ONE, 0) == 0

    def test_rounding_toward_zero(self) -> None:
        # (3e18) * (1e18 + 1) / 1e18 = 3e18 + 3, but exact div by 1e18 truncates 3
        # i.e., 3 * 1.000000_000000000001 should round DOWN to 3.000000000000000003
        a = 3 * ONE
        b = ONE + 1
        assert fp.mul_down(a, b) == 3 * ONE + 3

    def test_small_remainder_truncates(self) -> None:
        # (1) * (1) // 1e18 = 0 (truncated)
        assert fp.mul_down(1, 1) == 0


class TestMulUp:
    def test_one_times_one_is_one(self) -> None:
        assert fp.mul_up(ONE, ONE) == ONE

    def test_zero_propagates(self) -> None:
        assert fp.mul_up(0, ONE) == 0
        assert fp.mul_up(ONE, 0) == 0

    def test_rounding_away_from_zero(self) -> None:
        # (1) * (1) // 1e18 with up rounding = 1 (not 0)
        assert fp.mul_up(1, 1) == 1

    def test_exact_product_does_not_round_up(self) -> None:
        # 2.0 * 3.0 has zero remainder; mulUp must equal mulDown
        assert fp.mul_up(2 * ONE, 3 * ONE) == 6 * ONE

    def test_remainder_triggers_round_up(self) -> None:
        # a * b = 1 * (ONE + 1) = 1e18 + 1; div by ONE has remainder 1.
        # mul_down truncates the +1 → 1; mul_up adds 1 back → 2.
        a = 1
        b = ONE + 1
        assert fp.mul_down(a, b) == 1
        assert fp.mul_up(a, b) == 2


# ---------------------------------------------------------------------------
# div_down / div_up
# ---------------------------------------------------------------------------


class TestDivDown:
    def test_one_div_one(self) -> None:
        assert fp.div_down(ONE, ONE) == ONE

    def test_two_div_one_is_two(self) -> None:
        assert fp.div_down(2 * ONE, ONE) == 2 * ONE

    def test_one_div_two_is_half(self) -> None:
        # 1.0 / 2.0 = 0.5 → 5e17
        assert fp.div_down(ONE, 2 * ONE) == ONE // 2

    def test_zero_division_raises(self) -> None:
        with pytest.raises(ZeroDivisionError):
            fp.div_down(ONE, 0)


class TestDivUp:
    def test_one_div_one(self) -> None:
        assert fp.div_up(ONE, ONE) == ONE

    def test_one_div_two_is_half(self) -> None:
        # 1.0 / 2.0 has zero remainder after inflation → divUp == divDown == 0.5
        assert fp.div_up(ONE, 2 * ONE) == ONE // 2

    def test_zero_numerator_returns_zero(self) -> None:
        assert fp.div_up(0, ONE) == 0

    def test_one_div_three_rounds_up(self) -> None:
        # 1e18 * 1e18 / 3e18 = 333333333333333333.333... → up = 333...334
        a = ONE
        b = 3 * ONE
        assert fp.div_up(a, b) == fp.div_down(a, b) + 1

    def test_zero_division_raises(self) -> None:
        with pytest.raises(ZeroDivisionError):
            fp.div_up(ONE, 0)


class TestMulDivUp:
    def test_basic(self) -> None:
        # (2 * 6) / 3 = 4
        assert fp.mul_div_up(2, 6, 3) == 4

    def test_remainder_rounds_up(self) -> None:
        # (1 * 1) / 3 = 0.33... → ceil = 1
        assert fp.mul_div_up(1, 1, 3) == 1

    def test_zero_product_returns_zero(self) -> None:
        assert fp.mul_div_up(0, 5, 3) == 0
        assert fp.mul_div_up(5, 0, 3) == 0

    def test_zero_division_raises(self) -> None:
        with pytest.raises(ZeroDivisionError):
            fp.mul_div_up(1, 1, 0)


class TestDivUpRaw:
    def test_basic(self) -> None:
        # divUpRaw on already-inflated values
        assert fp.div_up_raw(10, 3) == 4
        assert fp.div_up_raw(9, 3) == 3

    def test_zero_numerator_returns_zero(self) -> None:
        assert fp.div_up_raw(0, 5) == 0

    def test_zero_division_raises(self) -> None:
        with pytest.raises(ZeroDivisionError):
            fp.div_up_raw(1, 0)


# ---------------------------------------------------------------------------
# Powers (special cases)
# ---------------------------------------------------------------------------


class TestPowDownSpecial:
    def test_y_eq_one_is_identity(self) -> None:
        # x^1 = x for any x
        assert fp.pow_down(123 * ONE, ONE) == 123 * ONE

    def test_y_eq_two_is_square(self) -> None:
        # 3.0 ^ 2 = 9.0
        assert fp.pow_down(3 * ONE, TWO) == 9 * ONE

    def test_y_eq_four_is_pow4(self) -> None:
        # 2.0 ^ 4 = 16.0
        assert fp.pow_down(2 * ONE, FOUR) == 16 * ONE

    def test_arbitrary_y_via_logexp(self) -> None:
        # 2^0.8 (80/20 Weighted exponent). pow_down must not exceed truth.
        result = fp.pow_down(2 * ONE, 8 * ONE // 10)
        true_value = round((2.0**0.8) * 1e18)
        assert result <= true_value


class TestPowUpSpecial:
    def test_y_eq_one_is_identity(self) -> None:
        assert fp.pow_up(123 * ONE, ONE) == 123 * ONE

    def test_y_eq_two_is_square_up(self) -> None:
        # mulUp matters when remainder is non-zero
        # x = 1e18 + 1 → x^2 has a non-zero remainder; up should add 1
        x = ONE + 1
        product = (x * x - 1) // ONE + 1
        assert fp.pow_up(x, TWO) == product

    def test_y_eq_four_is_pow4(self) -> None:
        assert fp.pow_up(2 * ONE, FOUR) == 16 * ONE

    def test_arbitrary_y_via_logexp(self) -> None:
        # sqrt(2). pow_up must not be below truth.
        result = fp.pow_up(2 * ONE, 5 * ONE // 10)
        true_value = round((2.0**0.5) * 1e18)
        assert result >= true_value


# ---------------------------------------------------------------------------
# Complement
# ---------------------------------------------------------------------------


class TestComplement:
    def test_zero_returns_one(self) -> None:
        assert fp.complement(0) == ONE

    def test_one_returns_zero(self) -> None:
        assert fp.complement(ONE) == 0

    def test_above_one_clamps_to_zero(self) -> None:
        assert fp.complement(2 * ONE) == 0

    def test_below_one_subtracts(self) -> None:
        # x = 0.3 → complement = 0.7
        assert fp.complement(3 * ONE // 10) == 7 * ONE // 10


# ---------------------------------------------------------------------------
# Overflow guards
# ---------------------------------------------------------------------------


class TestOverflowGuards:
    def test_negative_input_raises(self) -> None:
        with pytest.raises(OverflowError):
            fp.mul_down(-1, ONE)

    def test_above_uint256_max_raises(self) -> None:
        with pytest.raises(OverflowError):
            fp.mul_down(fp.UINT256_MAX + 1, 1)

    def test_product_overflow_raises(self) -> None:
        # a * b would exceed uint256 max → guard trips
        with pytest.raises(OverflowError):
            fp.mul_down(fp.UINT256_MAX, fp.UINT256_MAX)
