import dataclasses
from typing import Protocol, runtime_checkable

from eth_typing import HexAddress

from degenbot.types.abstract import AbstractPoolState
from degenbot.types.aliases import BlockNumber
from degenbot.types.concrete import PoolStateMessage


@runtime_checkable
class CurveDataProvider(Protocol):
    """On-chain data access used by Curve per-block caches."""

    def virtual_price(self, block_number: BlockNumber) -> int: ...

    def base_virtual_price(self, block_number: BlockNumber) -> int: ...

    def base_cache_updated(self, block_number: BlockNumber) -> int: ...

    def admin_balances(self, block_number: BlockNumber) -> tuple[int, ...]: ...

    def d(self, block_number: BlockNumber) -> int: ...

    def gamma(self, block_number: BlockNumber) -> int: ...

    def price_scale(self, block_number: BlockNumber) -> tuple[int, ...]: ...

    def block_timestamp(self, block_number: BlockNumber) -> int: ...

    def redemption_price(self, block_number: BlockNumber) -> int: ...


@dataclasses.dataclass(slots=True, frozen=True, kw_only=True)
class CurveStableswapPoolState(AbstractPoolState):
    balances: tuple[int, ...]
    base: "CurveStableswapPoolState | None" = None


@dataclasses.dataclass(slots=True, frozen=True)
class CurveStableswapPoolSimulationResult:
    amount0_delta: int
    amount1_delta: int
    current_state: CurveStableswapPoolState
    future_state: CurveStableswapPoolState


@dataclasses.dataclass(slots=True, frozen=True)
class CurveStableSwapPoolAttributes:
    address: HexAddress
    lp_token_address: HexAddress
    coin_addresses: list[HexAddress]
    coin_index_type: str
    is_metapool: bool
    underlying_coin_addresses: list[HexAddress] | None = dataclasses.field(default=None)
    base_pool_address: HexAddress | None = dataclasses.field(default=None)


@dataclasses.dataclass(slots=True, frozen=True)
class CurveStableSwapPoolStateUpdated(PoolStateMessage):
    state: CurveStableswapPoolState
