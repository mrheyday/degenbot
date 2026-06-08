"""Per-block on-chain cache for Curve stableswap pools."""

import contextlib
from typing import Any

from eth_typing import ChecksumAddress

from degenbot.curve.types import CurveDataProvider
from degenbot.exceptions.liquidity_pool import MissingCurveData
from degenbot.types.aliases import BlockNumber
from degenbot.types.concrete import BoundedCache


class PerBlockCache:
    """Owns Curve data caches that are keyed by block number."""

    BASE_CACHE_EXPIRES = 10 * 60

    def __init__(
        self,
        data_provider: CurveDataProvider | None,
        address: ChecksumAddress,
        *,
        base_pool_is_set: bool,
        state_cache_depth: int,
    ) -> None:
        self._data_provider = data_provider
        self._address = address
        self._base_pool_is_set = base_pool_is_set

        self._cache_block_timestamps: BoundedCache[BlockNumber, int] = BoundedCache(
            max_items=state_cache_depth
        )
        self._cache_contract_D: BoundedCache[BlockNumber, int] = BoundedCache(
            max_items=state_cache_depth
        )
        self._cache_gamma: BoundedCache[BlockNumber, int] = BoundedCache(
            max_items=state_cache_depth
        )
        self._cache_price_scale: BoundedCache[BlockNumber, tuple[int, ...]] = BoundedCache(
            max_items=state_cache_depth
        )
        self._cache_admin_balances: BoundedCache[BlockNumber, tuple[int, ...]] = BoundedCache(
            max_items=state_cache_depth
        )
        self._cache_scaled_redemption_price: BoundedCache[BlockNumber, int] = BoundedCache(
            max_items=state_cache_depth
        )
        self._cache_virtual_price: BoundedCache[BlockNumber, int] = BoundedCache(
            max_items=state_cache_depth
        )
        self._cache_base_cache_updated: BoundedCache[BlockNumber, int] = BoundedCache(
            max_items=state_cache_depth
        )
        self._cache_base_virtual_price: BoundedCache[BlockNumber, int] = BoundedCache(
            max_items=state_cache_depth
        )

    def set_data_provider(self, data_provider: CurveDataProvider | None) -> None:
        self._data_provider = data_provider

    def get_cached_block_timestamp(self, block_number: BlockNumber) -> int:
        with contextlib.suppress(KeyError):
            return self._cache_block_timestamps[block_number]
        provider = self._require_provider("block_timestamp")
        result = provider.block_timestamp(block_number)
        self._cache_block_timestamps[block_number] = result
        return result

    def get_cached_contract_d(self, block_number: BlockNumber) -> int:
        with contextlib.suppress(KeyError):
            return self._cache_contract_D[block_number]
        provider = self._require_provider("D")
        result = provider.d(block_number)
        self._cache_contract_D[block_number] = result
        return result

    def get_cached_gamma(self, block_number: BlockNumber) -> int:
        with contextlib.suppress(KeyError):
            return self._cache_gamma[block_number]
        provider = self._require_provider("gamma")
        result = provider.gamma(block_number)
        self._cache_gamma[block_number] = result
        return result

    def get_cached_price_scale(self, block_number: BlockNumber) -> tuple[int, ...]:
        with contextlib.suppress(KeyError):
            return self._cache_price_scale[block_number]
        provider = self._require_provider("price_scale")
        result = provider.price_scale(block_number)
        self._cache_price_scale[block_number] = result
        return result

    def get_cached_admin_balances(self, block_number: BlockNumber) -> tuple[int, ...]:
        with contextlib.suppress(KeyError):
            return self._cache_admin_balances[block_number]
        provider = self._require_provider("admin_balances")
        result = provider.admin_balances(block_number)
        self._cache_admin_balances[block_number] = result
        return result

    def get_cached_scaled_redemption_price(self, block_number: BlockNumber) -> int:
        with contextlib.suppress(KeyError):
            return self._cache_scaled_redemption_price[block_number]
        provider = self._require_provider("redemption_price")
        result = provider.redemption_price(block_number)
        self._cache_scaled_redemption_price[block_number] = result
        return result

    def get_cached_base_cache_updated(self, block_number: BlockNumber) -> int:
        with contextlib.suppress(KeyError):
            return self._cache_base_cache_updated[block_number]
        provider = self._require_provider("base_cache_updated")
        result = provider.base_cache_updated(block_number)
        self._cache_base_cache_updated[block_number] = result
        return result

    def get_cached_base_virtual_price(self, block_number: BlockNumber) -> int:
        with contextlib.suppress(KeyError):
            return self._cache_base_virtual_price[block_number]
        provider = self._require_provider("base_virtual_price")
        result = provider.base_virtual_price(block_number)
        self._cache_base_virtual_price[block_number] = result
        return result

    def get_cached_virtual_price(self, block_number: BlockNumber) -> int:
        with contextlib.suppress(KeyError):
            return self._cache_virtual_price[block_number]

        if not self._base_pool_is_set:
            provider = self._require_provider("virtual_price")
            result = provider.virtual_price(block_number)
        else:
            block_timestamp = self.get_cached_block_timestamp(block_number)
            base_cache_updated = self.get_cached_base_cache_updated(block_number)
            if block_timestamp > base_cache_updated + self.BASE_CACHE_EXPIRES:
                provider = self._require_provider("virtual_price")
                result = provider.virtual_price(block_number)
            else:
                result = self.get_cached_base_virtual_price(block_number)

        self._cache_virtual_price[block_number] = result
        return result

    def _require_provider(self, field: str) -> CurveDataProvider:
        if self._data_provider is None:
            msg = f"{field} requires a data provider."
            raise MissingCurveData(self._address, field, msg)
        return self._data_provider

    def __getstate__(self) -> dict[str, Any]:
        state = self.__dict__.copy()
        state["_data_provider"] = None
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        self.__dict__.update(state)
