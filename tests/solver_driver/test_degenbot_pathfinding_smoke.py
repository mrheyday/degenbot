"""Repo-side smoke for degenbot SQLite pathfinding.

This test intentionally builds a tiny temporary Arbitrum database instead of
touching the operator's real degenbot database under ``~/.config/degenbot``.
It proves the pinned vendor surface we depend on:

- ``degenbot.pathfinding.find_paths``
- SQLite-backed ``Erc20TokenTable`` / ``ExchangeTable``
- concrete V2 pool tables as graph edges
"""

from __future__ import annotations

import importlib
import sys
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


ARBITRUM_CHAIN_ID = 42161
WETH = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"
USDC = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
USDT = "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9"
FACTORY = "0x6EcCab422D763aC031210895C81787E87B43A652"
POOL_WETH_USDC = "0x0000000000000000000000000000000000001001"
POOL_USDC_WETH = "0x0000000000000000000000000000000000001002"
POOL_WETH_USDT = "0x0000000000000000000000000000000000001003"
POOL_USDT_WETH = "0x0000000000000000000000000000000000001004"


def _purge_degenbot_modules() -> None:
    """Ensure degenbot reads the test HOME before its import-time config runs."""

    for module_name in tuple(sys.modules):
        if module_name == "degenbot" or module_name.startswith("degenbot."):
            del sys.modules[module_name]


def test_degenbot_find_paths_generates_arbitrum_two_pool_cycles(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _purge_degenbot_modules()

    pytest.importorskip("degenbot")

    base_module = importlib.import_module("degenbot.database.models.base")
    erc20_module = importlib.import_module("degenbot.database.models.erc20")
    pools_module = importlib.import_module("degenbot.database.models.pools")
    operations_module = importlib.import_module("degenbot.database.operations")
    pathfinding_module = importlib.import_module("degenbot.pathfinding")

    base_model = base_module.Base
    erc20_token_table = erc20_module.Erc20TokenTable
    exchange_table = base_module.ExchangeTable
    uniswap_v2_pool_table = pools_module.UniswapV2PoolTable
    get_scoped_sqlite_session = operations_module.get_scoped_sqlite_session
    find_paths = pathfinding_module.find_paths

    db_path = tmp_path / "arbitrum-pathfinding.db"
    db_session = get_scoped_sqlite_session(db_path)
    engine = db_session().bind
    assert engine is not None
    base_model.metadata.create_all(bind=engine)

    # find_paths imports db_session by value, so patch its local binding.
    monkeypatch.setattr(pathfinding_module, "db_session", db_session)

    with db_session() as session:
        exchange = exchange_table(
            chain_id=ARBITRUM_CHAIN_ID,
            name="camelot-v2-smoke",
            active=True,
            last_update_block=None,
            factory=FACTORY,
            deployer=None,
        )
        weth = erc20_token_table(
            chain=ARBITRUM_CHAIN_ID,
            address=WETH,
            name="Wrapped Ether",
            symbol="WETH",
            decimals=18,
        )
        usdc = erc20_token_table(
            chain=ARBITRUM_CHAIN_ID,
            address=USDC,
            name="USD Coin",
            symbol="USDC",
            decimals=6,
        )
        usdt = erc20_token_table(
            chain=ARBITRUM_CHAIN_ID,
            address=USDT,
            name="Tether USD",
            symbol="USDT",
            decimals=6,
        )
        session.add_all((exchange, weth, usdc, usdt))
        session.flush()

        session.add_all((
            uniswap_v2_pool_table(
                address=POOL_WETH_USDC,
                chain=ARBITRUM_CHAIN_ID,
                token0_id=weth.id,
                token1_id=usdc.id,
                exchange_id=exchange.id,
                fee_token0=30,
                fee_token1=30,
                fee_denominator=10_000,
            ),
            uniswap_v2_pool_table(
                address=POOL_USDC_WETH,
                chain=ARBITRUM_CHAIN_ID,
                token0_id=usdc.id,
                token1_id=weth.id,
                exchange_id=exchange.id,
                fee_token0=30,
                fee_token1=30,
                fee_denominator=10_000,
            ),
            uniswap_v2_pool_table(
                address=POOL_WETH_USDT,
                chain=ARBITRUM_CHAIN_ID,
                token0_id=weth.id,
                token1_id=usdt.id,
                exchange_id=exchange.id,
                fee_token0=30,
                fee_token1=30,
                fee_denominator=10_000,
            ),
            uniswap_v2_pool_table(
                address=POOL_USDT_WETH,
                chain=ARBITRUM_CHAIN_ID,
                token0_id=usdt.id,
                token1_id=weth.id,
                exchange_id=exchange.id,
                fee_token0=30,
                fee_token1=30,
                fee_denominator=10_000,
            ),
        ))
        session.commit()

    paths = list(
        find_paths(
            chain_id=ARBITRUM_CHAIN_ID,
            start_tokens=[WETH],
            end_tokens=[WETH],
            min_depth=2,
            max_depth=2,
            pool_types=[uniswap_v2_pool_table],
        )
    )

    assert paths
    assert all(len(path) == 2 for path in paths)
    assert any(
        {step.address for step in path} == {POOL_WETH_USDC, POOL_USDC_WETH} for path in paths
    )
