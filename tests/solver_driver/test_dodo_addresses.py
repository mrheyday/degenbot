"""Sanity tests for the DODO addresses module.

Cheap-to-run gates that catch:
- copy-paste typos that produce non-checksum-valid addresses,
- accidental duplicates across the V1 / V2 / D3 surfaces,
- groupings drifting out of sync with the underlying constants.

These don't hit the network — they just validate the literal strings.
"""

from __future__ import annotations

from web3 import Web3

from degenbot.execution import dodo_addresses as d

_ALL_ADDRESSES: list[tuple[str, str]] = [
    # V1
    ("V1_PAIR_WETH_USDC", d.V1_PAIR_WETH_USDC),
    ("V1_PAIR_WBTC_USDC", d.V1_PAIR_WBTC_USDC),
    ("V1_PAIR_USDT_USDC", d.V1_PAIR_USDT_USDC),
    ("V1_DODO_ZOO", d.V1_DODO_ZOO),
    ("V1_SELL_HELPER", d.V1_SELL_HELPER),
    # V2 templates
    ("V2_TEMPLATE_DVM", d.V2_TEMPLATE_DVM),
    ("V2_TEMPLATE_DPP", d.V2_TEMPLATE_DPP),
    ("V2_TEMPLATE_DSP", d.V2_TEMPLATE_DSP),
    ("V2_TEMPLATE_DPP_ADMIN", d.V2_TEMPLATE_DPP_ADMIN),
    ("V2_TEMPLATE_CP", d.V2_TEMPLATE_CP),
    ("V2_CLONE_FACTORY", d.V2_CLONE_FACTORY),
    ("V2_FEE_RATE_MODEL", d.V2_FEE_RATE_MODEL),
    ("V2_PERMISSION_MANAGER", d.V2_PERMISSION_MANAGER),
    # V2 factories
    ("V2_DVM_FACTORY", d.V2_DVM_FACTORY),
    ("V2_DPP_FACTORY", d.V2_DPP_FACTORY),
    ("V2_DSP_FACTORY", d.V2_DSP_FACTORY),
    ("V2_UPCP_FACTORY", d.V2_UPCP_FACTORY),
    ("V2_CROWD_POOLING_FACTORY", d.V2_CROWD_POOLING_FACTORY),
    ("V2_DODO_MINE_V2_FACTORY", d.V2_DODO_MINE_V2_FACTORY),
    ("V2_DODO_MINE_V3_REGISTRY", d.V2_DODO_MINE_V3_REGISTRY),
    # V2 proxies
    ("V2_DODO_V2_PROXY", d.V2_DODO_V2_PROXY),
    ("V2_DPP_PROXY", d.V2_DPP_PROXY),
    ("V2_DSP_PROXY", d.V2_DSP_PROXY),
    ("V2_CP_PROXY", d.V2_CP_PROXY),
    ("V2_ROUTE_PROXY", d.V2_ROUTE_PROXY),
    ("V2_FEE_ROUTE_PROXY", d.V2_FEE_ROUTE_PROXY),
    ("V2_FEE_ROUTE_PROXY_WIDGET", d.V2_FEE_ROUTE_PROXY_WIDGET),
    ("V2_DODO_MINE_V3_PROXY", d.V2_DODO_MINE_V3_PROXY),
    # V2 helpers
    ("V2_DODO_V2_ADAPTER", d.V2_DODO_V2_ADAPTER),
    ("V2_DODO_V2_ROUTE_HELPER", d.V2_DODO_V2_ROUTE_HELPER),
    ("V2_DODO_SWAP_CALC_HELPER", d.V2_DODO_SWAP_CALC_HELPER),
    ("V2_DODO_APPROVE", d.V2_DODO_APPROVE),
    ("V2_DODO_APPROVE_PROXY", d.V2_DODO_APPROVE_PROXY),
    # D3
    ("D3_ORACLE", d.D3_ORACLE),
    ("D3_MM_FACTORY", d.D3_MM_FACTORY),
    ("D3_PROXY", d.D3_PROXY),
    ("D3_RATE_MANAGER", d.D3_RATE_MANAGER),
    ("D3_MM_LIQUIDATION_ROUTER", d.D3_MM_LIQUIDATION_ROUTER),
    ("D3_VAULT", d.D3_VAULT),
    ("D3_USER_QUOTA", d.D3_USER_QUOTA),
    ("D3_POOL_QUOTA", d.D3_POOL_QUOTA),
    ("D3_FEE_RATE_MODEL", d.D3_FEE_RATE_MODEL),
    ("D3_TOKEN_TEMPLATE", d.D3_TOKEN_TEMPLATE),
    ("D3_MM_TEMPLATE", d.D3_MM_TEMPLATE),
    ("D3_MAKER_TEMPLATE", d.D3_MAKER_TEMPLATE),
    # Token + mining
    ("DODO_TOKEN_ARB", d.DODO_TOKEN_ARB),
    ("DODO_MINING_V1", d.DODO_MINING_V1),
]


class TestEachAddressIsChecksumValid:
    """Each constant must be a valid 0x-prefixed 20-byte hex string with
    correct EIP-55 checksum casing."""

    def test_every_constant_is_a_checksum_address(self) -> None:
        for name, addr in _ALL_ADDRESSES:
            assert Web3.is_address(addr), f"{name}: {addr} is not a valid address"
            assert Web3.is_checksum_address(addr), (
                f"{name}: {addr} is not EIP-55 checksum-valid; expected casing {Web3.to_checksum_address(addr)}"
            )


class TestNoDuplicates:
    """A copy-paste of the same address into two named constants would be
    a silent integrity bug — catch it here."""

    def test_all_addresses_are_mutually_distinct(self) -> None:
        # Lowercase to neutralize EIP-55 casing differences (already
        # tested by the checksum case above; this is dedup-only).
        seen: dict[str, str] = {}
        for name, addr in _ALL_ADDRESSES:
            key = addr.lower()
            assert key not in seen, f"duplicate address {addr}: assigned to {seen[key]} and {name}"
            seen[key] = name


class TestGroupings:
    """Convenience frozensets must agree with the underlying constants."""

    def test_v1_pairs_has_three_entries_and_matches_constants(self) -> None:
        assert (
            frozenset(
                {d.V1_PAIR_WETH_USDC, d.V1_PAIR_WBTC_USDC, d.V1_PAIR_USDT_USDC},
            )
            == d.V1_PAIRS
        )
        assert len(d.V1_PAIRS) == 3

    def test_v2_pmm_factories_has_five_entries(self) -> None:
        # DVM, DPP, DSP, CrowdPooling, UpCp — the five PMM factory variants.
        assert len(d.V2_PMM_FACTORIES) == 5
        assert d.V2_DVM_FACTORY in d.V2_PMM_FACTORIES
        assert d.V2_DPP_FACTORY in d.V2_PMM_FACTORIES
        assert d.V2_DSP_FACTORY in d.V2_PMM_FACTORIES
        assert d.V2_CROWD_POOLING_FACTORY in d.V2_PMM_FACTORIES
        assert d.V2_UPCP_FACTORY in d.V2_PMM_FACTORIES

    def test_v2_route_proxies_has_three_variants(self) -> None:
        assert (
            frozenset(
                {d.V2_ROUTE_PROXY, d.V2_FEE_ROUTE_PROXY, d.V2_FEE_ROUTE_PROXY_WIDGET},
            )
            == d.V2_ROUTE_PROXIES
        )

    def test_d3mm_contracts_has_twelve_entries(self) -> None:
        assert len(d.D3MM_CONTRACTS) == 12
        assert d.D3_VAULT in d.D3MM_CONTRACTS
        assert d.D3_MM_FACTORY in d.D3MM_CONTRACTS

    def test_v1_pairs_disjoint_from_v2_proxies(self) -> None:
        """Sanity: the V1 pair guardrail set must not overlap V2 execution
        proxies. A V1 pair address showing up in V2_ROUTE_PROXIES would
        indicate a copy-paste bug."""
        assert d.V1_PAIRS.isdisjoint(d.V2_ROUTE_PROXIES)
        assert d.V1_PAIRS.isdisjoint(d.V2_PMM_FACTORIES)
        assert d.V1_PAIRS.isdisjoint(d.D3MM_CONTRACTS)
