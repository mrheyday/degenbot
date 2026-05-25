"""Tests for the canonical CoW Protocol core contract addresses."""

from __future__ import annotations

import re

from degenbot.orderbook import addresses

_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


def test_core_addresses_are_well_formed_20_byte_hex() -> None:
    for value in (
        addresses.GPV2_SETTLEMENT,
        addresses.GPV2_ALLOW_LIST_AUTHENTICATION,
        addresses.GPV2_VAULT_RELAYER,
    ):
        assert _ADDRESS_RE.match(value)


def test_typed_aliases_mirror_the_gpv2_constants() -> None:
    assert addresses.SETTLEMENT == addresses.GPV2_SETTLEMENT
    assert addresses.ALLOW_LIST_AUTHENTICATION == addresses.GPV2_ALLOW_LIST_AUTHENTICATION
    assert addresses.VAULT_RELAYER == addresses.GPV2_VAULT_RELAYER


def test_canonical_deployment_chain_list_includes_arbitrum_one() -> None:
    chains = addresses.CHAINS_WITH_CANONICAL_DEPLOYMENT
    assert "arbitrum_one" in chains
    # Sorted + de-duplicated so the list stays grep-stable.
    assert list(chains) == sorted(set(chains))
