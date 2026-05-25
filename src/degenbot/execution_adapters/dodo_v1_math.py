"""Fixed-point Python port of DODO V1 PMM math helpers."""

from __future__ import annotations

from math import isqrt
from typing import Final

ONE: Final[int] = 10**18
UINT256_MAX: Final[int] = (1 << 256) - 1


class DodoV1MathError(ValueError):
    """Raised when DODO V1 math would revert on-chain."""


def _check_uint256(*values: int) -> None:
    for value in values:
        if value < 0 or value > UINT256_MAX:
            msg = f"value {value} out of uint256 range"
            raise OverflowError(msg)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise DodoV1MathError(message)


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


def mul(target: int, d: int) -> int:
    """Port of DODO V1 `DecimalMath.mul`."""

    return _div(_mul(target, d), ONE)


def mul_ceil(target: int, d: int) -> int:
    """Port of DODO V1 `DecimalMath.mulCeil`."""

    return _div_ceil_raw(_mul(target, d), ONE)


def div_floor(target: int, d: int) -> int:
    """Port of DODO V1 `DecimalMath.divFloor`."""

    return _div(_mul(target, ONE), d)


def div_ceil(target: int, d: int) -> int:
    """Port of DODO V1 `DecimalMath.divCeil`."""

    return _div_ceil_raw(_mul(target, ONE), d)


def general_integrate(v0: int, v1: int, v2: int, i: int, k: int) -> int:
    """Port of DODO V1 `_GeneralIntegrate(V0, V1, V2, i, k)`."""

    fair_amount = mul(i, _sub(v1, v2))
    if k == 0:
        return fair_amount
    v0v0v1v2 = div_ceil(_div(_mul(v0, v0), v1), v2)
    penalty = mul(k, v0v0v1v2)
    return mul(fair_amount, _add(_sub(ONE, k), penalty))


def solve_quadratic_function_for_trade(
    q0: int,
    q1: int,
    idelta_b: int,
    delta_b_sig: bool,
    k: int,
) -> int:
    """Port of DODO V1 `_SolveQuadraticFunctionForTrade`."""

    kq02q1 = _div(mul(_mul(k, q0), q0), q1)
    b = mul(_sub(ONE, k), q1)
    b = _add(b, idelta_b) if delta_b_sig else _sub(b, idelta_b)

    if b >= kq02q1:
        b -= kq02q1
        minus_b_sig = True
    else:
        b = kq02q1 - b
        minus_b_sig = False

    four_minus_k = _mul(_sub(ONE, k), 4)
    inner = mul(four_minus_k, _mul(kq02q1, q1))
    square_root = isqrt(_add(_mul(b, b), inner))
    denominator = _mul(_sub(ONE, k), 2)

    numerator = _add(b, square_root) if minus_b_sig else _sub(square_root, b)
    return div_floor(numerator, denominator) if delta_b_sig else div_ceil(numerator, denominator)


def solve_quadratic_function_for_target(v1: int, k: int, fair_amount: int) -> int:
    """Port of DODO V1 `_SolveQuadraticFunctionForTarget(V1, k, fairAmount)`."""

    if k == 0:
        return _add(v1, fair_amount)
    sqrt_argument = div_ceil(_mul(_mul(k, fair_amount), 4), v1)
    sqrt_value = isqrt(_mul(_add(sqrt_argument, ONE), ONE))
    premium = div_ceil(_sub(sqrt_value, ONE), _mul(k, 2))
    return mul(v1, _add(ONE, premium))
