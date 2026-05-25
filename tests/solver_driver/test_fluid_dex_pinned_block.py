"""Fluid DEX PoolT1 pinned-block reserve-read smoke (opt-in network test).

Validates that the Fluid DEX address bundle in
`solver/driver/execution/fluid_dex_addresses.py` is wired to a live
PoolT1 at a pinned block, and that the read-side ABI in
`docs/research/fluid/abis/IFluidDex_*` decodes correctly via web3.py.

Why a smoke and not a math comparison: the Fluid math port has not
landed yet (`solver/driver/execution/fluid_dex_adapter.py` is a forward
stub raising NotImplementedError per the
`degenbot-dex-coverage-gap-2026-05-05.md` Q-7 design — full integration
is gated on a degenbot upstream PR + lending-layer state coordination).
This test is the read-side plumbing proof that paves the way: it
confirms `constantsView` decodes, the `liquidity` field matches the
pinned `LIQUIDITY` constant, the `factory` field matches `FACTORY`, the
declared token0/token1 are non-zero ERC20 addresses, and `oraclePrice`
returns a positive current price. When the math port lands, the same
fixture pattern can be extended with `getCollateralReserves` /
`getDebtReserves` comparisons after first deriving the
`(geometricMean, upperRange, lowerRange, *ExchangePrice)` inputs they
require.

Run by setting the env vars below; otherwise the suite is skipped so
unattended pytest runs against the solver package don't burn RPC credits
or flake on offline CI.

Required env vars:
    ARB_RPC_HTTP                  Arbitrum One RPC URL
    FLUID_DEX_PIN_BLOCK           block number to pin (decimal int or
                                  0x-hex)

Optional env vars:
    FLUID_DEX_POOL_ADDRESS        PoolT1 address. Defaults to USDC_ETH_POOL_T1.

Documented follow-ons:
- Reserve reads using getCollateralReserves / getDebtReserves once the
  PricesAndExchangePrice ingest is implemented.
- Math comparison once the Fluid swap math is ported.
- Liquidity-layer side reads (token0/1 supply + borrow exchange prices)
  via FluidLiquidity at LIQUIDITY.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

import pytest
from degenbot.execution.fluid_dex_addresses import (
    FACTORY as FLUID_FACTORY,
)
from degenbot.execution.fluid_dex_addresses import (
    LIQUIDITY as FLUID_LIQUIDITY,
)
from degenbot.execution.fluid_dex_addresses import (
    USDC_ETH_POOL_T1,
)
from web3 import Web3

if TYPE_CHECKING:
    from web3.contract import Contract

_ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

# Subset of IFluidDex PoolT1 ABI sufficient for the smoke. The full
# struct shapes match `docs/research/fluid/abis/IFluidDex_USDC_ETH_*.sol`
# library Structs section.
_POOL_T1_ABI: list[dict[str, object]] = [
    {
        "type": "function",
        "name": "constantsView",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [
            {
                "name": "",
                "type": "tuple",
                "components": [
                    {"name": "dexId", "type": "uint256"},
                    {"name": "liquidity", "type": "address"},
                    {"name": "factory", "type": "address"},
                    {
                        "name": "implementations",
                        "type": "tuple",
                        "components": [
                            {"name": "shift", "type": "address"},
                            {"name": "admin", "type": "address"},
                            {"name": "colOperations", "type": "address"},
                            {"name": "debtOperations", "type": "address"},
                            {"name": "perfectOperationsAndSwapOut", "type": "address"},
                        ],
                    },
                    {"name": "deployerContract", "type": "address"},
                    {"name": "token0", "type": "address"},
                    {"name": "token1", "type": "address"},
                    {"name": "supplyToken0Slot", "type": "bytes32"},
                    {"name": "borrowToken0Slot", "type": "bytes32"},
                    {"name": "supplyToken1Slot", "type": "bytes32"},
                    {"name": "borrowToken1Slot", "type": "bytes32"},
                    {"name": "exchangePriceToken0Slot", "type": "bytes32"},
                    {"name": "exchangePriceToken1Slot", "type": "bytes32"},
                    {"name": "oracleMapping", "type": "uint256"},
                ],
            }
        ],
    },
    {
        "type": "function",
        "name": "oraclePrice",
        "stateMutability": "view",
        "inputs": [{"name": "secondsAgos_", "type": "uint256[]"}],
        "outputs": [
            {
                "name": "twaps_",
                "type": "tuple[]",
                "components": [
                    {"name": "twap1by0", "type": "uint256"},
                    {"name": "lowestPrice1by0", "type": "uint256"},
                    {"name": "highestPrice1by0", "type": "uint256"},
                    {"name": "twap0by1", "type": "uint256"},
                    {"name": "lowestPrice0by1", "type": "uint256"},
                    {"name": "highestPrice0by1", "type": "uint256"},
                ],
            },
            {"name": "currentPrice_", "type": "uint256"},
        ],
    },
]


@dataclass(frozen=True)
class _Env:
    rpc_url: str
    pool: str
    pin_block: int


def _parse_block(raw: str) -> int:
    if raw.startswith(("0x", "0X")):
        return int(raw, 16)
    return int(raw)


def _read_env() -> _Env | None:
    rpc_url = os.environ.get("ARB_RPC_HTTP")
    pin_block_raw = os.environ.get("FLUID_DEX_PIN_BLOCK")
    if not rpc_url or not pin_block_raw:
        return None
    try:
        pin_block = _parse_block(pin_block_raw)
    except ValueError:
        return None
    pool = os.environ.get("FLUID_DEX_POOL_ADDRESS") or USDC_ETH_POOL_T1
    return _Env(
        rpc_url=rpc_url,
        pool=Web3.to_checksum_address(pool),
        pin_block=pin_block,
    )


_env: _Env | None = _read_env()

pytestmark = pytest.mark.skipif(
    _env is None,
    reason=(
        "Fluid PoolT1 reserve-read smoke requires ARB_RPC_HTTP + "
        "FLUID_DEX_PIN_BLOCK in the environment "
        "(FLUID_DEX_POOL_ADDRESS optional; defaults to USDC_ETH_POOL_T1)."
    ),
)


@pytest.fixture(scope="module")
def env() -> _Env:
    assert _env is not None  # narrowed by pytestmark above
    return _env


@pytest.fixture(scope="module")
def web3_client(env: _Env) -> Web3:
    return Web3(Web3.HTTPProvider(env.rpc_url))


@pytest.fixture(scope="module")
def pool_contract(web3_client: Web3, env: _Env) -> Contract:
    return web3_client.eth.contract(
        address=Web3.to_checksum_address(env.pool),
        abi=cast("Any", _POOL_T1_ABI),
    )


def test_constants_view_decodes_and_matches_address_bundle(
    pool_contract: Contract, env: _Env
) -> None:
    """`constantsView` must decode and the embedded `liquidity` and
    `factory` fields must match the pinned bundle. token0 / token1
    must be non-zero ERC20 addresses.
    """
    raw = pool_contract.functions.constantsView().call(block_identifier=env.pin_block)
    # tuple order matches the ABI components above.
    (
        dex_id,
        liquidity_addr,
        factory_addr,
        _impls,
        _deployer_contract,
        token0,
        token1,
        *_storage_and_oracle_fields,
    ) = raw

    assert int(dex_id) > 0, "dexId must be positive"
    assert Web3.to_checksum_address(liquidity_addr) == Web3.to_checksum_address(FLUID_LIQUIDITY), (
        f"pool reports liquidity={liquidity_addr}; expected {FLUID_LIQUIDITY} from fluid_dex_addresses.LIQUIDITY"
    )
    assert Web3.to_checksum_address(factory_addr) == Web3.to_checksum_address(FLUID_FACTORY), (
        f"pool reports factory={factory_addr}; expected {FLUID_FACTORY} from fluid_dex_addresses.FACTORY"
    )
    token0_cs = Web3.to_checksum_address(token0)
    token1_cs = Web3.to_checksum_address(token1)
    assert token0_cs != _ZERO_ADDRESS, "token0 must be a non-zero ERC20"
    assert token1_cs != _ZERO_ADDRESS, "token1 must be a non-zero ERC20"
    assert token0_cs.lower() != token1_cs.lower(), (
        f"token0 == token1 ({token0_cs}); pool would be degenerate"
    )


def test_oracle_price_returns_positive_current_price(pool_contract: Contract, env: _Env) -> None:
    """`oraclePrice([0])` must return a positive `currentPrice_`. We pass
    a single-element `secondsAgos_=[0]` so the call returns the spot price
    plus exactly one (zero-window) TWAP entry. A zero `currentPrice_`
    would indicate a misconfigured pool or wrong block.
    """
    twaps, current_price = pool_contract.functions.oraclePrice([0]).call(
        block_identifier=env.pin_block
    )
    assert int(current_price) > 0, "currentPrice_ must be positive"
    assert len(twaps) == 1, "expected exactly one TWAP entry for one secondsAgos input"
