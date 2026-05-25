# RUF002/RUF003: Unicode math glyphs in docstrings are intentional — they're
# the canonical DODO PMM notation. Replacing with ASCII would obscure the math.
# TC002: `ChecksumAddress` is used at runtime as the `to_checksum_address`
# annotation target — cannot move into TYPE_CHECKING.
# PLR0913: matches degenbot's existing pool constructor pattern.
# ruff: noqa: TC002, PLR0913
"""DODO PMM (Proactive Market Maker) v2 pool adapter.

Wraps the audited `dodo_pmm_math` primitives into a degenbot-pattern
pool class. Targets DODO PMM v2 deployments on Arbitrum (DexKind 12
per `IExecutor.sol`, Phase F.3 promotion 2026-05-12).

## What DODO PMM v2 actually is

A PMM v2 pool tracks two reserves `(B, Q)` and two **targets**
`(B0, Q0)` plus an external oracle price `i` and a slippage parameter
`K`. The pool's R-state classifies the inventory relative to targets:

  * `R = ONE`        — `B == B0` AND `Q == Q0` (perfectly balanced)
  * `R = ABOVE_ONE`  — `B  > B0` (excess base; reduce base price)
  * `R = BELOW_ONE`  — `Q  > Q0` (excess quote; raise base price)

Swap routes through one of six state-specific branches in
`dodo_pmm_math` (`_r_one_*`, `_r_above_*`, `_r_below_*`) which compute
the actual `amount_out` via either `general_integrate` (linear
integral against the PMM curve) or
`solve_quadratic_function_for_trade` (quadratic root for the
inventory-overshoot case).

The pool class delegates exact-input swaps to the audited
`sell_base_token` / `sell_quote_token` entry points — those already
handle the state branching internally. Our wrapper:

  1. Tracks the live `PmmState` snapshot.
  2. Applies the LP fee (and optional maintainer fee) AFTER the math
     primitives compute the receive amount (matches the on-chain
     dispatcher's order of operations).
  3. Self-registers into `degenbot.registry.pool_registry` when
     constructed with `chain_id`, so
     `degenbot_ipc.RegistryBackedDegenbotSimulator._simulate_step`
     resolves it identically to UniswapV2/V3/V4 + the other Phase F.2
     adapter venues.

## On-chain DexKind mapping

DexKind ordinal **12** (`DodoPmm`) per `IExecutor.sol` and the
cross-language mirrors. IPC string identifier: `"DodoPmm"`.

## Pinned references

  * DODO PMM v2 source:    https://github.com/DODOEX/dodo-smart-contract
  * Math primitives:       `solver/driver/execution/dodo_pmm_math.py`
                           (60+ functions, locked by
                           `test_dodo_pmm_math.py` 30+ tests)
  * Spec deferred: PMM v3 (split-target / dynamic-fee plugin) — Phase
    F.4 candidate; v3 contracts not yet deployed on Arbitrum at scale.
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
from eth_typing import ChecksumAddress
from eth_utils.address import to_checksum_address

from degenbot.execution_adapters.adapter_base import configure_execution_logging
from degenbot.execution_adapters.dodo_pmm_math import (
    PmmState,
    RState,
    sell_base_token,
    sell_quote_token,
)

if TYPE_CHECKING:
    from degenbot.types.concrete import Subscriber

logger = structlog.get_logger(__name__).bind(
    service="solver",
    component="execution.dodo_pmm_adapter",
)


# DODO fee precision: hundredths-of-a-bip-equivalent, denominator 10^18 wad
# (DODO contracts express LP fee and maintainer fee as `wei`-scaled fractions
# of `amount_out`).
_FEE_DENOMINATOR_WAD = 10**18


# ---------------------------------------------------------------------------
# Pool state
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True, kw_only=True)
class DodoPmmPoolState:
    """Frozen snapshot of a DODO PMM v2 pool at a given block.

    `pmm` is the live PMM state read from the pool's `getPMMState()`
    view (or reconstructed from individual `_BASE_RESERVE_`,
    `_QUOTE_RESERVE_`, `_BASE_TARGET_`, `_QUOTE_TARGET_`, `_RSTATE_`,
    `_K_`, and `_I_` slots).
    """

    address: ChecksumAddress
    block: int | None
    pmm: PmmState


# ---------------------------------------------------------------------------
# Pool class
# ---------------------------------------------------------------------------


class DodoPmmPool(PublisherMixin, AbstractLiquidityPool):
    """DODO PMM v2 pool — wraps audited `dodo_pmm_math` primitives.

    Exact-input swaps delegate to `sell_base_token(state, qty)` or
    `sell_quote_token(state, qty)` depending on the direction. The
    returned `amount_out` is the post-curve, pre-fee amount; the
    constructor's `lp_fee_bps_wad` is applied here for the
    on-chain-equivalent result.
    """

    type PoolState = DodoPmmPoolState

    _state: DodoPmmPoolState
    _state_cache: deque[DodoPmmPoolState]

    def __init__(
        self,
        address: ChecksumAddress | str,
        *,
        base_token: ChecksumAddress | str,
        quote_token: ChecksumAddress | str,
        pmm: PmmState,
        lp_fee_bps_wad: int = 0,
        maintainer_fee_bps_wad: int = 0,
        state_block: int | None = None,
        state_cache_depth: int = 8,
        chain_id: int | None = None,
    ) -> None:
        """Construct from a pre-fetched PMM state.

        Args:
            address: pool contract address.
            base_token / quote_token: ERC-20 addresses of the pool's two
                sides (DODO PMM v2 pools are directional — `base` is
                the asset being priced, `quote` is the numeraire).
            pmm: live `PmmState` from `getPMMState()`.
            lp_fee_bps_wad: LP fee fraction in 10^18 wad units
                (`5e15` = 0.5%). Applied AFTER the curve math computes
                the gross receive amount — matches the on-chain
                dispatcher's order of operations.
            maintainer_fee_bps_wad: DODO maintainer-fee fraction in the
                same wad form. Defaults to 0 (Arbitrum pools typically
                disable this).
            state_block: block height the snapshot was taken at.
            state_cache_depth: how many historical states to retain.
            chain_id: optional Arbitrum chainId (42161). When supplied,
                self-registers into `pool_registry`.

        Raises:
            ValueError: on degenerate inputs.
        """
        if lp_fee_bps_wad < 0 or lp_fee_bps_wad >= _FEE_DENOMINATOR_WAD:
            raise ValueError(
                f"lp_fee_bps_wad must be in [0, {_FEE_DENOMINATOR_WAD}), got {lp_fee_bps_wad}",
            )
        if maintainer_fee_bps_wad < 0 or maintainer_fee_bps_wad >= _FEE_DENOMINATOR_WAD:
            raise ValueError(
                f"maintainer_fee_bps_wad must be in [0, {_FEE_DENOMINATOR_WAD}), "
                f"got {maintainer_fee_bps_wad}",
            )
        if lp_fee_bps_wad + maintainer_fee_bps_wad >= _FEE_DENOMINATOR_WAD:
            raise ValueError("combined fees exceed 100%")

        self.address = to_checksum_address(address)
        self.token0 = to_checksum_address(base_token)
        self.token1 = to_checksum_address(quote_token)
        self.base_token = self.token0
        self.quote_token = self.token1
        self.lp_fee_bps_wad = lp_fee_bps_wad
        self.maintainer_fee_bps_wad = maintainer_fee_bps_wad

        self._state_lock = threading.Lock()

        initial_state = DodoPmmPoolState(
            address=self.address,
            block=state_block,
            pmm=pmm,
        )
        self._state = initial_state
        self._state_cache = deque(maxlen=max(1, state_cache_depth))
        self._state_cache.append(initial_state)

        self._subscribers: WeakSet[Subscriber] = WeakSet()
        self._chain_id = chain_id

        if chain_id is not None:
            pool_registry.add(pool=self, chain_id=chain_id, pool_address=self.address)

        total_fee_pct = 100.0 * (lp_fee_bps_wad + maintainer_fee_bps_wad) / _FEE_DENOMINATOR_WAD
        self.name = (
            f"{self.base_token[:8]}…/{self.quote_token[:8]}… "  # pylint: disable=unsubscriptable-object
            f"(DodoPmmPool, R={pmm.R.name}, {total_fee_pct:.4f}%)"
        )

    # -- state ----------------------------------------------------------------

    @property
    def state(self) -> DodoPmmPoolState:
        return self._state

    @property
    def tokens(self) -> tuple[ChecksumAddress, ChecksumAddress]:
        return (self.base_token, self.quote_token)

    # -- swap simulation ------------------------------------------------------

    def calculate_tokens_out_from_tokens_in(
        self,
        token_in: ChecksumAddress | str,
        token_in_quantity: int,
        *,
        override_state: DodoPmmPoolState | None = None,
    ) -> int:
        """Exact-input simulation routed through audited PMM math.

        Args:
            token_in: address of the token being spent (must be
                `base_token` or `quote_token`).
            token_in_quantity: input quantity in `token_in`'s native units.
            override_state: optional state snapshot override.

        Returns:
            Net `amount_out` in `token_out`'s native units, AFTER LP fee
            and maintainer fee deductions.

        Raises:
            ValueError: if `token_in` is unknown or quantity non-positive.
            DodoMathError: if the underlying PMM solver detects an
                invalid state (e.g., target reserve mismatch).
        """
        if token_in_quantity <= 0:
            raise ValueError(f"token_in_quantity must be positive, got {token_in_quantity}")

        token_in_cs = to_checksum_address(token_in)
        s = override_state if override_state is not None else self._state
        pmm = s.pmm

        if token_in_cs == self.base_token:
            gross_out, _new_r = sell_base_token(pmm, token_in_quantity)
        elif token_in_cs == self.quote_token:
            gross_out, _new_r = sell_quote_token(pmm, token_in_quantity)
        else:
            raise ValueError(
                f"token_in {token_in_cs} matches neither pool token "
                f"({self.base_token}, {self.quote_token})",
            )

        # Apply LP + maintainer fees on the receive side. The on-chain DODO
        # dispatcher (DODOZoo or DODODSPProxy) applies these in the same
        # order: math.sell_*_token → deduct LP fee → deduct maintainer fee.
        lp_fee = (gross_out * self.lp_fee_bps_wad) // _FEE_DENOMINATOR_WAD
        maintainer_fee = (gross_out * self.maintainer_fee_bps_wad) // _FEE_DENOMINATOR_WAD
        return gross_out - lp_fee - maintainer_fee

    # -- state mutation -------------------------------------------------------

    def update_state(
        self,
        *,
        pmm: PmmState,
        block: int,
    ) -> DodoPmmPoolState:
        """Apply a fresh PMM snapshot (typically after a `getPMMState()` poll
        or a `RChange` / `LpFeeRateChange` event)."""
        if block < (self._state.block or 0):
            raise ValueError(
                f"update for block {block} predates current state block {self._state.block}",
            )

        new_state = DodoPmmPoolState(
            address=self.address,
            block=block,
            pmm=pmm,
        )

        with self._state_lock:
            if self._state.block == block:
                self._state_cache.pop()
            self._state_cache.append(new_state)
            self._state = new_state

        return new_state


__all__ = ["DodoPmmPool", "DodoPmmPoolState", "PmmState", "RState"]


def configure_logging(level: str) -> None:
    """Match the existing adapter logging-init convention."""
    configure_execution_logging(level)
