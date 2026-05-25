"""Sanity tests for the Uniswap addresses module.

Mirror of `test_dodo_addresses.py`. Cheap-to-run gates that catch
copy-paste typos, accidental duplicates, and groupings drifting out of
sync with the underlying constants. No network access.
"""

from __future__ import annotations

from degenbot.execution import uniswap_addresses as u
from web3 import Web3

_ALL_ADDRESSES: list[tuple[str, str]] = [
    # Cross-protocol shared
    ("PERMIT2", u.PERMIT2),
    ("WETH9", u.WETH9),
    ("UNIVERSAL_ROUTER", u.UNIVERSAL_ROUTER),
    # V2
    ("V2_FACTORY", u.V2_FACTORY),
    ("V2_ROUTER02", u.V2_ROUTER02),
    # V3
    ("V3_FACTORY", u.V3_FACTORY),
    ("V3_TICK_LENS", u.V3_TICK_LENS),
    ("V3_QUOTER_V2", u.V3_QUOTER_V2),
    ("V3_SWAP_ROUTER02", u.V3_SWAP_ROUTER02),
    ("V3_NONFUNGIBLE_POSITION_MANAGER", u.V3_NONFUNGIBLE_POSITION_MANAGER),
    # V4
    ("V4_POOL_MANAGER", u.V4_POOL_MANAGER),
    ("V4_QUOTER", u.V4_QUOTER),
    ("V4_STATE_VIEW", u.V4_STATE_VIEW),
    ("V4_POSITION_MANAGER", u.V4_POSITION_MANAGER),
    ("V4_POSITION_DESCRIPTOR", u.V4_POSITION_DESCRIPTOR),
    # UniswapX
    ("UNISWAPX_DUTCH_V3_REACTOR", u.UNISWAPX_DUTCH_V3_REACTOR),
    ("UNISWAPX_ORDER_QUOTER", u.UNISWAPX_ORDER_QUOTER),
]


class TestEachAddressIsValid:
    """Each constant must be a valid 0x-prefixed 20-byte hex string. We
    don't enforce EIP-55 checksum casing here because the canonical
    Uniswap docs publish some addresses in all-lowercase (e.g., V4
    PoolManager, V4Quoter) — `is_address` accepts those, and forcing
    `is_checksum_address` would require us to deviate from the
    upstream docs' casing."""

    def test_every_constant_is_a_valid_address(self) -> None:
        for name, addr in _ALL_ADDRESSES:
            assert Web3.is_address(addr), f"{name}: {addr} is not a valid address"


class TestNoDuplicates:
    """No address should appear under two different names."""

    def test_all_addresses_are_mutually_distinct(self) -> None:
        # Lowercase to neutralize EIP-55 casing.
        seen: dict[str, str] = {}
        for name, addr in _ALL_ADDRESSES:
            key = addr.lower()
            assert key not in seen, f"duplicate address {addr}: assigned to {seen[key]} and {name}"
            seen[key] = name


class TestGroupings:
    """Convenience frozensets must agree with the underlying constants."""

    def test_factories_includes_v2_v3_and_v4_singletons(self) -> None:
        assert frozenset({u.V2_FACTORY, u.V3_FACTORY, u.V4_POOL_MANAGER}) == u.FACTORIES
        assert len(u.FACTORIES) == 3

    def test_v3_contracts_has_five_entries(self) -> None:
        assert len(u.V3_CONTRACTS) == 5
        assert u.V3_FACTORY in u.V3_CONTRACTS
        assert u.V3_QUOTER_V2 in u.V3_CONTRACTS
        assert u.V3_SWAP_ROUTER02 in u.V3_CONTRACTS

    def test_v4_contracts_has_five_entries(self) -> None:
        assert len(u.V4_CONTRACTS) == 5
        assert u.V4_POOL_MANAGER in u.V4_CONTRACTS
        assert u.V4_QUOTER in u.V4_CONTRACTS
        assert u.V4_STATE_VIEW in u.V4_CONTRACTS

    def test_uniswapx_contracts_has_two_entries(self) -> None:
        assert (
            frozenset(
                {u.UNISWAPX_DUTCH_V3_REACTOR, u.UNISWAPX_ORDER_QUOTER},
            )
            == u.UNISWAPX_CONTRACTS
        )

    def test_universal_router_not_in_v3_or_v4_groupings(self) -> None:
        """Universal Router is shared between V3 and V4 and intentionally
        kept out of the per-version groupings to avoid a membership
        check ambiguity in callers."""
        assert u.UNIVERSAL_ROUTER not in u.V3_CONTRACTS
        assert u.UNIVERSAL_ROUTER not in u.V4_CONTRACTS

    def test_permit2_not_in_per_version_groupings(self) -> None:
        """Permit2 is chain-invariant; it shouldn't show up in any
        per-protocol-version frozenset."""
        assert u.PERMIT2 not in u.V3_CONTRACTS
        assert u.PERMIT2 not in u.V4_CONTRACTS
        assert u.PERMIT2 not in u.UNISWAPX_CONTRACTS
        assert u.PERMIT2 not in u.FACTORIES

    def test_groupings_disjoint_pairwise(self) -> None:
        """V3, V4, and UniswapX groupings should not overlap — a leak
        would mean a copy-paste between sections."""
        assert u.V3_CONTRACTS.isdisjoint(u.V4_CONTRACTS)
        assert u.V3_CONTRACTS.isdisjoint(u.UNISWAPX_CONTRACTS)
        assert u.V4_CONTRACTS.isdisjoint(u.UNISWAPX_CONTRACTS)
