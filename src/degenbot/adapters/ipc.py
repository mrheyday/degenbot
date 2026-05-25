"""IPC discriminator sets derived from adapter templates."""

from __future__ import annotations

from degenbot.adapters.registry import ALL_ADAPTERS


def _union(attr: str) -> frozenset[str]:
    values: set[str] = set()
    for adapter in ALL_ADAPTERS:
        values.update(getattr(adapter, attr))
    return frozenset(values)


ADDRESS_KEYED_DEGENBOT_DEX_KINDS = _union("ipc_address_keyed_kinds")
POOL_ID_REQUIRED_DEX_KINDS = _union("ipc_pool_id_required_kinds")
RECOGNIZED_DEX_KINDS = frozenset({
    *ADDRESS_KEYED_DEGENBOT_DEX_KINDS,
    *POOL_ID_REQUIRED_DEX_KINDS,
    *_union("ipc_recognized_kinds"),
})


def is_address_keyed_degenbot_kind(dex: str) -> bool:
    """True iff `dex` can resolve through degenbot pool_registry by address."""
    return dex in ADDRESS_KEYED_DEGENBOT_DEX_KINDS


def is_pool_id_required_kind(dex: str) -> bool:
    """True iff `dex` requires pool-id keyed lookup."""
    return dex in POOL_ID_REQUIRED_DEX_KINDS


def is_recognized_dex_kind(dex: str) -> bool:
    """True iff the IPC layer recognizes the discriminator."""
    return dex in RECOGNIZED_DEX_KINDS
