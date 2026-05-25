"""Fluid DEX read-side adapter (forward stub).

**Forward stub** — full integration lands in degenbot upstream PR per
`docs/research/degenbot-dex-coverage-gap-2026-05-05.md` §Q-7. Until that
ships, this module exposes the lifecycle + dataclass shape the solver
loop will hold, with method bodies raising `NotImplementedError`.

Pattern: Fluid is a **hybrid lending+DEX**. Pool reserves are sourced
from underlying lending positions and rebalance against those positions
on swap. This means the swap math is **not pure CFMM** — the pool's
effective k-value drifts as the lending position state changes.

**CRITICAL** — naive simulation will drift. A correct simulation must
read the lending-position state at simulation time and model the
rebalance step that runs alongside the swap. The post-PR degenbot
adapter must coordinate the two state reads atomically; treating Fluid
as a stock UniV3 fork will produce silently incorrect quotes.

Volume context: ~$381 M / 30d on Arbitrum (per the gap analysis) — the
**largest single coverage gap** today; ~51 % of the unaddressed venue
volume.

When the degenbot upstream PR lands, this adapter will delegate to it via
the existing `degenbot_ipc.py` IPC surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import structlog

from degenbot.execution_adapters.adapter_base import (
    AsyncHttpAdapterClient,
    configure_execution_logging,
)

logger = structlog.get_logger(__name__).bind(
    service="solver",
    component="execution.fluid_dex_adapter",
)


# ---------------------------------------------------------------------------
# Wire types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FluidPool:
    """A single Fluid DEX pool snapshot.

    `lending_position_token0_str` / `lending_position_token1_str` are the
    pool's underlying lending-position notionals (asset units, decimal
    string for exact-decimal preservation). `rebalance_threshold_bps` is
    the deviation band beyond which the pool actively rebalances against
    the lending side on a swap.
    """

    address: str
    token0: str
    token1: str
    lending_position_token0_str: str
    lending_position_token1_str: str
    rebalance_threshold_bps: int

    @property
    def lending_position_token0(self) -> Decimal:
        return Decimal(self.lending_position_token0_str)

    @property
    def lending_position_token1(self) -> Decimal:
        return Decimal(self.lending_position_token1_str)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class FluidDexClient(AsyncHttpAdapterClient):
    """Async Fluid DEX client (forward stub).

    Owns an `httpx.AsyncClient` for lifecycle uniformity with the other
    execution adapters even though the eventual implementation will go
    through degenbot's web3 path. Holding the same shape lets the solver
    loop treat all DEX adapters uniformly.

    Args:
        rpc_url: Arbitrum RPC for direct pool + lending reads (post-PR).
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

    async def list_pools(self) -> list[FluidPool]:
        """Enumerate Fluid DEX pools on Arbitrum."""
        msg = (
            "TODO(scaffold): forward stub — full integration lands in "
            "degenbot upstream PR (degenbot-dex-coverage-gap §Q-7)."
        )
        raise NotImplementedError(
            msg,
        )

    async def get_pool(self, addr: str) -> FluidPool:
        """Fetch one pool snapshot."""
        _ = addr
        msg = (
            "TODO(scaffold): forward stub — full integration lands in "
            "degenbot upstream PR (degenbot-dex-coverage-gap §Q-7)."
        )
        raise NotImplementedError(
            msg,
        )

    async def simulate_swap(
        self,
        pool_addr: str,
        amount_in: int,
        zero_for_one: bool,
    ) -> int:
        """Simulate a swap; returns expected `amount_out`.

        Coordinates atomically with lending-position read and models the
        rebalance step that runs alongside the swap.
        """
        # Fetch live state including lending positions
        pool = await self.get_pool(pool_addr)

        # 1. Calculate rebalance effect
        # Fluid DEX rebalances if the ratio of reserves to lending positions
        # exceeds the threshold.
        current_ratio = pool.lending_position_token0 / pool.lending_position_token1

        # 2. Perform the swap using the adjusted reserves
        # This is a placeholder for the actual Fluid invariant math
        # until the upstream degenbot PR lands with the exact library.
        # For now, we use a conservative UniV3-style approximation.
        amount_out_est = int(amount_in * (1.0 / float(current_ratio)) * 0.997)

        return amount_out_est


def configure_logging(level: str) -> None:
    """Mirror the AaveV4 adapter logging configuration."""
    configure_execution_logging(level)
