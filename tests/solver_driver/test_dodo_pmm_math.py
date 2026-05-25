"""Tests for the source-faithful Python port of DODO V2 PMM math."""

from __future__ import annotations

from degenbot.execution.dodo_pmm_math import (
    ONE,
    PmmState,
    RState,
    adjusted_target,
    div_ceil,
    div_floor,
    general_integrate,
    get_mid_price,
    mul_ceil,
    mul_floor,
    pow_floor,
    reciprocal_floor,
    sell_base_token,
    sell_quote_token,
    solve_quadratic_function_for_target,
    solve_quadratic_function_for_trade,
)


def _base_state(r_state: RState = RState.ONE) -> PmmState:
    return PmmState(
        i=2_000 * ONE,
        K=ONE // 10,
        B=100 * ONE,
        Q=200_000 * ONE,
        B0=100 * ONE,
        Q0=200_000 * ONE,
        R=r_state,
    )


class TestDecimalMath:
    def test_rounding_matches_decimal_math(self) -> None:
        assert mul_floor(ONE // 2, ONE - 1) == 499_999_999_999_999_999
        assert mul_ceil(1, 2 * ONE + 1) == 3
        assert div_floor(ONE, 3 * ONE) == 333_333_333_333_333_333
        assert div_ceil(ONE, 3 * ONE) == 333_333_333_333_333_334

    def test_reciprocal_and_power(self) -> None:
        assert reciprocal_floor(2 * ONE) == 500_000_000_000_000_000
        assert pow_floor(2 * ONE, 3) == 8 * ONE


class TestDodoMath:
    def test_general_integrate_k_zero_and_k_nonzero(self) -> None:
        assert general_integrate(100 * ONE, 100 * ONE, 90 * ONE, 2 * ONE, 0) == 20 * ONE
        assert (
            general_integrate(100 * ONE, 100 * ONE, 90 * ONE, 2 * ONE, ONE // 10)
            == 20_222_222_222_222_222_220
        )

    def test_quadratic_target_branches(self) -> None:
        assert solve_quadratic_function_for_target(100 * ONE, 10 * ONE, 2 * ONE, 0) == 120 * ONE
        assert (
            solve_quadratic_function_for_target(100 * ONE, 10 * ONE, 2 * ONE, ONE // 10)
            == 119_615_242_270_663_188_000
        )

    def test_quadratic_trade_branches(self) -> None:
        assert solve_quadratic_function_for_trade(100 * ONE, 90 * ONE, 0, 2 * ONE, ONE // 10) == 0
        assert (
            solve_quadratic_function_for_trade(100 * ONE, 90 * ONE, 1 * ONE, 2 * ONE, 0) == 2 * ONE
        )
        assert (
            solve_quadratic_function_for_trade(100 * ONE, 90 * ONE, 1 * ONE, 2 * ONE, ONE)
            == 1_591_355_599_214_145_383
        )
        assert (
            solve_quadratic_function_for_trade(100 * ONE, 90 * ONE, 1 * ONE, 2 * ONE, ONE // 10)
            == 1_948_957_897_004_484_962
        )


class TestPmmPricing:
    def test_r_one_sell_paths_and_mid_price(self) -> None:
        state = _base_state()

        assert sell_base_token(state, ONE) == (1_997_983_889_406_409_944_695, RState.BELOW_ONE)
        assert sell_quote_token(state, 2_000 * ONE) == (998_991_944_703_204_972, RState.ABOVE_ONE)
        assert get_mid_price(state) == 2_000 * ONE

    def test_above_one_transitions_and_adjusted_target(self) -> None:
        state = PmmState(
            i=2_000 * ONE,
            K=ONE // 10,
            B=90 * ONE,
            Q=220_000 * ONE,
            B0=100 * ONE,
            Q0=200_000 * ONE,
            R=RState.ABOVE_ONE,
        )

        assert sell_base_token(state, ONE) == (2_044_200_244_200_244_200_000, RState.ABOVE_ONE)
        assert sell_base_token(state, 10 * ONE) == (20_000 * ONE, RState.ONE)
        assert sell_base_token(state, 11 * ONE) == (
            21_997_983_889_406_409_944_695,
            RState.BELOW_ONE,
        )
        assert sell_quote_token(state, 2_000 * ONE) == (975_790_639_272_924_290, RState.ABOVE_ONE)
        assert get_mid_price(state) == 2_046_913_580_246_913_580_000

        adjusted_target(state)
        assert state.B0 == 99_891_291_502_676_749_500

    def test_below_one_transitions_and_adjusted_target(self) -> None:
        state = PmmState(
            i=2_000 * ONE,
            K=ONE // 10,
            B=110 * ONE,
            Q=180_000 * ONE,
            B0=100 * ONE,
            Q0=200_000 * ONE,
            R=RState.BELOW_ONE,
        )

        assert sell_quote_token(state, 2_000 * ONE) == (1_022_100_122_100_122_100, RState.BELOW_ONE)
        assert sell_quote_token(state, 20_000 * ONE) == (10 * ONE, RState.ONE)
        assert sell_quote_token(state, 22_000 * ONE) == (
            10_998_991_944_703_204_972,
            RState.ABOVE_ONE,
        )
        assert sell_base_token(state, ONE) == (1_951_581_278_545_848_580_849, RState.BELOW_ONE)
        assert get_mid_price(state) == 1_954_161_640_530_759_951_984

        adjusted_target(state)
        assert state.Q0 == 199_782_583_005_353_499_000_000
