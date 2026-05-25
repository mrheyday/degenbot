"""Legacy Balancer log/exp wrapper with Pythonic exception semantics."""

from __future__ import annotations

from degenbot.balancer.libraries import log_exp_math as _lem
from degenbot.balancer.libraries.log_exp_math import (  # noqa: F401
    LN_36_LOWER_BOUND,
    LN_36_UPPER_BOUND,
    MAX_NATURAL_EXPONENT,
    MILD_EXPONENT_BOUND,
    MIN_NATURAL_EXPONENT,
    ONE_18,
    log,
)
from degenbot.exceptions.evm import EVMRevertError


def exp(x: int) -> int:
    try:
        return _lem.exp(x)
    except EVMRevertError as exc:
        raise OverflowError(str(exc)) from exc


def ln(a: int) -> int:
    try:
        return _lem.ln(a)
    except EVMRevertError as exc:
        msg = f"math domain error: {exc}"
        raise ValueError(msg) from exc


def pow(x: int, y: int) -> int:  # noqa: A001
    try:
        return _lem.pow(x, y)
    except EVMRevertError as exc:
        text = str(exc)
        if "PRODUCT_OUT_OF_BOUNDS" in text:
            msg = "product outside natural-exponent range"
            raise OverflowError(msg) from exc
        raise OverflowError(text) from exc
