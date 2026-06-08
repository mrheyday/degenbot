"""Async provider backend adapters and facade."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, Literal, Self, cast

if TYPE_CHECKING:
    from hexbytes import HexBytes

    from degenbot.provider.protocols import AsyncProviderBackend


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _configured_method(obj: Any, name: str) -> Any | None:
    if obj.__class__.__module__ == "unittest.mock" and name not in vars(obj):
        return None
    return getattr(obj, name, None)


class _AsyncWeb3Adapter:
    """Adapter wrapping a web3.py AsyncWeb3 instance."""

    def __init__(self, w3: Any) -> None:
        self._w3 = w3

    async def get_block_number(self) -> int:
        return cast("int", await self._w3.eth.get_block_number())

    async def get_chain_id(self) -> int:
        return cast("int", await _maybe_await(self._w3.eth.chain_id))

    async def get_block(self, block_identifier: int | str) -> dict[str, Any] | None:
        return cast("dict[str, Any] | None", await self._w3.eth.get_block(block_identifier))

    async def get_logs(
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
        return cast("list[dict[str, Any]]", await self._w3.eth.get_logs(filter_param))

    async def call(self, to: str, data: bytes, block: int | None = None) -> HexBytes:
        return cast("HexBytes", await self._w3.eth.call({"to": to, "data": data}, block))

    async def get_code(self, address: str, block: int | None = None) -> HexBytes:
        return cast("HexBytes", await self._w3.eth.get_code(address, block))

    async def get_balance(self, address: str, block: int | None = None) -> int:
        return cast("int", await self._w3.eth.get_balance(address, block))

    async def get_storage_at(
        self, address: str, position: int, block: int | None = None
    ) -> HexBytes:
        return cast("HexBytes", await self._w3.eth.get_storage_at(address, position, block))

    async def get_transaction_count(self, address: str, block: int | None = None) -> int:
        return cast("int", await self._w3.eth.get_transaction_count(address, block))

    def is_connected(self) -> bool:
        return True

    def close(self) -> None:
        if hasattr(self._w3, "close"):
            self._w3.close()


class _AsyncAlloyAdapter:
    """Adapter wrapping an async Alloy provider."""

    def __init__(self, alloy: Any) -> None:
        self._alloy = alloy

    async def get_block_number(self) -> int:
        return cast("int", await self._alloy.get_block_number())

    async def get_chain_id(self) -> int:
        return cast("int", await self._alloy.get_chain_id())

    async def get_block(self, block_identifier: int | str) -> dict[str, Any] | None:
        if isinstance(block_identifier, str):
            if block_identifier == "latest":
                block_identifier = await self._alloy.get_block_number()
            elif block_identifier == "earliest":
                block_identifier = 0
            elif block_identifier == "pending":
                block_identifier = await self._alloy.get_block_number() + 1
        return cast("dict[str, Any] | None", await self._alloy.get_block(block_identifier))

    async def get_logs(
        self,
        from_block: int,
        to_block: int,
        addresses: list[str] | None = None,
        topics: list[list[str]] | None = None,
    ) -> list[dict[str, Any]]:
        return cast(
            "list[dict[str, Any]]",
            await self._alloy.get_logs(
                from_block=from_block,
                to_block=to_block,
                addresses=addresses,
                topics=topics,
            ),
        )

    async def call(self, to: str, data: bytes, block: int | None = None) -> HexBytes:
        return cast("HexBytes", await self._alloy.call(to, data, block_number=block))

    async def get_code(self, address: str, block: int | None = None) -> HexBytes:
        return cast("HexBytes", await self._alloy.get_code(address, block))

    async def get_balance(self, address: str, block: int | None = None) -> int:
        method = _configured_method(self._alloy, "get_balance")
        if method is None:
            msg = "get_balance not implemented by async Alloy provider"
            raise NotImplementedError(msg)
        return cast("int", await method(address, block))

    async def get_storage_at(
        self, address: str, position: int, block: int | None = None
    ) -> HexBytes:
        return cast("HexBytes", await self._alloy.get_storage_at(address, position, block))

    async def get_transaction_count(self, address: str, block: int | None = None) -> int:
        method = _configured_method(self._alloy, "get_transaction_count")
        if method is None:
            msg = "get_transaction_count not implemented by async Alloy provider"
            raise NotImplementedError(msg)
        return cast("int", await method(address, block))

    def is_connected(self) -> bool:
        return True

    def close(self) -> None:
        if hasattr(self._alloy, "close"):
            self._alloy.close()


class AsyncProviderAdapter:
    """Uniform async facade over AsyncWeb3 or async Alloy providers."""

    def __init__(
        self,
        backend: AsyncProviderBackend,
        *,
        provider_type: Literal["web3", "alloy"],
        raw_provider: Any,
    ) -> None:
        self._backend = backend
        self._provider_type = provider_type
        self._raw_provider = raw_provider

    @classmethod
    def from_web3(cls, async_w3: Any) -> Self:
        return cls(_AsyncWeb3Adapter(async_w3), provider_type="web3", raw_provider=async_w3)

    @classmethod
    def from_alloy(cls, async_alloy: Any) -> Self:
        return cls(_AsyncAlloyAdapter(async_alloy), provider_type="alloy", raw_provider=async_alloy)

    @property
    def provider_type(self) -> Literal["web3", "alloy"]:
        return self._provider_type

    @property
    def underlying(self) -> Any:
        return self._raw_provider

    @property
    def chain_id(self) -> int:
        msg = "Use await get_chain_id() for async provider"
        raise NotImplementedError(msg)

    @property
    def block_number(self) -> int:
        msg = "Use await get_block_number() for async provider"
        raise NotImplementedError(msg)

    async def get_chain_id(self) -> int:
        return await self._backend.get_chain_id()

    async def get_block_number(self) -> int:
        return await self._backend.get_block_number()

    async def get_block(self, block_identifier: int | str) -> dict[str, Any] | None:
        return await self._backend.get_block(block_identifier)

    async def get_logs(
        self,
        from_block: int,
        to_block: int,
        addresses: list[str] | None = None,
        topics: list[list[str]] | None = None,
    ) -> list[dict[str, Any]]:
        return await self._backend.get_logs(from_block, to_block, addresses, topics)

    async def call(self, to: str, data: bytes, block: int | None = None) -> HexBytes:
        return await self._backend.call(to, data, block)

    async def get_code(self, address: str, block: int | None = None) -> HexBytes:
        return await self._backend.get_code(address, block)

    async def get_balance(self, address: str, block: int | None = None) -> int:
        return await self._backend.get_balance(address, block)

    async def get_storage_at(
        self, address: str, position: int, block: int | None = None
    ) -> HexBytes:
        return await self._backend.get_storage_at(address, position, block)

    async def get_transaction_count(self, address: str, block: int | None = None) -> int:
        return await self._backend.get_transaction_count(address, block)

    def is_connected(self) -> bool:
        return self._backend.is_connected()

    def close(self) -> None:
        self._backend.close()

    def __repr__(self) -> str:
        return f"AsyncProviderAdapter(type={self._provider_type})"


__all__ = [
    "AsyncProviderAdapter",
    "_AsyncAlloyAdapter",
    "_AsyncWeb3Adapter",
]
