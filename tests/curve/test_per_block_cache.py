"""Unit tests for the Curve per-block cache."""

import pickle

import pytest

from degenbot.curve.per_block_cache import PerBlockCache
from degenbot.exceptions.liquidity_pool import MissingCurveData
from tests.fakes.curve_data_provider import FakeCurveDataProvider


def _make_cache(
    *,
    data_provider: FakeCurveDataProvider | None = None,
    base_pool_is_set: bool = False,
    state_cache_depth: int = 8,
) -> PerBlockCache:
    return PerBlockCache(
        data_provider=data_provider,
        address="0x" + "0" * 40,
        base_pool_is_set=base_pool_is_set,
        state_cache_depth=state_cache_depth,
    )


def test_cache_miss_calls_provider_then_reuses_cached_value() -> None:
    fake = FakeCurveDataProvider(d=10**18)
    cache = _make_cache(data_provider=fake)

    assert cache.get_cached_contract_d(100) == 10**18
    fake._d_value = 2 * 10**18
    assert cache.get_cached_contract_d(100) == 10**18


def test_cache_miss_without_provider_raises() -> None:
    cache = _make_cache(data_provider=None)

    with pytest.raises(MissingCurveData):
        cache.get_cached_admin_balances(100)


def test_non_metapool_virtual_price_fetches_directly() -> None:
    fake = FakeCurveDataProvider(virtual_price=10**18)
    cache = _make_cache(data_provider=fake, base_pool_is_set=False)

    assert cache.get_cached_virtual_price(100) == 10**18


def test_metapool_valid_base_cache_uses_base_virtual_price() -> None:
    fake = FakeCurveDataProvider(
        base_cache_updated=1_700_000_000,
        base_virtual_price=10**18 + 42,
        virtual_price=10**18 + 999,
        block_timestamp=1_700_000_100,
    )
    cache = _make_cache(data_provider=fake, base_pool_is_set=True)

    assert cache.get_cached_virtual_price(100) == 10**18 + 42


def test_metapool_expired_base_cache_fetches_live_virtual_price() -> None:
    fake = FakeCurveDataProvider(
        base_cache_updated=1_700_000_000,
        base_virtual_price=10**18 + 42,
        virtual_price=10**18 + 999,
        block_timestamp=1_700_000_700,
    )
    cache = _make_cache(data_provider=fake, base_pool_is_set=True)

    assert cache.get_cached_virtual_price(100) == 10**18 + 999


def test_pickle_drops_provider_but_keeps_cached_values() -> None:
    fake = FakeCurveDataProvider(d=10**18)
    cache = _make_cache(data_provider=fake)
    cache.get_cached_contract_d(100)

    restored = pickle.loads(pickle.dumps(cache))

    assert restored.get_cached_contract_d(100) == 10**18
    with pytest.raises(MissingCurveData):
        restored.get_cached_contract_d(200)
