"""Aave V4 read-side adapter for the Python solver.

Mirrors the degenbot adapter pattern: thin async wrapper around an external
data source, exposes structured methods for the solver loop to call. Source
is the AaveKit GraphQL endpoint per §07 §1.1a (`@aave/client@next`).

**Scope (v1):** READ-ONLY. Aave V4 is not a v1 flash-loan provider per ADR
chain (§07 §1.1a). This adapter is for liquidation discovery, reserve-rate
reads, oracle reads, and swap-planning — not transaction submission.

V3 (Aave V3) flash loans remain handled by the on-chain Executor per ADR-007.

**Reference path landed (2026-05-07):** `coordinator/src/aavekit/graphql.ts`
exposes the V4-shaped reads — `hubs`, `spokes`, `reserves`, `userPositions`,
`userSummary`, `liquidatePosition` — typed, tested, and ResultAsync-wrapped.
The Python adapter below remains a forward stub per the original "full
integration lands in degenbot upstream PR" plan; until that ships, the
solver loop should call the TS coordinator's `/aavekit/v4/*` HTTP surface
when V4 reads are needed (or wait for the degenbot upstream).

Decimal handling: AaveKit returns `BigDecimal` strings. We preserve them
unchanged on the wire; consumers convert to `Decimal` (exact) or scaled
`int` only when needed. Never coerce through `float` per §07 §1.1a.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import structlog

from degenbot.execution_adapters.adapter_base import (
    AsyncGraphqlAdapterClient,
    GraphqlAdapterConfig,
    configure_execution_logging,
)

logger = structlog.get_logger(__name__).bind(
    service="solver",
    component="execution.aave_v4_adapter",
)


# ---------------------------------------------------------------------------
# Wire types — exact-decimal preserving
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AaveV4Reserve:
    """A single reserve / Spoke asset slot. Exact decimals preserved as strings."""

    spoke_address: str
    underlying: str
    symbol: str
    decimals: int
    supply_apy_str: str
    borrow_apy_str: str
    liquidity_index_str: str
    debt_index_str: str
    oracle_price_usd_str: str

    @property
    def supply_apy(self) -> Decimal:
        return Decimal(self.supply_apy_str)

    @property
    def borrow_apy(self) -> Decimal:
        return Decimal(self.borrow_apy_str)

    @property
    def oracle_price_usd(self) -> Decimal:
        return Decimal(self.oracle_price_usd_str)


@dataclass(frozen=True)
class AaveV4UserHealth:
    """Health-factor snapshot for a single user across one Hub."""

    user_address: str
    hub_address: str
    health_factor_str: str
    total_collateral_usd_str: str
    total_debt_usd_str: str
    available_borrows_usd_str: str

    @property
    def health_factor(self) -> Decimal:
        return Decimal(self.health_factor_str)


@dataclass(frozen=True)
class AaveV4SwapQuote:
    """Read-side swap planning quote. CoW-backed in current AaveKit per §07."""

    src_asset: str
    dst_asset: str
    src_amount_str: str
    dst_amount_str: str
    slippage_bps: int
    route_kind: str  # "cow" | "direct" | "aggregator"


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class AaveV4Client(AsyncGraphqlAdapterClient):
    """Async AaveKit GraphQL client.

    Construct once per solver instance. Uses a shared `httpx.AsyncClient` for
    keepalive across calls. Caller owns the lifecycle (`async with`).
    """

    def __init__(
        self,
        graphql_url: str,
        *,
        timeout_sec: float = 5.0,
        bearer_token: str | None = None,
    ) -> None:
        super().__init__(
            graphql_url,
            timeout_sec=timeout_sec,
            bearer_token=bearer_token,
            config=GraphqlAdapterConfig(
                http_error_event="aave_v4_graphql_error",
                graphql_errors_event="aave_v4_graphql_errors",
                graphql_error_prefix="AaveKit GraphQL errors",
                log=logger,
                log_context={"graphql_url": graphql_url},
            ),
        )

    # -- queries --------------------------------------------------------------

    async def list_reserves(self, hub_address: str) -> list[AaveV4Reserve]:
        """Fetch all reserves under a single Hub. Read-only."""
        # TODO(scaffold): wire actual AaveKit GraphQL `reserves(hub: $hub)` query.
        # The v4 schema is documented at https://aave.com/docs/api/raw-md/aave-v4
        # and the @aave/client@next TypeScript SDK has the ready-made query strings.
        # For Python we issue raw GraphQL via httpx.
        _ = hub_address
        raise NotImplementedError(
            "TODO(scaffold): wire AaveKit GraphQL `reserves(hub: $hub)` query and map response → AaveV4Reserve list.",
        )

    async def get_user_health(self, hub_address: str, user_address: str) -> AaveV4UserHealth:
        """Fetch health-factor snapshot for one user under one Hub. Read-only."""
        _ = (hub_address, user_address)
        raise NotImplementedError(
            "TODO(scaffold): wire AaveKit GraphQL `userPosition` query and map response.",
        )

    async def query_swap(
        self,
        *,
        src_asset: str,
        dst_asset: str,
        src_amount: int,
    ) -> AaveV4SwapQuote:
        """Plan a swap via AaveKit's CoW-backed swap action. Read-only.

        This is a quote — does NOT submit. The solver uses this as a sanity
        check on intent paths before submitting solutions to CoW competition.
        Per §07 §1.1a: "AaveKit token swaps are currently CoW-backed; route
        them through intent-policy review before any signing/submission."
        """
        _ = (src_asset, dst_asset, src_amount)
        raise NotImplementedError(
            "TODO(scaffold): wire AaveKit `useTokenSwap` planner equivalent. "
            "Result is a quote only; signing/submission is solver-side.",
        )

    async def get_oracle_price(self, hub_address: str, asset: str) -> Decimal:
        """Spoke-oracle reserve price (`ISpoke(spoke).ORACLE().getReservePrice`).

        Note: AaveKit GraphQL exposes `oracle_price_usd` on the reserve, but per
        §07 §1.1a we MUST NOT use that as an on-chain safety input — for that
        the solver reads the on-chain Spoke oracle directly via web3. This
        method is for off-chain planning only.
        """
        _ = (hub_address, asset)
        raise NotImplementedError(
            "TODO(scaffold): GraphQL `reserve(hub:..., asset:...).oraclePrice` read.",
        )


# ---------------------------------------------------------------------------
# Solver-facing convenience
# ---------------------------------------------------------------------------


async def quote_intent_path(
    client: AaveV4Client,
    *,
    intent_src: str,
    intent_dst: str,
    intent_src_amount: int,
) -> AaveV4SwapQuote:
    """Validate an intent path against AaveKit's planner.

    Used by the solver loop as ONE of multiple validators (alongside degenbot's
    pathfinder + the aggregator-validator adapter). Returns a quote; caller
    decides whether to act on it.
    """
    return await client.query_swap(
        src_asset=intent_src,
        dst_asset=intent_dst,
        src_amount=intent_src_amount,
    )


def configure_logging(level: str) -> None:
    """Mirror the degenbot adapter logging configuration."""
    configure_execution_logging(level)
