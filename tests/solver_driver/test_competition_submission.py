"""Unit tests for CompetitionSubmitter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from degenbot.config import Settings
from degenbot.execution.competition_submitter import CompetitionSubmitter
from degenbot.orderbook.client import OrderbookClient
from degenbot.protocol.models import Auction, Interaction, Trade
from degenbot.protocol.models import Solution as ProtocolSolution
from pydantic import SecretStr


@pytest.fixture
def mock_client() -> MagicMock:
    client = MagicMock(spec=OrderbookClient)
    client.post_competition_solution = AsyncMock(return_value="submission-123")
    return client


@pytest.fixture
def settings() -> Settings:
    return Settings(
        cow_solver_address="0x" + "11" * 20,
        cow_solver_private_key=SecretStr("0x" + "22" * 32),
    )


@pytest.mark.asyncio
async def test_submit_success(
    mock_client: MagicMock,
    settings: Settings,
) -> None:
    submitter = CompetitionSubmitter(client=mock_client, settings=settings)

    auction = Auction(
        id="auction-1",
        tokens={},
        orders=[],
        liquidity=[],
        effective_gas_price=10**9,
        deadline="2026-05-10T12:00:00Z",
        surplus_capturing_jit_order_owners=[],
    )
    solution = ProtocolSolution(
        id=1,
        prices={},
        trades=[],
        interactions=[],
    )

    result = await submitter.submit(auction, solution)

    assert result == "submission-123"
    mock_client.post_competition_solution.assert_called_once()

    # Verify the payload was wrapped correctly
    call_args = mock_client.post_competition_solution.call_args[0][0]
    assert call_args.solution.id == 1
    assert call_args.signature.startswith("0x")
    assert len(call_args.signature) == 132  # 0x + 65 bytes * 2


def test_build_typed_data_uses_full_settlement_shape(
    mock_client: MagicMock,
    settings: Settings,
) -> None:
    submitter = CompetitionSubmitter(client=mock_client, settings=settings)
    auction = Auction(
        id="auction-1",
        tokens={},
        orders=[],
        liquidity=[],
        effective_gas_price=10**9,
        deadline="2026-05-10T12:00:00Z",
        surplus_capturing_jit_order_owners=[],
    )
    solution = ProtocolSolution(
        id=1,
        prices={"0xaf88d065e77c8cC2239327C5EDb3A432268e5831": 10**6},
        trades=[
            Trade.model_validate(
                {
                    "sellTokenIndex": 0,
                    "buyTokenIndex": 1,
                    "receiver": "0x" + "33" * 20,
                    "sellAmount": "1000000",
                    "buyAmount": "999000",
                    "validTo": 1_776_886_400,
                    "appData": "0x" + "44" * 32,
                    "feeAmount": "1000",
                    "flags": 0,
                    "executedAmount": "1000000",
                    "signature": "0x1234",
                }
            )
        ],
        interactions=[
            Interaction.model_validate(
                {
                    "target": "0x" + "55" * 20,
                    "value": 0,
                    "callData": "0xabcdef",
                }
            )
        ],
        preInteractions=[{"target": "0x" + "66" * 20, "value": 0, "callData": "0x"}],
        postInteractions=[{"target": "0x" + "77" * 20, "value": 0, "callData": "0x"}],
    )

    typed_data = submitter._build_typed_data(auction, solution)

    assert typed_data["primaryType"] == "Settlement"
    assert typed_data["domain"]["chainId"] == 42161
    assert typed_data["types"]["Settlement"] == [
        {"name": "tokens", "type": "address[]"},
        {"name": "clearingPrices", "type": "uint256[]"},
        {"name": "trades", "type": "Trade[]"},
        {"name": "interactions", "type": "Interaction[][]"},
    ]
    assert typed_data["message"]["tokens"] == ["0xaf88d065e77c8cC2239327C5EDb3A432268e5831"]
    assert typed_data["message"]["clearingPrices"] == [10**6]
    assert typed_data["message"]["trades"][0]["sellTokenIndex"] == 0
    assert typed_data["message"]["trades"][0]["buyAmount"] == "999000"
    assert typed_data["message"]["interactions"][0][0]["target"] == "0x" + "66" * 20
    assert typed_data["message"]["interactions"][1][0]["target"] == "0x" + "55" * 20
    assert typed_data["message"]["interactions"][2][0]["target"] == "0x" + "77" * 20


@pytest.mark.asyncio
async def test_submit_error_logged_and_swallowed(
    mock_client: MagicMock,
    settings: Settings,
) -> None:
    mock_client.post_competition_solution.side_effect = Exception("network error")
    submitter = CompetitionSubmitter(client=mock_client, settings=settings)

    auction = Auction(
        id="auction-1",
        tokens={},
        orders=[],
        liquidity=[],
        effective_gas_price=10**9,
        deadline="2026-05-10T12:00:00Z",
        surplus_capturing_jit_order_owners=[],
    )
    solution = ProtocolSolution(id=1, prices={}, trades=[], interactions=[])

    result = await submitter.submit(auction, solution)

    assert result is None
