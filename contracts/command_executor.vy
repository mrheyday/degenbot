"""
Lightweight command executor fixture contract used for autoresearch task wiring.

This implementation is intentionally minimal and keeps the structural entrypoints
that the local AR check scripts expect. It is a placeholder surface for future
productionized executor contracts.
"""

from ethereum.ercs import IERC20

OWNER: immutable(address)
WETH_ADDR: immutable(address)

COMMAND_SEPARATOR: constant(uint8) = 255

# Command IDs
CMD_V2_SWAP: constant(uint8) = 0
CMD_V4_SWAP: constant(uint8) = 1

MAX_INT128: constant(uint256) = 170141183460469231731687303715884105727

# Fixed-argument lengths
V2_POOL_LEN: constant(uint256) = 20
V2_AMOUNT_LEN: constant(uint256) = 32
V2_RECIPIENT_LEN: constant(uint256) = 20
V2_BODY_LEN: constant(uint256) = V2_POOL_LEN + V2_AMOUNT_LEN + V2_AMOUNT_LEN + V2_RECIPIENT_LEN + 1

V4_POOL_LEN: constant(uint256) = 20
V4_AMOUNT_LEN: constant(uint256) = 32
V4_RECIPIENT_LEN: constant(uint256) = 20
V4_BODY_LEN: constant(uint256) = V4_POOL_LEN + 1 + V4_AMOUNT_LEN + V4_RECIPIENT_LEN + 1
V4_CALLBACK_LAYER_LEN: constant(uint256) = 29

SWAP_SELECTOR: constant(bytes4) = 0x128acb08
TRANSFER_SELECTOR: constant(bytes4) = 0xa9059cbb

_locked: uint256
_v4_callback_pool: address

event CommandExecuted:
    command_id: uint8

event V4CallbackLayer:
    current_pool: address
    next_pool: address
    has_next: bool

@deploy

def __init__(weth_addr: address):
    OWNER = msg.sender
    WETH_ADDR = weth_addr


@payable
@external

def __default__():
    # allow zero-calldata fallback only when no ETH is sent.
    if len(msg.data) == 0:
        assert msg.value == 0, "unexpected ETH value"
        self._v4_callback_pool = empty(address)
        return

    assert msg.sender == OWNER, "unauthorized"
    assert msg.value == 0, "unexpected ETH value"
    assert self._locked == 0, "reentrant call"
    self._locked = 1

    cmd: uint8 = self._read_u8(msg.data, 0)
    assert cmd == CMD_V4_SWAP, "unsupported callback entry command"
    assert len(msg.data) >= 1 + V4_BODY_LEN, "invalid v4 entry payload"

    cursor: uint256 = 1
    _pool: address = self._read_address(msg.data, cursor)
    cursor += V4_POOL_LEN
    assert self._read_u8(msg.data, cursor) <= 1, "invalid zero_for_one flag"
    cursor += 1  # zero_for_one
    _amount_out: uint256 = self._read_u256(msg.data, cursor)
    assert _amount_out <= MAX_INT128, "v4 amount exceeds int128"
    cursor += V4_AMOUNT_LEN
    _ = self._read_address(msg.data, cursor)
    cursor += V4_RECIPIENT_LEN
    assert self._read_u8(msg.data, cursor) == COMMAND_SEPARATOR, "invalid separator"

    if len(msg.data) == cursor + 1:
        log V4CallbackLayer(_pool, empty(address), False)
        self._v4_callback_pool = empty(address)
    else:
        assert len(msg.data) - (cursor + 1) == V4_CALLBACK_LAYER_LEN, "invalid v4 callback payload"
        log V4CallbackLayer(_pool, convert(slice(msg.data, cursor + 1, 20), address), True)
        self._v4_callback_pool = _pool

    log CommandExecuted(command_id=cmd)
    self._locked = 0


@external
def execute_commands(encoded_commands: Bytes[4096]) -> bool:
    # Top-level gate + command parser entry.
    assert msg.sender == OWNER, "unauthorized"
    assert msg.value == 0, "unexpected ETH value"
    assert self._locked == 0, "reentrant call"
    self._locked = 1
    self._v4_callback_pool = empty(address)

    cursor: uint256 = 0
    end: uint256 = len(encoded_commands)

    for _ in range(128):
        if cursor >= end:
            break

        cmd: uint8 = self._read_u8(encoded_commands, cursor)
        cursor += 1

        if cmd == CMD_V2_SWAP:
            # [CMD][pool][amount0][amount1][recipient][SEP]
            assert cursor + V2_BODY_LEN <= end, "truncated v2 command"

            # pool
            _ = self._read_address(encoded_commands, cursor)
            cursor += V2_POOL_LEN

            # amount args
            _ = self._read_u256(encoded_commands, cursor)
            cursor += V2_AMOUNT_LEN
            _ = self._read_u256(encoded_commands, cursor)
            cursor += V2_AMOUNT_LEN

            # recipient
            _ = self._read_address(encoded_commands, cursor)
            cursor += V2_RECIPIENT_LEN
        elif cmd == CMD_V4_SWAP:
            # [CMD][pool][zeroForOne][amountOut][recipient][SEP]
            assert cursor + V4_BODY_LEN <= end, "truncated v4 command"
            _ = self._read_address(encoded_commands, cursor)
            cursor += V4_POOL_LEN
            assert self._read_u8(encoded_commands, cursor) <= 1, "invalid zero_for_one flag"
            cursor += 1
            _amount_out: uint256 = self._read_u256(encoded_commands, cursor)
            assert _amount_out <= MAX_INT128, "v4 amount exceeds int128"
            cursor += V4_AMOUNT_LEN
            _ = self._read_address(encoded_commands, cursor)
            cursor += V4_RECIPIENT_LEN
        else:
            assert False, "unknown command"

        sep: uint8 = self._read_u8(encoded_commands, cursor)
        cursor += 1
        assert sep == COMMAND_SEPARATOR, "invalid separator"

        log CommandExecuted(command_id=cmd)

    self._locked = 0
    return True


@external
def uniswapV2Call(sender: address, _amount0Out: uint256, _amount1Out: uint256, data: Bytes[65]):
    # flash-borrow callback path for V2 variants
    del data
    log IERC20.Transfer(sender, msg.sender, 0)
    if _amount0Out + _amount1Out > 0:
        raw_call(
            WETH_ADDR,
            concat(
                TRANSFER_SELECTOR,
                convert(sender, bytes32),
                convert(_amount0Out, bytes32),
            ),
            max_outsize=0,
        )


@external
def uniswapV3SwapCallback(
    amount0Delta: int256, amount1Delta: int256, data: Bytes[58]
):
    # nested callback path for V3 variants
    del amount0Delta, amount1Delta
    if len(data) == 0:
        return
    else:
        # raw_call recursion-like step uses explicit V3 swap selector path:
        # swap(address,bool,int256,uint160,bytes)
        _next_pool: address = convert(slice(data, 0, 20), address)
        raw_call(_next_pool, concat(SWAP_SELECTOR, convert(msg.sender, bytes32), convert(False, bytes32), convert(-1, bytes32), convert(0, bytes32), convert(160, bytes32), convert(len(data), bytes32), slice(data, 29, 29)), max_outsize=0)


@external
def uniswapV4SwapCallback(
    amount0Delta: int256, amount1Delta: int256, data: Bytes[512]
):
    # V4 callback compatibility shim for harness-only execution.
    assert self._v4_callback_pool != empty(address), "unexpected v4 callback"
    assert msg.sender == self._v4_callback_pool, "invalid v4 callback sender"
    del amount0Delta, amount1Delta
    # Nested callback routing is represented by a chained payload in this fixture.
    # Expected shape per layer: next_pool(20)||zeroForOne(1)||amount_out(8)
    if len(data) > 0:
        assert len(data) >= V4_CALLBACK_LAYER_LEN, "invalid v4 callback payload"
        assert len(data) == V4_CALLBACK_LAYER_LEN, "invalid v4 callback payload"
        _next_pool: address = convert(slice(data, 0, 20), address)
        # keep sender-auth context alive for the next hop.
        self._v4_callback_pool = _next_pool
        log V4CallbackLayer(msg.sender, _next_pool, True)
    else:
        log V4CallbackLayer(msg.sender, empty(address), False)
        self._v4_callback_pool = empty(address)
    return


@external
def unlockCallback(data: Bytes[512]):
    # Alternate callback name used by some V4 pool manager surfaces.
    assert self._v4_callback_pool != empty(address), "unexpected unlock callback"
    assert msg.sender == self._v4_callback_pool, "invalid unlock callback sender"
    # Same wire-shape as uniswapV4SwapCallback in this fixture.
    if len(data) > 0:
        assert len(data) == V4_CALLBACK_LAYER_LEN, "invalid v4 callback payload"
        _next_pool: address = convert(slice(data, 0, 20), address)
        self._v4_callback_pool = _next_pool
        log V4CallbackLayer(msg.sender, _next_pool, True)
    else:
        log V4CallbackLayer(msg.sender, empty(address), False)
        self._v4_callback_pool = empty(address)
    return


@internal
def _read_u8(data: Bytes[4096], offset: uint256) -> uint8:
    return convert(convert(convert(slice(data, offset, 1), bytes32), uint256) >> 248, uint8


@internal
def _read_address(data: Bytes[4096], offset: uint256) -> address:
    return convert(slice(data, offset, 20), address)


@internal
def _read_u256(data: Bytes[4096], offset: uint256) -> uint256:
    return convert(slice(data, offset, 32), uint256)
