"""DODO PMM port pinned-block staticcall comparison.

Opt-in network test that validates `dodo_pmm_math.py` against a live
DODO V2 pool on Arbitrum. Reads pool state via `getPMMState()`, runs
the Python port locally, and asserts the result against the contract's
`getMidPrice()` and (when fee-model plumbing is exposed) `querySellBase`.

Run by setting the env vars below; otherwise the suite is skipped so
unattended pytest runs against the solver package don't burn RPC credits
or flake on offline CI.

Required env vars:
    ARB_RPC_HTTP                  Arbitrum One RPC URL
    DODO_PMM_POOL_ADDRESS         DVM/DPP/DSP pool address (checksum or lower)
    DODO_PMM_PIN_BLOCK            block number to pin (decimal int or 0x-hex)

Optional env vars:
    DODO_PMM_TRADE_AMOUNT         pay amount for querySellBase (default: 10^18)
    DODO_PMM_DIRECTION            'sellBase' (default) | 'sellQuote'

What this test proves: the Python port of `PMMPricing.getMidPrice` and,
when the pool exposes the standard DPP/DSP fee-model plumbing, the
post-fee output of `querySellBase` / `querySellQuote` matches the
on-chain contract byte-for-byte at the pinned block.

What it does NOT prove: pre-fee curve equality on DVM pools (DVM stores
`_LP_FEE_RATE_` as a uint constant rather than a fee-model contract,
which we don't yet read here). That gap is logged as a follow-on inside
the test rather than as a separate skip — see the `pytest.skip` in
`test_quote_matches_python_after_dpp_fees`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

import pytest
from degenbot.execution.dodo_pmm_math import (
    PmmState,
    RState,
    get_mid_price,
    mul_floor,
    sell_base_token,
    sell_quote_token,
)
from web3 import Web3

if TYPE_CHECKING:
    from collections.abc import Callable

    from web3.contract import Contract

_ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
_DEFAULT_TRADE_AMOUNT = 10**18
_DIRECTION_SELL_BASE = "sellBase"
_DIRECTION_SELL_QUOTE = "sellQuote"

_DODO_V2_ABI: list[dict[str, object]] = [
    {
        "type": "function",
        "name": "getPMMState",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [
            {
                "name": "state",
                "type": "tuple",
                "components": [
                    {"name": "i", "type": "uint256"},
                    {"name": "K", "type": "uint256"},
                    {"name": "B", "type": "uint256"},
                    {"name": "Q", "type": "uint256"},
                    {"name": "B0", "type": "uint256"},
                    {"name": "Q0", "type": "uint256"},
                    {"name": "R", "type": "uint8"},
                ],
            }
        ],
    },
    {
        "type": "function",
        "name": "getMidPrice",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "midPrice", "type": "uint256"}],
    },
    {
        "type": "function",
        "name": "querySellBase",
        "stateMutability": "view",
        "inputs": [
            {"name": "trader", "type": "address"},
            {"name": "payBaseAmount", "type": "uint256"},
        ],
        "outputs": [
            {"name": "receiveQuoteAmount", "type": "uint256"},
            {"name": "mtFee", "type": "uint256"},
            {"name": "newRState", "type": "uint8"},
            {"name": "newBaseTarget", "type": "uint256"},
        ],
    },
    {
        "type": "function",
        "name": "querySellQuote",
        "stateMutability": "view",
        "inputs": [
            {"name": "trader", "type": "address"},
            {"name": "payQuoteAmount", "type": "uint256"},
        ],
        "outputs": [
            {"name": "receiveBaseAmount", "type": "uint256"},
            {"name": "mtFee", "type": "uint256"},
            {"name": "newRState", "type": "uint8"},
            {"name": "newQuoteTarget", "type": "uint256"},
        ],
    },
    {
        "type": "function",
        "name": "_LP_FEE_RATE_MODEL_",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"type": "address"}],
    },
    {
        "type": "function",
        "name": "_MT_FEE_RATE_MODEL_",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"type": "address"}],
    },
]

_FEE_RATE_MODEL_ABI: list[dict[str, object]] = [
    {
        "type": "function",
        "name": "getFeeRate",
        "stateMutability": "view",
        "inputs": [{"name": "trader", "type": "address"}],
        "outputs": [{"type": "uint256"}],
    },
]


@dataclass(frozen=True)
class _Env:
    rpc_url: str
    pool: str
    pin_block: int
    trade_amount: int
    direction: str


def _parse_block(raw: str) -> int:
    if raw.startswith("0x") or raw.startswith("0X"):
        return int(raw, 16)
    return int(raw)


def _read_env() -> _Env | None:
    rpc_url = os.environ.get("ARB_RPC_HTTP")
    pool = os.environ.get("DODO_PMM_POOL_ADDRESS")
    pin_block_raw = os.environ.get("DODO_PMM_PIN_BLOCK")
    if not rpc_url or not pool or not pin_block_raw:
        return None
    try:
        pin_block = _parse_block(pin_block_raw)
    except ValueError:
        return None
    direction = os.environ.get("DODO_PMM_DIRECTION", _DIRECTION_SELL_BASE)
    if direction not in {_DIRECTION_SELL_BASE, _DIRECTION_SELL_QUOTE}:
        return None
    trade_amount_raw = os.environ.get("DODO_PMM_TRADE_AMOUNT")
    try:
        trade_amount = int(trade_amount_raw) if trade_amount_raw else _DEFAULT_TRADE_AMOUNT
    except ValueError:
        return None
    if trade_amount <= 0:
        return None
    return _Env(
        rpc_url=rpc_url,
        pool=Web3.to_checksum_address(pool),
        pin_block=pin_block,
        trade_amount=trade_amount,
        direction=direction,
    )


_env: _Env | None = _read_env()

pytestmark = pytest.mark.skipif(
    _env is None,
    reason=(
        "DODO pinned-block staticcall test requires ARB_RPC_HTTP + "
        "DODO_PMM_POOL_ADDRESS + DODO_PMM_PIN_BLOCK in the environment."
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
        abi=cast("Any", _DODO_V2_ABI),
    )


def _read_pmm_state(pool: Contract, block: int) -> PmmState:
    raw = pool.functions.getPMMState().call(block_identifier=block)
    # Web3 v6 returns the tuple as a list when the ABI marks the output
    # as a struct. The component order is fixed: (i, K, B, Q, B0, Q0, R).
    i, k, b, q, b0, q0, r = raw
    return PmmState(i=int(i), K=int(k), B=int(b), Q=int(q), B0=int(b0), Q0=int(q0), R=RState(int(r)))


def _try_call(call: Callable[[], object]) -> object | None:
    try:
        return call()
    except Exception:
        return None


def _read_dpp_fee_rates(
    web3_client: Web3,
    pool: Contract,
    block: int,
) -> tuple[int, int] | None:
    """Return `(lp_fee_rate, mt_fee_rate)` if the pool exposes the standard
    DPP/DSP `_LP_FEE_RATE_MODEL_` + `_MT_FEE_RATE_MODEL_` plumbing.

    Returns `None` for DVM and other pool types that store the fee rate
    as a uint constant — those need a different reader. Logging that gap
    here keeps the test useful for the DPP/DSP variant without forcing
    it on every pool.
    """
    lp_model_addr = _try_call(lambda: pool.functions._LP_FEE_RATE_MODEL_().call(block_identifier=block))
    mt_model_addr = _try_call(lambda: pool.functions._MT_FEE_RATE_MODEL_().call(block_identifier=block))
    if not isinstance(lp_model_addr, str) or not isinstance(mt_model_addr, str):
        return None
    lp_model = web3_client.eth.contract(address=Web3.to_checksum_address(lp_model_addr), abi=_FEE_RATE_MODEL_ABI)
    mt_model = web3_client.eth.contract(address=Web3.to_checksum_address(mt_model_addr), abi=_FEE_RATE_MODEL_ABI)
    lp_rate = _try_call(lambda: lp_model.functions.getFeeRate(_ZERO_ADDRESS).call(block_identifier=block))
    mt_rate = _try_call(lambda: mt_model.functions.getFeeRate(_ZERO_ADDRESS).call(block_identifier=block))
    if not isinstance(lp_rate, int) or not isinstance(mt_rate, int):
        return None
    return int(lp_rate), int(mt_rate)


def test_pmm_state_round_trips(pool_contract: Contract, env: _Env) -> None:
    state = _read_pmm_state(pool_contract, env.pin_block)
    assert state.i > 0, "pool oracle price must be positive"
    assert state.B > 0, "pool base reserve must be positive"
    assert state.Q > 0, "pool quote reserve must be positive"
    assert state.B0 > 0, "base target must be positive"
    assert state.Q0 > 0, "quote target must be positive"


def test_get_mid_price_matches_python(pool_contract: Contract, env: _Env) -> None:
    """Python `get_mid_price` must match the contract's `getMidPrice` byte-for-byte."""
    state = _read_pmm_state(pool_contract, env.pin_block)
    chain_mid = int(pool_contract.functions.getMidPrice().call(block_identifier=env.pin_block))
    python_mid = get_mid_price(state)
    assert python_mid == chain_mid, (
        f"mid-price mismatch at block {env.pin_block}: python={python_mid} vs chain={chain_mid}; state={state}"
    )


def test_quote_matches_python_after_dpp_fees(web3_client: Web3, pool_contract: Contract, env: _Env) -> None:
    """Python `sell_base_token`/`sell_quote_token` after applying the
    contract's LP+MT fee math must equal `querySellBase`/`querySellQuote`.

    Skips on DVM pools (and any other pool that doesn't expose the
    `_LP_FEE_RATE_MODEL_` / `_MT_FEE_RATE_MODEL_` getters) — that's a
    distinct fee-plumbing test left as a follow-on.
    """
    fee_rates = _read_dpp_fee_rates(web3_client, pool_contract, env.pin_block)
    if fee_rates is None:
        pytest.skip(
            "pool does not expose DPP/DSP fee-model plumbing "
            "(_LP_FEE_RATE_MODEL_ / _MT_FEE_RATE_MODEL_); "
            "DVM-style fee-rate reader is a separate follow-on."
        )
    lp_rate, mt_rate = fee_rates
    state = _read_pmm_state(pool_contract, env.pin_block)

    if env.direction == _DIRECTION_SELL_BASE:
        chain_receive, chain_mt_fee, chain_new_r_state, _chain_new_target = pool_contract.functions.querySellBase(
            _ZERO_ADDRESS, env.trade_amount
        ).call(block_identifier=env.pin_block)
        gross_python, py_new_r = sell_base_token(state, env.trade_amount)
    else:
        chain_receive, chain_mt_fee, chain_new_r_state, _chain_new_target = pool_contract.functions.querySellQuote(
            _ZERO_ADDRESS, env.trade_amount
        ).call(block_identifier=env.pin_block)
        gross_python, py_new_r = sell_quote_token(state, env.trade_amount)

    py_mt_fee = mul_floor(gross_python, mt_rate)
    py_lp_fee = mul_floor(gross_python, lp_rate)
    py_receive_net = gross_python - py_lp_fee - py_mt_fee

    assert py_receive_net == int(chain_receive), (
        f"net receive mismatch ({env.direction}) at block {env.pin_block}: "
        f"python={py_receive_net} vs chain={chain_receive}; "
        f"gross_python={gross_python}, lp_rate={lp_rate}, mt_rate={mt_rate}"
    )
    assert py_mt_fee == int(chain_mt_fee), (
        f"mt fee mismatch ({env.direction}) at block {env.pin_block}: python={py_mt_fee} vs chain={chain_mt_fee}"
    )
    assert int(py_new_r) == int(chain_new_r_state), (
        f"new RState mismatch ({env.direction}) at block {env.pin_block}: "
        f"python={int(py_new_r)} vs chain={int(chain_new_r_state)}"
    )
