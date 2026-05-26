"""Unit tests for the ported internal matching logic (Pick A)."""

import pytest

from degenbot.decision.types import CowOrderSummary, MatchCandidate, UniswapXOrderSummary
from degenbot.matching.encoder import encode_match_pair
from degenbot.matching.internal_matcher import find_best_match
from degenbot.matching.price_compat import (
    PRICE_SCALE,
    clearing_price,
    counter_max_price,
    fill_amount,
    is_price_compatible,
    outbound_min_price,
)

# Mock addresses
_TOKEN_A = "0x" + "a" * 40
_TOKEN_B = "0x" + "b" * 40
_EXECUTOR = "0x" + "e" * 40


@pytest.fixture
def outbound_cand() -> MatchCandidate:
    return MatchCandidate(
        id="out-1",
        side="outbound",
        pair_sell=_TOKEN_A,
        pair_buy=_TOKEN_B,
        pair_sell_decimals=18,
        pair_buy_decimals=6,
        amount_sell=10**18,  # 1.0 A
        amount_buy_min=2 * 10**6,  # 2.0 B
        source_id="src-out-1",
        source_venue="across",
        source_expires_at=0,
        received_at_ms=123456789,
    )


@pytest.fixture
def inbound_cand() -> MatchCandidate:
    return MatchCandidate(
        id="in-1",
        side="inbound",
        pair_sell=_TOKEN_B,
        pair_buy=_TOKEN_A,
        pair_sell_decimals=6,
        pair_buy_decimals=18,
        amount_sell=3 * 10**6,  # 3.0 B
        amount_buy_min=10**18,  # 1.0 A
        source_id="src-in-1",
        source_venue="cow",
        source_expires_at=0,
        received_at_ms=123456789,
    )


def test_price_compat_math(outbound_cand: MatchCandidate, inbound_cand: MatchCandidate):
    # Outbound: 1.0 A -> 2.0 B. Min price = 2.0 B/A (scaled)
    # Inbound: 3.0 B -> 1.0 A. Max price = 3.0 B/A (scaled)

    op = outbound_min_price(outbound_cand)
    cp = counter_max_price(inbound_cand)

    assert op == 2 * PRICE_SCALE
    assert cp == 3 * PRICE_SCALE
    assert is_price_compatible(outbound_cand, inbound_cand)

    assert clearing_price(outbound_cand, inbound_cand) == 5 * PRICE_SCALE // 2


def test_fill_amount(outbound_cand: MatchCandidate, inbound_cand: MatchCandidate):
    # Outbound wants to sell 1.0 A.
    # Inbound has 3.0 B to sell. At clearing price 2.5 B/A (unscaled),
    # 1.0 A costs 2.5 B.
    # Inbound budget is 3.0 B, which can buy 3.0 / 2.5 = 1.2 A.
    # Outbound is the bottleneck (1.0 A).

    fill = fill_amount(outbound_cand, inbound_cand)
    assert fill == 10**18


def test_find_best_match(outbound_cand: MatchCandidate, inbound_cand: MatchCandidate):
    match = find_best_match(
        outbound=[outbound_cand],
        inbound=[inbound_cand],
        uniswapx=[],
    )
    assert match is not None
    assert match.o.id == "out-1"
    assert match.fill_amount == 10**18


def test_encoder_cow_settle(outbound_cand: MatchCandidate, inbound_cand: MatchCandidate):
    # Ported from TS encoder.test.ts
    pair = find_best_match([outbound_cand], [inbound_cand], [])
    assert pair is not None

    cow_order = CowOrderSummary(
        uid="0x123",
        owner=_EXECUTOR,
        sell_token=_TOKEN_B,
        buy_token=_TOKEN_A,
        sell_amount=3 * 10**6,
        buy_amount=10**18,
        valid_to=9999999,
        app_data="0x" + "0" * 64,
        fee_amount=0,
        kind="sell",
        partially_fillable=True,
        signature="0x" + "0" * 130,
        signing_scheme="eip712",
    )

    ux_order = UniswapXOrderSummary(
        order_hash="0xabc",
        reactor=_EXECUTOR,
        swapper=_EXECUTOR,
        input_token=_TOKEN_A,
        output_token=_TOKEN_B,
        input_amount=10**18,
        output_amount_min=2 * 10**6,
        deadline=9999999,
        encoded_order="0x" + "0" * 200,
        signature="0x" + "0" * 130,
    )

    trade = encode_match_pair(
        pair=pair,
        cow_order=cow_order,
        uniswapx_order=ux_order,
        estimated_profit_wei=10**15,
        flash_token=_TOKEN_A,
        flash_amount=10**18,
        executor_address=_EXECUTOR,
    )

    assert trade.cow_settlement_calldata.startswith("0x1700684f")
    assert trade.uniswapx_batch_calldata.startswith("0x364a2754")
    assert trade.expected_token_inflows == [_TOKEN_A, _TOKEN_B]
    assert trade.expected_token_inflow_min == [950_000_000_000_000_000, 2_375_000]
