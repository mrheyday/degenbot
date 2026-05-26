"""Sanity tests for the Fluid DEX address bundle."""

from __future__ import annotations

from web3 import Web3

from degenbot.adapters import adapter_for
from degenbot.execution import fluid_dex_addresses as f

_ALL_ADDRESSES: list[tuple[str, str]] = [
    ("FACTORY", f.FACTORY),
    ("LIQUIDITY", f.LIQUIDITY),
    ("USDC_ETH_POOL_T1", f.USDC_ETH_POOL_T1),
    ("DEX_RESERVES_RESOLVER", f.DEX_RESERVES_RESOLVER),
    ("DEX_RESOLVER", f.DEX_RESOLVER),
]


def test_every_constant_is_a_valid_address() -> None:
    for name, address in _ALL_ADDRESSES:
        assert Web3.is_address(address), f"{name}: {address} is not a valid address"


def test_groupings_match_underlying_constants() -> None:
    assert frozenset({f.DEX_RESERVES_RESOLVER, f.DEX_RESOLVER}) == f.RESOLVER_CONTRACTS
    assert frozenset({f.FACTORY, f.LIQUIDITY, f.USDC_ETH_POOL_T1}) == f.POOLT1_READ_SIDE_CONTRACTS
    assert f.ALL_CONTRACTS == f.RESOLVER_CONTRACTS | f.POOLT1_READ_SIDE_CONTRACTS
    assert f.RESOLVER_CONTRACTS.isdisjoint(f.POOLT1_READ_SIDE_CONTRACTS)


def test_defillama_arbitrum_metadata_is_pinned() -> None:
    assert f.DEFILLAMA_DIMENSION_ADAPTER_COMMIT == "5bfdd74e9b98d60e423453406f8e1c8dcc5d8af9"
    assert f.DEFILLAMA_FLUID_DEX_PATH == "dexs/fluid-dex/index.ts"
    assert f.DEFILLAMA_FLUID_DEX_LITE_PATH == "dexs/fluid-dex-lite/index.ts"
    assert f.DIMENSION_ADAPTER_START_DATE == "2024-12-23"
    assert f.DEX_LITE_AVAILABLE_ON_ARBITRUM is False


def test_fluid_adapter_binds_defillama_resolvers_without_enabling_execution() -> None:
    adapter = adapter_for("swap", "FluidDex")

    assert not adapter.enabled_for_execution
    assert adapter.contract("DEX_RESERVES_RESOLVER").address == f.DEX_RESERVES_RESOLVER
    assert adapter.contract("DEX_RESOLVER").address == f.DEX_RESOLVER
    assert adapter.contract("DEX_RESOLVER").source_ref.endswith(
        "dexs/fluid-dex/index.ts:DEX_RESOLVER"
    )
