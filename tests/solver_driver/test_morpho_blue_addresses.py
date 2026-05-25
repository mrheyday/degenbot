"""Sanity tests for the Morpho Blue addresses module.

Mirror of `test_aave_v3_addresses.py` / `test_compound_v3_addresses.py`.
No network access.
"""

from __future__ import annotations

from degenbot.execution import morpho_blue_addresses as m
from web3 import Web3

_ALL_ADDRESSES: list[tuple[str, str]] = [
    # Core Morpho Blue
    ("MORPHO_BLUE", m.MORPHO_BLUE),
    ("PUBLIC_ALLOCATOR", m.PUBLIC_ALLOCATOR),
    # Bundler3 family
    ("BUNDLER3", m.BUNDLER3),
    ("GENERAL_ADAPTER_1", m.GENERAL_ADAPTER_1),
    ("PARASWAP_ADAPTER", m.PARASWAP_ADAPTER),
    ("AAVE_V3_MIGRATION_ADAPTER", m.AAVE_V3_MIGRATION_ADAPTER),
    ("COMPOUND_V3_MIGRATION_ADAPTER", m.COMPOUND_V3_MIGRATION_ADAPTER),
    # External registry referenced by Bundler3 ParaswapAdapter
    ("PARASWAP_AUGUSTUS_REGISTRY", m.PARASWAP_AUGUSTUS_REGISTRY),
]


class TestEachAddressIsValid:
    def test_every_constant_is_a_valid_address(self) -> None:
        for name, addr in _ALL_ADDRESSES:
            assert Web3.is_address(addr), f"{name}: {addr} is not a valid address"


class TestNoDuplicates:
    def test_all_addresses_are_mutually_distinct(self) -> None:
        seen: dict[str, str] = {}
        for name, addr in _ALL_ADDRESSES:
            key = addr.lower()
            assert key not in seen, f"duplicate address {addr}: assigned to {seen[key]} and {name}"
            seen[key] = name


class TestCriticalGuardrails:
    """The single highest-stakes invariant in this module: Bundler3 +
    its adapters must NOT leak into the EXECUTOR_RELEVANT set, because
    allowlisting any of them on Executor.sol would let arbitrary
    user-position calldata reach the autonomous flash-loan path.
    """

    def test_bundler3_not_executor_relevant(self) -> None:
        assert m.BUNDLER3 not in m.EXECUTOR_RELEVANT

    def test_general_adapter_1_not_executor_relevant(self) -> None:
        assert m.GENERAL_ADAPTER_1 not in m.EXECUTOR_RELEVANT

    def test_paraswap_adapter_not_executor_relevant(self) -> None:
        """And distinct from the project's allowlisted Paraswap Augustus
        router — that's `0x6A000F20...001068`. The Bundler3 ParaswapAdapter
        is a different contract and must never be confused for it."""
        assert m.PARASWAP_ADAPTER.lower() != "0x6A000F20005980200259B80c5102003040001068".lower()
        assert m.PARASWAP_ADAPTER not in m.EXECUTOR_RELEVANT

    def test_migration_adapters_not_executor_relevant(self) -> None:
        assert m.AAVE_V3_MIGRATION_ADAPTER not in m.EXECUTOR_RELEVANT
        assert m.COMPOUND_V3_MIGRATION_ADAPTER not in m.EXECUTOR_RELEVANT

    def test_executor_relevant_disjoint_from_bundler3_family(self) -> None:
        assert m.EXECUTOR_RELEVANT.isdisjoint(m.BUNDLER3_FAMILY)


class TestGroupings:
    def test_executor_relevant_has_two_entries(self) -> None:
        assert frozenset({m.MORPHO_BLUE, m.PUBLIC_ALLOCATOR}) == m.EXECUTOR_RELEVANT

    def test_bundler3_family_has_five_entries(self) -> None:
        # Bundler3 + 4 adapters.
        assert len(m.BUNDLER3_FAMILY) == 5
        assert m.BUNDLER3 in m.BUNDLER3_FAMILY
        assert m.GENERAL_ADAPTER_1 in m.BUNDLER3_FAMILY
        assert m.PARASWAP_ADAPTER in m.BUNDLER3_FAMILY
        assert m.AAVE_V3_MIGRATION_ADAPTER in m.BUNDLER3_FAMILY
        assert m.COMPOUND_V3_MIGRATION_ADAPTER in m.BUNDLER3_FAMILY

    def test_all_contracts_is_executor_plus_bundler_plus_external(self) -> None:
        assert (m.EXECUTOR_RELEVANT | m.BUNDLER3_FAMILY | {m.PARASWAP_AUGUSTUS_REGISTRY}) == m.ALL_CONTRACTS
        # 2 executor-relevant + 5 bundler3-family + 1 external = 8.
        assert len(m.ALL_CONTRACTS) == 8


class TestParityWithCoordinatorConfig:
    """The MORPHO_BLUE constant pinned here must match the literal
    used in coordinator/src/config.ts and the Executor.sol immutable —
    drift would mean two sources of truth."""

    def test_morpho_blue_matches_coordinator_config(self) -> None:
        # Verbatim from coordinator/src/config.ts line ~114:
        #   morphoBlue: optionalAddrSchema.default('0x6c247b1F6182318877311737BaC0844bAa518F5e' as Address)
        assert m.MORPHO_BLUE == "0x6c247b1F6182318877311737BaC0844bAa518F5e"
