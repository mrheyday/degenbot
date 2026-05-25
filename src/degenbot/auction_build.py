"""CoW auction quote/provenance request contract for the TS coordinator bridge.

The TypeScript coordinator POSTs this shape to `/auction/build`.  This
module intentionally does not expose an HTTP server and does not submit CoW
solver bids in the current no-bond posture. It validates the cross-process
contract and returns a fail-closed response for quote/provenance analysis.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from degenbot.protocol.models import Auction, SolveResponse
from degenbot.strategies_solver import D3Filter

if TYPE_CHECKING:
    from degenbot.execution.competition_submitter import CompetitionSubmitter
    from degenbot.strategies_solver import SolutionBuilder

ADDRESS_PATTERN = r"^0x[a-fA-F0-9]{40}$"
HEX_PATTERN = r"^0x[a-fA-F0-9]*$"
ORDER_UID_PATTERN = r"^0x[a-fA-F0-9]{112}$"


class AuctionOrderRef(BaseModel):
    """JSON-safe CoW order summary forwarded by the coordinator.

    This is intentionally narrower than `cowprotocol/services`
    `solvers-dto::auction::Order`: it carries enough data for deterministic D3
    pre-batch screening while keeping full settlement construction disabled.
    Amounts are accepted as decimal or 0x-prefixed strings because the TS
    coordinator cannot JSON-encode bigint values directly.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    uid: str = Field(pattern=ORDER_UID_PATTERN)
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

    @field_validator("sell_amount", "buy_amount", "fee_amount", mode="before")
    @classmethod
    def _parse_u256_string(cls, value: object) -> object:
        if isinstance(value, str):
            return int(value, 16) if value.startswith(("0x", "0X")) else int(value, 10)
        return value


class AuctionRef(BaseModel):
    """Minimal CoW auction state forwarded by the coordinator."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    auction_id: str = Field(alias="auctionId", min_length=1)
    orders: tuple[AuctionOrderRef, ...] = Field(min_length=1)
    deadline_ms: int = Field(alias="deadlineMs", gt=0)
    raw: dict[str, Any] | None = None


class AuctionQuotePolicy(BaseModel):
    """Bounded coordinator policy inputs for CoW quote/provenance analysis."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    chain_id: Literal[42161] = Field(alias="chainId")
    max_bid_fraction_bps: int = Field(alias="maxBidFractionBps", ge=0, le=10_000)
    min_profit_usd: float = Field(alias="minProfitUsd", ge=0.0)
    d3_filter_enabled: bool = Field(alias="d3FilterEnabled", default=True)


class AuctionBuildRequest(BaseModel):
    """Request body accepted by the `/auction/build` analysis endpoint."""

    model_config = ConfigDict(frozen=True)

    auction: AuctionRef
    policy: AuctionQuotePolicy

    @field_validator("auction")
    @classmethod
    def _auction_deadline_must_be_live(cls, auction: AuctionRef) -> AuctionRef:
        if auction.deadline_ms <= int(time.time() * 1000):
            raise ValueError("auction deadline elapsed")
        return auction


class AuctionBuildResponse(BaseModel):
    """Fail-closed auction-build response.

    The wire status values are retained for compatibility with older bridge
    clients. In the active posture, `status="bid"` means a solution candidate
    was constructed for analysis; submission only happens when a submitter is
    explicitly configured.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    auction_id: str = Field(alias="auctionId")
    status: Literal["no_bid", "bid"]
    reason: str | None = None
    orders_seen: int = Field(alias="ordersSeen", ge=0)
    candidate_orders: int = Field(alias="candidateOrders", ge=0)
    filtered_orders: int = Field(alias="filteredOrders", ge=0)
    # The built solution, if any.
    solution: dict[str, Any] | None = None
    # Result of the optional competition submission.
    submission_id: str | None = Field(default=None, alias="submissionId")


async def build_auction_response(
    request: AuctionBuildRequest,
    builder: SolutionBuilder,
    submitter: CompetitionSubmitter | None = None,
) -> AuctionBuildResponse:
    """Validate a coordinator auction-build request and build an analysis candidate.

    This handles the bridge from TS minimal refs back to full protocol models
    to leverage the existing Pick C analysis builder without requiring a CoW
    solver bond or key.
    """

    # Stage 1: Screen orders for metrics
    candidate_orders, filtered_orders = _screen_orders(request)

    # Stage 2: Hydrate full auction if possible
    if not request.auction.raw:
        return AuctionBuildResponse(
            auction_id=request.auction.auction_id,
            status="no_bid",
            reason="missing_raw_auction_data",
            orders_seen=len(request.auction.orders),
            candidate_orders=candidate_orders,
            filtered_orders=filtered_orders,
        )

    try:
        auction = Auction.model_validate(request.auction.raw)
    except Exception as err:  # pylint: disable=broad-exception-caught
        return AuctionBuildResponse(
            auction_id=request.auction.auction_id,
            status="no_bid",
            reason=f"raw_auction_validation_failed: {err}",
            orders_seen=len(request.auction.orders),
            candidate_orders=candidate_orders,
            filtered_orders=filtered_orders,
        )

    # Stage 3: Build solution
    strategy_solution = await builder.build(auction)

    if strategy_solution is None:
        return AuctionBuildResponse(
            auction_id=request.auction.auction_id,
            status="no_bid",
            reason="no_profitable_solution",
            orders_seen=len(request.auction.orders),
            candidate_orders=candidate_orders,
            filtered_orders=filtered_orders,
        )

    # Stage 4: Success
    submission_id: str | None = None
    if submitter:
        submission_id = await submitter.submit(auction, strategy_solution.protocol_solution)

    solution_wire = SolveResponse(solutions=[strategy_solution.protocol_solution]).model_dump_wire()
    solutions = solution_wire.get("solutions")
    if not isinstance(solutions, list) or not solutions or not isinstance(solutions[0], dict):
        return AuctionBuildResponse(
            auction_id=request.auction.auction_id,
            status="no_bid",
            reason="invalid_solution_wire_shape",
            orders_seen=len(request.auction.orders),
            candidate_orders=candidate_orders,
            filtered_orders=filtered_orders,
        )

    return AuctionBuildResponse(
        auction_id=request.auction.auction_id,
        status="bid",
        orders_seen=len(request.auction.orders),
        candidate_orders=candidate_orders,
        filtered_orders=filtered_orders,
        solution=solutions[0],
        submission_id=submission_id,
    )


async def handle_auction_build_payload(
    payload: object,
    builder: SolutionBuilder,
    submitter: CompetitionSubmitter | None = None,
) -> AuctionBuildResponse:
    """Parse raw JSON-like payload and return the response."""

    request = AuctionBuildRequest.model_validate(payload)
    return await build_auction_response(request, builder, submitter)


def _screen_orders(request: AuctionBuildRequest) -> tuple[int, int]:
    orders = request.auction.orders
    if not request.policy.d3_filter_enabled:
        return len(orders), 0

    d3_filter = D3Filter()
    candidate_orders = 0
    filtered_orders = 0
    for order in orders:
        peers = [peer for peer in orders if peer.uid != order.uid]
        if d3_filter.should_bid(order, peers):
            candidate_orders += 1
        else:
            filtered_orders += 1
    return candidate_orders, filtered_orders
