# RUF002/RUF003: Unicode math glyphs (·, ³, ², ×, −) are intentional in
# docstrings + comments — they're the canonical notation for the Solidly
# invariants and quoted directly from the contract spec. Replacing with
# ASCII would obscure the math.
# TC002: `ChecksumAddress` is used at runtime as the `to_checksum_address`
# annotation target — cannot move into TYPE_CHECKING.
# TC003: `Fraction` is used at runtime in the constructor signature.
# PLR0913: matches degenbot's existing pool constructor pattern
# (`AerodromeV2Pool.__init__` has 10+ args).
# ruff: noqa: RUF003, TC002, TC003
"""Solidly-fork pool adapter (Arbitrum venues).

Targets the Solidly-fork DEXes deployed on Arbitrum:

  * Ramses     — Solidly v1 fork, oldest live Arbitrum deployment
  * Chronos    — Solidly v1 fork
  * Solidlizard — Solidly v1 fork

Each fork ships two pool families:

  * **volatile**:  `x · y = k`           (UniV2-style, identical math)
  * **stable**:    `y · x³ + x · y³ ≥ k` (Solidly-stable curve)

The math is chain-agnostic — formulas are identical across all
Solidly forks regardless of where they're deployed (Aerodrome on Base,
Velodrome on Optimism, Ramses on Arbitrum, …). We reuse degenbot's
canonical primitives from [`degenbot.solidly.solidly_functions`][] and
inline the `_get_y` solver (Newton-style refinement, capped at 255
iterations — matches every Solidly Solidity implementation).

## Class shape

`SolidlyV1Pool` inherits `PublisherMixin + AbstractLiquidityPool` so it
drops into degenbot's pool taxonomy alongside `UniswapV2Pool`,
`AerodromeV2Pool`, `CurveStableswapPool`. The canonical degenbot entry
point is `calculate_tokens_out_from_tokens_in(token_in, qty)`. State is
caller-supplied at construction (no Web3 batched fetch yet — full
auto-discovery is the upstream-PR scope per CLAUDE.md "Still queued").

## On-chain DexKind mapping

DexKind ordinal **8** (`Solidly`) per `IExecutor.sol` and the
cross-language mirrors in `coordinator/src/types/executor.ts` +
`engine/src/types/executor.rs`. IPC string identifier: `"Solidly"`.

## Pinned references

  * Solidly v1 reference contract:    https://github.com/0xc1ab/solidly
  * Aerodrome (Solidly v2) port:      `vendor/degenbot/src/degenbot/aerodrome/`
  * Solidly math primitives:          `vendor/degenbot/src/degenbot/solidly/solidly_functions.py`
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING, Literal
from weakref import WeakSet

import structlog
from eth_typing import ChecksumAddress
from eth_utils.address import to_checksum_address

# Re-use degenbot's audited Solidly primitives + base classes.
from degenbot.exceptions.evm import EVMRevertError
from degenbot.execution_adapters.adapter_base import configure_execution_logging
from degenbot.registry import pool_registry
from degenbot.solidly.solidly_functions import (
    general_calc_d,
    general_calc_exact_in_stable,
    general_calc_exact_in_volatile,
    general_calc_k,
)
from degenbot.types.abstract import AbstractLiquidityPool
from degenbot.types.concrete import PublisherMixin

if TYPE_CHECKING:
    from degenbot.types.concrete import Subscriber

logger = structlog.get_logger(__name__).bind(
    service="solver",
    component="execution.solidly_adapter",
)


# ---------------------------------------------------------------------------
# Pool state
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True, kw_only=True)
class SolidlyV1PoolState:
    """Frozen snapshot of a Solidly-fork pool at a given block.

    Mirrors degenbot's `AbstractPoolState` shape — `address` + `block`
    plus pool-specific reserves. Immutable so the cache deque can hold
    historical states for re-org replay without copying.
    """

    address: ChecksumAddress
    block: int | None
    reserves_token0: int
    reserves_token1: int


# ---------------------------------------------------------------------------
# Pool class
# ---------------------------------------------------------------------------


class SolidlyV1Pool(PublisherMixin, AbstractLiquidityPool):
    """Solidly v1-fork pool — covers Ramses / Chronos / Solidlizard.

    Construction shape mirrors degenbot's pattern but skips the Web3
    batched-fetch — state is caller-supplied. Auto-discovery via
    `connection_manager.get_web3(...)` is the upstream-PR scope; until
    then the strategist constructs from `getReserves()` / `stable()` /
    `swapFee()` views fetched by whatever Web3 client they use.

    Use `calculate_tokens_out_from_tokens_in(token_in, qty)` for
    exact-input simulation — the canonical degenbot entry point.
    """

    type PoolState = SolidlyV1PoolState

    _state: SolidlyV1PoolState
    _state_cache: deque[SolidlyV1PoolState]

    # Solidly fees are quoted in basis points of `amount_in` typically;
    # callers pre-normalise into a `Fraction`. The denominator base is
    # fork-specific (Ramses uses 1e5 fee precision; this class is
    # denominator-agnostic since it takes a `Fraction` directly).

    def __init__(
        self,
        address: ChecksumAddress | str,
        *,
        token0: ChecksumAddress | str,
        token1: ChecksumAddress | str,
        reserves_token0: int,
        reserves_token1: int,
        decimals_token0: int,
        decimals_token1: int,
        fee: Fraction,
        stable: bool,
        state_block: int | None = None,
        state_cache_depth: int = 8,
        chain_id: int | None = None,
    ) -> None:
        """Construct from a pre-fetched pool snapshot.

        Args:
            address: pool contract address.
            token0 / token1: ERC-20 addresses, sorted as on-chain.
            reserves_token0 / reserves_token1: pool reserves at `state_block`.
            decimals_token0 / decimals_token1: 10^d scalars for each token
                (NOT the raw `decimals()` integer — passes through to
                `general_calc_k` which expects scalar form).
            fee: swap fee as `Fraction` of `amount_in`. `Fraction(1, 10_000)`
                = 1 bp. Use `Fraction(0)` for incentive pools with zero LP fee.
            stable: true if this is a Solidly-stable pool (`y·x³+x·y³≥k`),
                false for volatile (`x·y=k`).
            state_block: block height the snapshot was taken at; None ⇒
                "latest" sentinel.
            state_cache_depth: how many historical states to retain for
                external_update / re-org replay.

        Raises:
            ValueError: on degenerate inputs (zero reserves, etc.).
        """
        if reserves_token0 < 0 or reserves_token1 < 0:
            msg = "reserves must be non-negative"
            raise ValueError(msg)
        if decimals_token0 <= 0 or decimals_token1 <= 0:
            msg = "decimals scalars must be positive"
            raise ValueError(msg)
        if fee < 0 or fee >= 1:
            msg = f"fee must be in [0, 1), got {fee}"
            raise ValueError(msg)

        self.address = to_checksum_address(address)
        self.token0 = to_checksum_address(token0)
        self.token1 = to_checksum_address(token1)
        self.decimals_token0 = decimals_token0
        self.decimals_token1 = decimals_token1
        self.fee = fee
        self.fee_token0 = fee
        self.fee_token1 = fee
        self.stable = stable

        self._state_lock = threading.Lock()

        initial_state = SolidlyV1PoolState(
            address=self.address,
            block=state_block,
            reserves_token0=reserves_token0,
            reserves_token1=reserves_token1,
        )
        self._state = initial_state
        self._state_cache = deque(maxlen=max(1, state_cache_depth))
        self._state_cache.append(initial_state)

        self._subscribers: WeakSet[Subscriber] = WeakSet()
        self._chain_id = chain_id

        # Self-register into degenbot's canonical `pool_registry` when a
        # chain_id is supplied so the IPC dispatcher in
        # `degenbot_ipc.py::_simulate_step` can look this pool up by
        # `(chain_id, pool_address)`. Skipped in unit tests where pools
        # are constructed without chain_id (no registry side-effects).
        if chain_id is not None:
            pool_registry.add(pool=self, chain_id=chain_id, pool_address=self.address)

        variant = "stable" if stable else "volatile"
        fee_bps = 100.0 * float(fee.numerator) / float(fee.denominator) if fee.denominator else 0.0
        self.name = (
            f"{self.token0[:8]}…/{self.token1[:8]}… "  # pylint: disable=unsubscriptable-object
            f"(SolidlyV1Pool, {variant}, {fee_bps:.4f}%)"
        )

    # -- state ----------------------------------------------------------------

    @property
    def state(self) -> SolidlyV1PoolState:
        return self._state

    @property
    def reserves_token0(self) -> int:
        return self._state.reserves_token0

    @property
    def reserves_token1(self) -> int:
        return self._state.reserves_token1

    @property
    def tokens(self) -> tuple[ChecksumAddress, ChecksumAddress]:
        return (self.token0, self.token1)

    # -- swap simulation ------------------------------------------------------

    def calculate_tokens_out_from_tokens_in(
        self,
        token_in: ChecksumAddress | str,
        token_in_quantity: int,
        *,
        override_state: SolidlyV1PoolState | None = None,
    ) -> int:
        """Exact-input simulation — the canonical degenbot entry point.

        Returns `amount_out` in `token_out`'s native units. Routes to
        the volatile (`x·y=k`) or stable (`y·x³+x·y³≥k`) math based on
        `self.stable`. Both come from degenbot's audited primitives.

        Args:
            token_in: address of the token being spent (must be `token0`
                or `token1`).
            token_in_quantity: input quantity in `token_in`'s native units.
                Must be positive.
            override_state: optional state snapshot to use instead of
                `self.state`; useful for hypothetical scenarios without
                mutating the live cache.

        Raises:
            ValueError: if `token_in` is unknown or `token_in_quantity`
                is non-positive.
            EVMRevertError: if the Solidly stable y-solver fails to
                converge (rare; only on degenerate pool states).
        """
        if token_in_quantity <= 0:
            msg = f"token_in_quantity must be positive, got {token_in_quantity}"
            raise ValueError(msg)

        token_in_cs = to_checksum_address(token_in)
        if token_in_cs == self.token0:
            token_idx: Literal[0, 1] = 0
        elif token_in_cs == self.token1:
            token_idx = 1
        else:
            msg = (
                f"token_in {token_in_cs} matches neither pool token ({self.token0}, {self.token1})"
            )
            raise ValueError(
                msg,
            )

        state = override_state if override_state is not None else self._state

        if self.stable:
            return general_calc_exact_in_stable(
                amount_in=token_in_quantity,
                token_in=token_idx,
                reserves0=state.reserves_token0,
                reserves1=state.reserves_token1,
                decimals0=self.decimals_token0,
                decimals1=self.decimals_token1,
                fee=self.fee,
                k_func=general_calc_k,
                get_y_func=_solidly_get_y,
            )

        return general_calc_exact_in_volatile(
            amount_in=token_in_quantity,
            token_in=token_idx,
            reserves0=state.reserves_token0,
            reserves1=state.reserves_token1,
            fee=self.fee,
        )

    # -- state mutation (for state-update events) -----------------------------

    def update_state(
        self,
        *,
        reserves_token0: int,
        reserves_token1: int,
        block: int,
    ) -> SolidlyV1PoolState:
        """Apply a fresh reserves snapshot.

        Mirrors Aerodrome's `external_update` shape — caller (typically
        a feed listener watching `Sync` events) hands in the new
        reserves; the cache deque retains prior states for re-org safety.

        Subscribers are NOT notified here — wire the notification when
        the upstream `Subscriber` protocol surface lands in this adapter.
        """
        if block < (self._state.block or 0):
            msg = f"update for block {block} predates current state block {self._state.block}"
            raise ValueError(
                msg,
            )

        new_state = SolidlyV1PoolState(
            address=self.address,
            block=block,
            reserves_token0=reserves_token0,
            reserves_token1=reserves_token1,
        )

        with self._state_lock:
            if self._state.block == block:
                # Same-block re-emission — replace the head of the cache.
                self._state_cache.pop()
            self._state_cache.append(new_state)
            self._state = new_state

        return new_state


# ---------------------------------------------------------------------------
# Internal — Solidly stable y-solver
# ---------------------------------------------------------------------------


def _solidly_f(x0: int, y: int) -> int:
    """Solidly stable invariant `f(x, y) = x·y·(x² + y²) / 1e36`."""
    a = (x0 * y) // 10**18
    b = (x0 * x0) // 10**18 + (y * y) // 10**18
    return (a * b) // 10**18


def _solidly_get_y(
    x0: int,
    xy: int,
    y: int,
    decimals0: int,
    decimals1: int,
) -> int:
    """Solve `f(x0, y) = xy` for y via Newton refinement (255-iteration cap).

    Identical across every Solidly fork (Aerodrome on Base, Ramses on
    Arbitrum, Velodrome on Optimism, …) — only the venue's CREATE2 salt
    differs. Reference:
    https://github.com/aerodrome-finance/contracts/blob/main/contracts/Pool.sol#L406
    """
    for _ in range(255):
        k = _solidly_f(x0, y)
        if k < xy:
            dy = ((xy - k) * 10**18) // general_calc_d(x0, y)
            if dy == 0:
                if k == xy:
                    return y
                if (
                    general_calc_k(
                        balance_0=x0,
                        balance_1=y + 1,
                        decimals_0=decimals0,
                        decimals_1=decimals1,
                    )
                    > xy
                ):
                    return y + 1
                dy = 1
            y += dy
        else:
            dy = ((k - xy) * 10**18) // general_calc_d(x0, y)
            if dy == 0:
                if k == xy or _solidly_f(x0, y - 1) < xy:
                    return y
                dy = 1
            y -= dy

    raise EVMRevertError(error="Solidly y-solver did not converge in 255 iterations")


def configure_logging(level: str) -> None:
    """Match the existing adapter logging-init convention."""
    configure_execution_logging(level)
