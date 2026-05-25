"""Sanity tests for the Compound V3 addresses module.

Mirror of `test_aave_v3_addresses.py` / `test_dodo_addresses.py` /
`test_uniswap_addresses.py`. No network access.
"""

from __future__ import annotations

from degenbot.execution import compound_v3_addresses as c
from web3 import Web3

_ALL_ADDRESSES: list[tuple[str, str]] = [
    ("COMET_USDC", c.COMET_USDC),
    ("COMET_USDC_E", c.COMET_USDC_E),
    ("COMET_USDT", c.COMET_USDT),
    ("COMET_WETH", c.COMET_WETH),
    ("CONFIGURATOR", c.CONFIGURATOR),
    ("REWARDS", c.REWARDS),
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

    def test_usdc_native_and_usdc_e_markets_distinct(self) -> None:
        """The USDC (Circle native) and USDC.e (bridged) markets are
        separate Comet deployments — confusing them silently mis-routes
        liquidations to the wrong base asset."""
        assert c.COMET_USDC.lower() != c.COMET_USDC_E.lower()


class TestGroupings:
    def test_comet_markets_has_four_entries(self) -> None:
        assert (
            frozenset(
                {c.COMET_USDC, c.COMET_USDC_E, c.COMET_USDT, c.COMET_WETH},
            )
            == c.COMET_MARKETS
        )

    def test_core_contracts_is_markets_plus_shared_infra(self) -> None:
        assert c.COMET_MARKETS | {c.CONFIGURATOR, c.REWARDS} == c.CORE_CONTRACTS
        assert len(c.CORE_CONTRACTS) == 6

    def test_configurator_and_rewards_not_in_markets(self) -> None:
        """Shared infra addresses must not leak into the markets set —
        callers using COMET_MARKETS as "iterate over lending positions"
        would mis-include the Configurator if there's a leak."""
        assert c.CONFIGURATOR not in c.COMET_MARKETS
        assert c.REWARDS not in c.COMET_MARKETS
