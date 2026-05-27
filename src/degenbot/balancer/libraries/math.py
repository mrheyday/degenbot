"""Checked integer helpers mirroring Balancer Solidity Math names."""

# ruff: noqa: A001,FURB136

from degenbot.constants import MAX_UINT256
from degenbot.exceptions.evm import EVMRevertError


def abs(a: int) -> int:
    return -a if a < 0 else a


def add(a: int, b: int) -> int:
    c = a + b
    if c > MAX_UINT256:
        raise EVMRevertError(error="ADD_OVERFLOW")
    return c


def sub(a: int, b: int) -> int:
    if b > a:
        raise EVMRevertError(error="SUB_OVERFLOW")
    return a - b


def max(a: int, b: int) -> int:
    return a if a > b else b


def min(a: int, b: int) -> int:
    return a if a < b else b


def mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    c = a * b
    if c > MAX_UINT256 or c // a != b:
        raise EVMRevertError(error="MUL_OVERFLOW")
    return c


def div(a: int, b: int, round_up: bool) -> int:
    return div_up(a, b) if round_up else div_down(a, b)


def div_down(a: int, b: int) -> int:
    if b == 0:
        raise EVMRevertError(error="ZERO_DIVISION")
    return a // b


def div_up(a: int, b: int) -> int:
    if b == 0:
        raise EVMRevertError(error="ZERO_DIVISION")
    return 0 if a == 0 else 1 + (a - 1) // b
