"""Tests for SolutionBuilder and QuoteEngineClient."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import respx

from degenbot.protocol.models import Auction, Order, OrderClass, OrderKind, SigningScheme
from degenbot.quote_engine import AggregatorQuote, QuoteEngineClient, QuoteRequest
from degenbot.strategies_solver.d3_filter import D3Filter
from degenbot.strategies_solver.solver_quality import SolutionBuilder


@pytest.fixture
def mock_quote_engine() -> MagicMock:
    client = MagicMock(spec=QuoteEngineClient)
    client.quote = AsyncMock()
    return client


@pytest.fixture
def mock_d3_filter() -> MagicMock:
    filter = MagicMock(spec=D3Filter)
    filter.should_bid.return_value = True
    return filter


@pytest.fixture
def sample_auction() -> Auction:
    return Auction(
        id="auction-1",
        tokens={
            "0x" + "b" * 40: {"referencePrice": "1000000000000000000"}  # 1.0 reference
        },
        orders=[
            Order(
                uid="0x" + "1" * 112,
                sell_token="0x" + "a" * 40,
                buy_token="0x" + "b" * 40,
                sell_amount=1000,
                full_sell_amount=1000,
                buy_amount=900,
                full_buy_amount=900,
                valid_to=int(1e10),
                kind=OrderKind.SELL,
                owner="0x" + "c" * 40,
                partially_fillable=False,
                order_class=OrderClass.MARKET,
                app_data="0x",
                signing_scheme=SigningScheme.EIP712,
                signature="0x",
            )
        ],
        liquidity=[],
        effective_gas_price=10**9,
        deadline="2026-05-10T10:00:00Z",
        surplus_capturing_jit_order_owners=[],
    )


@pytest.mark.asyncio
async def test_solution_builder_builds_profitable_solution(
    mock_quote_engine: MagicMock,
    mock_d3_filter: MagicMock,
    sample_auction: Auction,
) -> None:
    mock_quote_engine.quote.return_value = AggregatorQuote(
        source="1inch",
        sell_amount="1000",
        buy_amount="1100",
        router="0x" + "r" * 40,
        calldata="0x1234",
        estimated_gas=100000,
    )

    builder = SolutionBuilder(mock_quote_engine, mock_d3_filter, min_profit_usd=0.0)
    solution = await builder.build(sample_auction)

    assert solution is not None
    assert solution.auction_id == "auction-1"
    assert solution.estimated_profit_usd >= 0.0
    assert len(solution.protocol_solution.prices) == 2
    assert solution.protocol_solution.prices["0x" + "a" * 40] == 1100


@pytest.mark.asyncio
async def test_solution_builder_skips_d3_filtered_orders(
    mock_quote_engine: MagicMock,
    mock_d3_filter: MagicMock,
    sample_auction: Auction,
) -> None:
    mock_d3_filter.should_bid.return_value = False

    builder = SolutionBuilder(mock_quote_engine, mock_d3_filter, min_profit_usd=0.0)
    solution = await builder.build(sample_auction)

    assert solution is None
    mock_quote_engine.quote.assert_not_called()


@pytest.mark.asyncio
async def test_quote_engine_client_retries_on_transport_error(respx_mock: respx.MockRouter) -> None:
    coordinator_url = "http://coordinator/quote"
    respx_mock.post(coordinator_url).side_effect = [
        httpx.ConnectError("fail"),
        httpx.Response(
            200,
            json={
                "source": "0x",
                "sellAmount": "100",
                "buyAmount": "200",
                "router": "0x123",
                "calldata": "0x",
                "estimatedGas": 50000,
            },
        ),
    ]

    async with QuoteEngineClient(coordinator_url) as client:
        quote = await client.quote(
            QuoteRequest(sell_token="0x1", buy_token="0x2", sell_amount="100")
        )
        assert quote.buy_amount == "200"
