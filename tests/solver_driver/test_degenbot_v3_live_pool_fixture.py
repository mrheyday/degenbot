"""Opt-in live fixture for degenbot V3 SQLite snapshot hydration.

This test is intentionally skipped unless all required environment variables
are present. It validates the production CLMM ingestion path without making CI
depend on RPC, Cryo, or a real operator database:

- load a prepared degenbot SQLite V3 snapshot
- hydrate a real Uniswap V3-style pool at a pinned Arbitrum block
- quote through degenbot's swap traversal using the imported tick bitmap/data
- optionally compare the result to a V3 Quoter/QuoterV2 staticcall

Required env vars:
    ARB_RPC_HTTP
    DEGENBOT_V3_DB_PATH
    DEGENBOT_V3_POOL_ADDRESS
    DEGENBOT_V3_FACTORY_ADDRESS
    DEGENBOT_V3_PIN_BLOCK
    DEGENBOT_V3_TOKEN_IN
    DEGENBOT_V3_AMOUNT_IN

Optional env vars:
    DEGENBOT_V3_QUOTER_ADDRESS
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pytest
from web3 import Web3

if TYPE_CHECKING:
    from sqlalchemy.orm import Session, scoped_session

ARBITRUM_CHAIN_ID = 42161

_QUOTER_V2_ABI: list[dict[str, object]] = [
    {
        "type": "function",
        "name": "quoteExactInputSingle",
        "stateMutability": "nonpayable",
        "inputs": [
            {
                "name": "params",
                "type": "tuple",
                "components": [
                    {"name": "tokenIn", "type": "address"},
                    {"name": "tokenOut", "type": "address"},
                    {"name": "amountIn", "type": "uint256"},
                    {"name": "fee", "type": "uint24"},
                    {"name": "sqrtPriceLimitX96", "type": "uint160"},
                ],
            }
        ],
        "outputs": [
            {"name": "amountOut", "type": "uint256"},
            {"name": "sqrtPriceX96After", "type": "uint160"},
            {"name": "initializedTicksCrossed", "type": "uint32"},
            {"name": "gasEstimate", "type": "uint256"},
        ],
    },
]

_QUOTER_V1_ABI: list[dict[str, object]] = [
    {
        "type": "function",
        "name": "quoteExactInputSingle",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "tokenIn", "type": "address"},
            {"name": "tokenOut", "type": "address"},
            {"name": "fee", "type": "uint24"},
            {"name": "amountIn", "type": "uint256"},
            {"name": "sqrtPriceLimitX96", "type": "uint160"},
        ],
        "outputs": [{"name": "amountOut", "type": "uint256"}],
    },
]


@dataclass(frozen=True)
class _Env:
    rpc_url: str
    db_path: Path
    pool: str
    factory: str
    pin_block: int
    token_in: str
    amount_in: int
    quoter: str | None


def _parse_block(raw: str) -> int:
    if raw.startswith(("0x", "0X")):
        return int(raw, 16)
    return int(raw)


def _read_env() -> _Env | None:
    rpc_url = os.environ.get("ARB_RPC_HTTP")
    db_path_raw = os.environ.get("DEGENBOT_V3_DB_PATH")
    pool = os.environ.get("DEGENBOT_V3_POOL_ADDRESS")
    factory = os.environ.get("DEGENBOT_V3_FACTORY_ADDRESS")
    pin_block_raw = os.environ.get("DEGENBOT_V3_PIN_BLOCK")
    token_in = os.environ.get("DEGENBOT_V3_TOKEN_IN")
    amount_in_raw = os.environ.get("DEGENBOT_V3_AMOUNT_IN")
    if (
        not rpc_url
        or not db_path_raw
        or not pool
        or not factory
        or not pin_block_raw
        or not token_in
        or not amount_in_raw
    ):
        return None

    db_path = Path(db_path_raw).expanduser()
    if not db_path.is_file():
        return None

    try:
        pin_block = _parse_block(pin_block_raw)
        amount_in = int(amount_in_raw)
    except ValueError:
        return None
    if pin_block <= 0 or amount_in <= 0:
        return None

    try:
        pool = Web3.to_checksum_address(pool)
        factory = Web3.to_checksum_address(factory)
        token_in = Web3.to_checksum_address(token_in)
        quoter = os.environ.get("DEGENBOT_V3_QUOTER_ADDRESS")
        quoter = Web3.to_checksum_address(quoter) if quoter else None
    except ValueError:
        return None

    return _Env(
        rpc_url=rpc_url,
        db_path=db_path,
        pool=pool,
        factory=factory,
        pin_block=pin_block,
        token_in=token_in,
        amount_in=amount_in,
        quoter=quoter,
    )


_env = _read_env()

pytestmark = pytest.mark.skipif(
    _env is None,
    reason=(
        "Degenbot V3 live fixture requires ARB_RPC_HTTP, DEGENBOT_V3_DB_PATH, "
        "DEGENBOT_V3_POOL_ADDRESS, DEGENBOT_V3_FACTORY_ADDRESS, "
        "DEGENBOT_V3_PIN_BLOCK, DEGENBOT_V3_TOKEN_IN, and DEGENBOT_V3_AMOUNT_IN."
    ),
)


@pytest.fixture(scope="module")
def env() -> _Env:
    assert _env is not None
    return _env


@pytest.fixture(scope="module")
def web3_client(env: _Env) -> Web3:
    return Web3(Web3.HTTPProvider(env.rpc_url))


def _patch_degenbot_database_sessions(
    monkeypatch: pytest.MonkeyPatch,
    db_session: scoped_session[Session],
) -> None:
    database_module = importlib.import_module("degenbot.database")
    erc20_module = importlib.import_module("degenbot.erc20.erc20")
    snapshot_module = importlib.import_module("degenbot.uniswap.v3_snapshot")
    v3_pool_module = importlib.import_module("degenbot.uniswap.v3_liquidity_pool")

    original_get_token_from_database = erc20_module.get_token_from_database
    original_get_pool_from_database = v3_pool_module.get_pool_from_database

    def get_token_from_fixture_database(token: str, chain_id: int) -> object | None:
        return cast(
            "object | None",
            original_get_token_from_database(token=token, chain_id=chain_id, session=db_session),
        )

    def get_pool_from_fixture_database(address: str, chain_id: int) -> object | None:
        return cast(
            "object | None",
            original_get_pool_from_database(address=address, chain_id=chain_id, session=db_session),
        )

    monkeypatch.setattr(database_module, "db_session", db_session)
    monkeypatch.setattr(snapshot_module, "db_session", db_session)
    monkeypatch.setattr(erc20_module, "db_session", db_session)
    monkeypatch.setattr(erc20_module, "get_token_from_database", get_token_from_fixture_database)
    monkeypatch.setattr(v3_pool_module, "db_session", db_session)
    monkeypatch.setattr(v3_pool_module, "get_pool_from_database", get_pool_from_fixture_database)


def _quote_with_quoter(
    *,
    web3_client: Web3,
    quoter_address: str,
    token_in: str,
    token_out: str,
    fee: int,
    amount_in: int,
    block: int,
) -> int:
    quoter_v2 = web3_client.eth.contract(
        address=Web3.to_checksum_address(quoter_address),
        abi=cast("Any", _QUOTER_V2_ABI),
    )
    try:
        v2_result = quoter_v2.functions.quoteExactInputSingle((
            token_in,
            token_out,
            amount_in,
            fee,
            0,
        )).call(block_identifier=block)
    except Exception:
        quoter_v1 = web3_client.eth.contract(
            address=Web3.to_checksum_address(quoter_address),
            abi=cast("Any", _QUOTER_V1_ABI),
        )
        v1_result = quoter_v1.functions.quoteExactInputSingle(
            token_in,
            token_out,
            fee,
            amount_in,
            0,
        ).call(block_identifier=block)
        return int(v1_result)

    return int(v2_result[0])


def test_degenbot_v3_snapshot_hydrates_live_pool_and_quotes(
    env: _Env,
    web3_client: Web3,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("degenbot")

    connection_module = importlib.import_module("degenbot.connection")
    operations_module = importlib.import_module("degenbot.database.operations")
    snapshot_module = importlib.import_module("degenbot.uniswap.v3_snapshot")
    managers_module = importlib.import_module("degenbot.uniswap.managers")
    registry_module = importlib.import_module("degenbot.registry")
    erc20_manager_module = importlib.import_module("degenbot.erc20.manager")

    get_scoped_sqlite_session = operations_module.get_scoped_sqlite_session
    database_snapshot = snapshot_module.DatabaseSnapshot
    uniswap_v3_liquidity_snapshot = snapshot_module.UniswapV3LiquiditySnapshot
    uniswap_v3_pool_manager = managers_module.UniswapV3PoolManager

    connection_module.set_web3(web3_client, optimize=False)
    assert int(web3_client.eth.chain_id) == ARBITRUM_CHAIN_ID

    db_session = get_scoped_sqlite_session(env.db_path)
    _patch_degenbot_database_sessions(monkeypatch, db_session)

    registry_module.pool_registry.remove(chain_id=ARBITRUM_CHAIN_ID, pool_address=env.pool)
    managers_module.UniswapV3PoolManager.instances.clear()
    erc20_manager_module.Erc20TokenManager._state.pop(ARBITRUM_CHAIN_ID, None)

    source = database_snapshot(chain_id=ARBITRUM_CHAIN_ID, database_path=env.db_path)
    snapshot = uniswap_v3_liquidity_snapshot(source=source)

    tick_bitmap = snapshot.tick_bitmap(env.pool)
    tick_data = snapshot.tick_data(env.pool)
    assert tick_bitmap, "prepared degenbot V3 DB has no initialized bitmap words for pool"
    assert tick_data, "prepared degenbot V3 DB has no initialized tick liquidity rows for pool"

    # Rebuild the snapshot because accessors consume the initial maps by design.
    snapshot = uniswap_v3_liquidity_snapshot(source=source)
    manager = uniswap_v3_pool_manager(
        factory_address=env.factory,
        chain_id=ARBITRUM_CHAIN_ID,
        snapshot=snapshot,
    )
    pool = manager.get_pool(
        env.pool,
        silent=True,
        pool_class_kwargs={"state_block": env.pin_block},
    )

    token_in = None
    for token in pool.tokens:
        if Web3.to_checksum_address(token.address) == env.token_in:
            token_in = token
            break
    assert token_in is not None, "DEGENBOT_V3_TOKEN_IN is not one of the pool tokens"

    amount_out = int(pool.calculate_tokens_out_from_tokens_in(token_in, env.amount_in))
    assert amount_out > 0

    if env.quoter is None:
        return

    token_out = pool.token1 if token_in == pool.token0 else pool.token0
    quoter_amount_out = _quote_with_quoter(
        web3_client=web3_client,
        quoter_address=env.quoter,
        token_in=Web3.to_checksum_address(token_in.address),
        token_out=Web3.to_checksum_address(token_out.address),
        fee=int(pool.fee),
        amount_in=env.amount_in,
        block=env.pin_block,
    )

    assert amount_out == quoter_amount_out
