"""Backward-compatible provider interface exports.

The provider adapter implementation is split across focused modules:
``protocols`` for runtime-checkable provider contracts, ``sync_adapter`` for
sync providers, and ``async_adapter`` for async providers. This module remains
the stable import path for older code.
"""

from degenbot.provider.async_adapter import (
    AsyncProviderAdapter,
    _AsyncAlloyAdapter,
    _AsyncWeb3Adapter,
)
from degenbot.provider.protocols import AsyncProviderBackend, EthereumProvider, ProviderBackend
from degenbot.provider.sync_adapter import (
    ProviderAdapter,
    _AlloyAdapter,
    _OfflineAdapter,
    _Web3Adapter,
)

__all__ = [
    "AsyncProviderAdapter",
    "AsyncProviderBackend",
    "EthereumProvider",
    "ProviderAdapter",
    "ProviderBackend",
    "_AlloyAdapter",
    "_AsyncAlloyAdapter",
    "_AsyncWeb3Adapter",
    "_OfflineAdapter",
    "_Web3Adapter",
]
