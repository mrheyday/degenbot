"""Orchestrates CoW competition solution signing and submission.

Coordinates the SolutionBuilder, EIP-712 signer, and OrderbookClient to
participate in the CoW external solver competition.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Protocol

import structlog

from degenbot.cow.models import CompetitionSolution
from degenbot.cow.signing import sign_solution
from degenbot.utils.metrics import SUBMISSION_LATENCY, SUBMISSION_REQUESTS

if TYPE_CHECKING:
    from pydantic import SecretStr

    from degenbot.cow.client import OrderbookClient
    from degenbot.cow.models import Auction
    from degenbot.cow.models import Solution as ProtocolSolution

    class CompetitionSubmitterSettings(Protocol):
        cow_solver_address: str | None
        cow_solver_private_key: SecretStr | None
        chain_id: int

log = structlog.get_logger(__name__).bind(service="solver", component="competition_submitter")

GPV2_SETTLEMENT_ADDRESS = "0x9008D19f58AAbD9eD0D60971565AA8510560ab41"
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
ZERO_BYTES32 = "0x0000000000000000000000000000000000000000000000000000000000000000"


class CompetitionSubmitter:
    """Signs and submits solutions to the CoW Competition API."""

    def __init__(
        self,
        client: OrderbookClient,
        settings: CompetitionSubmitterSettings,
    ) -> None:
        self._client = client
        self._settings = settings
        if settings.cow_solver_address is None or settings.cow_solver_private_key is None:
            msg = "CompetitionSubmitter requires explicit CoW solver address and private key"
            raise ValueError(msg)
        self._solver_address = settings.cow_solver_address
        self._private_key = settings.cow_solver_private_key

    async def submit(
        self,
        auction: Auction,
        solution: ProtocolSolution,
    ) -> str | None:
        """Sign and submit a solution for the given auction.

        Returns the response body (usually a submission id) or None on error.
        """
        start_time = asyncio.get_event_loop().time()
        try:
            # 1. Build EIP-712 typed data
            typed_data = self._build_typed_data(auction, solution)

            # 2. Sign
            signature_bytes = sign_solution(typed_data, self._private_key)
            signature_hex = "0x" + signature_bytes.hex()

            # 3. Wrap in CompetitionSolution
            comp_sol = CompetitionSolution(
                solution=solution,
                signature=signature_hex,
            )

            # 4. POST
            log.info(
                "submitting_solution",
                auction_id=auction.id,
                solver=self._solver_address,
            )
            response = await self._client.post_competition_solution(comp_sol)

            latency = asyncio.get_event_loop().time() - start_time
            SUBMISSION_LATENCY.observe(latency)
            SUBMISSION_REQUESTS.labels(outcome="success").inc()

            log.info(
                "solution_submitted",
                auction_id=auction.id,
                response=response,
                latency_sec=latency,
            )
            return response

        except Exception as err:  # pylint: disable=broad-exception-caught
            SUBMISSION_REQUESTS.labels(outcome="error").inc()
            log.exception(
                "submission_failed",
                auction_id=auction.id,
                error=str(err),
            )
            return None

    def _build_typed_data(
        self,
        _auction: Auction,
        solution: ProtocolSolution,
    ) -> dict[str, Any]:
        """Construct the full EIP-712 typed data for a settlement.

        Matches the CoW Protocol 'Settlement' type used for external solver
        authentication in the competition.
        """
        pre_interactions = self._build_interactions(
            self._field(solution, "pre_interactions", "preInteractions", default=[])
        )
        custom_interactions = self._build_interactions(solution.interactions)
        post_interactions = self._build_interactions(
            self._field(solution, "post_interactions", "postInteractions", default=[])
        )

        return {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"},
                ],
                "Settlement": [
                    {"name": "tokens", "type": "address[]"},
                    {"name": "clearingPrices", "type": "uint256[]"},
                    {"name": "trades", "type": "Trade[]"},
                    {"name": "interactions", "type": "Interaction[][]"},
                ],
                "Trade": [
                    {"name": "sellTokenIndex", "type": "uint256"},
                    {"name": "buyTokenIndex", "type": "uint256"},
                    {"name": "receiver", "type": "address"},
                    {"name": "sellAmount", "type": "uint256"},
                    {"name": "buyAmount", "type": "uint256"},
                    {"name": "validTo", "type": "uint32"},
                    {"name": "appData", "type": "bytes32"},
                    {"name": "feeAmount", "type": "uint256"},
                    {"name": "flags", "type": "uint256"},
                    {"name": "executedAmount", "type": "uint256"},
                    {"name": "signature", "type": "bytes"},
                ],
                "Interaction": [
                    {"name": "target", "type": "address"},
                    {"name": "value", "type": "uint256"},
                    {"name": "callData", "type": "bytes"},
                ],
            },
            "primaryType": "Settlement",
            "domain": {
                "name": "Gnosis Protocol",
                "version": "v2",
                "chainId": self._settings.chain_id,
                "verifyingContract": GPV2_SETTLEMENT_ADDRESS,
            },
            "message": {
                "tokens": list(solution.prices.keys()),
                "clearingPrices": list(solution.prices.values()),
                "trades": [self._build_trade(trade) for trade in solution.trades],
                "interactions": [pre_interactions, custom_interactions, post_interactions],
            },
        }

    @classmethod
    def _build_trade(cls, trade: Any) -> dict[str, Any]:
        return {
            "sellTokenIndex": cls._field(trade, "sell_token_index", "sellTokenIndex", default=0),
            "buyTokenIndex": cls._field(trade, "buy_token_index", "buyTokenIndex", default=0),
            "receiver": cls._field(trade, "receiver", default=ZERO_ADDRESS),
            "sellAmount": cls._uint_string_field(trade, "sell_amount", "sellAmount"),
            "buyAmount": cls._uint_string_field(trade, "buy_amount", "buyAmount"),
            "validTo": cls._field(trade, "valid_to", "validTo", default=0),
            "appData": cls._field(trade, "app_data", "appData", default=ZERO_BYTES32),
            "feeAmount": cls._uint_string_field(trade, "fee_amount", "feeAmount"),
            "flags": cls._field(trade, "flags", default=0),
            "executedAmount": cls._uint_string_field(
                trade,
                "executed_amount",
                "executedAmount",
            ),
            "signature": cls._field(trade, "signature", default="0x"),
        }

    @classmethod
    def _build_interactions(cls, interactions: Any) -> list[dict[str, Any]]:
        if interactions is None:
            return []
        return [
            {
                "target": cls._field(interaction, "target", default=ZERO_ADDRESS),
                "value": cls._field(interaction, "value", default=0),
                "callData": cls._field(interaction, "call_data", "callData", default="0x"),
            }
            for interaction in interactions
        ]

    @staticmethod
    def _field(obj: Any, *names: str, default: Any) -> Any:
        if isinstance(obj, Mapping):
            for name in names:
                if name in obj:
                    return obj[name]

        for name in names:
            if hasattr(obj, name):
                return getattr(obj, name)

        extra = getattr(obj, "model_extra", None)
        if isinstance(extra, Mapping):
            for name in names:
                if name in extra:
                    return extra[name]

        return default

    @classmethod
    def _uint_string_field(cls, obj: Any, *names: str) -> str:
        return str(cls._field(obj, *names, default=0))
