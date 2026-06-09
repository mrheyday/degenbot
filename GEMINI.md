# GEMINI.md for Degenbot

This document provides an overview of the Degenbot project, its setup, and development guidelines, serving as instructional context for future interactions.

## Project Overview

Degenbot is a Python library designed to accelerate the development of integrations with various DeFi protocols (Uniswap V2, V3, V4; Curve StableSwap V1 and NG; Solidly V2; Balancer V2; Aave V3) on EVM-compatible blockchains. It abstracts complex liquidity pool and ERC-20 token interactions, leveraging `web3.py` for blockchain communication and a high-performance Rust extension (`degenbot_rs`) for critical operations.

The project originated as building blocks for Degen Code lessons and has been extended with an MEV-Arbitrum execution overlay, Rust solver acceleration for arbitrage, and offline simulation capabilities.

**Key Features:**
*   **DEX Integrations:** Support for multiple Uniswap versions, Aerodrome, PancakeSwap, SushiSwap, Curve, Solidly, Balancer, and Camelot.
*   **Lending Protocols:** Aave V3 integration for supply, borrow, liquidation, E-Mode, and GHO.
*   **Infrastructure:** Chainlink Price Feeds, Anvil Forking for local testing, and offline provider for deterministic simulations.
*   **Arbitrage Optimization:** Rust-accelerated solvers for V2/V3 path optimization and other AMM coverages.
*   **Rust Extension:** Optimized implementations for performance-critical operations like tick math, ABI decoding/encoding, and address utilities.

## Installation

### Requirements

*   Python 3.12+
*   `pip` or `uv` package manager
*   Rust 1.70+ (for source builds of the Rust extension)

### From PyPI

```bash
pip install degenbot
```

### From Source

```bash
git clone https://github.com/mrheyday/degenbot.git
cd degenbot
uv sync  # or: pip install -e .
```

## Usage

Degenbot provides both a Python API and a Command-Line Interface (CLI).

### Python Quick Start

```python
import web3
import degenbot

# Connect to an Ethereum RPC endpoint
w3 = web3.Web3(web3.HTTPProvider("https://eth-mainnet.example.com"))
assert w3.is_connected()

# Create a Uniswap V3 pool helper
pool = degenbot.UniswapV3Pool("0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8")

print(f"Pool: {pool.name}")
print(f"Token 0: {pool.token0.symbol}")
print(f"Token 1: {pool.token1.symbol}")

# Calculate swap outputs
amount_out = pool.calculate_tokens_out_from_tokens_in(
    token_in=pool.token0,
    token_in_quantity=10**18,  # 1 token (18 decimals)
)
print(f"Output: {amount_out}")
```

### CLI Reference

The CLI is installed automatically with the package (`degenbot --help`).

**Common Commands:**

*   **Bot Scanning:**
    ```bash
    degenbot bot best 
      --chain-id 1 
      --input-token 0x0000000000000000000000000000000000000000 
      --from-address 0x000000000000000000000000000000000000dEaD
    ```
*   **Execution Calldata (MEV-Arbitrum Overlay):**
    ```bash
    degenbot execution native-arb 
      --flash-lender 0x... --flash-protocol AaveV3 
      --flash-token 0x... --flash-amount 1000000 
      --swaps-json '[{"kind":"UniswapV3", ...}]' 
      --min-profit 0 --deadline 0
    ```
*   **Database Management:**
    ```bash
    degenbot database backup
    degenbot database reset
    degenbot database upgrade
    ```
*   **Pool State Management:**
    ```bash
    degenbot pool update
    degenbot exchange activate arbitrum_uniswap_v4
    ```
*   **Aave State Management:**
    ```bash
    degenbot aave update
    degenbot aave position show <ADDRESS>
    ```

## Development Conventions

### Testing

The project uses `just` commands for running tests:

*   `just test-python`: Run deterministic Python tests.
*   `just test-python-live`: Run external-gated tests (requires prerequisites).
*   `just test-python-database`: Run database-related tests.
*   `just test-rust`: Run Rust extension tests.
*   `just test-all`: Run all tests.

### Linting & Type Checking

*   `env -u RUST_LOG uv run ruff check`: Run `ruff` for linting.
*   `env -u RUST_LOG uv run mypy`: Run `mypy` for type checking.

### `justfile`

The `justfile` at the project root contains various development automation scripts. Developers should refer to it for common tasks like building, testing, and linting.

### Configuration

*   **Environment Variables:** Configure behavior using environment variables like `DEGENBOT_DEBUG`, `ALCHEMY_API_KEY`, etc. (refer to `README.md` for full list).
*   **Configuration File:** Degenbot uses a TOML configuration file at `~/.config/degenbot/config.toml` for RPC endpoints and database paths.

## Further Documentation

More detailed documentation can be found in the `docs/` directory, including:

*   [Aave V3](docs/aave/)
*   [Arbitrage](docs/arbitrage/)
*   [Arbitrage Optimizer](plans/arbitrage-optimizer/README.md)
*   [CLI](docs/cli/)
*   [Configuration](docs/config.md)
*   [MEV-Arbitrum Code Home](../../docs/architecture/mev-arbitrum-code-home.md) (for understanding the overlay architecture)
