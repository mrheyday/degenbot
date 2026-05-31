"""Ostium Oracle Gap source (JB-11).

Detects price divergence between Chainlink and Stork/Ostium.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from collections.abc import Sequence

    from web3 import AsyncWeb3

logger = logging.getLogger(__name__)

NORMALIZED_PRICE_DECIMALS = 18
PROBABILITY_BPS_DENOMINATOR = 10_000

MarketType = Literal["equity", "fx", "crypto", "commodity"]


class OstiumOracleGapPayload(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)
    aggregator: str
    ostium_source: str = Field(alias="ostiumSource")
    symbol: str
    onchain_price: int = Field(alias="onchainPrice")
    ostium_price: int = Field(alias="ostiumPrice")
    gap_bps: int = Field(alias="gapBps")
    reference_published_at_ms: int = Field(alias="referencePublishedAtMs")
    ostium_published_at_ms: int = Field(alias="ostiumPublishedAtMs")


class OstiumOracleGapSource:
    """Poller for Ostium vs Chainlink price divergence."""

    def __init__(
        self,
        w3: AsyncWeb3[Any],
        symbols: Sequence[str],
        ostium_feeds: dict[str, str],
        reference_feeds: dict[str, str],
        gap_threshold_bps: int = 50,
        poll_interval_s: float = 10.0,
        max_price_age_ms: int = 60_000,
    ) -> None:
        self._w3 = w3
        self._symbols = symbols
        self._ostium_feeds = ostium_feeds
        self._reference_feeds = reference_feeds
        self._gap_threshold_bps = gap_threshold_bps
        self._poll_interval_s = poll_interval_s
        self._max_price_age_ms = max_price_age_ms
        self._running = False
        self._handlers: list[Any] = []

    def on_gap(self, handler: Any) -> None:
        self._handlers.append(handler)

    async def start(self) -> None:
        self._running = True
        while self._running:
            try:
                await self.poll()
            except Exception:
                logger.exception("OstiumOracleGapSource.poll failed")
            await asyncio.sleep(self._poll_interval_s)

    async def stop(self) -> None:
        self._running = False

    async def poll(self) -> None:
        tasks = [self._poll_symbol(s) for s in self._symbols]
        await asyncio.gather(*tasks)

    async def _poll_symbol(self, symbol: str) -> None:
        ostium_addr = self._ostium_feeds.get(symbol)
        ref_addr = self._reference_feeds.get(symbol)
        if not ostium_addr or not ref_addr:
            return

        # Simplified reading logic (Chainlink AggregatorV3Interface)
        # In production, use multicall or specialized reader.
        try:
            onchain = await self._read_aggregator(ref_addr)
            ostium = await self._read_aggregator(ostium_addr)

            if onchain is None or ostium is None:
                return

            now_ms = int(time.time() * 1000)
            if (
                now_ms - onchain["updatedAtMs"] > self._max_price_age_ms
                or now_ms - ostium["updatedAtMs"] > self._max_price_age_ms
            ):
                return

            gap_bps = ((ostium["price"] - onchain["price"]) * 10_000) // onchain["price"]
            if abs(gap_bps) < self._gap_threshold_bps:
                return

            payload = OstiumOracleGapPayload(
                aggregator=ref_addr,
                ostium_source=ostium_addr,
                symbol=symbol,
                onchain_price=onchain["price"],
                ostium_price=ostium["price"],
                gap_bps=gap_bps,
                reference_published_at_ms=onchain["updatedAtMs"],
                ostium_published_at_ms=ostium["updatedAtMs"],
            )

            for h in self._handlers:
                h(payload)

        except Exception as e:
            logger.warning("Failed to poll %s: %s", symbol, e)

    async def _read_aggregator(self, address: str) -> dict[str, Any] | None:
        # Minimal ABI for latestRoundData
        abi = [
            {
                "inputs": [],
                "name": "latestRoundData",
                "outputs": [
                    {"name": "roundId", "type": "uint80"},
                    {"name": "answer", "type": "int256"},
                    {"name": "startedAt", "type": "uint256"},
                    {"name": "updatedAt", "type": "uint256"},
                    {"name": "answeredInRound", "type": "uint80"},
                ],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "stateMutability": "view",
                "type": "function",
            },
        ]
        contract = self._w3.eth.contract(address=self._w3.to_checksum_address(address), abi=abi)

        decimals = await contract.functions.decimals().call()
        round_data = await contract.functions.latestRoundData().call()

        answer = round_data[1]
        updated_at = round_data[3]

        if answer <= 0 or updated_at == 0:
            return None

        if decimals <= 18:
            price = answer * (10 ** (18 - decimals))
        else:
            price = answer // (10 ** (decimals - 18))

        return {
            "price": price,
            "updatedAtMs": updated_at * 1000,
        }
