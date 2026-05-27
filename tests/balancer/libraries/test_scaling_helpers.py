from __future__ import annotations

import pytest

from degenbot.balancer.libraries.constants import ONE
from degenbot.balancer.libraries.scaling_helpers import (
    _downscale_down,
    _downscale_down_array,
    _downscale_up,
    _downscale_up_array,
    _upscale,
    _upscale_array,
)

USDC_SCALING_FACTOR = ONE * 10**12
WETH_SCALING_FACTOR = ONE


def test_upscale_matches_rehackt_balancer_helper_rounding() -> None:
    assert _upscale(1_000_000, USDC_SCALING_FACTOR) == ONE
    assert _upscale(2 * ONE, WETH_SCALING_FACTOR) == 2 * ONE


def test_downscale_rounding_direction_is_explicit() -> None:
    one_usdc_scaled_plus_one_wei = ONE + 1

    assert _downscale_down(one_usdc_scaled_plus_one_wei, USDC_SCALING_FACTOR) == 1_000_000
    assert _downscale_up(one_usdc_scaled_plus_one_wei, USDC_SCALING_FACTOR) == 1_000_001


def test_upscale_array_mutates_input_like_balancer_solidity_helper() -> None:
    amounts = [1_000_000, 2 * ONE]

    _upscale_array(amounts, (USDC_SCALING_FACTOR, WETH_SCALING_FACTOR))

    assert amounts == [ONE, 2 * ONE]


def test_downscale_down_array_mutates_input_like_balancer_solidity_helper() -> None:
    amounts = [ONE + 1, 2 * ONE]

    _downscale_down_array(amounts, (USDC_SCALING_FACTOR, WETH_SCALING_FACTOR))

    assert amounts == [1_000_000, 2 * ONE]


def test_downscale_up_array_mutates_input_like_balancer_solidity_helper() -> None:
    amounts = [ONE + 1, 2 * ONE]

    _downscale_up_array(amounts, (USDC_SCALING_FACTOR, WETH_SCALING_FACTOR))

    assert amounts == [1_000_001, 2 * ONE]


@pytest.mark.parametrize(
    "helper",
    [
        _upscale_array,
        _downscale_down_array,
        _downscale_up_array,
    ],
)
def test_array_helpers_reject_length_mismatch(helper) -> None:
    with pytest.raises(ValueError, match="length mismatch"):
        helper([ONE], (WETH_SCALING_FACTOR, WETH_SCALING_FACTOR))
