"""Balancer V3 Weighted pool pinned-block fixture comparison.

Opt-in network test that validates `balancer_v3_weighted_math.py`
against a live Balancer V3 Weighted pool on Arbitrum at a pinned block.
Reads pool weights, balances, and the static swap fee, runs the Python
port locally, and asserts byte-equal output against the V3 Router's
`querySwapSingleTokenExactIn`.

Run by setting the env vars below; otherwise the suite is skipped so
unattended pytest runs against the solver package don't burn RPC credits
or flake on offline CI.

Required env vars:
    ARB_RPC_HTTP                  Arbitrum One RPC URL
    BALANCER_V3_POOL_ADDRESS      Weighted pool address (single-pair
                                  case; both tokens MUST be 18-decimal
                                  for this iteration — multi-token + non-
                                  18-decimal scaling factors are a
                                  follow-on)
    BALANCER_V3_TOKEN_IN          ERC20 input token address (must be in
                                  the pool token list)
    BALANCER_V3_TOKEN_OUT         ERC20 output token address (must be in
                                  the pool token list)
    BALANCER_V3_PIN_BLOCK         block number to pin (decimal int or
                                  0x-hex)

Optional env vars:
    BALANCER_V3_AMOUNT_IN         exactAmountIn for the swap query
                                  (default: 10^17 — 0.1 token to stay
                                  well under the 30% MAX_IN_RATIO)

Scope of this iteration:
- single-pair weighted pool (2 tokens)
- both tokens 18 decimals
- static swap fee (no dynamic-fee hook)
- ExactIn only

Follow-ons (separate test files):
- multi-token pools (n > 2)
- non-18-decimal tokens (decimal-scaling factors)
- dynamic-fee hook variants (StableSurge, etc.)
- ExactOut path

Address pin (the V3 Router used as validation oracle):
    0xEAedc32a51c510d35ebC11088fD5fF2b47aACF2E (Arbitrum One,
    20250307-v3-router-v2; mirrored in
    `solver/driver/execution/balancer_v3_addresses.py`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

import pytest
from degenbot.execution import balancer_v3_weighted_math as wm
from degenbot.execution.balancer_fixed_point import mul_up
from degenbot.execution.balancer_v3_addresses import ROUTER as V3_ROUTER_ADDRESS
from degenbot.execution.balancer_v3_addresses import VAULT as V3_VAULT_ADDRESS
from web3 import Web3

if TYPE_CHECKING:
    from web3.contract import Contract

_DEFAULT_AMOUNT_IN = 10**17  # 0.1 token, well under MAX_IN_RATIO (30%)
_ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

# IVault.getPoolTokens returns the token list. VaultExtension on V3 also exposes
# `getPoolTokenInfo` and `getPoolTokens`, both reachable through the Vault
# proxy. We prefer `getPoolTokens` because the typed ABI is simpler (the
# `TokenInfo` struct contains a non-trivial enum that Web3.py decodes with
# extra ceremony).
_VAULT_ABI: list[dict[str, object]] = [
    {
        "type": "function",
        "name": "getPoolTokens",
        "stateMutability": "view",
        "inputs": [{"name": "pool", "type": "address"}],
        "outputs": [{"name": "tokens", "type": "address[]"}],
    },
    {
        "type": "function",
        "name": "getStaticSwapFeePercentage",
        "stateMutability": "view",
        "inputs": [{"name": "pool", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "type": "function",
        "name": "getCurrentLiveBalances",
        "stateMutability": "view",
        "inputs": [{"name": "pool", "type": "address"}],
        "outputs": [{"name": "balancesLiveScaled18", "type": "uint256[]"}],
    },
]

_WEIGHTED_POOL_ABI: list[dict[str, object]] = [
    {
        "type": "function",
        "name": "getNormalizedWeights",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256[]"}],
    },
]

_ROUTER_ABI: list[dict[str, object]] = [
    {
        "type": "function",
        "name": "querySwapSingleTokenExactIn",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "pool", "type": "address"},
            {"name": "tokenIn", "type": "address"},
            {"name": "tokenOut", "type": "address"},
            {"name": "exactAmountIn", "type": "uint256"},
            {"name": "sender", "type": "address"},
            {"name": "userData", "type": "bytes"},
        ],
        "outputs": [{"name": "amountCalculated", "type": "uint256"}],
    },
]


@dataclass(frozen=True)
class _Env:
    rpc_url: str
    pool: str
    token_in: str
    token_out: str
    pin_block: int
    amount_in: int


def _parse_block(raw: str) -> int:
    if raw.startswith("0x") or raw.startswith("0X"):
        return int(raw, 16)
    return int(raw)


def _read_env() -> _Env | None:
    rpc_url = os.environ.get("ARB_RPC_HTTP")
    pool = os.environ.get("BALANCER_V3_POOL_ADDRESS")
    token_in = os.environ.get("BALANCER_V3_TOKEN_IN")
    token_out = os.environ.get("BALANCER_V3_TOKEN_OUT")
    pin_block_raw = os.environ.get("BALANCER_V3_PIN_BLOCK")
    if not rpc_url or not pool or not token_in or not token_out or not pin_block_raw:
        return None
    try:
        pin_block = _parse_block(pin_block_raw)
    except ValueError:
        return None
    amount_in_raw = os.environ.get("BALANCER_V3_AMOUNT_IN")
    try:
        amount_in = int(amount_in_raw) if amount_in_raw else _DEFAULT_AMOUNT_IN
    except ValueError:
        return None
    if amount_in <= 0:
        return None
    return _Env(
        rpc_url=rpc_url,
        pool=Web3.to_checksum_address(pool),
        token_in=Web3.to_checksum_address(token_in),
        token_out=Web3.to_checksum_address(token_out),
        pin_block=pin_block,
        amount_in=amount_in,
    )


_env: _Env | None = _read_env()

pytestmark = pytest.mark.skipif(
    _env is None,
    reason=(
        "Balancer V3 Weighted pinned-block fixture requires ARB_RPC_HTTP + "
        "BALANCER_V3_POOL_ADDRESS + BALANCER_V3_TOKEN_IN + BALANCER_V3_TOKEN_OUT + "
        "BALANCER_V3_PIN_BLOCK in the environment."
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
def vault_contract(web3_client: Web3) -> Contract:
    return web3_client.eth.contract(
        address=Web3.to_checksum_address(V3_VAULT_ADDRESS),
        abi=cast("Any", _VAULT_ABI),
    )


@pytest.fixture(scope="module")
def pool_contract(web3_client: Web3, env: _Env) -> Contract:
    return web3_client.eth.contract(
        address=Web3.to_checksum_address(env.pool),
        abi=cast("Any", _WEIGHTED_POOL_ABI),
    )


@pytest.fixture(scope="module")
def router_contract(web3_client: Web3) -> Contract:
    return web3_client.eth.contract(
        address=Web3.to_checksum_address(V3_ROUTER_ADDRESS),
        abi=cast("Any", _ROUTER_ABI),
    )


def _read_pool_state(vault: Contract, pool: Contract, env: _Env) -> tuple[list[str], list[int], list[int], int]:
    """Return (tokens, weights, live-scaled-balances-18, swap-fee-pct)."""
    tokens_raw = vault.functions.getPoolTokens(env.pool).call(block_identifier=env.pin_block)
    weights_raw = pool.functions.getNormalizedWeights().call(block_identifier=env.pin_block)
    balances_raw = vault.functions.getCurrentLiveBalances(env.pool).call(block_identifier=env.pin_block)
    fee_raw = vault.functions.getStaticSwapFeePercentage(env.pool).call(block_identifier=env.pin_block)
    tokens = [str(Web3.to_checksum_address(t)) for t in tokens_raw]
    weights = [int(w) for w in weights_raw]
    balances = [int(b) for b in balances_raw]
    return tokens, weights, balances, int(fee_raw)


def test_pool_state_round_trips(vault_contract: Contract, pool_contract: Contract, env: _Env) -> None:
    tokens, weights, balances, fee = _read_pool_state(vault_contract, pool_contract, env)
    assert len(tokens) == 2, f"this iteration handles single-pair Weighted pools only; pool has {len(tokens)} tokens"
    assert len(weights) == len(tokens) == len(balances)
    assert sum(weights) == 10**18, f"normalized weights must sum to 1e18; got {sum(weights)}"
    assert all(b > 0 for b in balances)
    assert 0 <= fee < 10**18


def test_query_swap_single_token_exact_in_matches_python(
    vault_contract: Contract,
    pool_contract: Contract,
    router_contract: Contract,
    env: _Env,
) -> None:
    """Python `compute_out_given_exact_in` after applying the same fee
    convention as the V3 Vault must equal `Router.querySwapSingleTokenExactIn`.
    """
    tokens, weights, balances, swap_fee = _read_pool_state(vault_contract, pool_contract, env)

    token_in_lower = env.token_in.lower()
    token_out_lower = env.token_out.lower()
    lowered = [t.lower() for t in tokens]
    if token_in_lower not in lowered or token_out_lower not in lowered:
        pytest.fail(
            f"BALANCER_V3_TOKEN_IN/OUT must be among pool tokens {tokens}; got in={env.token_in} out={env.token_out}",
        )
    idx_in = lowered.index(token_in_lower)
    idx_out = lowered.index(token_out_lower)

    # Vault charges fee on the input side: amountIn -> amountInAfterFee
    # before the pool curve consumes it. Solidity uses mulUp on the fee.
    fee_amount = mul_up(env.amount_in, swap_fee)
    amount_in_net = env.amount_in - fee_amount

    expected_amount_out = wm.compute_out_given_exact_in(
        balance_in=balances[idx_in],
        weight_in=weights[idx_in],
        balance_out=balances[idx_out],
        weight_out=weights[idx_out],
        amount_in=amount_in_net,
    )

    chain_amount_out = int(
        router_contract.functions.querySwapSingleTokenExactIn(
            env.pool,
            env.token_in,
            env.token_out,
            env.amount_in,
            _ZERO_ADDRESS,
            b"",
        ).call(block_identifier=env.pin_block)
    )

    assert expected_amount_out == chain_amount_out, (
        f"amountOut mismatch at block {env.pin_block}: "
        f"python={expected_amount_out} vs chain={chain_amount_out}; "
        f"balances={balances}, weights={weights}, fee={swap_fee}, "
        f"amount_in={env.amount_in}, amount_in_net={amount_in_net}"
    )
