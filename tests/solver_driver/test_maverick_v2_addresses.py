"""Sanity tests for Maverick V2 Arbitrum addresses and DefiLlama metadata."""

from __future__ import annotations

from web3 import Web3

from degenbot.adapters import adapter_for
from degenbot.execution import maverick_v2_addresses as m

_ALL_ADDRESSES: list[tuple[str, str]] = [
    ("ROUTER", m.ROUTER),
    ("QUOTER", m.QUOTER),
    ("REWARD_ROUTER", m.REWARD_ROUTER),
]


def test_every_constant_is_a_valid_address() -> None:
    for name, address in _ALL_ADDRESSES:
        assert Web3.is_address(address), f"{name}: {address} is not a valid address"


def test_contract_grouping_matches_underlying_constants() -> None:
    assert frozenset({m.ROUTER, m.QUOTER, m.REWARD_ROUTER}) == m.EXECUTION_CONTRACTS
    assert len(m.EXECUTION_CONTRACTS) == 3


def test_defillama_arbitrum_metadata_is_pinned() -> None:
    assert m.DEFILLAMA_DIMENSION_ADAPTER_COMMIT == "5bfdd74e9b98d60e423453406f8e1c8dcc5d8af9"
    assert m.DEFILLAMA_DIMENSION_ADAPTER_PATH == "dexs/maverick-v2/index.ts"
    assert m.DEFILLAMA_ARBITRUM_SUBGRAPH_ID == "9oEipJ8CzpnQ4PnCDBQFa16AME8E9r3Kr4GurTtdUKRh"
    assert m.DEFILLAMA_ARBITRUM_START_DATE == "2024-06-03"


def test_maverick_adapter_contracts_match_address_module_without_enabling_execution() -> None:
    adapter = adapter_for("swap", "MaverickV2")

    assert not adapter.enabled_for_execution
    assert adapter.contract("MAVERICK_V2_ROUTER").address == m.ROUTER
    assert adapter.contract("MAVERICK_V2_QUOTER").address == m.QUOTER
    assert adapter.contract("MAVERICK_V2_REWARD_ROUTER").address == m.REWARD_ROUTER
