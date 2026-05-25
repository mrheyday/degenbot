"""Pydantic-model tests for the CoW Solver Engine API protocol.

Validates that we round-trip the canonical wire shape from
[`cowprotocol/services::crates/solvers/openapi.yml`](https://github.com/cowprotocol/services/blob/main/crates/solvers/openapi.yml).
The fixture under `tests/data/auction_minimal.json` is the smallest
auction body that satisfies the OpenAPI spec.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from degenbot.protocol import (
    Auction,
    Order,
    OrderClass,
    OrderKind,
    SigningScheme,
    Solution,
    SolveResponse,
    TokenInfo,
)

DATA_DIR = Path(__file__).parent / "data"


def _load(name: str) -> dict[str, object]:
    data: dict[str, object] = json.loads((DATA_DIR / name).read_text())
    return data


# -- TokenInfo --------------------------------------------------------------


class TestTokenInfo:
    def test_decodes_decimal_string_reference_price_to_int(self) -> None:
        ti = TokenInfo.model_validate(
            {
                "decimals": 18,
                "symbol": "WETH",
                "referencePrice": "1000000000000000000",
                "availableBalance": "5000000000000000000",
                "trusted": True,
            },
        )
        assert ti.reference_price == 10**18
        assert ti.available_balance == 5 * 10**18
        assert ti.trusted is True

    def test_accepts_hex_prefixed_bigint(self) -> None:
        ti = TokenInfo.model_validate({"referencePrice": "0xde0b6b3a7640000"})
        assert ti.reference_price == 10**18

    def test_accepts_scientific_notation_bigint(self) -> None:
        # Some CoW serializers emit "1e18" for large round numbers.
        ti = TokenInfo.model_validate({"referencePrice": "1e18"})
        assert ti.reference_price == 10**18

    def test_rejects_non_integer_decimal_bigint(self) -> None:
        with pytest.raises(ValidationError):
            TokenInfo.model_validate({"referencePrice": "1.5"})

    def test_extra_fields_passthrough(self) -> None:
        ti = TokenInfo.model_validate({"trusted": True, "futureField": 42})
        # extra='allow' preserves unknown fields without error.
        assert ti.trusted is True


# -- Order ------------------------------------------------------------------


class TestOrder:
    def test_decodes_canonical_order(self) -> None:
        order = Order.model_validate(_minimal_order())
        assert order.kind is OrderKind.SELL
        assert order.signing_scheme is SigningScheme.EIP712
        assert order.order_class is OrderClass.MARKET
        assert order.sell_amount == 10**18
        assert order.partially_fillable is False

    def test_rejects_missing_required_field(self) -> None:
        body = _minimal_order()
        del body["sellAmount"]
        with pytest.raises(ValidationError) as ei:
            Order.model_validate(body)
        msgs = "\n".join(str(e) for e in ei.value.errors())
        assert "sellAmount" in msgs or "sell_amount" in msgs


# -- Auction ----------------------------------------------------------------


class TestAuction:
    def test_decodes_minimal_auction(self) -> None:
        auc = Auction.model_validate(_load("auction_minimal.json"))
        assert auc.id == "auction-1"
        assert auc.effective_gas_price == 1_500_000_000
        assert auc.deadline == datetime(2027, 6, 1, 12, 0, tzinfo=UTC)
        assert len(auc.orders) == 1
        assert auc.orders[0].uid == "0xorder1"

    def test_passes_liquidity_through_unchanged(self) -> None:
        body = _load("auction_minimal.json")
        body["liquidity"] = [
            {
                "id": "pool-1",
                "address": "0x" + "1" * 40,
                "gasEstimate": "100000",
                "kind": "constantProduct",
                "tokens": {},
                "fee": "0.003",
                "router": "0x" + "2" * 40,
            },
        ]
        auc = Auction.model_validate(body)
        assert len(auc.liquidity) == 1
        assert auc.liquidity[0]["kind"] == "constantProduct"

    def test_rejects_invalid_deadline(self) -> None:
        body = _load("auction_minimal.json")
        body["deadline"] = "not-a-date"
        with pytest.raises(ValidationError):
            Auction.model_validate(body)


# -- SolveResponse + Solution ----------------------------------------------


class TestSolveResponse:
    def test_empty_solutions_serializes_to_empty_array(self) -> None:
        resp = SolveResponse(solutions=[])
        wire = resp.model_dump_wire()
        assert wire == {"solutions": []}

    def test_solution_with_prices_serializes_bigint_to_string(self) -> None:
        sol = Solution.model_validate(
            {
                "id": 7,
                "prices": {
                    "0x" + "a" * 40: "1000000000000000000",
                    "0x" + "b" * 40: "500000000000000000",
                },
                "trades": [],
                "interactions": [],
            },
        )
        resp = SolveResponse(solutions=[sol])
        wire = resp.model_dump_wire()
        assert wire["solutions"][0]["id"] == 7
        # Prices over 2**32 must be emitted as decimal strings.
        prices = wire["solutions"][0]["prices"]
        assert all(isinstance(v, str) for v in prices.values())
        assert prices["0x" + "a" * 40] == "1000000000000000000"

    def test_round_trip_preserves_optional_fields(self) -> None:
        body: dict[str, object] = {
            "id": 1,
            "prices": {},
            "trades": [],
            "interactions": [],
            "gas": 500_000,
            "maxFeePerGas": "30000000000",
        }
        sol = Solution.model_validate(body)
        wire = SolveResponse(solutions=[sol]).model_dump_wire()
        s = wire["solutions"][0]
        assert s["gas"] == 500_000
        assert s["maxFeePerGas"] == "30000000000"


# -- helpers ---------------------------------------------------------------


def _minimal_order() -> dict[str, object]:
    return {
        "uid": "0xorder1",
        "sellToken": "0x" + "1" * 40,
        "buyToken": "0x" + "2" * 40,
        "sellAmount": "1000000000000000000",
        "buyAmount": "1000000",
        "fullBuyAmount": "1000000",
        "validTo": 9_999_999_999,
        "kind": "sell",
        "owner": "0x" + "3" * 40,
        "partiallyFillable": False,
        "preInteractions": [],
        "postInteractions": [],
        "class": "market",
        "appData": "0x" + "0" * 64,
        "signingScheme": "eip712",
        "signature": "0x" + "0" * 130,
    }
