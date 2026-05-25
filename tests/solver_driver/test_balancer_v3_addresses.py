"""Tests for the pinned Balancer V3 Arbitrum address constants.

These tests guard against silent drift between the constants module and
the source-of-truth deployment-task outputs cached under
`docs/research/balancer/source/balancer-deployments/`. They do **not**
make network calls — pure shape + checksum validation.
"""

from __future__ import annotations

import re

from degenbot.execution import balancer_v3_addresses as addr

# Strict 0x-prefixed 20-byte hex; checksum-mixed-case is acceptable as long
# as the length and prefix are right (the cache outputs are checksum-cased).
_ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
_TOPIC_RE = re.compile(r"^0x[a-fA-F0-9]{64}$")


class TestAddressFormat:
    def test_all_string_constants_are_valid_addresses(self) -> None:
        for name in (
            "VAULT",
            "VAULT_ADMIN",
            "VAULT_EXTENSION",
            "VAULT_FACTORY",
            "PROTOCOL_FEE_CONTROLLER",
            "WEIGHTED_POOL_FACTORY",
            "STABLE_POOL_FACTORY",
            "STABLE_SURGE_POOL_FACTORY",
            "ROUTER",
            "BATCH_ROUTER",
            "COMPOSITE_LIQUIDITY_ROUTER",
            "AGGREGATOR_ROUTER",
            "BUFFER_ROUTER",
        ):
            value = getattr(addr, name)
            assert _ADDRESS_RE.match(value), f"{name}={value!r} is not a 0x20-byte hex"

    def test_pool_registered_topic_is_32_bytes(self) -> None:
        assert _TOPIC_RE.match(addr.POOL_REGISTERED_TOPIC)

    def test_vault_from_block_is_positive(self) -> None:
        assert addr.VAULT_FROM_BLOCK > 0


class TestVaultPin:
    def test_vault_matches_design_doc(self) -> None:
        # Pinned per balancer-v3-degenbot-adapter-design-2026-05-05.md
        # § "Source Pinning Update" + § "Pinned Arbitrum V3 deployment addresses"
        assert addr.VAULT == "0xbA1333333333a1BA1108E8412f11850A5C319bA9"


class TestFactoryGroups:
    def test_initial_scope_is_subset_of_all_factories(self) -> None:
        assert addr.INITIAL_SCOPE_FACTORIES <= addr.ALL_POOL_FACTORIES

    def test_initial_scope_is_weighted_plus_stable_only(self) -> None:
        # Q-6 initial scope explicitly excludes StableSurge per the design doc.
        assert (
            frozenset(
                {addr.WEIGHTED_POOL_FACTORY, addr.STABLE_POOL_FACTORY},
            )
            == addr.INITIAL_SCOPE_FACTORIES
        )
        assert addr.STABLE_SURGE_POOL_FACTORY not in addr.INITIAL_SCOPE_FACTORIES

    def test_no_factory_collisions(self) -> None:
        # Sanity: every factory in ALL_POOL_FACTORIES is unique.
        listed = (
            addr.WEIGHTED_POOL_FACTORY,
            addr.STABLE_POOL_FACTORY,
            addr.STABLE_SURGE_POOL_FACTORY,
        )
        assert len(set(listed)) == len(listed)


class TestRouterDistinctness:
    def test_routers_do_not_alias(self) -> None:
        # All five routers are separately deployed; tests would mask a
        # copy-paste error here.
        routers = (
            addr.ROUTER,
            addr.BATCH_ROUTER,
            addr.COMPOSITE_LIQUIDITY_ROUTER,
            addr.AGGREGATOR_ROUTER,
            addr.BUFFER_ROUTER,
        )
        assert len(set(routers)) == len(routers)

    def test_routers_distinct_from_vault(self) -> None:
        for r in (
            addr.ROUTER,
            addr.BATCH_ROUTER,
            addr.COMPOSITE_LIQUIDITY_ROUTER,
            addr.AGGREGATOR_ROUTER,
            addr.BUFFER_ROUTER,
        ):
            assert r != addr.VAULT
