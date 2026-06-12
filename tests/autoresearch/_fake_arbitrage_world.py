from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict

Address = str

COMMAND_SEPARATOR = 0xFF
CMD_V2_SWAP = 0
CMD_V4_SWAP = 1

CMD_V2_LEN = 1 + 20 + 32 + 32 + 20 + 1
CMD_V4_LEN = 1 + 20 + 1 + 32 + 20 + 1
V4_CALLBACK_PAYLOAD_LAYER_LEN: int = 29

# Uniswap V3 sqrt bounds.
MIN_SQRT_RATIO: int = 4_295_128_739
MAX_SQRT_RATIO: int = 1_461_446_703_485_210_103_287_273_052_203_988_822_378_723_970_342
MAX_INT128: int = (1 << 127) - 1


@dataclass(frozen=True)
class V2Command:
    pool_addr: Address
    amount0_out: int
    amount1_out: int
    recipient: Address

    @property
    def output(self) -> int:
        return self.amount0_out + self.amount1_out


@dataclass(frozen=True)
class V4Command:
    pool_addr: Address
    zero_for_one: bool
    amount_out: int
    recipient: Address

    @property
    def output(self) -> int:
        return self.amount_out


@dataclass(frozen=True)
class V4CallbackLayer:
    next_pool: Address
    zero_for_one: bool
    amount_out: int


@dataclass
class MockERC20:
    name: str
    symbol: str
    decimals: int
    address: Address
    balances: dict[Address, int] = field(default_factory=dict)

    def balance_of(self, account: Address) -> int:
        return self.balances.get(account, 0)

    def mint(self, account: Address, amount: int) -> None:
        assert amount >= 0
        self.balances[account] = self.balance_of(account) + amount

    def transfer(self, sender: Address, receiver: Address, amount: int) -> None:
        assert amount >= 0
        assert self.balance_of(sender) >= amount
        self.balances[sender] = self.balance_of(sender) - amount
        self.balances[receiver] = self.balance_of(receiver) + amount


@dataclass
class MockV2Pair:
    token0: MockERC20
    token1: MockERC20
    address: Address
    swap_fee: int = 30
    reserve0: int = 0
    reserve1: int = 0
    unlocked: bool = True

    def sync(self) -> None:
        self.reserve0 = self.token0.balance_of(self.address)
        self.reserve1 = self.token1.balance_of(self.address)

    def swap(
        self,
        amount0_out: int,
        amount1_out: int,
        recipient: Address,
        data: bytes,
        callback: Callable[[Address, int, int, bytes], None] | None = None,
    ) -> None:
        assert self.unlocked, "reentrant"
        self.unlocked = False

        assert amount0_out > 0 or amount1_out > 0
        assert amount0_out <= self.reserve0 and amount1_out <= self.reserve1
        assert recipient != self.token0.address and recipient != self.token1.address

        pre0: int = self.token0.balance_of(self.address)
        pre1: int = self.token1.balance_of(self.address)

        if amount0_out:
            self.token0.transfer(self.address, recipient, amount0_out)
        if amount1_out:
            self.token1.transfer(self.address, recipient, amount1_out)

        if data and callback is not None:
            callback(self.address, amount0_out, amount1_out, data)

        post0: int = self.token0.balance_of(self.address)
        post1: int = self.token1.balance_of(self.address)

        amount0_in: int = (post0 + amount0_out - self.reserve0) if (
            post0 + amount0_out > self.reserve0
        ) else 0
        amount1_in: int = (post1 + amount1_out - self.reserve1) if (
            post1 + amount1_out > self.reserve1
        ) else 0

        assert amount0_in > 0 or amount1_in > 0

        balance0_adjusted: int = post0 * 10_000 - amount0_in * self.swap_fee
        balance1_adjusted: int = post1 * 10_000 - amount1_in * self.swap_fee
        assert balance0_adjusted * balance1_adjusted >= self.reserve0 * self.reserve1 * 10_000 * 10_000

        self.reserve0 = post0
        self.reserve1 = post1
        self.unlocked = True


@dataclass
class MockV3Pool:
    token0: MockERC20
    token1: MockERC20
    address: Address
    amount_in: int = 0
    amount_out: int = 0
    zero_for_one: bool = True
    unlocked: bool = True

    def set_next_swap(self, amount_in: int, amount_out: int, zero_for_one: bool) -> None:
        assert amount_in > 0
        assert amount_out > 0
        self.amount_in = amount_in
        self.amount_out = amount_out
        self.zero_for_one = zero_for_one

    def swap(
        self,
        recipient: Address,
        zero_for_one: bool,
        amount_specified: int,
        sqrt_price_limit_x96: int,
        data: bytes,
        callback: Callable[[Address, int, int, bytes], None],
    ) -> tuple[int, int]:
        assert self.unlocked, "unlocked"
        self.unlocked = False

        assert amount_specified != 0
        assert sqrt_price_limit_x96 > MIN_SQRT_RATIO and sqrt_price_limit_x96 < MAX_SQRT_RATIO
        assert self.amount_in > 0 and self.amount_out > 0
        assert zero_for_one == self.zero_for_one

        if zero_for_one:
            assert self.token1.balance_of(self.address) >= self.amount_out
            self.token1.transfer(self.address, recipient, self.amount_out)
            amount0_delta = int(self.amount_in)
            amount1_delta = -int(self.amount_out)
            input_token = self.token0
        else:
            assert self.token0.balance_of(self.address) >= self.amount_out
            self.token0.transfer(self.address, recipient, self.amount_out)
            amount0_delta = -int(self.amount_out)
            amount1_delta = int(self.amount_in)
            input_token = self.token1

        balance_before = input_token.balance_of(self.address)

        if callback is not None:
            callback(self.address, amount0_delta, amount1_delta, data)

        balance_after = input_token.balance_of(self.address)
        assert balance_before + self.amount_in <= balance_after

        self.amount_in = 0
        self.amount_out = 0
        self.unlocked = True
        return amount0_delta, amount1_delta


@dataclass
class MockV4Pool:
    token0: MockERC20
    token1: MockERC20
    address: Address
    amount_in: int = 0
    amount_out: int = 0
    zero_for_one: bool = True
    unlocked: bool = True

    def set_next_swap(self, amount_in: int, amount_out: int, zero_for_one: bool) -> None:
        assert amount_in > 0
        assert amount_out > 0
        assert amount_in <= MAX_INT128
        assert amount_out <= MAX_INT128
        self.amount_in = amount_in
        self.amount_out = amount_out
        self.zero_for_one = zero_for_one

    def swap(
        self,
        recipient: Address,
        zero_for_one: bool,
        amount_specified: int,
        data: bytes,
        callback: Callable[[Address, int, int, bytes], None],
    ) -> tuple[int, int]:
        assert self.unlocked, "unlocked"
        self.unlocked = False

        assert amount_specified != 0
        assert self.amount_in > 0 and self.amount_out > 0
        assert zero_for_one == self.zero_for_one

        if amount_specified > 0:
            assert amount_specified <= MAX_INT128
            assert int(amount_specified) == self.amount_in
        else:
            assert -int(amount_specified) <= MAX_INT128
            assert -int(amount_specified) == self.amount_out

        if zero_for_one:
            assert self.token1.balance_of(self.address) >= self.amount_out
            self.token1.transfer(self.address, recipient, self.amount_out)
            amount0_delta = int(self.amount_in)
            amount1_delta = -int(self.amount_out)
            input_token = self.token0
        else:
            assert self.token0.balance_of(self.address) >= self.amount_out
            self.token0.transfer(self.address, recipient, self.amount_out)
            amount0_delta = -int(self.amount_out)
            amount1_delta = int(self.amount_in)
            input_token = self.token1

        balance_before = input_token.balance_of(self.address)

        if callback is not None:
            callback(self.address, amount0_delta, amount1_delta, data)

        balance_after = input_token.balance_of(self.address)
        assert balance_before + self.amount_in <= balance_after

        self.amount_in = 0
        self.amount_out = 0
        self.unlocked = True
        return amount0_delta, amount1_delta


@dataclass
class MockExecutor:
    owner: Address
    weth: MockERC20
    address: Address
    v4_callback_trace: list[Address] = field(default_factory=list)
    _v4_callback_chain_active: bool = False
    _v4_expected_callback_chain: list[Address] = field(default_factory=list)
    _v4_callback_step: int = 0
    gas_used: int = 0

    def _record_gas(self, gas: int) -> None:
        self.gas_used += gas

    def execute_v2_keep_stream(
        self,
        commands: list[V2Command],
        pools: Dict[Address, MockV2Pair],
        seed: int,
    ) -> int:
        # Baseline parser + dispatch shape check for stream contract tests.
        self.gas_used = 0
        assert len(commands) == 3

        for index, cmd in enumerate(commands):
            assert cmd.pool_addr in pools
            self._record_gas(12_500 + index * 13 + seed % 7)

        return self.gas_used

    def execute_v4_keep_stream(
        self,
        commands: list[V4Command],
        pools: Dict[Address, MockV4Pool],
        seed: int,
    ) -> int:
        self.gas_used = 0
        assert len(commands) == 3

        for index, cmd in enumerate(commands):
            assert cmd.pool_addr in pools
            self._record_gas(11_500 + index * 17 + seed % 9)

        return self.gas_used

    def execute_v2_zero_balance_arbitrage(
        self,
        pool1: MockV2Pair,
        pool2: MockV2Pair,
        pool3: MockV2Pair,
        commands: list[V2Command],
        pay_amount: int,
        seed: int,
    ) -> int:
        assert len(commands) == 3
        cmd1, cmd2, cmd3 = commands
        self.gas_used = 0

        flash_out = cmd3.output
        assert pay_amount <= flash_out

        def _callback(_sender: Address, amount0_out: int, amount1_out: int, data: bytes) -> None:
            del _sender, data
            assert amount0_out == cmd3.amount0_out or amount1_out == cmd3.amount1_out

            # Explicit payment at innermost pool is deterministic in this model.
            self.weth.transfer(self.address, cmd1.pool_addr, pay_amount)
            self._record_gas(4_000)

            # Route outputs directly across pool chain.
            pool1.swap(cmd1.amount0_out, cmd1.amount1_out, pool2.address, b"", None)
            pool2.swap(cmd2.amount0_out, cmd2.amount1_out, pool3.address, b"", None)

        self._record_gas(9_000 + seed % 11)
        pool3.swap(cmd3.amount0_out, cmd3.amount1_out, self.address, b"x", _callback)

        return self.gas_used

    def execute_v3_nested_arbitrage(
        self,
        pool3: MockV3Pool,
        pools: Dict[Address, MockV3Pool],
        payload: bytes,
        seed: int,
    ) -> int:
        self.gas_used = 0

        def _callback(sender: Address, amount0_delta: int, amount1_delta: int, data: bytes) -> None:
            self._record_gas(3_000 + seed % 9)
            if len(data) == 0:
                owed = amount0_delta if amount0_delta > 0 else amount1_delta
                if owed < 0:
                    owed = -owed
                self.weth.transfer(self.address, sender, owed)
                return

            # data is an on-chain onion: [next_pool(20)||dir(1)||amt(8)||rest...]
            assert len(data) >= 29
            next_pool_addr = "0x" + data[:20].hex()
            next_zfo = (data[20] & 1) != 0
            next_amount = int.from_bytes(data[21:29], "big")
            next_payload = data[29:]

            next_pool = pools[next_pool_addr]
            self._record_gas(5_000)
            next_pool.swap(
                sender,
                next_zfo,
                -int(next_amount),
                MIN_SQRT_RATIO + 1 if next_zfo else MAX_SQRT_RATIO - 1,
                next_payload,
                _callback,
            )

        self._record_gas(8_500)
        pool3.swap(
            self.address,
            pool3.zero_for_one,
            -int(pool3.amount_out),
            MIN_SQRT_RATIO + 1 if pool3.zero_for_one else MAX_SQRT_RATIO - 1,
            payload,
            _callback,
        )

        return self.gas_used

    def execute_v4_nested_arbitrage(
        self,
        pool3: MockV4Pool,
        pools: Dict[Address, MockV4Pool],
        payload: bytes,
        seed: int,
        expected_callback_chain: list[Address] | None = None,
    ) -> int:
        self.gas_used = 0
        self.v4_callback_trace = []
        layers = parse_v4_callback_layers(payload)
        expected_chain = [pool3.address] + [layer.next_pool for layer in layers]

        assert len(expected_chain) >= 1

        if expected_callback_chain is not None:
            assert expected_callback_chain == expected_chain

        self._v4_callback_chain_active = True
        self._v4_expected_callback_chain = expected_chain
        self._v4_callback_step = 0

        def _record_callback(sender: Address) -> None:
            self._record_gas(3_000 + seed % 11)
            assert self._v4_callback_chain_active, "v4 callback context inactive"
            self.v4_callback_trace.append(sender)

            assert self._v4_callback_step < len(self._v4_expected_callback_chain), (
                "callback sender step out of range"
            )
            assert (
                sender == self._v4_expected_callback_chain[self._v4_callback_step]
            ), "unexpected callback sender order"
            self._v4_callback_step += 1

        def _callback(sender: Address, amount0_delta: int, amount1_delta: int, data: bytes) -> None:
            _record_callback(sender)

            if len(data) == 0:
                owed = amount0_delta if amount0_delta > 0 else amount1_delta
                if owed < 0:
                    owed = -owed
                self.weth.transfer(self.address, sender, owed)
                assert self._v4_callback_step == len(self._v4_expected_callback_chain), (
                    "missing expected callback hop"
                )
                return

            # data is an on-chain onion: [next_pool(20)||dir(1)||amt(8)||rest...]
            layers = parse_v4_callback_layers(data)
            assert len(layers) == 1 or len(data) % V4_CALLBACK_PAYLOAD_LAYER_LEN == 0
            layer = layers[0]
            assert layer.next_pool == self._v4_expected_callback_chain[self._v4_callback_step], (
                "unexpected next pool"
            )
            next_payload = data[V4_CALLBACK_PAYLOAD_LAYER_LEN:]

            next_pool = pools[layer.next_pool]
            self._record_gas(5_000)
            next_pool.swap(sender, layer.zero_for_one, -int(layer.amount_out), next_payload, _callback)

        self._record_gas(8_500)
        try:
            pool3.swap(
                self.address,
                pool3.zero_for_one,
                -int(pool3.amount_out),
                payload,
                _callback,
            )
        finally:
            self._v4_callback_chain_active = False
            self._v4_expected_callback_chain = []
            self._v4_callback_step = 0

        if expected_callback_chain is not None:
            assert len(self.v4_callback_trace) == len(expected_callback_chain), "callback chain length mismatch"
            assert self.v4_callback_trace == expected_callback_chain
        else:
            assert len(self.v4_callback_trace) == len(expected_chain)
            assert self.v4_callback_trace == expected_chain

        for pool in pools.values():
            if hasattr(pool, "amount_in"):
                pool.amount_in = 0
            if hasattr(pool, "amount_out"):
                pool.amount_out = 0

        return self.gas_used

    def execute_v2_v4_v4_nested_arbitrage(
        self,
        pool3: MockV2Pair,
        pools: Dict[Address, MockV4Pool],
        payload: bytes,
        seed: int,
        output_amounts: tuple[int, int],
        expected_callback_chain: list[Address] | None = None,
    ) -> int:
        self.gas_used = 0
        self.v4_callback_trace = []

        layers = parse_v4_callback_layers(payload)
        expected_chain = [pool3.address] + [layer.next_pool for layer in layers]
        assert len(expected_chain) >= 2
        amount0_out, amount1_out = output_amounts
        assert amount0_out > 0 or amount1_out > 0

        if expected_callback_chain is not None:
            assert expected_callback_chain == expected_chain

        self._v4_callback_chain_active = True
        self._v4_expected_callback_chain = expected_chain
        self._v4_callback_step = 0

        def _record_callback(sender: Address) -> None:
            self._record_gas(3_000 + seed % 11)
            assert self._v4_callback_chain_active, "v4 callback context inactive"
            self.v4_callback_trace.append(sender)

            assert self._v4_callback_step < len(self._v4_expected_callback_chain), (
                "callback sender step out of range"
            )
            assert (
                sender == self._v4_expected_callback_chain[self._v4_callback_step]
            ), "unexpected callback sender order"
            self._v4_callback_step += 1

        def _v4_callback(sender: Address, amount0_delta: int, amount1_delta: int, data: bytes) -> None:
            _record_callback(sender)

            if len(data) == 0:
                owed = amount0_delta if amount0_delta > 0 else amount1_delta
                if owed < 0:
                    owed = -owed
                self.weth.transfer(self.address, sender, owed)
                assert self._v4_callback_step == len(self._v4_expected_callback_chain), (
                    "missing expected callback hop"
                )
                return

            layers_inner = parse_v4_callback_layers(data)
            assert len(layers_inner) >= 1
            layer = layers_inner[0]
            assert layer.next_pool == self._v4_expected_callback_chain[self._v4_callback_step], (
                "unexpected next pool"
            )
            next_payload = data[V4_CALLBACK_PAYLOAD_LAYER_LEN:]

            next_pool = pools[layer.next_pool]
            self._record_gas(5_000)
            next_pool.swap(sender, layer.zero_for_one, -int(layer.amount_out), next_payload, _v4_callback)

        def _v2_callback(sender: Address, _amount0_out: int, _amount1_out: int, data: bytes) -> None:
            _record_callback(sender)

            if _amount0_out > 0:
                assert _amount0_out == amount0_out
            if _amount1_out > 0:
                assert _amount1_out == amount1_out

            if len(data) == 0:
                assert self._v4_callback_step == len(self._v4_expected_callback_chain), (
                    "missing expected callback hop"
                )
                return

            layers_inner = parse_v4_callback_layers(data)
            assert len(layers_inner) >= 1
            layer = layers_inner[0]
            assert layer.next_pool == self._v4_expected_callback_chain[self._v4_callback_step], (
                "unexpected next pool"
            )
            next_payload = data[V4_CALLBACK_PAYLOAD_LAYER_LEN:]
            next_pool = pools[layer.next_pool]
            self._record_gas(5_000)
            next_pool.swap(sender, layer.zero_for_one, -int(layer.amount_out), next_payload, _v4_callback)

        self._record_gas(8_500)
        try:
            pool3.swap(
                amount0_out,
                amount1_out,
                self.address,
                payload,
                _v2_callback,
            )
        finally:
            self._v4_callback_chain_active = False
            self._v4_expected_callback_chain = []
            self._v4_callback_step = 0

        if expected_callback_chain is not None:
            assert len(self.v4_callback_trace) == len(expected_callback_chain), "callback chain length mismatch"
            assert self.v4_callback_trace == expected_callback_chain
        else:
            assert len(self.v4_callback_trace) == len(expected_chain)
            assert self.v4_callback_trace == expected_chain

        for pool in pools.values():
            if hasattr(pool, "amount_in"):
                pool.amount_in = 0
            if hasattr(pool, "amount_out"):
                pool.amount_out = 0

        return self.gas_used

    def execute_v3_v4_v4_nested_arbitrage(
        self,
        pool3: MockV3Pool,
        pools: Dict[Address, MockV4Pool],
        payload: bytes,
        seed: int,
        output_amounts: tuple[int, int],
        expected_callback_chain: list[Address] | None = None,
    ) -> int:
        self.gas_used = 0
        self.v4_callback_trace = []

        layers = parse_v4_callback_layers(payload)
        expected_chain = [pool3.address] + [layer.next_pool for layer in layers]
        assert len(expected_chain) >= 2
        amount0_out, amount1_out = output_amounts
        assert amount0_out > 0 or amount1_out > 0

        if expected_callback_chain is not None:
            assert expected_callback_chain == expected_chain

        self._v4_callback_chain_active = True
        self._v4_expected_callback_chain = expected_chain
        self._v4_callback_step = 0

        def _record_callback(sender: Address) -> None:
            self._record_gas(3_000 + seed % 11)
            assert self._v4_callback_chain_active, "v4 callback context inactive"
            self.v4_callback_trace.append(sender)
            assert self._v4_callback_step < len(self._v4_expected_callback_chain), (
                "callback sender step out of range"
            )
            assert (
                sender == self._v4_expected_callback_chain[self._v4_callback_step]
            ), "unexpected callback sender order"
            self._v4_callback_step += 1

        def _v4_callback(sender: Address, amount0_delta: int, amount1_delta: int, data: bytes) -> None:
            _record_callback(sender)

            if len(data) == 0:
                owed = amount0_delta if amount0_delta > 0 else amount1_delta
                if owed < 0:
                    owed = -owed
                self.weth.transfer(self.address, sender, owed)
                assert self._v4_callback_step == len(self._v4_expected_callback_chain), (
                    "missing expected callback hop"
                )
                return

            layers_inner = parse_v4_callback_layers(data)
            assert len(layers_inner) >= 1
            layer = layers_inner[0]
            assert layer.next_pool == self._v4_expected_callback_chain[self._v4_callback_step], (
                "unexpected next pool"
            )
            next_payload = data[V4_CALLBACK_PAYLOAD_LAYER_LEN:]

            next_pool = pools[layer.next_pool]
            self._record_gas(5_000)
            next_pool.swap(sender, layer.zero_for_one, -int(layer.amount_out), next_payload, _v4_callback)

        def _v3_callback(sender: Address, amount0_delta: int, amount1_delta: int, data: bytes) -> None:
            _record_callback(sender)

            if len(data) == 0:
                assert self._v4_callback_step == len(self._v4_expected_callback_chain), (
                    "missing expected callback hop"
                )
                return

            layers_inner = parse_v4_callback_layers(data)
            assert len(layers_inner) >= 1
            layer = layers_inner[0]
            assert layer.next_pool == self._v4_expected_callback_chain[self._v4_callback_step], (
                "unexpected next pool"
            )
            next_payload = data[V4_CALLBACK_PAYLOAD_LAYER_LEN:]
            next_pool = pools[layer.next_pool]
            self._record_gas(5_000)
            next_pool.swap(sender, layer.zero_for_one, -int(layer.amount_out), next_payload, _v4_callback)

        _amount0_out, _amount1_out = amount0_out, amount1_out
        _sqrt_limit = MIN_SQRT_RATIO + 1 if pool3.zero_for_one else MAX_SQRT_RATIO - 1
        _output_amount = _amount1_out if pool3.zero_for_one else _amount0_out

        assert _output_amount > 0

        self._record_gas(8_500)
        try:
            pool3.swap(
                self.address,
                pool3.zero_for_one,
                -int(_output_amount),
                _sqrt_limit,
                payload,
                _v3_callback,
            )
        finally:
            self._v4_callback_chain_active = False
            self._v4_expected_callback_chain = []
            self._v4_callback_step = 0

        if expected_callback_chain is not None:
            assert len(self.v4_callback_trace) == len(expected_callback_chain), "callback chain length mismatch"
            assert self.v4_callback_trace == expected_callback_chain
        else:
            assert len(self.v4_callback_trace) == len(expected_chain)
            assert self.v4_callback_trace == expected_chain

        for pool in pools.values():
            if hasattr(pool, "amount_in"):
                pool.amount_in = 0
            if hasattr(pool, "amount_out"):
                pool.amount_out = 0

        return self.gas_used

    def execute_v4_v3_v3_nested_arbitrage(
        self,
        pool3: MockV4Pool,
        pools: Dict[Address, MockV3Pool],
        payload: bytes,
        seed: int,
        output_amounts: tuple[int, int],
        expected_callback_chain: list[Address] | None = None,
    ) -> int:
        self.gas_used = 0
        self.v4_callback_trace = []

        layers = parse_v4_callback_layers(payload)
        expected_chain = [pool3.address] + [layer.next_pool for layer in layers]
        assert len(expected_chain) >= 2
        amount0_out, amount1_out = output_amounts
        assert amount0_out > 0 or amount1_out > 0

        if expected_callback_chain is not None:
            assert expected_callback_chain == expected_chain

        self._v4_callback_chain_active = True
        self._v4_expected_callback_chain = expected_chain
        self._v4_callback_step = 0

        def _record_callback(sender: Address) -> None:
            self._record_gas(3_000 + seed % 11)
            assert self._v4_callback_chain_active, "v4 callback context inactive"
            self.v4_callback_trace.append(sender)
            assert self._v4_callback_step < len(self._v4_expected_callback_chain), (
                "callback sender step out of range"
            )
            assert (
                sender == self._v4_expected_callback_chain[self._v4_callback_step]
            ), "unexpected callback sender order"
            self._v4_callback_step += 1

        def _v4_callback(sender: Address, amount0_delta: int, amount1_delta: int, data: bytes) -> None:
            _record_callback(sender)

            if len(data) == 0:
                owed = amount0_delta if amount0_delta > 0 else amount1_delta
                if owed < 0:
                    owed = -owed
                self.weth.transfer(self.address, sender, owed)
                assert self._v4_callback_step == len(self._v4_expected_callback_chain), (
                    "missing expected callback hop"
                )
                return

            layers_inner = parse_v4_callback_layers(data)
            assert len(layers_inner) >= 1
            layer = layers_inner[0]
            assert layer.next_pool == self._v4_expected_callback_chain[self._v4_callback_step], (
                "unexpected next pool"
            )
            next_payload = data[V4_CALLBACK_PAYLOAD_LAYER_LEN:]
            next_pool = pools[layer.next_pool]
            self._record_gas(5_000)
            next_pool.swap(
                sender,
                layer.zero_for_one,
                -int(layer.amount_out),
                MIN_SQRT_RATIO + 1 if layer.zero_for_one else MAX_SQRT_RATIO - 1,
                next_payload,
                _v3_callback,
            )

        def _v3_callback(sender: Address, amount0_delta: int, amount1_delta: int, data: bytes) -> None:
            _record_callback(sender)

            if amount0_delta > 0:
                input_token = pools[sender].token0
                required_input = amount0_delta
            elif amount1_delta > 0:
                input_token = pools[sender].token1
                required_input = amount1_delta
            else:
                required_input = 0
                input_token = None

            if len(data) == 0:
                if required_input > 0:
                    current = input_token.balance_of(sender)
                    if current < required_input:
                        input_token.transfer(self.address, sender, required_input - current)
                assert self._v4_callback_step == len(self._v4_expected_callback_chain), (
                    "missing expected callback hop"
                )
                return

            layers_inner = parse_v4_callback_layers(data)
            assert len(layers_inner) >= 1
            layer = layers_inner[0]
            assert layer.next_pool == self._v4_expected_callback_chain[self._v4_callback_step], (
                "unexpected next pool"
            )
            next_payload = data[V4_CALLBACK_PAYLOAD_LAYER_LEN:]
            next_pool = pools[layer.next_pool]
            self._record_gas(5_000)
            next_pool.swap(
                sender,
                layer.zero_for_one,
                -int(layer.amount_out),
                MIN_SQRT_RATIO + 1 if layer.zero_for_one else MAX_SQRT_RATIO - 1,
                next_payload,
                _v3_callback,
            )

            if required_input > 0:
                current = input_token.balance_of(sender)
                if current < required_input:
                    input_token.transfer(self.address, sender, required_input - current)

        self._record_gas(8_500)
        amount0_out, amount1_out = output_amounts
        _output_amount = amount1_out if pool3.zero_for_one else amount0_out
        assert _output_amount > 0

        try:
            pool3.swap(
                self.address,
                pool3.zero_for_one,
                -int(_output_amount),
                payload,
                _v4_callback,
            )
        finally:
            self._v4_callback_chain_active = False
            self._v4_expected_callback_chain = []
            self._v4_callback_step = 0

        if expected_callback_chain is not None:
            assert len(self.v4_callback_trace) == len(expected_callback_chain), "callback chain length mismatch"
            assert self.v4_callback_trace == expected_callback_chain
        else:
            assert len(self.v4_callback_trace) == len(expected_chain)
            assert self.v4_callback_trace == expected_chain

        for pool in pools.values():
            if hasattr(pool, "amount_in"):
                pool.amount_in = 0
            if hasattr(pool, "amount_out"):
                pool.amount_out = 0

        return self.gas_used

    def execute_v4_v3_v2_nested_arbitrage(
        self,
        pool3: MockV4Pool,
        pools: Dict[Address, MockV2Pair | MockV3Pool],
        payload: bytes,
        seed: int,
        output_amounts: tuple[int, int],
        final_pay_amount: int,
        expected_callback_chain: list[Address] | None = None,
    ) -> int:
        self.gas_used = 0
        self.v4_callback_trace = []

        layers = parse_v4_callback_layers(payload)
        expected_chain = [pool3.address] + [layer.next_pool for layer in layers]
        assert len(expected_chain) >= 2
        amount0_out, amount1_out = output_amounts
        assert amount0_out > 0 or amount1_out > 0

        if expected_callback_chain is not None:
            assert expected_callback_chain == expected_chain

        self._v4_callback_chain_active = True
        self._v4_expected_callback_chain = expected_chain
        self._v4_callback_step = 0

        def _record_callback(sender: Address) -> None:
            self._record_gas(3_000 + seed % 11)
            assert self._v4_callback_chain_active, "v4 callback context inactive"
            self.v4_callback_trace.append(sender)
            assert self._v4_callback_step < len(self._v4_expected_callback_chain), (
                "callback sender step out of range"
            )
            assert (
                sender == self._v4_expected_callback_chain[self._v4_callback_step]
            ), "unexpected callback sender order"
            self._v4_callback_step += 1

        def _v2_callback(sender: Address, _amount0_out: int, _amount1_out: int, data: bytes) -> None:
            _record_callback(sender)
            del data
            assert self._v4_callback_step == len(self._v4_expected_callback_chain), (
                "missing expected callback hop"
            )

            pool = pools[sender]
            assert isinstance(pool, MockV2Pair)
            baseline = pool.reserve0

            if _amount0_out > 0:
                pay_token = pools[sender].token1
                baseline = pool.reserve1
            elif _amount1_out > 0:
                pay_token = pools[sender].token0
            else:
                raise AssertionError("invalid V2 callback")

            current = pay_token.balance_of(sender)
            missing = baseline + final_pay_amount - current
            if missing > 0:
                pay_token.transfer(self.address, sender, missing)

        def _v3_callback(sender: Address, amount0_delta: int, amount1_delta: int, data: bytes) -> None:
            _record_callback(sender)
            del amount0_delta
            del amount1_delta

            if len(data) == 0:
                assert self._v4_callback_step == len(self._v4_expected_callback_chain), (
                    "missing expected callback hop"
                )
                return

            layers_inner = parse_v4_callback_layers(data)
            assert len(layers_inner) >= 1
            layer = layers_inner[0]
            assert layer.next_pool == self._v4_expected_callback_chain[self._v4_callback_step], (
                "unexpected next pool"
            )
            next_payload = data[V4_CALLBACK_PAYLOAD_LAYER_LEN:]

            next_pool = pools[layer.next_pool]
            assert isinstance(next_pool, MockV2Pair)

            next_zero_for_one = layer.zero_for_one
            next_amount = layer.amount_out
            amt0 = 0 if next_zero_for_one else next_amount
            amt1 = next_amount if next_zero_for_one else 0
            self._record_gas(5_000)
            next_pool.swap(
                recipient=sender,
                amount0_out=amt0,
                amount1_out=amt1,
                data=b"\x00",
                callback=_v2_callback,
            )

        def _v4_callback(sender: Address, amount0_delta: int, amount1_delta: int, data: bytes) -> None:
            _record_callback(sender)

            if len(data) == 0:
                owed = amount0_delta if amount0_delta > 0 else amount1_delta
                if owed < 0:
                    owed = -owed
                self.weth.transfer(self.address, sender, owed)
                assert self._v4_callback_step == len(self._v4_expected_callback_chain), (
                    "missing expected callback hop"
                )
                return

            layers_inner = parse_v4_callback_layers(data)
            assert len(layers_inner) >= 1
            layer = layers_inner[0]
            assert layer.next_pool == self._v4_expected_callback_chain[self._v4_callback_step], (
                "unexpected next pool"
            )
            next_payload = data[V4_CALLBACK_PAYLOAD_LAYER_LEN:]

            next_pool = pools[layer.next_pool]
            assert isinstance(next_pool, MockV3Pool)
            self._record_gas(5_000)
            next_pool.swap(
                sender,
                layer.zero_for_one,
                -int(layer.amount_out),
                MIN_SQRT_RATIO + 1 if layer.zero_for_one else MAX_SQRT_RATIO - 1,
                next_payload,
                _v3_callback,
            )

        _output_amount = amount1_out if pool3.zero_for_one else amount0_out
        assert _output_amount > 0

        self._record_gas(8_500)
        try:
            pool3.swap(
                self.address,
                pool3.zero_for_one,
                -int(_output_amount),
                payload,
                _v4_callback,
            )
        finally:
            self._v4_callback_chain_active = False
            self._v4_expected_callback_chain = []
            self._v4_callback_step = 0

        if expected_callback_chain is not None:
            assert len(self.v4_callback_trace) == len(expected_callback_chain), "callback chain length mismatch"
            assert self.v4_callback_trace == expected_callback_chain
        else:
            assert len(self.v4_callback_trace) == len(expected_chain)
            assert self.v4_callback_trace == expected_chain

        return self.gas_used

    def execute_v4_v2_v4_nested_arbitrage(
        self,
        pool3: MockV4Pool,
        pools: Dict[Address, MockV2Pair | MockV4Pool],
        payload: bytes,
        seed: int,
        output_amounts: tuple[int, int],
        final_pay_amount: int,
        expected_callback_chain: list[Address] | None = None,
    ) -> int:
        self.gas_used = 0
        self.v4_callback_trace = []

        layers = parse_v4_callback_layers(payload)
        expected_chain = [pool3.address] + [layer.next_pool for layer in layers]
        assert len(expected_chain) >= 3, "v4->v2->v4 requires two callback hops"
        amount0_out, amount1_out = output_amounts
        assert amount0_out > 0 or amount1_out > 0

        if expected_callback_chain is not None:
            assert expected_callback_chain == expected_chain

        self._v4_callback_chain_active = True
        self._v4_expected_callback_chain = expected_chain
        self._v4_callback_step = 0

        def _record_callback(sender: Address) -> None:
            self._record_gas(3_000 + seed % 11)
            assert self._v4_callback_chain_active, "v4 callback context inactive"
            self.v4_callback_trace.append(sender)
            assert self._v4_callback_step < len(self._v4_expected_callback_chain), (
                "callback sender step out of range"
            )
            assert (
                sender == self._v4_expected_callback_chain[self._v4_callback_step]
            ), "unexpected callback sender order"
            self._v4_callback_step += 1

        def _v4_innermost(sender: Address, amount0_delta: int, amount1_delta: int, data: bytes) -> None:
            _record_callback(sender)
            if len(data) == 1:
                assert data == b"\x00"
            elif len(data) != 0:
                raise AssertionError("unexpected innermost callback payload")

            assert self._v4_callback_step == len(self._v4_expected_callback_chain), (
                "missing expected callback hop"
            )
            del amount0_delta, amount1_delta

            assert self.weth.balance_of(self.address) >= final_pay_amount
            self.weth.transfer(self.address, sender, final_pay_amount)

        def _v2_callback(sender: Address, _amount0_out: int, _amount1_out: int, data: bytes) -> None:
            _record_callback(sender)
            del _amount0_out, _amount1_out
            assert len(data) == 0 or len(data) >= V4_CALLBACK_PAYLOAD_LAYER_LEN, "invalid v2 callback payload"

            if len(data) == 0:
                assert self._v4_callback_step == len(self._v4_expected_callback_chain), (
                    "missing expected callback hop"
                )
                return

            layers_inner = parse_v4_callback_layers(data)
            assert len(layers_inner) >= 1, "invalid v2->v4 payload"
            layer = layers_inner[0]
            assert layer.next_pool == self._v4_expected_callback_chain[self._v4_callback_step], (
                "unexpected next pool"
            )

            next_payload = data[V4_CALLBACK_PAYLOAD_LAYER_LEN:]
            next_pool = pools[layer.next_pool]
            assert isinstance(next_pool, MockV4Pool)

            self._record_gas(5_000)
            next_pool.swap(
                recipient=sender,
                zero_for_one=layer.zero_for_one,
                amount_specified=-int(layer.amount_out),
                data=next_payload if next_payload else b"\x00",
                callback=_v4_innermost,
            )

        def _v4_callback(sender: Address, amount0_delta: int, amount1_delta: int, data: bytes) -> None:
            _record_callback(sender)

            if len(data) == 0:
                owed = amount0_delta if amount0_delta > 0 else amount1_delta
                if owed < 0:
                    owed = -owed
                if owed > 0:
                    self.weth.transfer(self.address, sender, owed)
                assert self._v4_callback_step == len(self._v4_expected_callback_chain), (
                    "missing expected callback hop"
                )
                return

            layers_inner = parse_v4_callback_layers(data)
            assert len(layers_inner) >= 1, "invalid v4 callback payload"
            layer = layers_inner[0]
            assert layer.next_pool == self._v4_expected_callback_chain[self._v4_callback_step], (
                "unexpected next pool"
            )

            next_payload = data[V4_CALLBACK_PAYLOAD_LAYER_LEN:]
            next_pool = pools[layer.next_pool]
            assert isinstance(next_pool, MockV2Pair)

            if layer.zero_for_one:
                next_pool.swap(
                    amount0_out=0,
                    amount1_out=layer.amount_out,
                    recipient=sender,
                    data=next_payload,
                    callback=_v2_callback,
                )
            else:
                next_pool.swap(
                    amount0_out=layer.amount_out,
                    amount1_out=0,
                    recipient=sender,
                    data=next_payload,
                    callback=_v2_callback,
                )

        _output_amount = amount1_out if pool3.zero_for_one else amount0_out
        assert _output_amount > 0

        self._record_gas(8_500)
        try:
            pool3.swap(
                self.address,
                pool3.zero_for_one,
                -int(_output_amount),
                payload,
                _v4_callback,
            )
        finally:
            self._v4_callback_chain_active = False
            self._v4_expected_callback_chain = []
            self._v4_callback_step = 0

        if expected_callback_chain is not None:
            assert len(self.v4_callback_trace) == len(expected_callback_chain), "callback chain length mismatch"
            assert self.v4_callback_trace == expected_callback_chain
        else:
            assert len(self.v4_callback_trace) == len(expected_chain)
            assert self.v4_callback_trace == expected_chain

        for pool in pools.values():
            if hasattr(pool, "amount_in"):
                pool.amount_in = 0
            if hasattr(pool, "amount_out"):
                pool.amount_out = 0

        return self.gas_used

    def execute_v4_v3_v4_nested_arbitrage(
        self,
        pool3: MockV4Pool,
        pools: Dict[Address, MockV4Pool | MockV3Pool],
        payload: bytes,
        seed: int,
        output_amounts: tuple[int, int],
        final_pay_amount: int,
        expected_callback_chain: list[Address] | None = None,
    ) -> int:
        self.gas_used = 0
        self.v4_callback_trace = []

        layers = parse_v4_callback_layers(payload)
        expected_chain = [pool3.address] + [layer.next_pool for layer in layers]
        assert len(expected_chain) >= 3, "v4->v3->v4 requires two callback hops"
        amount0_out, amount1_out = output_amounts
        assert amount0_out > 0 or amount1_out > 0

        if expected_callback_chain is not None:
            assert expected_callback_chain == expected_chain

        self._v4_callback_chain_active = True
        self._v4_expected_callback_chain = expected_chain
        self._v4_callback_step = 0

        def _record_callback(sender: Address) -> None:
            self._record_gas(3_000 + seed % 11)
            assert self._v4_callback_chain_active, "v4 callback context inactive"
            self.v4_callback_trace.append(sender)
            assert self._v4_callback_step < len(self._v4_expected_callback_chain), (
                "callback sender step out of range"
            )
            assert (
                sender == self._v4_expected_callback_chain[self._v4_callback_step]
            ), "unexpected callback sender order"
            self._v4_callback_step += 1

        def _v4_innermost(sender: Address, amount0_delta: int, amount1_delta: int, data: bytes) -> None:
            _record_callback(sender)
            if len(data) != 0:
                raise AssertionError("unexpected innermost v4 payload")

            assert self._v4_callback_step == len(self._v4_expected_callback_chain), (
                "missing expected callback hop"
            )
            del amount0_delta, amount1_delta

            assert self.weth.balance_of(self.address) >= final_pay_amount
            self.weth.transfer(self.address, sender, final_pay_amount)

        def _v3_callback(sender: Address, amount0_delta: int, amount1_delta: int, data: bytes) -> None:
            _record_callback(sender)
            del amount0_delta, amount1_delta

            if len(data) == 0:
                raise AssertionError("missing v4 layer payload")

            layers_inner = parse_v4_callback_layers(data)
            assert len(layers_inner) >= 1, "invalid v3->v4 payload"
            layer = layers_inner[0]
            assert layer.next_pool == self._v4_expected_callback_chain[self._v4_callback_step], (
                "unexpected next pool"
            )

            next_payload = data[V4_CALLBACK_PAYLOAD_LAYER_LEN:]
            next_pool = pools[layer.next_pool]
            assert isinstance(next_pool, MockV4Pool)

            self._record_gas(5_000)
            next_pool.swap(
                recipient=sender,
                zero_for_one=layer.zero_for_one,
                amount_specified=-int(layer.amount_out),
                data=next_payload,
                callback=_v4_innermost,
            )

        def _v4_callback(sender: Address, amount0_delta: int, amount1_delta: int, data: bytes) -> None:
            _record_callback(sender)
            if len(data) == 0:
                owed = amount0_delta if amount0_delta > 0 else amount1_delta
                if owed < 0:
                    owed = -owed
                if owed > 0:
                    self.weth.transfer(self.address, sender, owed)
                assert self._v4_callback_step == len(self._v4_expected_callback_chain), (
                    "missing expected callback hop"
                )
                return

            layers_inner = parse_v4_callback_layers(data)
            assert len(layers_inner) >= 1, "invalid v4 callback payload"
            layer = layers_inner[0]
            assert layer.next_pool == self._v4_expected_callback_chain[self._v4_callback_step], (
                "unexpected next pool"
            )

            next_payload = data[V4_CALLBACK_PAYLOAD_LAYER_LEN:]
            next_pool = pools[layer.next_pool]
            assert isinstance(next_pool, MockV3Pool)

            self._record_gas(5_000)
            next_pool.swap(
                recipient=sender,
                zero_for_one=layer.zero_for_one,
                amount_specified=-int(layer.amount_out),
                sqrt_price_limit_x96=MIN_SQRT_RATIO + 1 if layer.zero_for_one else MAX_SQRT_RATIO - 1,
                data=next_payload,
                callback=_v3_callback,
            )

            del amount0_delta, amount1_delta

        _output_amount = amount1_out if pool3.zero_for_one else amount0_out
        assert _output_amount > 0

        self._record_gas(8_500)
        try:
            pool3.swap(
                self.address,
                pool3.zero_for_one,
                -int(_output_amount),
                payload,
                _v4_callback,
            )
        finally:
            self._v4_callback_chain_active = False
            self._v4_expected_callback_chain = []
            self._v4_callback_step = 0

        if expected_callback_chain is not None:
            assert len(self.v4_callback_trace) == len(expected_callback_chain), "callback chain length mismatch"
            assert self.v4_callback_trace == expected_callback_chain
        else:
            assert len(self.v4_callback_trace) == len(expected_chain)
            assert self.v4_callback_trace == expected_chain

        return self.gas_used

    def execute_v4_v2_v2_nested_arbitrage(
        self,
        pool3: MockV4Pool,
        pools: Dict[Address, MockV2Pair],
        payload: bytes,
        seed: int,
        output_amounts: tuple[int, int],
        final_pay_amount: int,
        expected_callback_chain: list[Address] | None = None,
    ) -> int:
        self.gas_used = 0
        self.v4_callback_trace = []

        layers = parse_v4_callback_layers(payload)
        expected_chain = [pool3.address] + [layer.next_pool for layer in layers]
        assert len(expected_chain) >= 3, "v4->v2->v2 requires two callback hops"
        amount0_out, amount1_out = output_amounts
        assert amount0_out > 0 or amount1_out > 0

        if expected_callback_chain is not None:
            assert expected_callback_chain == expected_chain

        self._v4_callback_chain_active = True
        self._v4_expected_callback_chain = expected_chain
        self._v4_callback_step = 0

        def _record_callback(sender: Address) -> None:
            self._record_gas(3_000 + seed % 11)
            assert self._v4_callback_chain_active, "v4 callback context inactive"
            self.v4_callback_trace.append(sender)
            assert self._v4_callback_step < len(self._v4_expected_callback_chain), (
                "callback sender step out of range"
            )
            assert (
                sender == self._v4_expected_callback_chain[self._v4_callback_step]
            ), "unexpected callback sender order"
            self._v4_callback_step += 1

        def _pay_innermost_pool(
            sender: Address,
            amount0_delta: int,
            amount1_delta: int,
            data: bytes,
        ) -> None:
            _record_callback(sender)

            if len(data) == 1:
                assert data == b"\x00"
            else:
                assert len(data) == 0, "unexpected inner callback payload"
            assert self._v4_callback_step == len(self._v4_expected_callback_chain), (
                "missing expected callback hop"
            )

            pool = pools[sender]
            assert isinstance(pool, MockV2Pair)

            if amount0_delta > 0:
                pay_token = pool.token1
            elif amount1_delta > 0:
                pay_token = pool.token0
            else:
                raise AssertionError("invalid innermost V2 callback")

            assert pay_token.balance_of(self.address) >= final_pay_amount
            pay_token.transfer(self.address, sender, final_pay_amount)

        def _v2_mid_callback(
            sender: Address,
            _amount0_out: int,
            _amount1_out: int,
            data: bytes,
        ) -> None:
            _record_callback(sender)
            del _amount0_out
            del _amount1_out
            assert len(data) >= V4_CALLBACK_PAYLOAD_LAYER_LEN, "missing intermediate callback payload"

            layers_inner = parse_v4_callback_layers(data)
            assert len(layers_inner) >= 1, "invalid v4->v2->v2 payload"
            layer = layers_inner[0]
            assert layer.next_pool == self._v4_expected_callback_chain[self._v4_callback_step], (
                "unexpected next pool"
            )
            next_payload = data[V4_CALLBACK_PAYLOAD_LAYER_LEN:]

            next_pool = pools[layer.next_pool]
            self._record_gas(5_000)
            if layer.zero_for_one:
                next_pool.swap(
                    amount0_out=0,
                    amount1_out=layer.amount_out,
                    recipient=sender,
                    data=next_payload if next_payload else b"\x00",
                    callback=_pay_innermost_pool,
                )
            else:
                next_pool.swap(
                    amount0_out=layer.amount_out,
                    amount1_out=0,
                    recipient=sender,
                    data=next_payload if next_payload else b"\x00",
                    callback=_pay_innermost_pool,
                )

        def _v4_callback(sender: Address, amount0_delta: int, amount1_delta: int, data: bytes) -> None:
            _record_callback(sender)
            if len(data) == 0:
                owed = amount0_delta if amount0_delta > 0 else amount1_delta
                if owed < 0:
                    owed = -owed
                self.weth.transfer(self.address, sender, owed)
                assert self._v4_callback_step == len(self._v4_expected_callback_chain), (
                    "missing expected callback hop"
                )
                return

            layers_inner = parse_v4_callback_layers(data)
            assert len(layers_inner) >= 1, "invalid v4 callback payload"
            layer = layers_inner[0]
            assert layer.next_pool == self._v4_expected_callback_chain[self._v4_callback_step], (
                "unexpected next pool"
            )
            next_payload = data[V4_CALLBACK_PAYLOAD_LAYER_LEN:]

            next_pool = pools[layer.next_pool]
            self._record_gas(5_000)
            if layer.zero_for_one:
                next_pool.swap(
                    amount0_out=0,
                    amount1_out=layer.amount_out,
                    recipient=sender,
                    data=next_payload,
                    callback=_v2_mid_callback,
                )
            else:
                next_pool.swap(
                    amount0_out=layer.amount_out,
                    amount1_out=0,
                    recipient=sender,
                    data=next_payload,
                    callback=_v2_mid_callback,
                )

        _output_amount = amount1_out if pool3.zero_for_one else amount0_out
        assert _output_amount > 0

        self._record_gas(8_500)
        try:
            pool3.swap(
                self.address,
                pool3.zero_for_one,
                -int(_output_amount),
                payload,
                _v4_callback,
            )
        finally:
            self._v4_callback_chain_active = False
            self._v4_expected_callback_chain = []
            self._v4_callback_step = 0

        if expected_callback_chain is not None:
            assert len(self.v4_callback_trace) == len(expected_callback_chain), "callback chain length mismatch"
            assert self.v4_callback_trace == expected_callback_chain
        else:
            assert len(self.v4_callback_trace) == len(expected_chain)
            assert self.v4_callback_trace == expected_chain

        for pool in pools.values():
            if hasattr(pool, "amount_in"):
                pool.amount_in = 0
            if hasattr(pool, "amount_out"):
                pool.amount_out = 0

        return self.gas_used


def _u256(value: int) -> bytes:
    return value.to_bytes(8, "big")


def _uint8(value: int) -> bytes:
    return value.to_bytes(1, "big")


def parse_v2_commands(encoded: bytes) -> list[V2Command]:
    cursor = 0
    out: list[V2Command] = []
    while cursor < len(encoded):
        assert cursor + CMD_V2_LEN <= len(encoded), "truncated v2 command"
        assert encoded[cursor] == CMD_V2_SWAP
        cursor += 1

        pool = "0x" + encoded[cursor : cursor + 20].hex()
        cursor += 20
        amount0 = int.from_bytes(encoded[cursor : cursor + 32], "big")
        cursor += 32
        amount1 = int.from_bytes(encoded[cursor : cursor + 32], "big")
        cursor += 32
        recipient = "0x" + encoded[cursor : cursor + 20].hex()
        cursor += 20

        assert encoded[cursor] == COMMAND_SEPARATOR
        cursor += 1

        out.append(V2Command(pool, amount0, amount1, recipient))
        assert cursor <= len(encoded), "invalid v2 cursor"

    assert cursor == len(encoded), "extra bytes after final command"

    return out


def parse_v4_commands(encoded: bytes) -> list[V4Command]:
    cursor = 0
    out: list[V4Command] = []
    while cursor < len(encoded):
        assert cursor + CMD_V4_LEN <= len(encoded), "truncated v4 command"
        assert encoded[cursor] == CMD_V4_SWAP
        cursor += 1

        pool = "0x" + encoded[cursor : cursor + 20].hex()
        cursor += 20
        zero_for_one_flag = encoded[cursor]
        assert zero_for_one_flag in (0, 1), "invalid zeroForOne flag"
        zero_for_one = zero_for_one_flag == 1
        cursor += 1
        amount_out = int.from_bytes(encoded[cursor : cursor + 32], "big")
        assert amount_out <= MAX_INT128
        cursor += 32
        recipient = "0x" + encoded[cursor : cursor + 20].hex()
        cursor += 20

        assert encoded[cursor] == COMMAND_SEPARATOR
        cursor += 1

        out.append(V4Command(pool, zero_for_one, amount_out, recipient))
        assert cursor <= len(encoded), "invalid v4 cursor"

    assert cursor == len(encoded), "extra bytes after final command"

    return out


def parse_v4_callback_layers(payload: bytes) -> list[V4CallbackLayer]:
    cursor = 0
    out: list[V4CallbackLayer] = []
    while cursor < len(payload):
        assert cursor + V4_CALLBACK_PAYLOAD_LAYER_LEN <= len(payload), "truncated v4 callback layer"
        next_pool = "0x" + payload[cursor : cursor + 20].hex()
        cursor += 20
        next_zfo_flag = payload[cursor]
        assert next_zfo_flag in (0, 1), "invalid callback zeroForOne flag"
        next_zfo = next_zfo_flag == 1
        cursor += 1
        amount = int.from_bytes(payload[cursor : cursor + 8], "big")
        cursor += 8

        out.append(V4CallbackLayer(next_pool, next_zfo, amount))
    return out


def mk_addr(value: int, *, prefix: str = "") -> Address:
    suffix = f"{value % (1 << 160):040x}"
    if prefix:
        suffix = prefix + suffix[len(prefix) :]
    return "0x" + suffix
