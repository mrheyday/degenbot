"""Tests for the IPC discriminator-set helpers."""

from __future__ import annotations

from degenbot.adapters import ipc


def test_address_keyed_kinds_is_a_subset_of_recognized_kinds() -> None:
    assert ipc.ADDRESS_KEYED_DEGENBOT_DEX_KINDS <= ipc.RECOGNIZED_DEX_KINDS


def test_pool_id_required_kinds_is_a_subset_of_recognized_kinds() -> None:
    assert ipc.POOL_ID_REQUIRED_DEX_KINDS <= ipc.RECOGNIZED_DEX_KINDS


def test_is_address_keyed_degenbot_kind_matches_the_set() -> None:
    for dex in ipc.ADDRESS_KEYED_DEGENBOT_DEX_KINDS:
        assert ipc.is_address_keyed_degenbot_kind(dex) is True
    assert ipc.is_address_keyed_degenbot_kind("definitely-not-a-dex-kind") is False


def test_is_pool_id_required_kind_matches_the_set() -> None:
    for dex in ipc.POOL_ID_REQUIRED_DEX_KINDS:
        assert ipc.is_pool_id_required_kind(dex) is True
    assert ipc.is_pool_id_required_kind("definitely-not-a-dex-kind") is False


def test_is_recognized_dex_kind_covers_both_keyed_families() -> None:
    for dex in ipc.ADDRESS_KEYED_DEGENBOT_DEX_KINDS | ipc.POOL_ID_REQUIRED_DEX_KINDS:
        assert ipc.is_recognized_dex_kind(dex) is True
    assert ipc.is_recognized_dex_kind("definitely-not-a-dex-kind") is False
