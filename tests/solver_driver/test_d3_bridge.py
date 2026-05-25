"""Tests for the D3 classifier bridge payloads."""

from __future__ import annotations

from typing import Any

import pytest
from degenbot.d3_bridge import D3OrderRef, handle_d3_classify_payload
from pydantic import ValidationError

_ADDR = "0x" + "11" * 20


def _order(**overrides: Any) -> dict[str, Any]:  # noqa: ANN401
    base: dict[str, Any] = {
        "uid": "0xabcd",
        "owner": _ADDR,
        "sellToken": _ADDR,
        "buyToken": "0x" + "22" * 20,
        "sellAmount": 1_000,
        "buyAmount": 900,
        "feeAmount": 0,
        "validTo": 1_900_000_000,
        "kind": "sell",
        "partiallyFillable": False,
        "signingScheme": "eip712",
        "signature": "0xdead",
        "appData": "0x",
    }
    base.update(overrides)
    return base


def _payload(classification: str, **order_overrides: Any) -> dict[str, Any]:  # noqa: ANN401
    return {
        "classification": classification,
        "reason": "test classification",
        "order": _order(**order_overrides),
    }


def test_classify_amm_routed_yields_should_bid_true() -> None:
    response = handle_d3_classify_payload(_payload("amm_routed"))
    assert response.status == "accepted"
    assert response.should_bid is True
    assert response.reason == "test classification"


@pytest.mark.parametrize("classification", ["cow_matchable", "sandwich_target", "unprofitable"])
def test_non_amm_routed_classifications_do_not_bid(classification: str) -> None:
    response = handle_d3_classify_payload(_payload(classification))
    assert response.should_bid is False


def test_u256_amount_strings_are_parsed_as_decimal_and_hex() -> None:
    decimal = D3OrderRef.model_validate(_order(sellAmount="12345"))
    assert decimal.sell_amount == 12_345
    hexed = D3OrderRef.model_validate(_order(buyAmount="0x1A"))
    assert hexed.buy_amount == 26


def test_integer_amounts_pass_through_the_validator_unchanged() -> None:
    order = D3OrderRef.model_validate(_order(feeAmount=7))
    assert order.fee_amount == 7


def test_invalid_owner_address_is_rejected() -> None:
    with pytest.raises(ValidationError):
        handle_d3_classify_payload(_payload("amm_routed", owner="not-an-address"))


def test_non_positive_sell_amount_is_rejected() -> None:
    with pytest.raises(ValidationError):
        handle_d3_classify_payload(_payload("amm_routed", sellAmount=0))
