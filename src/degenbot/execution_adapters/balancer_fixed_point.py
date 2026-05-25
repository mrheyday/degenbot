"""Legacy Balancer fixed-point wrapper with Pythonic exception semantics."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from degenbot.balancer.libraries import fixed_point as _fp
from degenbot.balancer.libraries.constants import (
    FOUR,
    ONE,
    TWO,
)
from degenbot.balancer.libraries.constants import (
    MAX_POW_RELATIVE_ERROR as _MAX_POW_RELATIVE_ERROR,
)
from degenbot.constants import MAX_UINT256 as UINT256_MAX
from degenbot.exceptions.evm import EVMRevertError

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = (
    "FOUR",
    "MAX_POW_RELATIVE_ERROR",
    "ONE",
    "TWO",
    "UINT256_MAX",
    "complement",
    "div_down",
    "div_up",
    "div_up_raw",
    "mul_div_up",
    "mul_down",
    "mul_up",
    "pow_down",
    "pow_up",
)


def _translate_evm_errors(fn: Callable[..., int], *args: int) -> int:
    try:
        return fn(*args)
    except EVMRevertError as exc:
        text = str(exc)
        if "ZERO_DIVISION" in text:
            raise ZeroDivisionError(text) from exc
        raise OverflowError(text) from exc


def _check_uint256(*values: int) -> None:
    for value in values:
        if value < 0 or value > UINT256_MAX:
            msg = f"value {value} out of uint256 range"
            raise OverflowError(msg)


def mul_down(a: int, b: int) -> int:
    _check_uint256(a, b)
    return _translate_evm_errors(_fp.mul_down, a, b)


def mul_up(a: int, b: int) -> int:
    _check_uint256(a, b)
    return _translate_evm_errors(_fp.mul_up, a, b)


def div_down(a: int, b: int) -> int:
    _check_uint256(a, b)
    return _translate_evm_errors(_fp.div_down, a, b)


def div_up(a: int, b: int) -> int:
    _check_uint256(a, b)
    return _translate_evm_errors(_fp.div_up, a, b)


def div_up_raw(a: int, b: int) -> int:
    _check_uint256(a, b)
    if b == 0:
        msg = "division by zero"
        raise ZeroDivisionError(msg)
    return 0 if a == 0 else ((a - 1) // b) + 1


def mul_div_up(a: int, b: int, denominator: int) -> int:
    _check_uint256(a, b, denominator)
    if denominator == 0:
        msg = "division by zero"
        raise ZeroDivisionError(msg)
    product = a * b
    _check_uint256(product)
    return div_up_raw(product, denominator)


def pow_down(x: int, y: int) -> int:
    _check_uint256(x, y)
    return _translate_evm_errors(_fp.pow_down, x, y)


def pow_up(x: int, y: int) -> int:
    _check_uint256(x, y)
    return _translate_evm_errors(_fp.pow_up, x, y)


def complement(x: int) -> int:
    _check_uint256(x)
    return _fp.complement(x)


MAX_POW_RELATIVE_ERROR: Final[int] = _MAX_POW_RELATIVE_ERROR
