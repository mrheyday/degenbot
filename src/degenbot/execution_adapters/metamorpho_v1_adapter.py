"""Read-only MetaMorpho V1.1 vault adapter.

MetaMorpho V1.1 is not a liquidation entrypoint. This adapter exists to
discover vault allocation queues, market caps, pending caps, and lost-assets
state so the solver can rank Morpho liquidity sources and avoid vaults with
operational risk signals.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, cast

import structlog
from web3 import Web3

logger = structlog.get_logger(__name__).bind(
    service="solver",
    component="execution.metamorpho_v1_adapter",
)

_BYTES32_BYTES = 32
_METAMORPHO_V1_ABI: list[dict[str, object]] = [
    {
        "type": "function",
        "name": "asset",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "address"}],
    },
    {
        "type": "function",
        "name": "MORPHO",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "address"}],
    },
    {
        "type": "function",
        "name": "supplyQueueLength",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "type": "function",
        "name": "supplyQueue",
        "stateMutability": "view",
        "inputs": [{"name": "", "type": "uint256"}],
        "outputs": [{"name": "", "type": "bytes32"}],
    },
    {
        "type": "function",
        "name": "withdrawQueueLength",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "type": "function",
        "name": "withdrawQueue",
        "stateMutability": "view",
        "inputs": [{"name": "", "type": "uint256"}],
        "outputs": [{"name": "", "type": "bytes32"}],
    },
    {
        "type": "function",
        "name": "config",
        "stateMutability": "view",
        "inputs": [{"name": "", "type": "bytes32"}],
        "outputs": [
            {"name": "cap", "type": "uint184"},
            {"name": "enabled", "type": "bool"},
            {"name": "removableAt", "type": "uint64"},
        ],
    },
    {
        "type": "function",
        "name": "pendingCap",
        "stateMutability": "view",
        "inputs": [{"name": "", "type": "bytes32"}],
        "outputs": [
            {"name": "value", "type": "uint192"},
            {"name": "validAt", "type": "uint64"},
        ],
    },
    {
        "type": "function",
        "name": "lastTotalAssets",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "type": "function",
        "name": "lostAssets",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "type": "function",
        "name": "maxDeposit",
        "stateMutability": "view",
        "inputs": [{"name": "receiver", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "type": "function",
        "name": "maxWithdraw",
        "stateMutability": "view",
        "inputs": [{"name": "owner", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
    },
]


class _ContractCall(Protocol):
    def call(self) -> object: ...


class _MetaMorphoV1Functions(Protocol):
    def asset(self) -> _ContractCall: ...
    def MORPHO(self) -> _ContractCall: ...  # noqa: N802
    def supplyQueueLength(self) -> _ContractCall: ...  # noqa: N802
    def supplyQueue(self, index: int) -> _ContractCall: ...  # noqa: N802
    def withdrawQueueLength(self) -> _ContractCall: ...  # noqa: N802
    def withdrawQueue(self, index: int) -> _ContractCall: ...  # noqa: N802
    def config(self, market_id: bytes) -> _ContractCall: ...
    def pendingCap(self, market_id: bytes) -> _ContractCall: ...  # noqa: N802
    def lastTotalAssets(self) -> _ContractCall: ...  # noqa: N802
    def lostAssets(self) -> _ContractCall: ...  # noqa: N802
    def maxDeposit(self, receiver: str) -> _ContractCall: ...  # noqa: N802
    def maxWithdraw(self, owner: str) -> _ContractCall: ...  # noqa: N802


class _MetaMorphoV1Contract(Protocol):
    functions: _MetaMorphoV1Functions


@dataclass(frozen=True)
class MetaMorphoMarketConfig:
    """MetaMorpho V1.1 per-market allocation config."""

    market_id: str
    cap: int
    enabled: bool
    removable_at: int
    pending_cap_value: int
    pending_cap_valid_at: int

    @property
    def has_pending_cap(self) -> bool:
        return self.pending_cap_valid_at != 0

    @property
    def supply_enabled(self) -> bool:
        return self.enabled and self.cap > 0


@dataclass(frozen=True)
class MetaMorphoErc4626Limits:
    """ERC4626 sizing limits for one receiver/owner address."""

    account: str
    max_deposit_assets: int
    max_withdraw_assets: int


@dataclass(frozen=True)
class MetaMorphoVaultSnapshot:
    """MetaMorpho V1.1 vault state relevant to liquidity/risk ranking."""

    vault: str
    asset: str
    morpho: str
    supply_queue: tuple[str, ...]
    withdraw_queue: tuple[str, ...]
    last_total_assets: int
    lost_assets: int
    market_configs: tuple[MetaMorphoMarketConfig, ...]
    erc4626_limits: MetaMorphoErc4626Limits | None = None

    @property
    def has_lost_assets(self) -> bool:
        return self.lost_assets > 0

    @property
    def market_ids(self) -> tuple[str, ...]:
        seen: set[str] = set()
        ordered: list[str] = []
        for market_id in (*self.supply_queue, *self.withdraw_queue):
            normalized = market_id.lower()
            if normalized not in seen:
                seen.add(normalized)
                ordered.append(market_id)
        return tuple(ordered)


class MetaMorphoV1Client:
    """Thin web3 read client for one MetaMorpho V1.1 vault."""

    def __init__(self, vault_address: str, rpc_url: str) -> None:
        self._vault_address = Web3.to_checksum_address(vault_address)
        self._rpc_url = rpc_url
        self._web3: Web3 | None = None
        self._log = logger.bind(vault_address=self._vault_address)

    def read_snapshot(
        self,
        *,
        extra_market_ids: list[str] | None = None,
        erc4626_account: str | None = None,
    ) -> MetaMorphoVaultSnapshot:
        """Read queues, vault accounting fields, and per-market config."""
        contract = self._contract()
        supply_queue = self._read_queue(contract, "supply")
        withdraw_queue = self._read_queue(contract, "withdraw")
        market_ids = _dedupe_market_ids(
            [
                *supply_queue,
                *withdraw_queue,
                *(extra_market_ids or []),
            ]
        )
        return MetaMorphoVaultSnapshot(
            vault=self._vault_address,
            asset=Web3.to_checksum_address(cast("str", contract.functions.asset().call())),
            morpho=Web3.to_checksum_address(cast("str", contract.functions.MORPHO().call())),
            supply_queue=supply_queue,
            withdraw_queue=withdraw_queue,
            last_total_assets=int(cast("int | str", contract.functions.lastTotalAssets().call())),
            lost_assets=int(cast("int | str", contract.functions.lostAssets().call())),
            market_configs=tuple(self.read_market_config(market_id) for market_id in market_ids),
            erc4626_limits=(self.read_erc4626_limits(erc4626_account) if erc4626_account is not None else None),
        )

    def read_erc4626_limits(self, account: str) -> MetaMorphoErc4626Limits:
        """Read ERC4626 `maxDeposit` and `maxWithdraw` for one account."""
        contract = self._contract()
        checksum_account = Web3.to_checksum_address(account)
        return MetaMorphoErc4626Limits(
            account=checksum_account,
            max_deposit_assets=int(cast("int | str", contract.functions.maxDeposit(checksum_account).call())),
            max_withdraw_assets=int(cast("int | str", contract.functions.maxWithdraw(checksum_account).call())),
        )

    def read_market_config(self, market_id: str) -> MetaMorphoMarketConfig:
        """Read cap/enabled/removal and pending-cap state for one market id."""
        contract = self._contract()
        market_id_bytes = _bytes32(market_id)
        cap, enabled, removable_at = cast(
            "tuple[int, bool, int]",
            contract.functions.config(market_id_bytes).call(),
        )
        pending_cap_value, pending_cap_valid_at = cast(
            "tuple[int, int]",
            contract.functions.pendingCap(market_id_bytes).call(),
        )
        return MetaMorphoMarketConfig(
            market_id=Web3.to_hex(market_id_bytes),
            cap=int(cap),
            enabled=bool(enabled),
            removable_at=int(removable_at),
            pending_cap_value=int(pending_cap_value),
            pending_cap_valid_at=int(pending_cap_valid_at),
        )

    def _read_queue(self, contract: _MetaMorphoV1Contract, queue: str) -> tuple[str, ...]:
        if queue == "supply":
            length = int(cast("int | str", contract.functions.supplyQueueLength().call()))
            return tuple(_bytes32_hex(contract.functions.supplyQueue(i).call()) for i in range(length))
        if queue == "withdraw":
            length = int(cast("int | str", contract.functions.withdrawQueueLength().call()))
            return tuple(_bytes32_hex(contract.functions.withdrawQueue(i).call()) for i in range(length))
        raise ValueError(f"unknown MetaMorpho queue: {queue}")

    def _contract(self) -> _MetaMorphoV1Contract:
        if self._web3 is None:
            self._web3 = Web3(Web3.HTTPProvider(self._rpc_url))
        return cast(
            "_MetaMorphoV1Contract",
            self._web3.eth.contract(address=self._vault_address, abi=_METAMORPHO_V1_ABI),
        )


def _dedupe_market_ids(market_ids: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for market_id in market_ids:
        normalized = market_id.lower()
        if normalized not in seen:
            seen.add(normalized)
            ordered.append(Web3.to_hex(_bytes32(market_id)))
    return tuple(ordered)


def _bytes32(value: str) -> bytes:
    raw = bytes.fromhex(value.lower().removeprefix("0x"))
    if len(raw) != _BYTES32_BYTES:
        raise ValueError(f"expected bytes32 hex string, got {value!r}")
    return raw


def _bytes32_hex(value: object) -> str:
    if isinstance(value, bytes):
        raw = value
    elif isinstance(value, str):
        raw = _bytes32(value)
    else:
        raise ValueError(f"expected bytes32 return value, got {value!r}")
    return Web3.to_hex(raw)
