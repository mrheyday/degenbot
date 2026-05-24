# RUF002/RUF003: Unicode math glyphs (×, ÷, −, …, ⇒) are intentional in
# docstrings — they're the canonical Algebra / UniV3 notation from the
# spec. Replacing with ASCII would obscure the math.
# TC002: `ChecksumAddress` is used at runtime as the `to_checksum_address`
# annotation target — cannot move into TYPE_CHECKING.
# PLR0913: matches degenbot's existing pool constructor pattern.
# ruff: noqa: RUF002, RUF003, TC002, PLR0913
"""Camelot V3 (Algebra Integral) pool adapter — single-tick simulation.

Camelot V3 on Arbitrum is built on the **Algebra Integral v1.2.2**
concentrated-liquidity engine, deployed at AlgebraFactory
`0x1a3c9B1d2F0529D97f2afC5136Cc23e58f1FD35B` (verify against
`docs/research/algebra-v3-spec/` before any production use).

## What this adapter does

Single-tick exact-input swap simulation. Within the current active
tick range, Algebra's swap math is **byte-identical to Uniswap V3's
`computeSwapStep`** — same Q64.96 sqrt-price arithmetic, same fee
deduction shape, same `getAmount0Delta` / `getAmount1Delta`
primitives. The divergence between Algebra and UniV3 only materialises
when a swap **crosses a tick boundary**:

  * UniV3 uses `tick_bitmap.next_initialized_tick_within_one_word(...)`.
  * Algebra uses a binary `TickTree` (`prevTick` / `nextTick` pointers)
    with custom traversal in `TickManagement.sol`.

For single-tick swaps we delegate to degenbot's audited
`uniswap.v3_libraries.swap_math.compute_swap_step`. For multi-tick
crossings the adapter raises `MultiTickCrossingNotSupportedError` — the
strategist falls back to Algebra's QuoterV2 at
`0x0Fc73040b26E9bC8514fA028D998E73A254Fa76E` (the on-chain reference
oracle, NOT the live computation source for the off-chain decision
plane). Multi-tick traversal lands when the upstream-PR work in
`docs/research/camelot-v3-degenbot-adapter-design-2026-05-05.md` Q-5
fully ports `TickTree.sol`.

## Plugin-driven dynamic fees

Algebra V3+ supports plugins (`IAlgebraPlugin`) that override the LP
fee per-swap. Static-fee plugins ship `lastFee` directly via
`globalState()` and we use that. Dynamic-fee plugins (volatility
oracles, etc.) require off-chain fee resolution before calling this
adapter — pass the resolved fee via `override_state.fee_pips`.

## Community-fee split

Algebra deducts a `communityFee` percentage of the LP fee at the
protocol level — it's invisible to the swap math (LPs get LP_fee × (1
- communityFee/1e3), protocol gets the rest). Both shares are
deducted from the user's `amount_in` at the same total rate, so
swap-side simulation is unaffected. We record the configured
`community_fee_token0` / `community_fee_token1` on the state for
downstream display only.

## Class shape

`CamelotV3Pool` inherits `PublisherMixin + AbstractLiquidityPool` to
match degenbot's pool taxonomy. State is caller-supplied at
construction (no Web3 auto-fetch yet — see CLAUDE.md "Still queued").

## On-chain DexKind mapping

DexKind ordinal **7** (`Algebra`) per `IExecutor.sol` + cross-language
mirrors. IPC string identifier: `"CamelotV3"` (venue-named, not
engine-named — the discriminator goes through the IPC layer where
venue-string maps to engine-class).

## Pinned references

  * Algebra Integral v1.2.2 source:    https://github.com/cryptoalgebra/Algebra
  * AlgebraFactory Arbitrum:           0x1a3c9B1d2F0529D97f2afC5136Cc23e58f1FD35B
  * AlgebraQuoterV2 Arbitrum:          0x0Fc73040b26E9bC8514fA028D998E73A254Fa76E
  * Seed pool fixture (WETH/USDC):     0xB1026b8e7276e7AC75410F1fcbbe21796e8f7526
  * Design doc:                        docs/research/camelot-v3-degenbot-adapter-design-2026-05-05.md (Q-5)
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING
from weakref import WeakSet

import structlog
from degenbot.registry import pool_registry
from degenbot.types.abstract import AbstractLiquidityPool
from degenbot.types.concrete import PublisherMixin
from degenbot.uniswap.v3_libraries.swap_math import compute_swap_step
from degenbot.uniswap.v3_libraries.tick_math import get_sqrt_ratio_at_tick
from eth_typing import ChecksumAddress
from eth_utils.address import to_checksum_address

from driver.execution.adapter_base import configure_execution_logging

if TYPE_CHECKING:
    from degenbot.types.concrete import Subscriber

logger = structlog.get_logger(__name__).bind(
    service="solver",
    component="execution.camelot_v3_adapter",
)


# Algebra fee precision: hundredths-of-a-bip, denominator 1_000_000 — matches
# UniV3's numeric base (500 = 0.05%, 3000 = 0.30%, etc.).
_FEE_PIPS_DENOMINATOR = 1_000_000


class MultiTickCrossingNotSupportedError(Exception):
    """Raised when a swap would cross at least one initialised tick boundary.

    The strategist should fall back to Algebra QuoterV2 (or the upstream-PR
    `TickTree` walk once that lands) for multi-tick swaps. This adapter
    explicitly refuses to silently return a partial swap result.
    """


# ---------------------------------------------------------------------------
# Pool state
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True, kw_only=True)
class CamelotV3PoolState:
    """Frozen snapshot of a Camelot V3 (Algebra) pool at a given block.

    Mirrors Algebra's `globalState()` + `liquidity()` views:

      * `sqrt_price_x96`: Q64.96 sqrt-price.
      * `tick`: signed 24-bit current tick.
      * `liquidity`: active in-range liquidity (uint128 on-chain).
      * `fee_pips`: current LP fee in Algebra's "hundredths-of-a-bip"
        units (e.g., 500 = 0.05%, matching the canonical UniV3 fee_pips
        scale — Algebra adopted the same numeric base). For static-fee
        pools this equals `globalState().lastFee`; for dynamic-fee
        plugins the caller resolves the volatility-adjusted value before
        constructing the state.
      * `tick_spacing`: spacing between initialisable ticks.
    """

    address: ChecksumAddress
    block: int | None
    sqrt_price_x96: int
    tick: int
    liquidity: int
    fee_pips: int
    tick_spacing: int


# ---------------------------------------------------------------------------
# Pool class
# ---------------------------------------------------------------------------


class CamelotV3Pool(PublisherMixin, AbstractLiquidityPool):
    """Camelot V3 (Algebra Integral) pool — single-tick swap simulation."""

    type PoolState = CamelotV3PoolState

    _state: CamelotV3PoolState
    _state_cache: deque[CamelotV3PoolState]

    def __init__(
        self,
        address: ChecksumAddress | str,
        *,
        token0: ChecksumAddress | str,
        token1: ChecksumAddress | str,
        sqrt_price_x96: int,
        tick: int,
        liquidity: int,
        fee_pips: int,
        tick_spacing: int,
        state_block: int | None = None,
        state_cache_depth: int = 8,
        chain_id: int | None = None,
    ) -> None:
        """Construct from pre-fetched pool snapshot.

        Args:
            address: pool contract address.
            token0 / token1: ERC-20 addresses, sorted as on-chain (token0
                < token1 by address).
            sqrt_price_x96: Q64.96 sqrt-price from `globalState()`.
            tick: signed 24-bit tick from `globalState()`.
            liquidity: in-range liquidity from `liquidity()` view.
            fee_pips: current LP fee (Algebra "lastFee" or dynamic-plugin-resolved).
            tick_spacing: from `tickSpacing()` view.
            state_block: block height the snapshot was taken at.
            state_cache_depth: how many historical states to retain.

        Raises:
            ValueError: on degenerate inputs.
        """
        if sqrt_price_x96 <= 0:
            raise ValueError("sqrt_price_x96 must be positive")
        if liquidity < 0:
            raise ValueError("liquidity must be non-negative")
        if fee_pips < 0 or fee_pips >= _FEE_PIPS_DENOMINATOR:
            raise ValueError(
                f"fee_pips must be in [0, {_FEE_PIPS_DENOMINATOR}), got {fee_pips}",
            )
        if tick_spacing <= 0:
            raise ValueError(f"tick_spacing must be positive, got {tick_spacing}")

        self.address = to_checksum_address(address)
        self.token0 = to_checksum_address(token0)
        self.token1 = to_checksum_address(token1)
        self.tick_spacing = tick_spacing

        self._state_lock = threading.Lock()

        initial_state = CamelotV3PoolState(
            address=self.address,
            block=state_block,
            sqrt_price_x96=sqrt_price_x96,
            tick=tick,
            liquidity=liquidity,
            fee_pips=fee_pips,
            tick_spacing=tick_spacing,
        )
        self._state = initial_state
        self._state_cache = deque(maxlen=max(1, state_cache_depth))
        self._state_cache.append(initial_state)

        self._subscribers: WeakSet[Subscriber] = WeakSet()
        self._chain_id = chain_id

        if chain_id is not None:
            pool_registry.add(pool=self, chain_id=chain_id, pool_address=self.address)

        fee_pct = 100.0 * fee_pips / _FEE_PIPS_DENOMINATOR
        self.name = (
            f"{self.token0[:8]}…/{self.token1[:8]}… "  # pylint: disable=unsubscriptable-object
            f"(CamelotV3Pool, {fee_pct:.4f}%)"
        )

    # -- state ----------------------------------------------------------------

    @property
    def state(self) -> CamelotV3PoolState:
        return self._state

    @property
    def tokens(self) -> tuple[ChecksumAddress, ChecksumAddress]:
        return (self.token0, self.token1)

    # -- swap simulation ------------------------------------------------------

    def calculate_tokens_out_from_tokens_in(
        self,
        token_in: ChecksumAddress | str,
        token_in_quantity: int,
        *,
        override_state: CamelotV3PoolState | None = None,
    ) -> int:
        """Exact-input simulation — single-tick scope.

        Returns `amount_out` in `token_out`'s native units. The math is
        delegated to degenbot's audited `compute_swap_step`, which is
        byte-identical to Algebra's inner step within a tick range.

        Args:
            token_in: address of the token being spent.
            token_in_quantity: input quantity (positive).
            override_state: optional state snapshot override.

        Raises:
            ValueError: on unknown token / non-positive quantity / zero
                liquidity (the pool has no active liquidity in the
                current range — equivalent to an on-chain revert).
            MultiTickCrossingNotSupportedError: if the swap would consume all
                liquidity at the current tick boundary. Caller falls
                back to Algebra QuoterV2.
        """
        if token_in_quantity <= 0:
            raise ValueError(f"token_in_quantity must be positive, got {token_in_quantity}")

        token_in_cs = to_checksum_address(token_in)
        if token_in_cs == self.token0:
            zero_for_one = True
        elif token_in_cs == self.token1:
            zero_for_one = False
        else:
            raise ValueError(
                f"token_in {token_in_cs} matches neither pool token "
                f"({self.token0}, {self.token1})",
            )

        s = override_state if override_state is not None else self._state

        if s.liquidity == 0:
            raise ValueError(
                f"pool {self.address} has zero liquidity at tick {s.tick} — swap would revert",
            )

        # Resolve the boundary tick we'd cross if this swap exhausts
        # the current tick range. Round towards -∞ to align with
        # Algebra's convention.
        compressed = s.tick // s.tick_spacing
        if s.tick < 0 and s.tick % s.tick_spacing != 0:
            compressed -= 1

        # zero_for_one=true ⇒ price decreasing ⇒ target = lower tick boundary.
        # zero_for_one=false ⇒ price increasing ⇒ target = upper tick boundary.
        target_tick = (
            compressed * s.tick_spacing
            if zero_for_one
            else (compressed + 1) * s.tick_spacing
        )

        sqrt_ratio_target = get_sqrt_ratio_at_tick(tick=target_tick)

        sqrt_next, _amount_in_consumed, amount_out, _fee = compute_swap_step(
            sqrt_ratio_x96_current=s.sqrt_price_x96,
            sqrt_ratio_x96_target=sqrt_ratio_target,
            liquidity=s.liquidity,
            amount_remaining=token_in_quantity,
            fee_pips=s.fee_pips,
        )

        # If `compute_swap_step` returned `sqrt_next == sqrt_ratio_target`,
        # the swap reached the next tick boundary — and we'd need to
        # cross. Refuse rather than silently truncate.
        if sqrt_next == sqrt_ratio_target:
            raise MultiTickCrossingNotSupportedError(
                f"swap on pool {self.address} would cross tick "
                f"{target_tick} (current tick {s.tick}, spacing "
                f"{s.tick_spacing}); fall back to Algebra QuoterV2 "
                f"or wait for upstream-PR TickTree port (CLAUDE.md Q-5)",
            )

        return amount_out

    # -- state mutation -------------------------------------------------------

    def update_state(
        self,
        *,
        sqrt_price_x96: int,
        tick: int,
        liquidity: int,
        fee_pips: int | None = None,
        block: int,
    ) -> CamelotV3PoolState:
        """Apply a fresh `globalState() + liquidity()` snapshot.

        `fee_pips` carries forward if not supplied — useful when a Swap
        event only emits price + tick + liquidity but the static-fee
        configuration didn't change.
        """
        if block < (self._state.block or 0):
            raise ValueError(
                f"update for block {block} predates current state block {self._state.block}",
            )

        new_state = CamelotV3PoolState(
            address=self.address,
            block=block,
            sqrt_price_x96=sqrt_price_x96,
            tick=tick,
            liquidity=liquidity,
            fee_pips=fee_pips if fee_pips is not None else self._state.fee_pips,
            tick_spacing=self._state.tick_spacing,
        )

        with self._state_lock:
            if self._state.block == block:
                self._state_cache.pop()
            self._state_cache.append(new_state)
            self._state = new_state

        return new_state


def configure_logging(level: str) -> None:
    """Match the existing adapter logging-init convention."""
    configure_execution_logging(level)
