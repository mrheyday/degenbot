"""Fixed-point Python port of DODO V2 PMM math.

Source:
- `docs/research/dodo/source/contractV2/contracts/lib/DecimalMath.sol`
- `docs/research/dodo/source/contractV2/contracts/lib/DODOMath.sol`
- `docs/research/dodo/source/contractV2/contracts/lib/PMMPricing.sol`

The implementation intentionally mirrors DODO V2's Solidity 0.6.9 integer
math and rounding semantics. It is not a continuous approximation of the PMM
curve; it ports the exact helper structure used by DVM/DPP/DSP pools.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from math import isqrt
from typing import Final

ONE: Final[int] = 10**18
ONE2: Final[int] = 10**36
UINT256_MAX: Final[int] = (1 << 256) - 1


class DodoMathError(ValueError):
    """Raised when DODO PMM math would revert on-chain."""


class RState(IntEnum):
    """DODO PMM inventory state."""

    ONE = 0
    ABOVE_ONE = 1
    BELOW_ONE = 2


@dataclass
class PmmState:
    """DODO `PMMPricing.PMMState` equivalent."""

    i: int
    K: int
    B: int
    Q: int
    B0: int
    Q0: int
    R: RState


def _check_uint256(*values: int) -> None:
    for value in values:
        if value < 0 or value > UINT256_MAX:
            msg = f"value {value} out of uint256 range"
            raise OverflowError(msg)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise DodoMathError(message)


def _add(a: int, b: int) -> int:
    _check_uint256(a, b)
    result = a + b
    _check_uint256(result)
    return result


def _sub(a: int, b: int) -> int:
    _check_uint256(a, b)
    _require(b <= a, "SUB_ERROR")
    return a - b


def _mul(a: int, b: int) -> int:
    _check_uint256(a, b)
    result = a * b
    _check_uint256(result)
    return result


def _div(a: int, b: int) -> int:
    _check_uint256(a, b)
    _require(b > 0, "DIVIDING_ERROR")
    return a // b


def _div_ceil_raw(a: int, b: int) -> int:
    quotient = _div(a, b)
    return quotient + 1 if a - quotient * b > 0 else quotient


def mul_floor(target: int, d: int) -> int:
    """Port of `DecimalMath.mulFloor`."""

    return _div(_mul(target, d), ONE)


def mul_ceil(target: int, d: int) -> int:
    """Port of `DecimalMath.mulCeil`."""

    return _div_ceil_raw(_mul(target, d), ONE)


def div_floor(target: int, d: int) -> int:
    """Port of `DecimalMath.divFloor`."""

    return _div(_mul(target, ONE), d)


def div_ceil(target: int, d: int) -> int:
    """Port of `DecimalMath.divCeil`."""

    return _div_ceil_raw(_mul(target, ONE), d)


def reciprocal_floor(target: int) -> int:
    """Port of `DecimalMath.reciprocalFloor`."""

    _check_uint256(target)
    _require(target > 0, "DIVIDING_ERROR")
    return ONE2 // target


def reciprocal_ceil(target: int) -> int:
    """Port of `DecimalMath.reciprocalCeil`."""

    return _div_ceil_raw(ONE2, target)


def pow_floor(target: int, e: int) -> int:
    """Port of `DecimalMath.powFloor`."""

    _check_uint256(target, e)
    if e == 0:
        return ONE
    if e == 1:
        return target
    p = pow_floor(target, e // 2)
    p = _div(_mul(p, p), ONE)
    if e % 2 == 1:
        p = _div(_mul(p, target), ONE)
    return p


def general_integrate(v0: int, v1: int, v2: int, i: int, k: int) -> int:
    """Port of `DODOMath._GeneralIntegrate`.

    Requires `v0 > 0` and `v1 >= v2 > 0`, matching the intended source precondition.
    """

    _require(v0 > 0, "TARGET_IS_ZERO")
    fair_amount = _mul(i, _sub(v1, v2))
    if k == 0:
        return _div(fair_amount, ONE)
    v0v0v1v2 = div_floor(_div(_mul(v0, v0), v1), v2)
    penalty = mul_floor(k, v0v0v1v2)
    return _div(_mul(_add(_sub(ONE, k), penalty), fair_amount), ONE2)


def solve_quadratic_function_for_target(v1: int, delta: int, i: int, k: int) -> int:
    """Port of `DODOMath._SolveQuadraticFunctionForTarget`."""

    if k == 0:
        return _add(v1, mul_floor(i, delta))
    if v1 == 0:
        return 0

    ki = _mul(_mul(4, k), i)
    if ki == 0:
        sqrt_value = ONE
    elif ki * delta <= UINT256_MAX:
        sqrt_value = isqrt(_add(_div(_mul(ki, delta), v1), ONE2))
    else:
        sqrt_value = isqrt(_add(_mul(_div(ki, v1), delta), ONE2))

    premium = _add(div_floor(_sub(sqrt_value, ONE), _mul(k, 2)), ONE)
    return mul_floor(v1, premium)


def solve_quadratic_function_for_trade(v0: int, v1: int, delta: int, i: int, k: int) -> int:
    """Port of `DODOMath._SolveQuadraticFunctionForTrade`."""

    _require(v0 > 0, "TARGET_IS_ZERO")
    if delta == 0:
        return 0

    if k == 0:
        return min(mul_floor(i, delta), v1)

    if k == ONE:
        idelta = _mul(i, delta)
        if idelta == 0:
            temp = 0
        elif idelta * v1 <= UINT256_MAX:
            temp = _div(_mul(idelta, v1), _mul(v0, v0))
        else:
            temp = _div(_mul(_div(_mul(delta, v1), v0), i), v0)
        return _div(_mul(v1, temp), _add(temp, ONE))

    part2 = _add(_mul(_div(_mul(k, v0), v1), v0), _mul(i, delta))
    b_abs = _mul(_sub(ONE, k), v1)

    if b_abs >= part2:
        b_abs -= part2
        b_sig = False
    else:
        b_abs = part2 - b_abs
        b_sig = True
    b_abs = _div(b_abs, ONE)

    square_root = mul_floor(_mul(_sub(ONE, k), 4), _mul(mul_floor(k, v0), v0))
    square_root = isqrt(_add(_mul(b_abs, b_abs), square_root))

    denominator = _mul(_sub(ONE, k), 2)
    if b_sig:
        numerator = _sub(square_root, b_abs)
        _require(numerator != 0, "DODOMath: should not be zero")
    else:
        numerator = _add(b_abs, square_root)

    v2 = div_ceil(numerator, denominator)
    return 0 if v2 > v1 else v1 - v2


def sell_base_token(state: PmmState, pay_base_amount: int) -> tuple[int, RState]:
    """Port of `PMMPricing.sellBaseToken`."""

    if state.R == RState.ONE:
        return _r_one_sell_base_token(state, pay_base_amount), RState.BELOW_ONE

    if state.R == RState.ABOVE_ONE:
        back_to_one_pay_base = _sub(state.B0, state.B)
        back_to_one_receive_quote = _sub(state.Q, state.Q0)
        if pay_base_amount < back_to_one_pay_base:
            receive_quote_amount = _r_above_sell_base_token(state, pay_base_amount)
            receive_quote_amount = min(receive_quote_amount, back_to_one_receive_quote)
            return receive_quote_amount, RState.ABOVE_ONE
        if pay_base_amount == back_to_one_pay_base:
            return back_to_one_receive_quote, RState.ONE
        receive_quote_amount = _add(
            back_to_one_receive_quote,
            _r_one_sell_base_token(state, _sub(pay_base_amount, back_to_one_pay_base)),
        )
        return receive_quote_amount, RState.BELOW_ONE

    return _r_below_sell_base_token(state, pay_base_amount), RState.BELOW_ONE


def sell_quote_token(state: PmmState, pay_quote_amount: int) -> tuple[int, RState]:
    """Port of `PMMPricing.sellQuoteToken`."""

    if state.R == RState.ONE:
        return _r_one_sell_quote_token(state, pay_quote_amount), RState.ABOVE_ONE

    if state.R == RState.ABOVE_ONE:
        return _r_above_sell_quote_token(state, pay_quote_amount), RState.ABOVE_ONE

    back_to_one_pay_quote = _sub(state.Q0, state.Q)
    back_to_one_receive_base = _sub(state.B, state.B0)
    if pay_quote_amount < back_to_one_pay_quote:
        receive_base_amount = _r_below_sell_quote_token(state, pay_quote_amount)
        receive_base_amount = min(receive_base_amount, back_to_one_receive_base)
        return receive_base_amount, RState.BELOW_ONE
    if pay_quote_amount == back_to_one_pay_quote:
        return back_to_one_receive_base, RState.ONE
    receive_base_amount = _add(
        back_to_one_receive_base,
        _r_one_sell_quote_token(state, _sub(pay_quote_amount, back_to_one_pay_quote)),
    )
    return receive_base_amount, RState.ABOVE_ONE


def adjusted_target(state: PmmState) -> PmmState:
    """Port of `PMMPricing.adjustedTarget`.

    The Solidity function mutates its memory struct. This function mutates and
    returns the same Python object for equivalent call-site behavior.
    """

    if state.R == RState.BELOW_ONE:
        state.Q0 = solve_quadratic_function_for_target(
            state.Q,
            _sub(state.B, state.B0),
            state.i,
            state.K,
        )
    elif state.R == RState.ABOVE_ONE:
        state.B0 = solve_quadratic_function_for_target(
            state.B,
            _sub(state.Q, state.Q0),
            reciprocal_floor(state.i),
            state.K,
        )
    return state


def get_mid_price(state: PmmState) -> int:
    """Port of `PMMPricing.getMidPrice`."""

    if state.R == RState.BELOW_ONE:
        r = div_floor(_div(_mul(state.Q0, state.Q0), state.Q), state.Q)
        r = _add(_sub(ONE, state.K), mul_floor(state.K, r))
        return div_floor(state.i, r)
    r = div_floor(_div(_mul(state.B0, state.B0), state.B), state.B)
    r = _add(_sub(ONE, state.K), mul_floor(state.K, r))
    return mul_floor(state.i, r)


def _r_one_sell_base_token(state: PmmState, pay_base_amount: int) -> int:
    return solve_quadratic_function_for_trade(
        state.Q0,
        state.Q0,
        pay_base_amount,
        state.i,
        state.K,
    )


def _r_one_sell_quote_token(state: PmmState, pay_quote_amount: int) -> int:
    return solve_quadratic_function_for_trade(
        state.B0,
        state.B0,
        pay_quote_amount,
        reciprocal_floor(state.i),
        state.K,
    )


def _r_below_sell_quote_token(state: PmmState, pay_quote_amount: int) -> int:
    return general_integrate(
        state.Q0,
        _add(state.Q, pay_quote_amount),
        state.Q,
        reciprocal_floor(state.i),
        state.K,
    )


def _r_below_sell_base_token(state: PmmState, pay_base_amount: int) -> int:
    return solve_quadratic_function_for_trade(
        state.Q0,
        state.Q,
        pay_base_amount,
        state.i,
        state.K,
    )


def _r_above_sell_base_token(state: PmmState, pay_base_amount: int) -> int:
    return general_integrate(
        state.B0,
        _add(state.B, pay_base_amount),
        state.B,
        state.i,
        state.K,
    )


def _r_above_sell_quote_token(state: PmmState, pay_quote_amount: int) -> int:
    return solve_quadratic_function_for_trade(
        state.B0,
        state.B,
        pay_quote_amount,
        reciprocal_floor(state.i),
        state.K,
    )
