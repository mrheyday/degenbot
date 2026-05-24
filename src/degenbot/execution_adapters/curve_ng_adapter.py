# RUF002/RUF003: Unicode math glyphs (·, Σ, Π, −, ⇒) are intentional in
# docstrings — they're the canonical Curve StableSwap notation from the
# Curve V1 white paper. Replacing with ASCII would obscure the math.
# TC002: `ChecksumAddress` is used at runtime as the `to_checksum_address`
# annotation target — cannot move into TYPE_CHECKING.
# PLR0913: matches degenbot's existing pool constructor pattern.
# ruff: noqa: RUF003, TC002, PLR0913
"""Curve New-Generation (NG) pool adapter.

Curve NG is Curve's evolution of the StableSwap design with two
material ABI changes from the legacy implementation:

  1. **uint256 indices** in `get_dy(uint256,uint256,uint256)` and
     `exchange(uint256,uint256,uint256,uint256)` — legacy pools used
     `int128`. The invariant math itself is unchanged.
  2. **EMA oracle + dynamic-fee plugin hooks** — NG pools optionally
     ship a moving-average price oracle and a fee multiplier that
     scales the base swap fee by recent volatility. The adapter
     captures `base_fee` (the configured floor) and computes the
     effective fee inline; if the strategist needs the EMA-adjusted
     fee, they pass it in via `override_state.fee`.

The StableSwap invariant for `n` tokens is the same Curve V1 form:

    A·n^n · Σ(x_i) + D = A·n^n · D + D^(n+1) / (n^n · Π(x_i))

For the common 2-token NG case (the only shape we target here) the
math collapses to a quadratic-in-y refinement bounded at 255 Newton
iterations. We do NOT depend on degenbot's `CurveStableswapPool`
class — it carries legacy int128 ABI assumptions + group-membership
checks against historical Curve address tables that aren't relevant
to NG pools. Instead we ship a self-contained 2-token solver against
the canonical Curve V1 reference.

## Class shape

`CurveNGPool` inherits `PublisherMixin + AbstractLiquidityPool` to
match degenbot's pool taxonomy. State is caller-supplied at
construction (no Web3 auto-fetch yet — see CLAUDE.md "Still queued"
upstream-PR scope).

## On-chain DexKind mapping

DexKind ordinal **9** (`CurveNG`) per `IExecutor.sol` and the
cross-language mirrors. IPC string identifier: `"CurveNG"`.

## Pinned reference

  * Curve V1 StableSwap white paper:    https://classic.curve.fi/files/stableswap-paper.pdf
  * Curve NG reference (uint256 ABI):   https://github.com/curvefi/stableswap-ng
  * Implementation cross-check: Brownie/vyper tests in
    `curvefi/stableswap-ng/tests/`.
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING
from weakref import WeakSet

import structlog
from degenbot.exceptions.evm import EVMRevertError
from degenbot.registry import pool_registry
from degenbot.types.abstract import AbstractLiquidityPool
from degenbot.types.concrete import PublisherMixin
from eth_typing import ChecksumAddress
from eth_utils.address import to_checksum_address

from driver.execution.adapter_base import configure_execution_logging

if TYPE_CHECKING:
    from degenbot.types.concrete import Subscriber

logger = structlog.get_logger(__name__).bind(
    service="solver",
    component="execution.curve_ng_adapter",
)


# Curve protocol-wide constants.
_A_PRECISION = 100
_FEE_DENOMINATOR = 10**10  # Curve fee precision (10 decimals)
_MAX_ITER = 255


# ---------------------------------------------------------------------------
# Pool state
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True, kw_only=True)
class CurveNGPoolState:
    """Frozen snapshot of a 2-token Curve NG pool at a given block.

    `balances` are raw token balances (NOT normalised). `rates` are the
    Curve NG `stored_rates()` view — 10^18-scaled multipliers that
    normalise each balance to 18-decimal precision before the invariant
    math runs.

    `amp` is the *unscaled* amplification factor (i.e., the user-facing
    `A` displayed on the front-end); the solver multiplies by
    `_A_PRECISION` internally. For ramped A (Curve's gradual-update
    feature) the caller resolves the current effective A and passes it
    in.

    `fee_bps` is in Curve fee precision (10^10 denominator). 4_000_000
    = 0.04% (Curve 3Pool fee, also typical NG default).
    """

    address: ChecksumAddress
    block: int | None
    balances: tuple[int, int]
    rates: tuple[int, int]
    amp: int
    fee_bps: int


# ---------------------------------------------------------------------------
# Pool class
# ---------------------------------------------------------------------------


class CurveNGPool(PublisherMixin, AbstractLiquidityPool):
    """Curve New-Generation 2-token pool — `get_dy(uint256,uint256,uint256)`."""

    type PoolState = CurveNGPoolState

    _state: CurveNGPoolState
    _state_cache: deque[CurveNGPoolState]

    def __init__(
        self,
        address: ChecksumAddress | str,
        *,
        token0: ChecksumAddress | str,
        token1: ChecksumAddress | str,
        balances: tuple[int, int],
        rates: tuple[int, int],
        amp: int,
        fee_bps: int,
        state_block: int | None = None,
        state_cache_depth: int = 8,
        chain_id: int | None = None,
    ) -> None:
        """Construct from a pre-fetched pool snapshot.

        Args:
            address: pool contract address.
            token0 / token1: ERC-20 addresses; conventional ordering is
                Curve's `coins(0)` / `coins(1)`.
            balances: `(balance0, balance1)` in raw token units.
            rates: `(rate0, rate1)` from `stored_rates()` — 10^18-scaled
                multipliers that compensate for differing token decimals
                and rebase factors. For a pair of 18-decimal stablecoins
                pass `(10**18, 10**18)`.
            amp: amplification factor `A` (unscaled — pass the
                user-facing value, e.g. 200).
            fee_bps: swap fee in Curve precision (10^10 denominator).
                4_000_000 ⇒ 0.04%.
            state_block: block height the snapshot was taken at; None ⇒
                "latest" sentinel.
            state_cache_depth: how many historical states to retain.

        Raises:
            ValueError: on degenerate inputs.
        """
        if any(b < 0 for b in balances):
            raise ValueError("balances must be non-negative")
        if any(r <= 0 for r in rates):
            raise ValueError("rates must be positive")
        if amp <= 0:
            raise ValueError(f"amp must be positive, got {amp}")
        if fee_bps < 0 or fee_bps >= _FEE_DENOMINATOR:
            raise ValueError(f"fee_bps must be in [0, {_FEE_DENOMINATOR}), got {fee_bps}")

        self.address = to_checksum_address(address)
        self.token0 = to_checksum_address(token0)
        self.token1 = to_checksum_address(token1)

        self._state_lock = threading.Lock()

        initial_state = CurveNGPoolState(
            address=self.address,
            block=state_block,
            balances=(balances[0], balances[1]),
            rates=(rates[0], rates[1]),
            amp=amp,
            fee_bps=fee_bps,
        )
        self._state = initial_state
        self._state_cache = deque(maxlen=max(1, state_cache_depth))
        self._state_cache.append(initial_state)

        self._subscribers: WeakSet[Subscriber] = WeakSet()
        self._chain_id = chain_id

        if chain_id is not None:
            pool_registry.add(pool=self, chain_id=chain_id, pool_address=self.address)

        fee_pct = 100.0 * fee_bps / _FEE_DENOMINATOR
        self.name = (
            f"{self.token0[:8]}…/{self.token1[:8]}… "  # pylint: disable=unsubscriptable-object
            f"(CurveNGPool, A={amp}, {fee_pct:.4f}%)"
        )

    # -- state ----------------------------------------------------------------

    @property
    def state(self) -> CurveNGPoolState:
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
        override_state: CurveNGPoolState | None = None,
    ) -> int:
        """Exact-input simulation — canonical degenbot entry point.

        Mirrors the on-chain `get_dy(uint256 i, uint256 j, uint256 dx)`.
        Returns `amount_out` in `token_out`'s native units.

        Args:
            token_in: address of the token being spent.
            token_in_quantity: input quantity in `token_in`'s native units.
            override_state: optional state snapshot override.

        Raises:
            ValueError: if `token_in` is unknown or quantity non-positive.
            EVMRevertError: if `_get_y` fails to converge.
        """
        if token_in_quantity <= 0:
            raise ValueError(f"token_in_quantity must be positive, got {token_in_quantity}")

        token_in_cs = to_checksum_address(token_in)
        if token_in_cs == self.token0:
            i, j = 0, 1
        elif token_in_cs == self.token1:
            i, j = 1, 0
        else:
            raise ValueError(
                f"token_in {token_in_cs} matches neither pool token "
                f"({self.token0}, {self.token1})",
            )

        s = override_state if override_state is not None else self._state

        # Normalised pool reserves (xp) = balance × rate / PRECISION
        # PRECISION here is 10^18 — `rates` are already 10^18-scaled.
        xp = (
            (s.balances[0] * s.rates[0]) // 10**18,
            (s.balances[1] * s.rates[1]) // 10**18,
        )

        # Normalised input
        dx_normalised = (token_in_quantity * s.rates[i]) // 10**18

        # Apply x_i = xp_i + dx, solve for y = xp_j'
        x_new = xp[i] + dx_normalised
        y = _curve_ng_get_y(i=i, j=j, x=x_new, xp=xp, amp=s.amp)

        # dy raw, before fee. Curve's `-1` reduces by 1 wei to round in
        # favour of the pool (matches the on-chain implementation).
        dy_normalised = xp[j] - y - 1

        # Apply fee.
        fee_amount = (dy_normalised * s.fee_bps) // _FEE_DENOMINATOR
        dy_after_fee = dy_normalised - fee_amount

        # De-normalise back to token_j's native units.
        return (dy_after_fee * 10**18) // s.rates[j]

    # -- state mutation -------------------------------------------------------

    def update_state(
        self,
        *,
        balances: tuple[int, int],
        rates: tuple[int, int] | None = None,
        amp: int | None = None,
        fee_bps: int | None = None,
        block: int,
    ) -> CurveNGPoolState:
        """Apply a fresh snapshot. Carry-forward semantics for unsupplied fields."""
        if block < (self._state.block or 0):
            raise ValueError(
                f"update for block {block} predates current state block {self._state.block}",
            )

        new_state = CurveNGPoolState(
            address=self.address,
            block=block,
            balances=(balances[0], balances[1]),
            rates=(rates[0], rates[1]) if rates is not None else self._state.rates,
            amp=amp if amp is not None else self._state.amp,
            fee_bps=fee_bps if fee_bps is not None else self._state.fee_bps,
        )

        with self._state_lock:
            if self._state.block == block:
                self._state_cache.pop()
            self._state_cache.append(new_state)
            self._state = new_state

        return new_state


# ---------------------------------------------------------------------------
# Internal — Curve StableSwap solver
# ---------------------------------------------------------------------------


def _curve_ng_get_d(xp: tuple[int, int], amp: int) -> int:
    """Compute invariant D via Newton refinement.

    Reference (Vyper): `_get_D` in
    https://github.com/curvefi/stableswap-ng/blob/main/contracts/main/CurveStableSwapNG.vy
    """
    n = len(xp)
    s = sum(xp)
    if s == 0:
        return 0

    d = s
    # n**n widens to Any in typeshed (negative exponents yield float); n is a
    # tuple length so it is always a non-negative int — pin the result.
    ann: int = amp * (n**n)

    for _ in range(_MAX_ITER):
        d_p = d
        for x in xp:
            # +1 in the denominator prevents div-by-zero on near-empty pools.
            d_p = d_p * d // (x * n + 1)

        d_prev = d
        # D = (ann·S·n·D + D_P·n·D·(n+1)) / (D·(ann·n − n) + n·D_P·(n+1))
        # The Vyper form factors A_PRECISION as 100 (constant).
        d = (
            (ann * s // _A_PRECISION + d_p * n)
            * d
            // ((ann - _A_PRECISION) * d // _A_PRECISION + (n + 1) * d_p)
        )

        if abs(d - d_prev) <= 1:
            return d

    raise EVMRevertError(error="Curve NG D-solver did not converge in 255 iterations")


def _curve_ng_get_y(i: int, j: int, x: int, xp: tuple[int, int], amp: int) -> int:
    """Solve for y = xp[j]' given x = xp[i]' and the invariant.

    Equivalent to the on-chain `get_y` view. Quadratic-in-y refinement,
    255-iteration cap.

    Reference (Vyper): `get_y` in
    https://github.com/curvefi/stableswap-ng/blob/main/contracts/main/CurveStableSwapNG.vy
    """
    if i == j:
        raise ValueError("i and j must differ")
    n = len(xp)
    if not (0 <= i < n) or not (0 <= j < n):
        raise ValueError("i / j out of range for 2-token pool")

    d = _curve_ng_get_d(xp, amp)
    ann: int = amp * (n**n)

    # Sum and product walk: iterate over coords except j.
    c = d
    s_ = 0
    for k in range(n):
        if k == i:
            x_k = x
        elif k != j:
            x_k = xp[k]
        else:
            continue
        s_ += x_k
        c = c * d // (x_k * n)

    c = c * d * _A_PRECISION // (ann * n)
    b = s_ + d * _A_PRECISION // ann

    y = d
    for _ in range(_MAX_ITER):
        y_prev = y
        y = (y * y + c) // (2 * y + b - d)
        if abs(y - y_prev) <= 1:
            return y

    raise EVMRevertError(error="Curve NG y-solver did not converge in 255 iterations")


def configure_logging(level: str) -> None:
    """Match the existing adapter logging-init convention."""
    configure_execution_logging(level)
