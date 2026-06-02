# Degenbot

Python classes to aid rapid development of Uniswap (V2, V3, V4), Curve StableSwap (V1 and NG), Solidly V2, Balancer V2, and Aave V3 integrations on EVM-compatible blockchains.

## Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Supported Protocols](#supported-protocols)
- [Examples](#examples)
  - [Uniswap V2 Liquidity Pools](#uniswap-v2-liquidity-pools)
  - [Uniswap V3 Liquidity Pools](#uniswap-v3-liquidity-pools)
  - [Uniswap V4 Liquidity Pools](#uniswap-v4-liquidity-pools)
  - [Forking With Anvil](#forking-with-anvil)
  - [Uniswap Arbitrage](#uniswap-arbitrage)
  - [Chainlink Price Feeds](#chainlink-price-feeds)
- [CLI Reference](#cli-reference)
- [Bot](#bot)
- [Configuration](#configuration)
- [Rust Extension](#rust-extension)
- [Documentation](#documentation)
- [MEV-Arbitrum Overlay](#mev-arbitrum-overlay)
- [Contributing](#contributing)
- [License](#license)
- [Donation](#donation)

## Overview

Degenbot is a set of Python classes that abstract many of the implementation details of Uniswap liquidity pools and their underlying ERC-20 tokens. It uses [web3.py](https://github.com/ethereum/web3.py/) for communication with an EVM blockchain through the standard JSON-RPC interface.

These classes serve as building blocks for the lessons published by [BowTiedDevil](https://twitter.com/BowTiedDevil) on [Degen Code](https://www.degencode.com/).

## Installation

### Requirements

- Python 3.12+
- `pip`, `uv`, or similar package management tool

### From PyPI

```bash
pip install degenbot
```

### From Source

```bash
git clone https://github.com/BowTiedDevil/degenbot.git
cd degenbot
uv sync  # or: pip install -e .
```

## Quick Start

```python
import web3
import degenbot

# Connect to an Ethereum RPC endpoint
w3 = web3.Web3(web3.HTTPProvider("https://eth-mainnet.example.com"))

# Verify connection
assert w3.is_connected()

# Create a Uniswap V3 pool helper from an address
pool = degenbot.UniswapV3Pool("0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8")

# Inspect pool state
print(f"Pool: {pool.name}")
print(f"Token 0: {pool.token0.symbol}")
print(f"Token 1: {pool.token1.symbol}")
print(f"Liquidity: {pool.liquidity}")

# Calculate swap outputs
amount_out = pool.calculate_tokens_out_from_tokens_in(
    token_in=pool.token0,
    token_in_quantity=10**18,  # 1 token (18 decimals)
)
print(f"Output: {amount_out}")
```

## Supported Protocols

### DEXs (Automated Market Makers)

| Protocol | Versions | Chains |
|----------|----------|--------|
| Uniswap | V2, V3, V4 | Ethereum, Base, Arbitrum |
| Aerodrome | V2, V3 | Base |
| PancakeSwap | V2, V3 | Ethereum, Base |
| SushiSwap | V2, V3 | Ethereum, Base |
| Curve | StableSwap V1, StableSwap-NG | Ethereum, Arbitrum |
| Solidly | V2 | Ethereum, Base | *(utility functions only, no pool class)*
| Balancer | V2, V2 ComposableStable | Ethereum | *(stable + composable-stable pool models; see `balancer/stable_pools.py`, `balancer/composable_stable_pools.py`)* |
| Camelot | V2, V3 (Algebra) | Arbitrum | *(V3 stored in `CamelotV3PoolTable`; activatable Algebra pool model gated — see CLI note below)* |
| SwapBased | V2 | Base |

### Lending Protocols

| Protocol | Features |
|----------|----------|
| Aave V3 | Supply, Borrow, Withdraw, Repay, Liquidation, E-Mode, GHO |

### Infrastructure

| Feature | Description |
|---------|-------------|
| Chainlink Price Feeds | Oracle price data |
| Anvil Forking | Local forked blockchain for testing |

## Examples

The following snippets assume a connected `Web3` instance with a working provider on Ethereum mainnet (chain ID #1), and the classes imported under the `degenbot` namespace.

### Uniswap V2 Liquidity Pools

```python
# Create `UniswapV2Pool` object from on-chain data at the given address and 
# current chain height
>>> lp = degenbot.UniswapV2Pool('0xBb2b8038a1640196FbE3e38816F3e67Cba72D940')
• WBTC (Wrapped BTC)
• WETH (Wrapped Ether)
• Token 0: WBTC - Reserves: 10732489743
• Token 1: WETH - Reserves: 2056834999904002274711

# Inspect the tokens held by the pool
>>> lp.token0
Erc20Token(
    address=0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599, 
    symbol='WBTC', 
    name='Wrapped BTC', 
    decimals=8
)

>>> lp.token1
Erc20Token(
    address=0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2, 
    symbol='WETH', 
    name='Wrapped Ether', 
    decimals=18
)

>>> lp.fee_token0
Fraction(3, 1000)

>>> lp.fee_token1
Fraction(3, 1000)

# Predict the input and output values for swaps through the pool, accounting for fees
>>> lp.calculate_tokens_out_from_tokens_in(
    token_in=lp.token1, 
    token_in_quantity=1*10**18
)
5199789

>>> lp.calculate_tokens_in_from_tokens_out(
    token_out=lp.token0, 
    token_out_quantity=5199789
)
999999992817074189

# Update the current reserves from the live blockchain
>>> lp.auto_update(silent=False)
[WBTC-WETH (V2, 0.30%)]
WBTC: 10732455184
WETH: 2056841643098872755548
       
>>> lp.reserves_token0
10732455184

>>> lp.reserves_token1
2056841643098872755548
```

### Uniswap V3 Liquidity Pools

```python
>>> lp = degenbot.UniswapV3Pool('0xCBCdF9626bC03E24f779434178A73a0B4bad62eD')
WBTC-WETH (V3, 0.30%)
• Token 0: WBTC
• Token 1: WETH
• Fee: 3000
• Liquidity: 544425151051415575
• SqrtPrice: 34048891009198980752047510166697902
• Tick: 259432

# Calculate inputs and outputs
>>> lp.calculate_tokens_out_from_tokens_in(
    token_in=lp.token1, 
    token_in_quantity=1*10**18
)
5398169

>>> lp.calculate_tokens_in_from_tokens_out(
    token_out=lp.token0, 
    token_out_quantity=5398169
)
999999871563434214

# Inspect the known liquidity positions
>>> lp.tick_bitmap
{
    0: UniswapV3BitmapAtWord(
        bitmap=1,
        block=18517665
        ),
    16: UniswapV3BitmapAtWord(
        bitmap=115792089237316195423570985008687907853268655437644779123584680198630541352072,
        block=18517670
        )
}

# The V3 liquidity pool helper is optimized for fast instantiation, and will lazy-load 
# liquidity data for positions outside of the current range as needed.
>>> lp.tick_data
{
    0: UniswapV3LiquidityAtTick(
        liquidityNet=10943161472679, 
        liquidityGross=10943161472679, 
        block=18517665
    ),
    261060: UniswapV3LiquidityAtTick(
        liquidityNet=-910396189679465, 
        liquidityGross=910396189679465, 
        block=18517670
    ),
    261000: UniswapV3LiquidityAtTick(
        liquidityNet=-3774266260841234, 
        liquidityGross=3774266260841234, 
        block=18517670
    ),
    ...
}
```

### Uniswap V4 Liquidity Pools

Uniswap V4 introduces hooks and a new pool manager architecture. The `UniswapV4Pool` class provides access to V4 pools with support for the new features.

```python
>>> lp = degenbot.UniswapV4Pool(
...     pool_id='0x96d4b53a38337a5733179751781178a2613306063c511b78cd02684739288c0a',
...     pool_manager_address='0x498581fF718922c3f8e6A244956aF099B2652b2b',
...     state_view_address='0xA3c0c9b65baD0b08107Aa264b0f3dB444b867A71',
...     tokens=[
...         '0x0000000000000000000000000000000000000000', 
...         '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
...     ],
...     fee=500,
...     tick_spacing=10
... )
ETH-USDC (UniswapV4Pool, id=0x96d4b53a38337a5733179751781178a2613306063c511b78cd02684739288c0a)
• ID: 0x96d4b53a38337a5733179751781178a2613306063c511b78cd02684739288c0a
• Token 0: ETH
• Token 1: USDC
• Liquidity: 60429069420043934
• SqrtPrice: 4220772448119892035402666
• Tick: -196812

# Calculate output for a 1 ETH swap
>>> lp.calculate_tokens_out_from_tokens_in(
...     token_in=lp.token0, 
...     token_in_quantity=1*10**18,
... )
2834164215

# Inspect active hooks
>>> lp.active_hooks
frozenset()

# Get pool key information
>>> lp.pool_key
UniswapV4PoolKey(
    currency0='0x0000000000000000000000000000000000000000',
    currency1='0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
    fee=500,
    tick_spacing=10,
    hooks='0x0000000000000000000000000000000000000000'
)
```

For dynamic-fee pools, the PoolKey `fee` is the `LPFeeLibrary.DYNAMIC_FEE_FLAG`
sentinel (`0x800000`). The effective LP fee is read from `StateView.getSlot0(pool_id)`;
hooks may also return one-swap override fees that require quoter or fork simulation to model safely.
Hook fees charged through return deltas are execution costs and must be included in route profitability.

### Forking With Anvil

The `AnvilFork` class is used to launch a fork with `anvil` from the [Foundry](https://github.com/foundry-rs/foundry) toolkit. The object provides a `w3` attribute, connected to an IPC socket, which can be used to communicate with the fork like a typical RPC.

```python
>>> fork = degenbot.AnvilFork(fork_url='http://localhost:8545')
>>> fork.w3.eth.chain_id
1
>>> fork.w3.eth.block_number
22675736

# The `AnvilFork` instance also exposes HTTP and WS endpoints that can be used to make a 
# separate connection from a remote machine.
>>> import web3
>>> _w3 = web3.Web3(web3.HTTPProvider(fork.http))
>>> _w3.is_connected()
True
>>> _w3 = web3.Web3(web3.LegacyWebSocketProvider(fork.ws_url))
>>> _w3.is_connected()
True

# The fork can be reset to a different endpoint, which defaults to the latest block.
>>> fork.reset(fork_url='http://localhost:8544')
>>> fork.w3.eth.chain_id
8453

# The fork can also be reset with a specified block number or a transaction hash.
>>> fork.reset(fork_url='http://localhost:8545', block_number=22_675_800)
>>> fork.w3.eth.chain_id
1
>>> fork.w3.eth.block_number
22675800

>>> fork.reset(fork_url='http://localhost:8545', block_number=22_675_800)
>>> fork.w3.eth.chain_id
1
>>> fork.w3.eth.block_number
22675800

# The fork can also be reset to an imaginary block after a specific transaction 
# hash. See the [Anvil reference](https://getfoundry.sh/anvil/reference/) for the 
# associated `--fork-transaction-hash` option.
>>> fork.reset(
    fork_url='http://localhost:8545',
    transaction_hash='0xc16e63e693a2748559c0fd653ade195be426472dddc5bfa3fcc769c4c88c249c'
)
>>> fork.w3.eth.block_number
22675814

# Blocks can be manually mined
>>> fork.mine()
>>> fork.w3.eth.block_number
22675815

# Byte code can be set for an arbitrary address.
>>> fork.set_code(
    address='0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045', 
    bytecode=bytes.fromhex('45')
)
>>> fork.w3.eth.get_code('0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045')
HexBytes('0x45')
```

#### Anvil Options

The Anvil client offers [many options](https://getfoundry.sh/anvil/reference/anvil/). The most common ones are exposed by constructor options to `AnvilFork`. 

Users wanting fine-grained control over **all** client options may pass them through the `anvil_opts` argument, which takes a list of strings. These will be passed directly to the client after all of the managed options. 

```python
# Launch with the Optimism feature set, which enables special transaction types.
>>> fork = degenbot.AnvilFork(
    fork_url='http://localhost:8544',
    anvil_opts=['--optimism']
)

# Launch with a non-default hardfork, which may be necessary for accurate simulation on a 
# historical block.
>>> fork = degenbot.AnvilFork(
    fork_url='http://localhost:8545',
    fork_block=12_980_000,
    anvil_opts=['--hardfork=london']
)

# Launch with a non-default transaction pool ordering scheme
>>> fork = degenbot.AnvilFork(
    fork_url='http://localhost:8545',
    anvil_opts=['--order=fifo']
)

# Launch with certain debugging features enabled
>>> fork = degenbot.AnvilFork(
    fork_url='http://localhost:8545',
    anvil_opts=[
        '--disable-block-gas-limit',
        '--disable-code-size-limit',
        '--disable-min-priority-fee',
    ]
)
```

### Uniswap Arbitrage

Several classes are provided to simplify the calculation of optimal arbitrage amounts for a given sequence of pools.

```python
>>> v2_lp = degenbot.UniswapV2Pool('0xBb2b8038a1640196FbE3e38816F3e67Cba72D940')
• WBTC (Wrapped BTC)
• WETH (Wrapped Ether)
• Token 0: WBTC - Reserves: 6390612659
• Token 1: WETH - Reserves: 2534027291379197003140

>>> v3_lp = degenbot.UniswapV3Pool('0xCBCdF9626bC03E24f779434178A73a0B4bad62eD')
WBTC-WETH (UniswapV3Pool, 0.30%)
• Address: 0xCBCdF9626bC03E24f779434178A73a0B4bad62eD           
• Token 0: WBTC           
• Token 1: WETH
• Fee: 3000               
• Liquidity: 261799575241796322         
• SqrtPrice: 49883600179466982678044042954714957         
• Tick: 267070              
• State Block (Initial): 22676748
                                                                       
>>> weth = v2_lp.token1 

>>> arb = degenbot.UniswapLpCycle(
    id="test", 
    input_token=weth, 
    swap_pools=[v2_lp, v3_lp]
)

# The minimum rate of exchange for a profitable arbitrage is 1.0. The pool states at
# a given block are likely to be less, so override the minimum for illustration.
# The `ArbitrageCalculationResult` must be encoded as a properly-formed transaction 
# by the user and broadcast to the network to secure the opportunity.
>>> arb.calculate(min_rate_of_exchange=0.8)
ArbitrageCalculationResult(
    id='test', 
    input_token=Erc20Token(
        address=0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2, 
        symbol='WETH', 
        name='Wrapped Ether', 
        decimals=18
    ), 
    profit_token=Erc20Token(
        address=0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2, 
        symbol='WETH', 
        name='Wrapped Ether', 
        decimals=18
    ), 
    input_amount=69600394635598,
    profit_amount=-623178922742, 
    swap_amounts=(
        UniswapV2PoolSwapAmounts(
            pool='0xBb2b8038a1640196FbE3e38816F3e67Cba72D940', 
            amounts_in=(0, 69600394635598), 
            amounts_out=(175, 0), 
            recipient=None
        ), 
        UniswapV3PoolSwapAmounts(
            pool='0xCBCdF9626bC03E24f779434178A73a0B4bad62eD',
            amount_specified=175,
            zero_for_one=True, 
            sqrt_price_limit_x96=4295128740, 
            recipient=None
        )
    ), 
    state_block=22676748
)
```

### Chainlink Price Feeds

Chainlink price feeds provide reliable oracle data for various assets. The `ChainlinkPriceContract` class simplifies access to these feeds.

```python
# Load the price feed for ETH/USD 
>>> price_feed = degenbot.ChainlinkPriceContract(
...     '0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419'
... )

>>> price_feed.price
2836.68731709

# Check the decimals used by the price feed
>>> price_feed.decimals
8

# Call an arbitrary function `latestRoundData` on the underlying contract
>>> price_feed.w3_contract.functions.latestRoundData().call()
[
    129127208515966883788, 
    283668731709, 
    1766031970, 
    1766031983, 
    129127208515966883788
]
```

## CLI Reference

Degenbot provides a command-line interface for managing blockchain data and pool state.

### Installation

The CLI is installed automatically with the package:

```bash
pip install degenbot
degenbot --help
```

### Commands

#### Bot

```bash
# Scan registered pools and print the best opportunity
degenbot bot best \
  --chain-id 1 \
  --input-token 0x0000000000000000000000000000000000000000 \
  --from-address 0x000000000000000000000000000000000000dEaD
```

#### Execution Calldata (MEV-Arbitrum overlay)

Encode calldata for the parent-repo `Executor.sol` entry points. Inputs are JSON payloads
echoed back as `0x`-prefixed hex; the command itself does not broadcast. See
[MEV-Arbitrum Overlay](#mev-arbitrum-overlay) for the full surface.

```bash
# Encode Executor.executeNativeArb(...)
degenbot execution native-arb \
  --flash-lender 0x... --flash-protocol AaveV3 \
  --flash-token 0x... --flash-amount 1000000 \
  --swaps-json '[{"kind":"UniswapV3", ...}]' \
  --min-profit 0 --deadline 0

# Encode Executor.matchInternal(...)
degenbot execution match-internal \
  --cow-settlement-calldata 0x... \
  --uniswapx-batch-calldata 0x... \
  --expected-token-inflows-json '["0x..."]' \
  --expected-token-inflow-min-json '[0]' \
  --flash-lender 0x... --flash-protocol AaveV3 \
  --flash-token 0x... --flash-amount 0 \
  --min-profit 0 --deadline 0

# Encode Executor.composeFourLeg(...)
degenbot execution compose-four-leg \
  --across-fill-calldata 0x... --arb-swaps-json '[...]' \
  --cow-fill-calldata 0x... --uniswapx-rebalance-calldata 0x... \
  --flash-lender 0x... --flash-protocol AaveV3 \
  --flash-token 0x... --flash-amount 0 \
  --min-profit 0 --deadline 0
```

#### Database Management

```bash
# Back up the database
degenbot database backup

# Reset database (creates fresh schema)
degenbot database reset

# Upgrade database schema to latest version
degenbot database upgrade [--force]

# Compact database to reclaim space
degenbot database compact
```

#### Pool State Management

```bash
# Update pool metadata and liquidity positions for all active exchanges
degenbot pool update [--chunk SIZE] [--to-block BLOCK]

# Activate an exchange for tracking
degenbot exchange activate arbitrum_uniswap_v4

# Deactivate an exchange
degenbot exchange deactivate arbitrum_uniswap_v4
```

**Supported exchanges:**
- Arbitrum: `arbitrum_camelot_v2`, `arbitrum_sushiswap_v2`, `arbitrum_sushiswap_v3`, `arbitrum_uniswap_v2`, `arbitrum_uniswap_v3`, `arbitrum_uniswap_v4`
- Base: `base_aerodrome_v2`, `base_aerodrome_v3`, `base_pancakeswap_v2`, `base_pancakeswap_v3`, `base_sushiswap_v2`, `base_sushiswap_v3`, `base_swapbased_v2`, `base_uniswap_v2`, `base_uniswap_v3`, `base_uniswap_v4`
- Ethereum: `ethereum_pancakeswap_v2`, `ethereum_pancakeswap_v3`, `ethereum_sushiswap_v2`, `ethereum_sushiswap_v3`, `ethereum_uniswap_v2`, `ethereum_uniswap_v3`, `ethereum_uniswap_v4`

Camelot Algebra V3/V4 constants are pinned in the mev-arbitrum TypeScript registry. The Python
Degenbot package tracks Camelot V2 pools today; Algebra concentrated-liquidity pool discovery needs
a dedicated Algebra model/updater before it can be safely exposed as an activatable exchange.

Curve Stableswap-NG uses the StableSwap `int128` index ABI (`exchange(int128,int128,uint256,uint256)`)
despite the NG deployment family name. On Arbitrum, use the Curve factory for discovery and route
plain/metapools through the stable Curve pool model unless a pool is explicitly classified as
crypto-NG.

Uniswap V4 pools are discovered from `PoolManager.initialize` events. The database stores the
`PoolId`/pool hash plus the PoolKey fields because V4 pools are not standalone contracts: sorted
`currency0/currency1`, fee, tick spacing, and hooks define the pool.
For dynamic-fee pools, this stored `fee` is PoolKey identity only; live quote math must use
`StateView` slot0 `lpFee`/`protocolFee`, and hook-return fee overrides require quoter or fork
simulation before routing size through the pool.

#### Aave State Management

```bash
# Update Aave V3 positions for all active markets
degenbot aave update [--chunk SIZE] [--to-block BLOCK]

# Activate an Aave market
degenbot aave activate ethereum_aave_v3

# Deactivate an Aave market
degenbot aave deactivate ethereum_aave_v3

# Show a user's position in a market
degenbot aave position show <ADDRESS> [--market MARKET] [--chain-id CHAIN_ID]

# Show risk parameters for a user's position
degenbot aave position risk <ADDRESS> [--market MARKET] [--chain-id CHAIN_ID]

# Show market state
degenbot aave market show [--chain-id CHAIN_ID] [--name NAME]
```

### Block Identifiers

Commands accepting `--to-block` support the following formats:

| Format | Example | Description |
|--------|---------|-------------|
| `latest` | `latest` | Latest block |
| `latest:-N` | `latest:-64` | N blocks before latest (default) |
| `safe:+N` | `safe:128` | N blocks after safe block |
| Number | `18900000` | Specific block number |

## Configuration

### Environment Variables

| Variable | Values | Description |
|----------|--------|-------------|
| `DEGENBOT_DEBUG` | `1`, `true`, `yes` | Enable debug-level logging output |
| `DEGENBOT_DEBUG_FUNCTION_CALLS` | `1`, `true`, `yes` | Enable function call trace logging |
| `ALCHEMY_API_KEY` | Alchemy key | Default key for generated HTTP RPC, WSS, and supported Bundler/Gas Manager endpoints |
| `WEB3_ALCHEMY_API_KEY` | Alchemy key | Ape-compatible fallback when `ALCHEMY_API_KEY` is unset |
| `ALCHEMY_CHAIN_<chain_id>_NETWORK` | Alchemy network identifier | Override/add the Alchemy network slug for a chain, e.g. `ALCHEMY_CHAIN_42161_NETWORK=arb-mainnet` |
| `ALCHEMY_NETWORK_<chain_id>` | Alchemy network identifier | Legacy-compatible override for the same network slug |
| `ALCHEMY_CHAIN_<chain_id>_ACCOUNT_ABSTRACTION` | `1`, `true`, `yes`, `on` | Enable Bundler/Gas Manager endpoint construction for a newly supported chain after confirming Alchemy AA support |

```bash
DEGENBOT_DEBUG=1 python my_script.py
```

If a chain is missing from the `[rpc]` table, degenbot falls back to Alchemy using
`ALCHEMY_API_KEY` or `WEB3_ALCHEMY_API_KEY`. The same resolved key and network identifier are used
for HTTP RPC, WebSocket RPC, Bundler API, and Gas Manager API endpoints through
`degenbot.provider.alchemy.alchemy_endpoint_bundle(chain_id)`. Check
`degenbot.provider.alchemy.alchemy_account_abstraction_supported(chain_id)` before routing Bundler
or Gas Manager calls; direct Bundler/Gas Manager endpoint construction is fail-closed for node-only
chains, and endpoint bundles expose `None` for unsupported AA endpoint fields. For newly supported
Alchemy AA chains, set
`ALCHEMY_CHAIN_<chain_id>_ACCOUNT_ABSTRACTION=true` after confirming support.
Use `degenbot.cli.utils.get_rpc_endpoint_from_config(chain_id=..., service=...)` when CLI code needs
the same fallback behavior for HTTP, WSS, Bundler, or Gas Manager endpoints.

### Configuration File

Degenbot uses a TOML configuration file located at `~/.config/degenbot/config.toml`:

```toml
[rpc]
# Chain ID to RPC endpoint mapping
1 = "https://eth-mainnet.example.com"
8453 = "https://base-mainnet.example.com"
42161 = "https://arb-mainnet.example.com"

[database]
# SQLite database path (optional, defaults to platform-specific location)
path = "/path/to/degenbot.db"
```

## Rust Extension

Degenbot includes a high-performance Rust extension module (`degenbot_rs`) that provides optimized implementations of performance-critical operations. The extension is built automatically during installation using [maturin](https://www.maturin.rs/).

### Key Dependencies

| Crate | Purpose |
|-------|--------|
| [alloy](https://github.com/alloy-rs/alloy) | Ethereum primitives (Address, U256, B256), RPC types, keccak256 |
| [pyo3](https://pyo3.rs) | Python bindings with `abi3-py312` for Python 3.12+ support |
| [tokio](https://tokio.rs) | Multi-threaded async runtime for concurrent RPC calls |
| [parking_lot](https://github.com/Amanieu/parking_lot) | High-performance RwLock for thread-safe caching |
| [thiserror](https://github.com/dtolnay/thiserror) | Derivative error types |
| [serde](https://serde.rs) | Serialization/deserialization |
| [lru](https://github.com/jaemk/lru) | LRU cache implementation |

### Parent Contract Bindings

For MEV-Arbitrum integration, degenbot keeps generated Alloy/Rust bindings for selected parent
`contracts/` executor, paymaster, flash-loan, callback, settlement, and routing surfaces under
`rust/crates/contract_bindings`.

```sh
just gen-contract-bindings
just check-contract-bindings
```

The generator builds the parent Foundry `src` tree into temporary artifacts, pins generated bindings
to Alloy `2.0.5`, and excludes tests, scripts, fuzz corpus files, and unrelated contract artifacts.
The Rust extension exposes the checked-in crate through `degenbot_rs::contract_bindings` and keeps
selector parity tests against the hand-maintained hot-path mirrors in `degenbot_rs::types`.
Stylus consumes the generated crate only from `native-test` parity tests; deployable WASM crates do
not depend on the host-side Alloy binding graph.

### Available Functions

#### Tick Math

Uniswap V3 tick-to-price conversions:

```python
from degenbot import get_sqrt_ratio_at_tick, get_tick_at_sqrt_ratio

# Convert tick to sqrt price (X96 format)
sqrt_price = get_sqrt_ratio_at_tick(253320)  # Returns: 56736275128821120...

# Convert sqrt price back to tick
tick = get_tick_at_sqrt_ratio(56736275128821120)  # Returns: 253320
```

#### ABI Decoding

High-performance ABI decoding for contract data:

```python
from degenbot import decode, decode_single

# Decode multiple values
types = ["address", "uint256", "uint256"]
data = bytes.fromhex("...")
values = decode(types, data)  # Returns list of decoded values

# Decode a single value
address = decode_single("address", bytes.fromhex("..."))
```

#### Address Utilities

EIP-55 checksummed address conversion:

```python
from degenbot import to_checksum_address

checksummed = to_checksum_address("0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef")
# Returns: "0xDeaDbeefdEAdbeefdEadbEEFdeadbeEFdEaDbeeF"
```

#### ABI Encoding & Selectors

Encode function calls and compute selectors:

```python
from degenbot import encode_function_call, get_function_selector, decode_return_data

# Get a 4-byte function selector
selector = get_function_selector("transfer(address,uint256)")
# Returns: "0xa9059cbb"

# Encode a function call (selector + encoded args)
calldata = encode_function_call("transfer(address,uint256)", ["0x...", "100"])

# Decode return data from a contract call
values = decode_return_data(bytes.fromhex("..."), ["uint256", "address"])
```

### Provider Classes

The extension includes synchronous and async Ethereum RPC providers:

```python
from degenbot.degenbot_rs import AlloyProvider, Contract

# Create provider with connection pooling
provider = AlloyProvider(
    rpc_url="https://eth-mainnet.example.com",
    max_connections=10,
    timeout=30.0,
    max_retries=10,
    max_blocks_per_request=5000,
)

# Query blockchain
block_number = provider.get_block_number()
chain_id = provider.get_chain_id()
logs = provider.get_logs(from_block=1000000, to_block=1000100, addresses=["0x..."])

# Contract interaction
contract = Contract("0x...", provider_url="https://...")
result = contract.call("balanceOf(address)", ["0x..."])

provider.close()
```

#### Async Provider

The extension also includes async wrappers for use with `asyncio`:

```python
from degenbot.degenbot_rs import AsyncAlloyProvider, AsyncContract

# Create an async provider
async_provider = await AsyncAlloyProvider.create(
    rpc_url="https://eth-mainnet.example.com",
    max_connections=10,
    timeout=30.0,
)

# Async contract interaction
async_contract = AsyncContract("0x...", provider_url="https://...")
result = await async_contract.call("balanceOf(address)", ["0x..."])

# Batch multiple contract calls
results = await async_contract.batch_call(
    [("balanceOf(address)", ["0x..."]), ("totalSupply()", [])],
)
```

#### Log Filtering

```python
from degenbot.degenbot_rs import LogFilter

# Build a log filter
log_filter = LogFilter(
    from_block=1000000,
    to_block=1000100,
    addresses=["0x..."],
    topics=[["0x..."]],
)
```

### Performance Benefits

| Operation | Pure Python | Rust Extension |
|-----------|-------------|----------------|
| Tick math | ~50μs | ~0.1μs |
| ABI decode (10 values) | ~200μs | ~5μs |
| Address checksum | ~10μs | ~0.5μs |
| Log query (1000 logs) | ~100ms | ~20ms |

### Build Requirements

The extension is pre-built in published packages. For source builds:

- Rust 1.70+ (stable toolchain)
- maturin (installed automatically with `uv sync`)

```bash
# Build the extension
env -u RUST_LOG uv run --no-project maturin build --release --manifest-path rust/Cargo.toml

# Or use the justfile
just dev  # Build and install Python extension
```

## Documentation

Additional documentation is available in the [`docs/`](docs/) directory:

- **[Aave V3](docs/aave/)**: Comprehensive control flow diagrams and amount transformations for Aave operations
- **[Arbitrage](docs/arbitrage/)**: Multi-pool cycle testing documentation
- **[CLI](docs/cli/)**: Detailed CLI command reference
- **[Configuration](docs/config.md)**: Configuration options

## MEV-Arbitrum Overlay

This checkout is the vendored degenbot used by the parent
[`mev-arbitrum`](../../README.md) project. The package is a strict superset of upstream
`BowTiedDevil/degenbot@0.6.0a2`: every upstream feature is preserved, and the following
surfaces are added here only. They are not published to PyPI and are not part of the
upstream public API.

Read [`docs/architecture/mev-arbitrum-code-home.md`](../../docs/architecture/mev-arbitrum-code-home.md)
for the boundary doctrine between this package, `coordinator/`, and `contracts/`.

### Execution CLI group

Encodes calldata for the parent-repo `Executor.sol` entry points. See the
[Execution Calldata](#execution-calldata-mev-arbitrum-overlay) block under CLI Reference for
the invocation form.

| Command | Encodes | Source |
| --- | --- | --- |
| `degenbot execution native-arb` | `Executor.executeNativeArb(...)` | `src/degenbot/cli/execution.py` |
| `degenbot execution match-internal` | `Executor.matchInternal(...)` | `src/degenbot/cli/execution.py` |
| `degenbot execution compose-four-leg` | `Executor.composeFourLeg(...)` | `src/degenbot/cli/execution.py` |

All three commands delegate to Rust encoders in `rust/src/execution_py.rs` via
`degenbot.execution` (Python convenience wrappers) and emit `0x`-prefixed hex on stdout.
The CLI does not sign or broadcast.

### Rust extension overlay modules

In addition to the upstream `tick_math_py` / `abi_decoder` / `abi_encoder` / `address_utils` /
`provider_py` / `contract_py` surface registered in `rust/src/lib.rs`, the maturin binding
exposes four overlay submodules:

| Submodule | Public functions | Purpose |
| --- | --- | --- |
| `execution_py` | `encode_native_arb_calldata`, `encode_match_internal_calldata`, `encode_compose_four_leg_calldata`, `v2_mid_price_x96`, `v3_mid_price_x96`, `apply_gap_to_price_x96`, `synthetic_victim_amount_in`, `optimal_v2_frontrun_amount`, `v2_sandwich_max_size`, `v2_optimal_sandwich_size`, `v3_sandwich_max_size`, `v3_optimal_sandwich_size`, `optimal_input_2pool`, `optimal_input_2pool_v3`, `optimal_input_2pool_curve` | Executor calldata + closed-form sandwich/two-pool math |
| `execution_engine_py` | `evaluate_sandoo_idea_json`, `find_best_match_json`, `compose_engine_job_json` | Strategy-candidate evaluation and engine-job composition |
| `signed_order_admission_py` | `evaluate_prediction_fx_match_json` | Pre-admission scoring for signed prediction/FX orders |
| `simulation_py` | `RevmDb` class (`call`, seeded pool warmup) | REVM-backed deterministic local simulation |

Python wrappers live in `src/degenbot/execution.py` and `src/degenbot/simulation.py`. Type
stubs are in `src/degenbot/degenbot_rs.pyi`.

### Execution adapters (`src/degenbot/execution_adapters/`)

Per-venue Python adapters that normalize state, encode swap/flash legs, and surface
deployment addresses. Re-exported lazily through `degenbot.execution_adapters`.

| Adapter | Coverage |
| --- | --- |
| `aave_v3_flashloan_adapter` | Aave V3 `flashLoan` builder + request type |
| `aave_v4_adapter` | Aave V4 reserves, user health, swap quote |
| `balancer_v3_adapter` + `balancer_v3_weighted_math` / `balancer_log_exp_math` / `balancer_fixed_point` | Balancer V3 client + pool math |
| `camelot_v3_adapter` | Camelot Algebra V3 pool state, `MultiTickCrossingNotSupportedError` |
| `curve_ng_adapter` | Curve StableSwap-NG pool state |
| `dodo_pmm_adapter` + `dodo_pmm_math` / `dodo_v1_math` | DODO PMM pool state and math |
| `fluid_dex_adapter` | Fluid DEX client + pool state |
| `maverick_v2_adapter` | Maverick V2 client + pool state |
| `metamorpho_v1_adapter` | MetaMorpho V1 vault client |
| `morpho_flashloan_adapter` | Morpho Blue `flashLoan` builder + request type |
| `morpho_lp_adapter` | Morpho Blue market + position helpers |
| `morpho_preliquidation_adapter` | Morpho pre-liquidation helpers |
| `solidly_adapter` | Solidly V1 pool state |
| `aggregator_validator` | Whitelisted aggregator router validation |

Address constants for the above live in sibling `*_addresses.py` modules
(`aave_v3_addresses`, `arbitrum_token_addresses`, `balancer_v3_addresses`,
`compound_v3_addresses`, `cow_addresses`, `dodo_addresses`, `fluid_dex_addresses`,
`maverick_v2_addresses`, `morpho_blue_addresses`, `uniswap_addresses`).

### Adapter registry (`src/degenbot/adapters/`)

Python-side venue/lane registry that mirrors `coordinator/src/router/registry.ts`. Read-only
view of "what we can execute through" and "is it ready":

- `adapters.registry` — `ALL_ADAPTERS`, `adapter_for`, `adapters_by_category`,
  `adapters_by_status`, `lane_for`, `lanes_by_status`
- `adapters.laneadapters.lanes` — `EXECUTION_LANES` enumeration
- `adapters.flashadapters.venues`, `adapters.liquidityadapters.venues`,
  `adapters.swapadapters.venues` — per-category venue catalogues
- `adapters.readiness` — `READINESS_EVIDENCE`, `ReadinessStatus`, `evidence_for_adapter`,
  `evidence_for_lane`, `readiness_evidence_for_id`
- `adapters.ipc`, `adapters.source`, `adapters.config`, `adapters.templates` — IPC
  contract, source provenance, config, and adapter scaffolding helpers

### CoW auction bridge (`src/degenbot/cow/auction_build.py` + `auction_build.py` shim)

`degenbot.auction_build` re-exports the CoW auction-build bridge used by the parent-repo
solver driver: `AuctionBuildRequest`, `AuctionBuildResponse`, `AuctionOrderRef`,
`AuctionQuotePolicy`, `AuctionRef`, `build_auction_response`,
`handle_auction_build_payload`.

### Bot scanner (`src/degenbot/bot.py`)

Backs the `degenbot bot best` CLI. Public types: `BotOpportunity`, `BotScanConfig`,
`DegenbotBot`.

### Database models added beyond upstream

`src/degenbot/database/models/pools.py` adds:

- `CamelotV3PoolTable` (Algebra V3, Arbitrum) — populated by the pool updater; the
  activator surface is still gated (see CLI Reference note on Camelot Algebra)
- Balancer stable / composable-stable model surface (`balancer/stable_pools.py`,
  `balancer/composable_stable_pools.py`) on top of the upstream V2 weighted-pool model

### Arbitrum chain support

Arbitrum is wired across the existing upstream protocol surface:

- Uniswap V2 / V3 / V4 deployments (`src/degenbot/uniswap/deployments.py` —
  `ArbitrumUniswapV2`, `ArbitrumUniswapV3`, `ArbitrumUniswapV4`, `ArbitrumCamelotV3`)
- Curve StableSwap-NG factory + pool model on Arbitrum
- Address constants in `execution_adapters/arbitrum_token_addresses.py` and
  `arbitrum_token_metadata.py`

### Verification

- Python: `just test-python` (covers the overlay surface)
- Rust: `just test-rust` (covers `execution_py`, `execution_engine_py`,
  `signed_order_admission_py`, `simulation_py`)
- Combined: `just test-all`

## Contributing

Contributions are welcome! Please submit issues and pull requests to the [GitHub repository](https://github.com/BowTiedDevil/degenbot).

### Development Setup

```bash
git clone https://github.com/BowTiedDevil/degenbot.git
cd degenbot
uv sync

# Run deterministic tests
just test-python

# Run external-gated tests when prerequisites are configured
just test-python-live
just test-python-database

# Run linting
env -u RUST_LOG uv run ruff check
env -u RUST_LOG uv run mypy
```

## License

This code is published under a permissive MIT license. See [LICENSE](LICENSE) for details.

## Donation

If you find this code valuable, please fund continuing development by donating to [`0xADAf500b965545C8A766CD9Cdeb3BF3FBef073e5`](https://etherscan.io/address/0xadaf500b965545c8a766cd9cdeb3bf3fbef073e5) on any EVM compatible chain.
