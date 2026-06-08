"""Sync provider backend adapters and facade."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Self, cast

if TYPE_CHECKING:
    from hexbytes import HexBytes

    from degenbot.provider.offline_provider import OfflineProvider
    from degenbot.provider.protocols import ProviderBackend


class _Web3Adapter:
    """Adapter wrapping a web3.py Web3 instance."""

    def __init__(self, w3: Any) -> None:
        self._w3 = w3

    @property
    def chain_id(self) -> int:
        return cast("int", self._w3.eth.chain_id)

    @property
    def block_number(self) -> int:
        return cast("int", self._w3.eth.block_number)

    def get_block_number(self) -> int:
        return cast("int", self._w3.eth.get_block_number())

    def get_block(self, block_identifier: int | str) -> dict[str, Any] | None:
        return cast("dict[str, Any] | None", self._w3.eth.get_block(block_identifier))

    def get_logs(
        self,
        from_block: int,
        to_block: int,
        addresses: list[str] | None = None,
        topics: list[list[str]] | None = None,
    ) -> list[dict[str, Any]]:
        filter_param: dict[str, Any] = {"fromBlock": from_block, "toBlock": to_block}
        if addresses:
            filter_param["address"] = addresses
        if topics:
            filter_param["topics"] = topics
        return cast("list[dict[str, Any]]", self._w3.eth.get_logs(filter_param))

    def call(self, to: str, data: bytes, block: int | None = None) -> HexBytes:
        tx: dict[str, Any] = {"to": to, "data": data}
        if block is None:
            return cast("HexBytes", self._w3.eth.call(tx))
        return cast("HexBytes", self._w3.eth.call(tx, block))

    def call_raw(self, tx: dict[str, Any], block: int | None = None) -> HexBytes:
        if block is None:
            return cast("HexBytes", self._w3.eth.call(tx))
        return cast("HexBytes", self._w3.eth.call(tx, block))

    def get_code(self, address: str, block: int | None = None) -> HexBytes:
        if block is None:
            return cast("HexBytes", self._w3.eth.get_code(address))
        return cast("HexBytes", self._w3.eth.get_code(address, block))

    def get_balance(self, address: str, block: int | None = None) -> int:
        if block is None:
            return cast("int", self._w3.eth.get_balance(address))
        return cast("int", self._w3.eth.get_balance(address, block))

    def get_storage_at(self, address: str, position: int, block: int | None = None) -> HexBytes:
        if block is None:
            return cast("HexBytes", self._w3.eth.get_storage_at(address, position))
        return cast("HexBytes", self._w3.eth.get_storage_at(address, position, block))

    def get_transaction_count(self, address: str, block: int | None = None) -> int:
        if block is None:
            return cast("int", self._w3.eth.get_transaction_count(address))
        return cast("int", self._w3.eth.get_transaction_count(address, block))

    def is_connected(self) -> bool:
        return cast("bool", self._w3.is_connected())

    def close(self) -> None:
        if hasattr(self._w3, "close"):
            self._w3.close()


class _AlloyAdapter:
    """Adapter wrapping a degenbot AlloyProvider instance."""

    def __init__(self, alloy: Any) -> None:
        self._alloy = alloy

    @property
    def chain_id(self) -> int:
        chain_id = getattr(self._alloy, "chain_id", None)
        if chain_id is not None:
            return cast("int", chain_id)
        return cast("int", self._alloy.get_chain_id())

    @property
    def block_number(self) -> int:
        block_number = getattr(self._alloy, "block_number", None)
        if block_number is not None:
            return cast("int", block_number)
        return cast("int", self._alloy.get_block_number())

    def get_block_number(self) -> int:
        return cast("int", self._alloy.get_block_number())

    def get_block(self, block_identifier: int | str) -> dict[str, Any] | None:
        if isinstance(block_identifier, str):
            if block_identifier == "latest":
                block_identifier = self._alloy.get_block_number()
            elif block_identifier == "earliest":
                block_identifier = 0
            elif block_identifier == "pending":
                block_identifier = self._alloy.get_block_number() + 1
        return cast("dict[str, Any] | None", self._alloy.get_block(block_identifier))

    def get_logs(
        self,
        from_block: int,
        to_block: int,
        addresses: list[str] | None = None,
        topics: list[list[str]] | None = None,
    ) -> list[dict[str, Any]]:
        return cast(
            "list[dict[str, Any]]",
            self._alloy.get_logs(
                from_block=from_block,
                to_block=to_block,
                addresses=addresses,
                topics=topics,
            ),
        )

    def call(self, to: str, data: bytes, block: int | None = None) -> HexBytes:
        return cast("HexBytes", self._alloy.call(to, data, block_number=block))

    def call_raw(self, tx: dict[str, Any], block: int | None = None) -> HexBytes:
        return cast("HexBytes", self._alloy.call(tx["to"], tx["data"], block_number=block))

    def get_code(self, address: str, block: int | None = None) -> HexBytes:
        return cast("HexBytes", self._alloy.get_code(address, block_number=block))

    def get_balance(self, address: str, block: int | None = None) -> int:
        return cast("int", self._alloy.get_balance(address, block_number=block))

    def get_storage_at(self, address: str, position: int, block: int | None = None) -> HexBytes:
        return cast("HexBytes", self._alloy.get_storage_at(address, position, block_number=block))

    def get_transaction_count(self, address: str, block: int | None = None) -> int:
        return cast("int", self._alloy.get_transaction_count(address, block_number=block))

    def is_connected(self) -> bool:
        return True

    def close(self) -> None:
        if hasattr(self._alloy, "close"):
            self._alloy.close()


class _OfflineAdapter:
    """Adapter wrapping an OfflineProvider instance."""

    def __init__(self, offline: OfflineProvider) -> None:
        self._offline = offline

    @property
    def chain_id(self) -> int:
        return self._offline.chain_id

    @property
    def block_number(self) -> int:
        return self._offline.block_number

    def get_block_number(self) -> int:
        return self._offline.get_block_number()

    def get_block(self, block_identifier: int | str) -> dict[str, Any] | None:
        return self._offline.get_block(block_identifier)

    def get_logs(
        self,
        from_block: int,
        to_block: int,
        addresses: list[str] | None = None,
        topics: list[list[str]] | None = None,
    ) -> list[dict[str, Any]]:
        return self._offline.get_logs(
            from_block=from_block,
            to_block=to_block,
            addresses=addresses,
            topics=topics,
        )

    def call(self, to: str, data: bytes, block: int | None = None) -> HexBytes:
        return self._offline.call(to, data, block_number=block)

    def call_raw(self, tx: dict[str, Any], block: int | None = None) -> HexBytes:
        return self._offline.call(tx["to"], tx["data"], block_number=block)

    def get_code(self, address: str, block: int | None = None) -> HexBytes:
        return self._offline.get_code(address, block_number=block)

    def get_balance(self, address: str, block: int | None = None) -> int:
        return self._offline.get_balance(address, block_number=block)

    def get_storage_at(self, address: str, position: int, block: int | None = None) -> HexBytes:
        return self._offline.get_storage_at(address, position, block_number=block)

    def get_transaction_count(self, address: str, block: int | None = None) -> int:
        return self._offline.get_transaction_count(address, block_number=block)

    def is_connected(self) -> bool:
        return True

    def close(self) -> None:
        if hasattr(self._offline, "close"):
            self._offline.close()


class ProviderAdapter:  # noqa: PLR0904
    """Uniform sync facade over Web3, AlloyProvider, or OfflineProvider."""

    def __init__(
        self,
        backend: ProviderBackend,
        *,
        provider_type: Literal["web3", "alloy", "offline"],
        raw_provider: Any,
    ) -> None:
        self._backend = backend
        self._provider_type = provider_type
        self._raw_provider = raw_provider

    @classmethod
    def from_web3(cls, w3: Any) -> Self:
        return cls(_Web3Adapter(w3), provider_type="web3", raw_provider=w3)

    @classmethod
    def from_alloy(cls, alloy: Any) -> Self:
        return cls(_AlloyAdapter(alloy), provider_type="alloy", raw_provider=alloy)

    @classmethod
    def from_offline(cls, offline: OfflineProvider) -> Self:
        return cls(_OfflineAdapter(offline), provider_type="offline", raw_provider=offline)

    @property
    def provider_type(self) -> Literal["web3", "alloy", "offline"]:
        return self._provider_type

    @property
    def underlying(self) -> Any:
        return self._raw_provider

    @property
    def provider(self) -> Any:
        return self._raw_provider

    def set_provider(self, provider: Any) -> None:
        self._backend = _backend_for_type(self._provider_type, provider)
        self._raw_provider = provider

    def as_web3(self) -> Any | None:
        return self._raw_provider if self._provider_type == "web3" else None

    def as_alloy(self) -> Any | None:
        return self._raw_provider if self._provider_type == "alloy" else None

    def as_offline(self) -> OfflineProvider | None:
        if self._provider_type == "offline":
            return cast("OfflineProvider", self._raw_provider)
        return None

    @property
    def chain_id(self) -> int:
        return self._backend.chain_id

    @property
    def block_number(self) -> int:
        return self._backend.block_number

    def get_block_number(self) -> int:
        return self._backend.get_block_number()

    def get_block(
        self,
        block_identifier: int | str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        if block_identifier is None:
            block_identifier = kwargs.pop("block_identifier", "latest")
        return self._backend.get_block(block_identifier)

    def get_logs(
        self,
        from_block: int,
        to_block: int,
        addresses: list[str] | None = None,
        topics: list[list[str]] | None = None,
    ) -> list[dict[str, Any]]:
        return self._backend.get_logs(from_block, to_block, addresses, topics)

    def call(self, to: str, data: bytes, block: int | None = None) -> HexBytes:
        return self._backend.call(to, data, block)

    def call_raw(self, tx: dict[str, Any], block: int | None = None) -> HexBytes:
        return self._backend.call_raw(tx, block)

    def batch_call(self, calls: list[dict[str, Any]], block: int | None = None) -> list[HexBytes]:
        return [self.call_raw(tx, block) for tx in calls]

    def get_block_timestamp(self, block: int | None = None) -> int:
        block_data = self.get_block(block if block is not None else "latest")
        if block_data is None:
            msg = f"Block {block} not found"
            raise ValueError(msg)
        return cast("int", block_data["timestamp"])

    def make_request(self, method: str, params: list[Any]) -> Any:
        raw_provider = self._raw_provider
        if hasattr(raw_provider, "make_request"):
            return raw_provider.make_request(method, params)
        msg = f"Provider type '{self._provider_type}' does not support make_request"
        raise AttributeError(msg)

    def get_code(self, address: str, block: int | None = None) -> HexBytes:
        return self._backend.get_code(address, block)

    def get_balance(self, address: str, block: int | None = None) -> int:
        return self._backend.get_balance(address, block)

    def get_storage_at(self, address: str, position: int, block: int | None = None) -> HexBytes:
        return self._backend.get_storage_at(address, position, block)

    def get_transaction_count(self, address: str, block: int | None = None) -> int:
        return self._backend.get_transaction_count(address, block)

    def is_connected(self) -> bool:
        return self._backend.is_connected()

    def close(self) -> None:
        self._backend.close()

    def __getstate__(self) -> dict[str, Any]:
        return {
            "_provider_type": self._provider_type,
            "_backend": None,
            "_raw_provider": None,
        }

    def __setstate__(self, state: dict[str, Any]) -> None:
        self.__dict__ = state

    def __repr__(self) -> str:
        return f"ProviderAdapter(type={self._provider_type})"


def _backend_for_type(
    provider_type: Literal["web3", "alloy", "offline"],
    provider: Any,
) -> ProviderBackend:
    match provider_type:
        case "web3":
            return _Web3Adapter(provider)
        case "alloy":
            return _AlloyAdapter(provider)
        case "offline":
            return _OfflineAdapter(cast("OfflineProvider", provider))
        case _:
            msg = f"Unknown provider type: {provider_type}"
            raise ValueError(msg)


__all__ = [
    "ProviderAdapter",
    "_AlloyAdapter",
    "_OfflineAdapter",
    "_Web3Adapter",
]
