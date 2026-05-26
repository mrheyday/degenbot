"""Maverick V2 read-side adapter (forward stub).

**Forward stub** — full integration lands in degenbot upstream PR per
`docs/research/degenbot-dex-coverage-gap-2026-05-05.md` §Q-5. Until that
ships, this module exposes the lifecycle + dataclass shape the solver
loop will hold, with method bodies raising `NotImplementedError`.

Pattern: Maverick V2 uses **directional-LP bins** (similar in spirit to
UniV3 ticks but with bin-shift mechanics — bins move with the active
price, creating predictable price-discovery moments). This is distinct
from UniV3 concentrated liquidity and needs custom math.

Volume context: ~$20 M / 30d on Arbitrum (per the gap analysis). Strategic
relevance is the directional-LP price-discovery edge during volatile
windows, not the absolute volume.

When the degenbot upstream PR lands, this adapter will delegate to it via
the existing `degenbot_ipc.py` IPC surface.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog

from degenbot.execution_adapters.adapter_base import (
    AsyncHttpAdapterClient,
    configure_execution_logging,
)

logger = structlog.get_logger(__name__).bind(
    service="solver",
    component="execution.maverick_v2_adapter",
)

MAVERICK_V2_FORWARD_STUB_MESSAGE = (
    "TODO(scaffold): forward stub -- full integration lands in "
    "degenbot upstream PR (degenbot-dex-coverage-gap §Q-5)."
)
MAVERICK_V2_BIN_SHIFT_STUB_MESSAGE = (
    "Maverick V2 swap simulation is not implemented: Bin-shift liquidity math must be "
    "ported before this adapter can quote safely."
)


# ---------------------------------------------------------------------------
# Wire types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MaverickV2Pool:
    """A single Maverick V2 pool snapshot.

    `current_bin` is the active bin index (signed-ish; Maverick uses bin
    deltas). `sqrt_price_x96` mirrors UniV3's Q64.96 form — Maverick uses
    the same fixed-point format for tick-equivalent price encoding.
    """

    address: str
    token0: str
    token1: str
    current_bin: int
    sqrt_price_x96: int
    fee_bps: int


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class MaverickV2Client(AsyncHttpAdapterClient):
    """Async Maverick V2 client (forward stub).

    Owns an `httpx.AsyncClient` for lifecycle uniformity with the other
    execution adapters even though the eventual implementation will go
    through degenbot's web3 path. Holding the same shape lets the solver
    loop treat all DEX adapters uniformly.

    Args:
        rpc_url: Arbitrum RPC for direct pool reads (post-PR).
        timeout_sec: per-request timeout.
    """

    def __init__(
        self,
        rpc_url: str,
        *,
        timeout_sec: float = 5.0,
    ) -> None:
        self._rpc_url = rpc_url
        super().__init__(
            rpc_url,
            timeout_sec=timeout_sec,
            log=logger,
            log_context={"rpc_url": rpc_url},
        )

    # -- queries --------------------------------------------------------------

    async def list_pools(self) -> list[MaverickV2Pool]:
        """Enumerate Maverick V2 pools on Arbitrum."""
        raise NotImplementedError(MAVERICK_V2_FORWARD_STUB_MESSAGE)

    async def get_pool(self, addr: str) -> MaverickV2Pool:
        """Fetch one pool snapshot."""
        _ = addr
        raise NotImplementedError(MAVERICK_V2_FORWARD_STUB_MESSAGE)

    async def simulate_swap(
        self,
        pool_addr: str,
        amount_in: int,
        zero_for_one: bool,
    ) -> int:
        """Simulate a swap; returns expected `amount_out`.

        Maverick V2 uses a bin-based liquidity model. This simulation
        approximates the output by iterating through active bins.
        """
        _ = pool_addr, amount_in, zero_for_one
        raise NotImplementedError(MAVERICK_V2_BIN_SHIFT_STUB_MESSAGE)


def configure_logging(level: str) -> None:
    """Mirror the AaveV4 adapter logging configuration."""
    configure_execution_logging(level)
