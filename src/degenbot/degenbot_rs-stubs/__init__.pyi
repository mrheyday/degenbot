"""
Type stubs for the degenbot Rust extension module (_rs).

This module provides high-performance implementations of common operations
used by the degenbot Python package.
"""

from collections.abc import Coroutine
from typing import Any, Literal, overload

from hexbytes import HexBytes

def evaluate_prediction_fx_match_json(input_json: str) -> str:
    """
    Evaluate a Prediction-FX style signed-order match as JSON.

    Args:
        input_json: JSON object encoded as a string. Numeric fields should be
            decimal strings for full integer precision.

    Returns:
        JSON string containing deterministic admission, accounting, and
        violation fields.
    """

def get_sqrt_ratio_at_tick(tick: int) -> int:
    """
    Convert a tick value to its corresponding sqrt price (X96 format).

    Args:
        tick: The tick value in range [-887272, 887272]

    Returns:
        A Python int representing the sqrt price X96 value

    Raises:
        ValueError: If the tick value is invalid (out of range)
    """

@overload
def get_tick_at_sqrt_ratio(sqrt_price_x96: int) -> int: ...
@overload
def get_tick_at_sqrt_ratio(sqrt_price_x96: bytes) -> int: ...
@overload
def to_checksum_address(address: str) -> str: ...
@overload
def to_checksum_address(address: bytes) -> str: ...
def decode(
    types: list[str],
    data: bytes,
    strict: bool = True,
    checksum: bool = True,
) -> list[Any]:
    """
    Decode ABI-encoded data for multiple types.

    Args:
        types: List of ABI type strings
        data: Raw ABI-encoded bytes
        strict: If True (default), performs strict validation
        checksum: If True (default), returns checksummed addresses

    Returns:
        A list of decoded Python values

    Raises:
        ValueError: If data is invalid or insufficient
        NotImplementedError: If strict=False or for unsupported types
    """

@overload
def decode_single(
    abi_type: Literal["address"],
    data: bytes,
    strict: bool = True,
    checksum: bool = True,
) -> str: ...
@overload
def decode_single(
    abi_type: Literal["bool"],
    data: bytes,
    strict: bool = True,
    checksum: bool = True,
) -> bool: ...
@overload
def decode_single(
    abi_type: Literal["string"],
    data: bytes,
    strict: bool = True,
    checksum: bool = True,
) -> str: ...
@overload
def decode_single(
    abi_type: Literal[
        "uint8",
        "uint16",
        "uint32",
        "uint64",
        "uint128",
        "uint256",
    ],
    data: bytes,
    strict: bool = True,
    checksum: bool = True,
) -> int: ...
@overload
def decode_single(
    abi_type: Literal[
        "int8",
        "int16",
        "int32",
        "int64",
        "int128",
        "int256",
    ],
    data: bytes,
    strict: bool = True,
    checksum: bool = True,
) -> int: ...
@overload
def decode_single(
    abi_type: Literal["bytes"],
    data: bytes,
    strict: bool = True,
    checksum: bool = True,
) -> bytes: ...
@overload
def decode_single(
    abi_type: Literal[
        "bytes1",
        "bytes2",
        "bytes3",
        "bytes4",
        "bytes5",
        "bytes6",
        "bytes7",
        "bytes8",
        "bytes9",
        "bytes10",
        "bytes11",
        "bytes12",
        "bytes13",
        "bytes14",
        "bytes15",
        "bytes16",
        "bytes17",
        "bytes18",
        "bytes19",
        "bytes20",
        "bytes21",
        "bytes22",
        "bytes23",
        "bytes24",
        "bytes25",
        "bytes26",
        "bytes27",
        "bytes28",
        "bytes29",
        "bytes30",
        "bytes31",
        "bytes32",
    ],
    data: bytes,
    strict: bool = True,
    checksum: bool = True,
) -> bytes: ...
@overload
def decode_single(
    abi_type: str,
    data: bytes,
    strict: bool = True,
    checksum: bool = True,
) -> str | bool | int | bytes:
    """
    Decode a single ABI value.

    Args:
        abi_type: ABI type string
        data: Raw ABI-encoded bytes
        strict: If True (default), performs strict validation
        checksum: If True (default), returns checksummed addresses

    Returns:
        The decoded Python value

    Raises:
        ValueError: If data is invalid or insufficient
        NotImplementedError: If strict=False or for unsupported types
    """

def encode_function_call(function_signature: str, args: list[str]) -> bytes:
    """
    Encode function arguments into calldata.

    Args:
        function_signature: Function signature like "transfer(address,uint256)"
        args: List of arguments as strings

    Returns:
        Encoded calldata as bytes (selector + encoded args)

    Raises:
        ValueError: If the signature or arguments are invalid
    """

def decode_return_data(data: bytes, output_types: list[str]) -> list[str]:
    """
    Decode return data from a contract call.

    Args:
        data: Return data as bytes
        output_types: List of output type strings like ["uint256", "address"]

    Returns:
        List of decoded values as strings

    Raises:
        ValueError: If data is invalid or cannot be decoded
    """

def get_function_selector(function_signature: str) -> str:
    """
    Parse a function signature and return its selector.

    Args:
        function_signature: Function signature like "transfer(address,uint256)"

    Returns:
        4-byte function selector as hex string (e.g., "0xa9059cbb")

    Raises:
        ValueError: If the function signature is invalid
    """

def encode_native_arb_calldata(
    flash_lender: str,
    flash_protocol: str,
    flash_token: str,
    flash_amount: int | bytes,
    swaps: list[dict[str, Any]],
    min_profit: int | bytes,
    deadline: int | bytes,
) -> bytes:
    """
    Encode calldata for `Executor.executeNativeArb`.

    Args:
        flash_lender: Flash-loan lender address
        flash_protocol: Flash protocol selector name
        flash_token: Flash-loan token address
        flash_amount: Flash-loan amount
        swaps: Ordered swap steps as dictionaries
        min_profit: Minimum profit threshold
        deadline: Unix deadline
    """

def encode_match_internal_calldata(
    cow_settlement_calldata: bytes,
    uniswapx_batch_calldata: bytes,
    expected_token_inflows: list[str],
    expected_token_inflow_min: list[int | bytes],
    flash_lender: str,
    flash_protocol: str,
    flash_token: str,
    flash_amount: int | bytes,
    min_profit: int | bytes,
    deadline: int | bytes,
) -> bytes:
    """
    Encode calldata for `Executor.matchInternal`.
    """

def encode_compose_four_leg_calldata(
    across_fill_calldata: bytes,
    arb_swaps: list[dict[str, Any]],
    cow_fill_calldata: bytes,
    uniswapx_rebalance_calldata: bytes,
    flash_lender: str,
    flash_protocol: str,
    flash_token: str,
    flash_amount: int | bytes,
    min_profit: int | bytes,
    deadline: int | bytes,
) -> bytes:
    """
    Encode calldata for `Executor.composeFourLeg`.
    """

def v2_mid_price_x96(reserve_in: int | bytes | str, reserve_out: int | bytes | str) -> str: ...
def v3_mid_price_x96(sqrt_price_x96: int | bytes | str) -> str: ...
def apply_gap_to_price_x96(price_x96: int | bytes | str, gap_bps: int) -> str: ...
def synthetic_victim_amount_in(gap_bps: int, reserve_in: int | bytes | str) -> str: ...
def optimal_v2_frontrun_amount(
    victim_amount_in: int | bytes | str,
    victim_min_out: int | bytes | str,
    reserve_in: int | bytes | str,
    reserve_out: int | bytes | str,
    fee_bps: int,
    margin_bps: int,
) -> str: ...
def v2_sandwich_max_size(
    victim_amount_in: int | bytes | str,
    victim_min_out: int | bytes | str,
    reserve_in: int | bytes | str,
    reserve_out: int | bytes | str,
    fee_bps: int,
) -> str: ...
def v2_optimal_sandwich_size(
    victim_amount_in: int | bytes | str,
    reserve_in: int | bytes | str,
    reserve_out: int | bytes | str,
    fee_bps: int,
    a_max: int | bytes | str,
) -> str: ...
def v3_sandwich_max_size(
    pool_json: str,
    victim_amount_in: int | bytes | str,
    victim_min_out: int | bytes | str,
    zero_for_one: bool,
) -> str: ...
def v3_optimal_sandwich_size(
    pool_json: str,
    victim_amount_in: int | bytes | str,
    zero_for_one: bool,
    a_max: int | bytes | str,
) -> str: ...
def optimal_input_2pool(
    r_a1: int | bytes | str,
    r_b1: int | bytes | str,
    fee_bps1: int,
    r_b2: int | bytes | str,
    r_a2: int | bytes | str,
    fee_bps2: int,
) -> str:
    """
    Calculate the optimal input amount for a two-pool Uniswap V2 arbitrage cycle.
    """

def optimal_input_2pool_v3(
    pool1_v3_json: str,
    pool1_zero_for_one: bool,
    pool2_v3_json: str | None,
    pool2_v2_data: tuple[str, str, int] | None,
) -> str:
    """
    Calculate the optimal input amount for a two-pool cycle with a V3 first pool.
    """

def optimal_input_2pool_curve(
    pool_curve_json: str,
    i: int,
    j: int,
    pool2_v2_data: tuple[str, str, int] | None,
) -> str:
    """
    Calculate the optimal input amount for a Curve-to-V2 two-pool cycle.
    """

def compose_engine_job_json(
    plan_json: str,
    policy_json: str,
    sources_json: str,
    gates_json: str,
    simulation_json: str,
    now_ms: int,
) -> str:
    """
    Compose and validate a deterministic Rust/Alloy execution-engine job.

    Returns a JSON report containing the plan hash and broadcast decision.
    Raises ValueError if policy, gate, or simulation admission fails.
    """

def evaluate_sandoo_idea_json(
    opp_json: str,
    best_quote_json: str | None,
    max_gas_price_gwei: int,
    flash_loan_fee_wei_str: str,
) -> str: ...
def find_best_match_json(outbound_json: str, counters_json: str) -> str | None: ...

class RevmDb:
    def __init__(self, arb_rpc_http: str, seed_pools: list[str] | None = None) -> None: ...
    def call(self, from_addr: str, to_addr: str, calldata: bytes, value: int = 0) -> bytes: ...

class Contract:
    """
    Synchronous wrapper for smart contract interactions.
    """

    def __init__(self, address: str, provider_url: str | None = None) -> None: ...
    @property
    def address(self) -> str: ...
    def call(
        self,
        function_signature: str,
        args: list[str],
        block_number: int | None = None,
    ) -> list[Any]:
        """
        Execute a contract call.

        Args:
            function_signature: Function signature like "balanceOf(address)"
            args: List of arguments as strings
            block_number: Optional block number to query

        Returns:
            List of decoded return values
        """

class LogFilter:
    """
    Filter for log queries.
    """

    def __init__(
        self,
        from_block: int,
        to_block: int,
        addresses: list[str] | None = None,
        topics: list[list[str]] | None = None,
    ) -> None: ...
    @property
    def from_block(self) -> int | None: ...
    @property
    def to_block(self) -> int | None: ...
    @property
    def addresses(self) -> list[str]: ...
    @property
    def topics(self) -> list[list[str]]: ...

class AlloyProvider:
    """
    Synchronous Ethereum RPC provider.

    Automatically detects connection type from URL:
    - HTTP/HTTPS URLs use HTTP transport with connection pooling
    - File paths (Unix: /path, Windows: \\\\.\\pipe\\...) use IPC transport
    """

    def __init__(
        self,
        rpc_url: str,
        max_retries: int = 10,
        max_blocks_per_request: int = 5000,
        network: str = "any",
    ) -> None: ...
    @property
    def rpc_url(self) -> str: ...
    @property
    def network(self) -> str: ...
    def get_block_number(self) -> int: ...
    def get_chain_id(self) -> int: ...
    def get_gas_price(self) -> str: ...
    def get_block(self, block_number: int) -> dict[str, Any] | None: ...
    def get_transaction(self, tx_hash: str) -> dict[str, Any] | None: ...
    def get_transaction_receipt(self, tx_hash: str) -> dict[str, Any] | None: ...
    def get_logs(
        self,
        *,
        from_block: int,
        to_block: int,
        addresses: list[str] | None = None,
        topics: list[list[str]] | None = None,
    ) -> list[dict[str, Any]]: ...
    def call(
        self,
        to: str,
        data: bytes,
        block_number: int | None = None,
    ) -> HexBytes: ...
    def get_code(
        self,
        address: str,
        block_number: int | None = None,
    ) -> HexBytes: ...
    def get_storage_at(
        self,
        address: str,
        position: int | bytes,
        block_number: int | None = None,
    ) -> HexBytes: ...
    def get_balance(
        self,
        address: str,
        block_number: int | None = None,
    ) -> int: ...
    def get_transaction_count(
        self,
        address: str,
        block_number: int | None = None,
    ) -> int: ...
    def estimate_gas(
        self,
        to: str,
        data: bytes,
        from_: str | None = None,
        value: int | None = None,
        block_number: int | None = None,
    ) -> int: ...
    def close(self) -> None: ...

class AsyncAlloyProvider:
    """
    Async wrapper for AlloyProvider operations.
    """

    def __init__(self, sync_provider: AlloyProvider) -> None: ...
    @staticmethod
    def create(
        rpc_url: str,
        max_retries: int = 10,
        max_blocks_per_request: int = 5000,
        network: str = "any",
    ) -> Coroutine[Any, Any, AsyncAlloyProvider]: ...
    def get_block_number(self) -> Coroutine[Any, Any, int]: ...
    def get_chain_id(self) -> Coroutine[Any, Any, int]: ...
    def get_logs(
        self,
        from_block: int,
        to_block: int,
        addresses: list[str] | None = None,
        topics: list[list[str]] | None = None,
    ) -> Coroutine[Any, Any, list[dict[str, Any]]]: ...
    def get_block(self, block_number: int) -> Coroutine[Any, Any, dict[str, Any] | None]: ...
    def call(
        self,
        to: str,
        data: bytes,
        block_number: int | None = None,
    ) -> Coroutine[Any, Any, HexBytes]: ...
    def get_code(
        self,
        address: str,
        block_number: int | None = None,
    ) -> Coroutine[Any, Any, HexBytes]: ...
    def get_balance(
        self,
        address: str,
        block_number: int | None = None,
    ) -> Coroutine[Any, Any, int]: ...
    def get_transaction_count(
        self,
        address: str,
        block_number: int | None = None,
    ) -> Coroutine[Any, Any, int]: ...
    def get_gas_price(self) -> Coroutine[Any, Any, str]: ...
    def estimate_gas(
        self,
        to: str,
        data: bytes,
        from_: str | None = None,
        value: int | None = None,
        block_number: int | None = None,
    ) -> Coroutine[Any, Any, int]: ...
    def get_transaction(self, tx_hash: str) -> Coroutine[Any, Any, dict[str, Any] | None]: ...
    def get_transaction_receipt(
        self, tx_hash: str
    ) -> Coroutine[Any, Any, dict[str, Any] | None]: ...
    def get_storage_at(
        self,
        address: str,
        position: int | bytes,
        block_number: int | None = None,
    ) -> Coroutine[Any, Any, HexBytes]: ...

class AsyncContract:
    """
    Async wrapper for contract interactions.
    """

    def __init__(self, address: str, provider_url: str) -> None: ...
    @staticmethod
    def create(
        address: str,
        provider_url: str,
        max_retries: int | None = None,
    ) -> Coroutine[Any, Any, AsyncContract]: ...
    @property
    def address(self) -> str: ...
    def call(
        self,
        function_signature: str,
        args: list[str],
        block_number: int | None = None,
    ) -> Coroutine[Any, Any, list[Any]]: ...
    def batch_call(
        self,
        calls: list[tuple[str, list[str]]],
        block_number: int | None = None,
    ) -> Coroutine[Any, Any, list[list[Any]]]: ...

__all__ = [
    "AlloyProvider",
    "AsyncAlloyProvider",
    "AsyncContract",
    "Contract",
    "HexBytes",
    "LogFilter",
    "compose_engine_job_json",
    "decode",
    "decode_return_data",
    "decode_single",
    "encode_compose_four_leg_calldata",
    "encode_function_call",
    "encode_match_internal_calldata",
    "encode_native_arb_calldata",
    "get_function_selector",
    "get_sqrt_ratio_at_tick",
    "get_tick_at_sqrt_ratio",
    "optimal_input_2pool",
    "optimal_input_2pool_curve",
    "optimal_input_2pool_v3",
    "to_checksum_address",
]
