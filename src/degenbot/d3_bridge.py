"""D3 classifier bridge payloads.

The TS coordinator can pre-classify individual CoW orders and forward the
result here for solver-side telemetry / policy hooks. This endpoint does
not build or submit a bid; `/auction/build` remains the auction-level bid
construction surface.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ADDRESS_PATTERN = r"^0x[a-fA-F0-9]{40}$"
HEX_PATTERN = r"^0x[a-fA-F0-9]*$"


class D3OrderRef(BaseModel):
    """JSON-safe CoW order summary forwarded by the TS coordinator."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    uid: str = Field(pattern=HEX_PATTERN)
    owner: str = Field(pattern=ADDRESS_PATTERN)
    sell_token: str = Field(alias="sellToken", pattern=ADDRESS_PATTERN)
    buy_token: str = Field(alias="buyToken", pattern=ADDRESS_PATTERN)
    sell_amount: int = Field(alias="sellAmount", gt=0)
    buy_amount: int = Field(alias="buyAmount", gt=0)
    fee_amount: int = Field(alias="feeAmount", ge=0)
    valid_to: int = Field(alias="validTo", gt=0)
    kind: Literal["buy", "sell"]
    partially_fillable: bool = Field(alias="partiallyFillable")
    signing_scheme: Literal["eip712", "ethsign", "presign", "eip1271"] = Field(alias="signingScheme")
    signature: str = Field(pattern=HEX_PATTERN)
    app_data: str = Field(alias="appData", pattern=HEX_PATTERN)

    @field_validator("sell_amount", "buy_amount", "fee_amount", mode="before")
    @classmethod
    def _parse_u256_string(cls, value: object) -> object:
        if isinstance(value, str):
            return int(value, 16) if value.startswith(("0x", "0X")) else int(value, 10)
        return value


class D3ClassifyRequest(BaseModel):
    """Coordinator-classified D3 order payload."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    classification: Literal["amm_routed", "cow_matchable", "sandwich_target", "unprofitable"]
    reason: str = Field(min_length=1)
    order: D3OrderRef


class D3ClassifyResponse(BaseModel):
    """Fail-closed acknowledgement for `/d3/classify`."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    status: Literal["accepted"] = "accepted"
    should_bid: bool = Field(alias="shouldBid")
    reason: str


def handle_d3_classify_payload(raw: object) -> D3ClassifyResponse:
    """Validate one classified D3 order and return the solver policy bit."""

    request = D3ClassifyRequest.model_validate(raw)
    return D3ClassifyResponse(
        should_bid=request.classification == "amm_routed",
        reason=request.reason,
    )
