"""Tests for the read-only MetaMorpho V1.1 adapter."""

from __future__ import annotations

from degenbot.execution.metamorpho_v1_adapter import (
    MetaMorphoErc4626Limits,
    MetaMorphoMarketConfig,
    MetaMorphoV1Client,
)

_VAULT = "0xa60643c90A542A95026C0F1dbdB0615fF42019Cf"
_ASSET = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
_MORPHO = "0x6c247b1F6182318877311737BaC0844bAa518F5e"
_ACCOUNT = "0x1000000000000000000000000000000000000000"
_MARKET_A = "0x" + "11" * 32
_MARKET_B = "0x" + "22" * 32
_MARKET_C = "0x" + "33" * 32


class TestMetaMorphoV1Client:
    def test_read_snapshot_reads_queues_configs_and_lost_assets(self) -> None:
        client = _FakeMetaMorphoV1Client(
            _FakeMetaMorphoContract(
                supply_queue=[_MARKET_A, _MARKET_B],
                withdraw_queue=[_MARKET_B, _MARKET_A],
                configs={
                    _MARKET_A: (1_000_000, True, 0),
                    _MARKET_B: (0, False, 1_800_000_000),
                    _MARKET_C: (500, True, 0),
                },
                pending_caps={
                    _MARKET_A: (0, 0),
                    _MARKET_B: (2_000_000, 1_800_000_100),
                    _MARKET_C: (0, 0),
                },
            )
        )

        snapshot = client.read_snapshot(extra_market_ids=[_MARKET_C, _MARKET_A.upper()])

        assert snapshot.vault == _VAULT
        assert snapshot.asset == _ASSET
        assert snapshot.morpho == _MORPHO
        assert snapshot.supply_queue == (_MARKET_A, _MARKET_B)
        assert snapshot.withdraw_queue == (_MARKET_B, _MARKET_A)
        assert snapshot.market_ids == (_MARKET_A, _MARKET_B)
        assert snapshot.last_total_assets == 123_000_000
        assert snapshot.lost_assets == 42
        assert snapshot.has_lost_assets
        assert snapshot.erc4626_limits is None
        assert snapshot.market_configs == (
            MetaMorphoMarketConfig(
                market_id=_MARKET_A,
                cap=1_000_000,
                enabled=True,
                removable_at=0,
                pending_cap_value=0,
                pending_cap_valid_at=0,
            ),
            MetaMorphoMarketConfig(
                market_id=_MARKET_B,
                cap=0,
                enabled=False,
                removable_at=1_800_000_000,
                pending_cap_value=2_000_000,
                pending_cap_valid_at=1_800_000_100,
            ),
            MetaMorphoMarketConfig(
                market_id=_MARKET_C,
                cap=500,
                enabled=True,
                removable_at=0,
                pending_cap_value=0,
                pending_cap_valid_at=0,
            ),
        )
        assert snapshot.market_configs[0].supply_enabled
        assert not snapshot.market_configs[1].supply_enabled
        assert snapshot.market_configs[1].has_pending_cap

    def test_read_market_config_normalizes_uppercase_market_id(self) -> None:
        client = _FakeMetaMorphoV1Client(
            _FakeMetaMorphoContract(
                supply_queue=[],
                withdraw_queue=[],
                configs={_MARKET_A: (1, True, 2)},
                pending_caps={_MARKET_A: (3, 4)},
            )
        )

        config = client.read_market_config(_MARKET_A.upper())

        assert config == MetaMorphoMarketConfig(
            market_id=_MARKET_A,
            cap=1,
            enabled=True,
            removable_at=2,
            pending_cap_value=3,
            pending_cap_valid_at=4,
        )

    def test_read_snapshot_can_include_erc4626_limits_for_hot_path_sizing(self) -> None:
        client = _FakeMetaMorphoV1Client(
            _FakeMetaMorphoContract(
                supply_queue=[],
                withdraw_queue=[],
                configs={},
                pending_caps={},
            )
        )

        snapshot = client.read_snapshot(erc4626_account=_ACCOUNT)

        assert snapshot.erc4626_limits == MetaMorphoErc4626Limits(
            account=_ACCOUNT,
            max_deposit_assets=1_000_000_000,
            max_withdraw_assets=250_000_000,
        )

    def test_read_erc4626_limits_normalizes_account(self) -> None:
        client = _FakeMetaMorphoV1Client(
            _FakeMetaMorphoContract(
                supply_queue=[],
                withdraw_queue=[],
                configs={},
                pending_caps={},
            )
        )

        assert client.read_erc4626_limits(_ACCOUNT.upper()) == MetaMorphoErc4626Limits(
            account=_ACCOUNT,
            max_deposit_assets=1_000_000_000,
            max_withdraw_assets=250_000_000,
        )


class _FakeMetaMorphoV1Client(MetaMorphoV1Client):
    def __init__(self, contract: _FakeMetaMorphoContract) -> None:
        self.contract = contract
        super().__init__(_VAULT, "http://localhost:8545")

    def _contract(self) -> _FakeMetaMorphoContract:
        return self.contract


class _FakeContractCall:
    def __init__(self, value: object) -> None:
        self.value = value

    def call(self) -> object:
        return self.value


class _FakeMetaMorphoFunctions:
    def __init__(
        self,
        *,
        supply_queue: list[str],
        withdraw_queue: list[str],
        configs: dict[str, tuple[int, bool, int]],
        pending_caps: dict[str, tuple[int, int]],
    ) -> None:
        self._supply_queue = supply_queue
        self._withdraw_queue = withdraw_queue
        self._configs = {key.lower(): value for key, value in configs.items()}
        self._pending_caps = {key.lower(): value for key, value in pending_caps.items()}

    def asset(self) -> _FakeContractCall:
        return _FakeContractCall(_ASSET)

    def MORPHO(self) -> _FakeContractCall:  # noqa: N802
        return _FakeContractCall(_MORPHO)

    def supplyQueueLength(self) -> _FakeContractCall:  # noqa: N802
        return _FakeContractCall(len(self._supply_queue))

    def supplyQueue(self, index: int) -> _FakeContractCall:  # noqa: N802
        return _FakeContractCall(bytes.fromhex(self._supply_queue[index].removeprefix("0x")))

    def withdrawQueueLength(self) -> _FakeContractCall:  # noqa: N802
        return _FakeContractCall(len(self._withdraw_queue))

    def withdrawQueue(self, index: int) -> _FakeContractCall:  # noqa: N802
        return _FakeContractCall(bytes.fromhex(self._withdraw_queue[index].removeprefix("0x")))

    def config(self, market_id: bytes) -> _FakeContractCall:
        return _FakeContractCall(self._configs["0x" + market_id.hex()])

    def pendingCap(self, market_id: bytes) -> _FakeContractCall:  # noqa: N802
        return _FakeContractCall(self._pending_caps["0x" + market_id.hex()])

    def lastTotalAssets(self) -> _FakeContractCall:  # noqa: N802
        return _FakeContractCall(123_000_000)

    def lostAssets(self) -> _FakeContractCall:  # noqa: N802
        return _FakeContractCall(42)

    def maxDeposit(self, receiver: str) -> _FakeContractCall:  # noqa: N802
        assert receiver == _ACCOUNT
        return _FakeContractCall(1_000_000_000)

    def maxWithdraw(self, owner: str) -> _FakeContractCall:  # noqa: N802
        assert owner == _ACCOUNT
        return _FakeContractCall(250_000_000)


class _FakeMetaMorphoContract:
    def __init__(
        self,
        *,
        supply_queue: list[str],
        withdraw_queue: list[str],
        configs: dict[str, tuple[int, bool, int]],
        pending_caps: dict[str, tuple[int, int]],
    ) -> None:
        self.functions = _FakeMetaMorphoFunctions(
            supply_queue=supply_queue,
            withdraw_queue=withdraw_queue,
            configs=configs,
            pending_caps=pending_caps,
        )
