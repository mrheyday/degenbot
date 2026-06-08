"""Provider protocols for sync and async Ethereum RPC backends."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from hexbytes import HexBytes


@runtime_checkable
class ProviderBackend(Protocol):
    """Protocol for sync Ethereum RPC provider backends."""

    @property
    def chain_id(self) -> int:
        """Return the chain ID."""
        ...

    @property
    def block_number(self) -> int:
        """Return the latest block number."""
        ...

    def get_block_number(self) -> int:
        """Return the latest block number."""
        ...

    def get_block(self, block_identifier: int | str) -> dict[str, Any] | None:
        """Return block data for a block identifier."""
        ...

    def get_logs(
        self,
        from_block: int,
        to_block: int,
        addresses: list[str] | None = None,
        topics: list[list[str]] | None = None,
    ) -> list[dict[str, Any]]:
        """Return logs matching the filter."""
        ...

    def call(self, to: str, data: bytes, block: int | None = None) -> HexBytes:
        """Execute an eth_call."""
        ...

    def call_raw(self, tx: dict[str, Any], block: int | None = None) -> HexBytes:
        """Execute an eth_call with a raw transaction mapping."""
        ...

    def get_code(self, address: str, block: int | None = None) -> HexBytes:
        """Return contract bytecode."""
        ...

    def get_balance(self, address: str, block: int | None = None) -> int:
        """Return native token balance."""
        ...

    def get_storage_at(self, address: str, position: int, block: int | None = None) -> HexBytes:
        """Return storage at a slot."""
        ...

    def get_transaction_count(self, address: str, block: int | None = None) -> int:
        """Return account nonce."""
        ...

    def is_connected(self) -> bool:
        """Return connection status."""
        ...

    def close(self) -> None:
        """Close provider resources."""
        ...


EthereumProvider = ProviderBackend


@runtime_checkable
class AsyncProviderBackend(Protocol):
    """Protocol for async Ethereum RPC provider backends."""

    async def get_block_number(self) -> int:
        """Return the latest block number."""
        ...

    async def get_chain_id(self) -> int:
        """Return the chain ID."""
        ...

    async def get_block(self, block_identifier: int | str) -> dict[str, Any] | None:
        """Return block data for a block identifier."""
        ...

    async def get_logs(
        self,
        from_block: int,
        to_block: int,
        addresses: list[str] | None = None,
        topics: list[list[str]] | None = None,
    ) -> list[dict[str, Any]]:
        """Return logs matching the filter."""
        ...

    async def call(self, to: str, data: bytes, block: int | None = None) -> HexBytes:
        """Execute an eth_call."""
        ...

    async def get_code(self, address: str, block: int | None = None) -> HexBytes:
        """Return contract bytecode."""
        ...

    async def get_balance(self, address: str, block: int | None = None) -> int:
        """Return native token balance."""
        ...

    async def get_storage_at(
        self, address: str, position: int, block: int | None = None
    ) -> HexBytes:
        """Return storage at a slot."""
        ...

    async def get_transaction_count(self, address: str, block: int | None = None) -> int:
        """Return account nonce."""
        ...

    def is_connected(self) -> bool:
        """Return connection status."""
        ...

    def close(self) -> None:
        """Close provider resources."""
        ...


__all__ = ["AsyncProviderBackend", "EthereumProvider", "ProviderBackend"]
