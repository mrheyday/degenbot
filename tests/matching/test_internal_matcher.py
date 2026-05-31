"""Unit tests for the ported internal matching logic (Pick A)."""

import pytest

from degenbot.decision.types import CowOrderSummary, MatchCandidate, UniswapXOrderSummary
from degenbot.matching.encoder import encode_match_pair
from degenbot.matching.internal_matcher import find_best_match
from degenbot.matching.price_compat import (
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
        amount_sell=10**18,  # 1.0 A
        amount_buy_min=2 * 10**6,  # 2.0 B (assuming 6 decimals)
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
        amount_sell=3 * 10**6,  # 3.0 B
        amount_buy_min=10**18,  # 1.0 A
        source_id="src-in-1",
        source_venue="cow",
        source_expires_at=0,
        received_at_ms=123456789,
    )


def test_price_compat_math(outbound_cand: MatchCandidate, inbound_cand: MatchCandidate):
    op = outbound_min_price(outbound_cand)
    cp = counter_max_price(inbound_cand)

    assert op == 2_000_000
    assert cp == 3_000_000
    assert is_price_compatible(outbound_cand, inbound_cand)

    assert clearing_price(outbound_cand, inbound_cand) == 2_500_000


def test_fill_amount(outbound_cand: MatchCandidate, inbound_cand: MatchCandidate):
    fill = fill_amount(outbound_cand, inbound_cand)
    assert fill == 10**18


def test_find_best_match(outbound_cand: MatchCandidate, inbound_cand: MatchCandidate):
    match = find_best_match(
        outbound=[outbound_cand],
        inbound=[inbound_cand],
        uniswapx=[]
    )
    assert match is not None
    assert match.o.id == "out-1"
    assert match.fill_amount == 10**18


def test_encoder_cow_settle(outbound_cand: MatchCandidate, inbound_cand: MatchCandidate):
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
    assert len(trade.expected_token_inflows) == 2
