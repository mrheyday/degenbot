"""Balancer V3 read-side adapter (forward stub).

**Forward stub** — full integration lands in degenbot upstream PR per
`docs/research/balancer-v3-degenbot-adapter-design-2026-05-05.md` (Q-6).
Until that ships, this module exposes the lifecycle + dataclass shape the
solver loop will hold, with method bodies raising `NotImplementedError`.

Pattern: Balancer V3 is a **vault-architecture** AMM — pool tokens and
balances live on a shared `Vault` contract, not on the pool contract
itself. Pool-specific math (Weighted, Stable, StableSurge, ReCLAMM)
applies on top of vault-tracked balances. This is materially different
from V3 concentrated liquidity and from Balancer V2.

Initial scope (per design § "Pool Identity"): Weighted + Stable only.
StableSurge / ReCLAMM are deferred until dynamic-fee hook behavior is
mapped explicitly.

When the degenbot upstream PR lands, this adapter will delegate to it via
the existing `degenbot_ipc.py` IPC surface. Pinned Arbitrum addresses
(Vault, factories, routers, discovery anchors) live in the sibling module
`balancer_v3_addresses` — sourced from the cached
`balancer/balancer-deployments` task outputs and verified against the
design doc.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import structlog

from degenbot.execution_adapters import balancer_v3_weighted_math as _wm
from degenbot.execution_adapters.adapter_base import (
    AsyncHttpAdapterClient,
    configure_execution_logging,
)

logger = structlog.get_logger(__name__).bind(
    service="solver",
    component="execution.balancer_v3_adapter",
)


# ---------------------------------------------------------------------------
# Wire types
# ---------------------------------------------------------------------------


class BalancerV3PoolType(Enum):
    """Initial pool-math families (per design § "Pool Identity")."""

    WEIGHTED = "weighted"
    STABLE = "stable"


@dataclass(frozen=True)
class BalancerV3Pool:
    """A single Balancer V3 pool snapshot.

    Identity is **vault-centered**: a pool is identified by `(vault, pool)`
    rather than by pool address alone. `tokens`, `balances_raw`,
    `scaling_factors`, and (for WEIGHTED pools) `normalized_weights` are
    aligned tuples of equal length; ordering follows the Vault's pool-token
    registry, not ERC-20 balance heuristics.

    `static_swap_fee_bps` is the pool's stored fee. `aggregate_swap_fee_bps`
    is the actually-charged fee after protocol fee aggregation; for pools
    with dynamic-fee hooks the two will diverge.

    `normalized_weights` is populated for WEIGHTED pools (sum to FixedPoint
    ONE = 1e18) and `None` for STABLE / other pool types — those use
    different state fields (amplification parameter, etc.).
    """

    address: str
    block: int
    vault: str
    pool_type: BalancerV3PoolType
    tokens: tuple[str, ...]
    balances_raw: tuple[int, ...]
    scaling_factors: tuple[int, ...]
    static_swap_fee_bps: int
    aggregate_swap_fee_bps: int
    normalized_weights: tuple[int, ...] | None = None


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class BalancerV3Client(AsyncHttpAdapterClient):
    """Async Balancer V3 client (forward stub).

    Owns an `httpx.AsyncClient` for lifecycle uniformity with the other
    execution adapters even though the eventual implementation will go
    through degenbot's web3 path. Holding the same shape lets the solver
    loop treat all DEX adapters uniformly.

    Args:
        rpc_url: Arbitrum RPC for direct Vault/pool reads (post-PR).
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

    async def list_pools(self) -> list[BalancerV3Pool]:
        """Enumerate Balancer V3 pools on Arbitrum.

        Discovery is factory-driven via Vault `PoolRegistered` logs from the
        Vault `fromBlock` pinned in the design doc; the upstream impl will
        filter by registered factory (Weighted, Stable) to bound scope.
        """
        raise NotImplementedError(
            "TODO(scaffold): forward stub — full integration lands in "
            "degenbot upstream PR (balancer-v3-degenbot-adapter-design Q-6).",
        )

    async def get_pool(self, addr: str) -> BalancerV3Pool:
        """Fetch one pool snapshot via Vault `getPoolTokenInfo`."""
        _ = addr
        raise NotImplementedError(
            "TODO(scaffold): forward stub — full integration lands in "
            "degenbot upstream PR (balancer-v3-degenbot-adapter-design Q-6).",
        )

    async def simulate_swap(
        self,
        pool_addr: str,
        amount_in: int,
        zero_for_one: bool,
    ) -> int:
        """Simulate a swap; returns expected `amount_out`.

        Pulls the pool snapshot via `get_pool` (currently a forward stub
        until on-chain Vault hydration lands), then dispatches by pool_type
        to the corresponding math module. Pure-math simulation without RPC
        is available via the module-level `simulate_weighted_swap_from_snapshot`.
        """
        pool = await self.get_pool(pool_addr)
        token_in_index, token_out_index = (0, 1) if zero_for_one else (1, 0)
        return simulate_weighted_swap_from_snapshot(
            pool,
            token_in_index,
            token_out_index,
            amount_in,
        )


# ---------------------------------------------------------------------------
# Pure-math helpers (no RPC) — testable in isolation
# ---------------------------------------------------------------------------


def simulate_weighted_swap_from_snapshot(
    pool: BalancerV3Pool,
    token_in_index: int,
    token_out_index: int,
    amount_in: int,
) -> int:
    """Compute `amount_out` for a Weighted-pool swap from a pool snapshot.

    Pure function — no RPC, no I/O. Useful for fork-test simulation and
    for the eventual `BalancerV3Client.simulate_swap` once `get_pool` is
    wired to live RPC. Applies the **static swap fee** (not aggregate fee)
    as on-chain `Pool.onSwap` does for the deterministic swap path.

    Raises:
        ValueError: if `pool.pool_type != WEIGHTED`, indices are out of
            range, or weights are missing.
        balancer_v3_weighted_math.MaxInRatioError: if `amount_in` exceeds
            the 30%-of-balance cap.
    """
    if pool.pool_type is not BalancerV3PoolType.WEIGHTED:
        raise ValueError(
            f"simulate_weighted_swap_from_snapshot only supports WEIGHTED pools; got {pool.pool_type.value}",
        )
    if pool.normalized_weights is None:
        raise ValueError("WEIGHTED pool snapshot missing normalized_weights")

    n = len(pool.tokens)
    if not 0 <= token_in_index < n or not 0 <= token_out_index < n:
        raise ValueError(
            f"token indices out of range for {n}-token pool: in={token_in_index} out={token_out_index}",
        )
    if token_in_index == token_out_index:
        raise ValueError("token_in_index and token_out_index must differ")

    # Apply static swap fee on the input side: the fee is taken from
    # `amount_in` before the math, so the user's effective input is reduced.
    # Fee is in 18-decimal FP units (e.g., 30 bps = 30e14).
    fee_fp = pool.static_swap_fee_bps * 10**14  # bps → 18-decimal FP
    # `amount_in_after_fee = amount_in * (1 - fee)` rounded down (favors pool).
    if fee_fp >= 10**18:
        raise ValueError(f"static_swap_fee_bps {pool.static_swap_fee_bps} >= 100%")
    amount_in_after_fee = (amount_in * (10**18 - fee_fp)) // 10**18

    return _wm.compute_out_given_exact_in(
        balance_in=pool.balances_raw[token_in_index],
        weight_in=pool.normalized_weights[token_in_index],
        balance_out=pool.balances_raw[token_out_index],
        weight_out=pool.normalized_weights[token_out_index],
        amount_in=amount_in_after_fee,
    )


def configure_logging(level: str) -> None:
    """Mirror the AaveV4 adapter logging configuration."""
    configure_execution_logging(level)
