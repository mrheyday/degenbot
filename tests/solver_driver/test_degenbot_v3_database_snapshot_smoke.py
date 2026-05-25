"""Repo-side smoke for degenbot SQLite-backed V3 liquidity snapshots.

This builds a tiny temporary Arbitrum database instead of touching the
operator's real degenbot database. It proves the pinned vendor surface we
need before relying on CLMM SQLite snapshots:

- ``DatabaseSnapshot(chain_id=42161, database_path=...)``
- ``UniswapV3LiquiditySnapshot(source=...)``
- concrete ``UniswapV3PoolTable`` rows with initialization maps and
  liquidity positions
"""

from __future__ import annotations

import importlib
import sys
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from typing import Protocol

    from sqlalchemy.orm import Session

    class _DbRow(Protocol):
        id: int


ARBITRUM_CHAIN_ID = 42161
WETH = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"
USDC = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
UNISWAP_V3_FACTORY = "0x1F98431c8aD98523631AE4a59f267346ea31F984"
POOL_WETH_USDC_005 = "0x0000000000000000000000000000000000003005"
SNAPSHOT_BLOCK = 333_333_333
SNAPSHOT_LOG_INDEX = 77


def _purge_degenbot_modules_if_not_loaded() -> None:
    """Let first import read the test HOME without reinitializing pyo3 modules."""

    if any(module_name == "degenbot" or module_name.startswith("degenbot.") for module_name in sys.modules):
        return

    for module_name in tuple(sys.modules):
        if module_name == "degenbot" or module_name.startswith("degenbot."):
            del sys.modules[module_name]


def _seed_v3_snapshot_database(
    *,
    db_session: Callable[[], Session],
    exchange_table: Callable[..., _DbRow],
    erc20_token_table: Callable[..., _DbRow],
    uniswap_v3_pool_table: Callable[..., _DbRow],
    initialization_map_table: Callable[..., object],
    liquidity_position_table: Callable[..., object],
) -> None:
    with db_session() as session:
        exchange = exchange_table(
            chain_id=ARBITRUM_CHAIN_ID,
            name="uniswap_v3",
            active=True,
            last_update_block=SNAPSHOT_BLOCK,
            factory=UNISWAP_V3_FACTORY,
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
        session.add_all((exchange, weth, usdc))
        session.flush()

        pool = uniswap_v3_pool_table(
            address=POOL_WETH_USDC_005,
            chain=ARBITRUM_CHAIN_ID,
            token0_id=weth.id,
            token1_id=usdc.id,
            exchange_id=exchange.id,
            fee_token0=500,
            fee_token1=500,
            fee_denominator=1_000_000,
            tick_spacing=10,
            liquidity_update_block=SNAPSHOT_BLOCK,
            liquidity_update_log_index=SNAPSHOT_LOG_INDEX,
        )
        session.add(pool)
        session.flush()

        session.add_all(
            (
                initialization_map_table(pool_id=pool.id, word=0, bitmap=1 << 10),
                liquidity_position_table(
                    pool_id=pool.id,
                    tick=0,
                    liquidity_gross=1_000_000,
                    liquidity_net=1_000_000,
                ),
                liquidity_position_table(
                    pool_id=pool.id,
                    tick=10,
                    liquidity_gross=1_000_000,
                    liquidity_net=-1_000_000,
                ),
            )
        )
        session.commit()


def test_degenbot_v3_database_snapshot_loads_arbitrum_pool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _purge_degenbot_modules_if_not_loaded()

    pytest.importorskip("degenbot")

    base_module = importlib.import_module("degenbot.database.models.base")
    erc20_module = importlib.import_module("degenbot.database.models.erc20")
    pools_module = importlib.import_module("degenbot.database.models.pools")
    operations_module = importlib.import_module("degenbot.database.operations")
    snapshot_module = importlib.import_module("degenbot.uniswap.v3_snapshot")

    base_model = base_module.Base
    erc20_token_table = erc20_module.Erc20TokenTable
    exchange_table = base_module.ExchangeTable
    initialization_map_table = pools_module.InitializationMapTable
    liquidity_position_table = pools_module.LiquidityPositionTable
    uniswap_v3_pool_table = pools_module.UniswapV3PoolTable
    get_scoped_sqlite_session = operations_module.get_scoped_sqlite_session
    database_snapshot = snapshot_module.DatabaseSnapshot
    uniswap_v3_liquidity_snapshot = snapshot_module.UniswapV3LiquiditySnapshot

    db_path = tmp_path / "arbitrum-v3-snapshot.db"
    db_session = get_scoped_sqlite_session(db_path)
    engine = db_session().bind
    assert engine is not None
    base_model.metadata.create_all(bind=engine)

    # DatabaseSnapshot.get_newest_block reads this module-level binding, while
    # get_liquidity_map uses its instance session. Patch both to the same temp DB.
    monkeypatch.setattr(snapshot_module, "db_session", db_session)

    _seed_v3_snapshot_database(
        db_session=db_session,
        exchange_table=exchange_table,
        erc20_token_table=erc20_token_table,
        uniswap_v3_pool_table=uniswap_v3_pool_table,
        initialization_map_table=initialization_map_table,
        liquidity_position_table=liquidity_position_table,
    )

    source = database_snapshot(
        chain_id=ARBITRUM_CHAIN_ID,
        database_path=db_path,
    )
    snapshot = uniswap_v3_liquidity_snapshot(source=source)

    assert snapshot.chain_id == ARBITRUM_CHAIN_ID
    assert snapshot.newest_block == SNAPSHOT_BLOCK
    assert POOL_WETH_USDC_005 in snapshot.pools

    tick_bitmap = snapshot.tick_bitmap(POOL_WETH_USDC_005)
    tick_data = snapshot.tick_data(POOL_WETH_USDC_005)

    assert tick_bitmap is not None
    assert tick_data is not None
    assert tick_bitmap[0].bitmap == 1 << 10
    assert tick_data[0].liquidity_gross == 1_000_000
    assert tick_data[0].liquidity_net == 1_000_000
    assert tick_data[10].liquidity_gross == 1_000_000
    assert tick_data[10].liquidity_net == -1_000_000
    assert snapshot.pending_updates(POOL_WETH_USDC_005) == ()

    # Snapshot accessors consume the initial maps so pool-manager construction
    # cannot accidentally reuse stale copies after the initial load.
    assert snapshot.tick_bitmap(POOL_WETH_USDC_005) == {}
    assert snapshot.tick_data(POOL_WETH_USDC_005) == {}
