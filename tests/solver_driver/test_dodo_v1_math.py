"""Tests for the source-faithful Python port of DODO V1 PMM math.

Validates the port in `solver/driver/execution/dodo_v1_math.py`.

Pinned vectors are derived directly from the V1 Solidity source by hand
(see comments) so they cannot drift if the port is ever refactored. The
DecimalMath cases also re-pin against the V2 port's published
expectations because V1 and V2 implement DecimalMath identically.

Where exact arithmetic for `solve_quadratic_function_for_trade` and
`solve_quadratic_function_for_target` is too tedious to derive by hand,
we pin the no-op identity (`ideltaB = 0` → returns Q1) and verify
monotonicity / source-pre-condition rejections instead. A future
opt-in pinned-block test (analogous to `test_dodo_pmm_pinned_block.py`)
can compare against a V1 pair on Arbitrum once a V1 adapter is wired —
the three V1 pairs at WETH/WBTC/USDT-USDC are the natural fixtures.
"""

from __future__ import annotations

import pytest
from degenbot.execution.dodo_v1_math import (
    ONE,
    DodoV1MathError,
    div_ceil,
    div_floor,
    general_integrate,
    mul,
    mul_ceil,
    solve_quadratic_function_for_target,
    solve_quadratic_function_for_trade,
)


class TestDecimalMathV1:
    """V1 DecimalMath has only 4 functions (no reciprocal/pow). The four
    are byte-for-byte identical to V2's same-named helpers."""

    def test_mul_floor_rounds_down(self) -> None:
        assert mul(ONE // 2, ONE - 1) == 499_999_999_999_999_999

    def test_mul_ceil_rounds_up(self) -> None:
        assert mul_ceil(1, 2 * ONE + 1) == 3

    def test_div_floor(self) -> None:
        assert div_floor(ONE, 3 * ONE) == 333_333_333_333_333_333

    def test_div_ceil(self) -> None:
        assert div_ceil(ONE, 3 * ONE) == 333_333_333_333_333_334

    def test_div_by_zero_reverts(self) -> None:
        with pytest.raises(DodoV1MathError, match="DIVIDING_ERROR"):
            div_floor(ONE, 0)
        with pytest.raises(DodoV1MathError, match="DIVIDING_ERROR"):
            div_ceil(ONE, 0)


class TestGeneralIntegrateV1:
    """`_GeneralIntegrate(V0, V1, V2, i, k)` per V1 source.

    Identity: `result = i * delta * (1 - k + k * V0^2 / V1 / V2)` with
    `delta = V1 - V2`.
    """

    def test_zero_delta_returns_zero(self) -> None:
        # delta = 0 ⇒ fairAmount = 0 ⇒ result = 0 regardless of k.
        assert general_integrate(100 * ONE, 100 * ONE, 100 * ONE, 2 * ONE, ONE // 10) == 0

    def test_canonical_vector(self) -> None:
        # V0=V1=100*ONE, V2=90*ONE, i=2*ONE, k=0.1*ONE
        # Hand-derivation:
        #   delta              = 10*ONE
        #   fairAmount         = mul(2*ONE, 10*ONE)              = 20*ONE
        #   V0^2/V1            = 100*ONE
        #   divCeil(100*ONE,
        #           90*ONE)    = ceil(100e36/90e18)
        #                      = 1_111_111_111_111_111_112
        #   penalty            = mul(0.1*ONE, 1_111_…_112)
        #                      = 111_111_111_111_111_111
        #   (1-k) + penalty    = 0.9*ONE + 0.111…*ONE
        #                      = 1_011_111_111_111_111_111
        #   final              = mul(20*ONE, 1.011…*ONE)
        #                      = 20_222_222_222_222_222_220
        assert general_integrate(100 * ONE, 100 * ONE, 90 * ONE, 2 * ONE, ONE // 10) == 20_222_222_222_222_222_220

    def test_v1_lt_v2_reverts(self) -> None:
        # Source precondition: V1 >= V2 (otherwise SafeMath.sub reverts).
        with pytest.raises(DodoV1MathError, match="SUB_ERROR"):
            general_integrate(100 * ONE, 90 * ONE, 100 * ONE, 2 * ONE, ONE // 10)

    def test_v2_zero_reverts(self) -> None:
        # V2 == 0 ⇒ V0*V0/V1 / V2 div-by-zero in DecimalMath.divCeil.
        with pytest.raises(DodoV1MathError, match="DIVIDING_ERROR"):
            general_integrate(100 * ONE, 100 * ONE, 0, 2 * ONE, ONE // 10)


class TestSolveQuadraticFunctionForTradeV1:
    """`_SolveQuadraticFunctionForTrade(Q0, Q1, ideltaB, deltaBSig, k)` per V1 source.

    The deltaBSig flag selects rounding direction on the final
    numerator/denominator division: `True ⇒ divFloor` (Q2 > Q1),
    `False ⇒ divCeil` (Q2 < Q1). Identity test: `ideltaB = 0` returns
    Q1 regardless of sign because the quadratic collapses.
    """

    def test_zero_idelta_b_returns_q1(self) -> None:
        # Q0 = Q1 = 100*ONE, ideltaB = 0, k = 0.1*ONE, deltaBSig = True
        # Hand-derivation:
        #   kQ02Q1            = ((0.1*ONE * 100*ONE)/ONE)*100*ONE / 100*ONE = 10*ONE
        #   b                 = mul(0.9*ONE, 100*ONE) = 90*ONE
        #   deltaBSig=True ⇒ b = 90*ONE + 0 = 90*ONE
        #   90*ONE >= 10*ONE  ⇒ b = 80*ONE; minusbSig = True
        #   inner_a           = 0.9*ONE * 4 = 3.6e18
        #   inner_b           = 10*ONE * 100*ONE = 1000e36
        #   mul(inner_a,
        #       inner_b)/ONE  = 3.6e39
        #   b*b               = (80*ONE)^2 = 6.4e39
        #   sqrt(b*b + mul)   = sqrt(10e39) = sqrt(1e40) = 1e20 = 100*ONE
        #   denominator       = 0.9*ONE * 2 = 1.8e18
        #   numerator         = 80*ONE + 100*ONE = 180*ONE
        #   divFloor(180*ONE,
        #            1.8e18)  = (180*ONE * ONE)/1.8e18 = 100*ONE
        assert solve_quadratic_function_for_trade(100 * ONE, 100 * ONE, 0, True, ONE // 10) == 100 * ONE

    def test_zero_idelta_b_round_down_branch(self) -> None:
        # Same identity holds for deltaBSig=False (uses divCeil instead).
        assert solve_quadratic_function_for_trade(100 * ONE, 100 * ONE, 0, False, ONE // 10) == 100 * ONE

    def test_positive_idelta_b_increases_result(self) -> None:
        # deltaBSig=True ⇒ Q2 should exceed Q1 = 100*ONE.
        result = solve_quadratic_function_for_trade(100 * ONE, 100 * ONE, 10 * ONE, True, ONE // 10)
        assert result > 100 * ONE

    def test_q1_zero_reverts(self) -> None:
        with pytest.raises(DodoV1MathError, match="DIVIDING_ERROR"):
            solve_quadratic_function_for_trade(100 * ONE, 0, 0, True, ONE // 10)


class TestSolveQuadraticFunctionForTargetV1:
    """`_SolveQuadraticFunctionForTarget(V1, k, fairAmount)` per V1 source.

    Note: V1 signature is `(V1, k, fairAmount)` — three arguments. V2's
    same-named function takes `(v1, delta, i, k)` and a different math.
    Don't mix.

    Identity (V1 form): `V0 = V1 + V1 * (sqrt - 1) / 2k` where
    `sqrt = sqrt(1 + 4 k * fairAmount / V1)`.
    """

    def test_zero_fair_amount_returns_v1(self) -> None:
        # fairAmount = 0 ⇒ inner sqrt argument = 0, so:
        #   sqrt = divCeil(0, V1) = 0
        #   sqrt = isqrt((0 + ONE) * ONE) = isqrt(ONE^2) = ONE
        #   premium = divCeil(ONE - ONE, 2k) = 0
        #   return mul(V1, ONE + 0) = V1
        assert solve_quadratic_function_for_target(100 * ONE, ONE // 10, 0) == 100 * ONE

    def test_positive_fair_amount_returns_target_above_v1(self) -> None:
        # V0 should be strictly greater than V1 when fairAmount > 0
        # (the curve says you need a target above the current depth to
        # explain the captured fairAmount).
        result = solve_quadratic_function_for_target(100 * ONE, ONE // 10, 5 * ONE)
        assert result > 100 * ONE

    def test_v1_zero_reverts(self) -> None:
        with pytest.raises(DodoV1MathError, match="DIVIDING_ERROR"):
            solve_quadratic_function_for_target(0, ONE // 10, 5 * ONE)
