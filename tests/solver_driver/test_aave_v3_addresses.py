"""Sanity tests for the Aave V3 addresses module.

Mirror of `test_dodo_addresses.py` / `test_uniswap_addresses.py`. No
network access — just validates the literal strings.
"""

from __future__ import annotations

from degenbot.execution import aave_v3_addresses as a
from web3 import Web3

_ALL_ADDRESSES: list[tuple[str, str]] = [
    ("POOL", a.POOL),
    ("POOL_ADDRESSES_PROVIDER", a.POOL_ADDRESSES_PROVIDER),
    ("POOL_CONFIGURATOR", a.POOL_CONFIGURATOR),
    ("ORACLE", a.ORACLE),
    ("PRICE_ORACLE_SENTINEL", a.PRICE_ORACLE_SENTINEL),
    ("ACL_MANAGER", a.ACL_MANAGER),
    ("ACL_ADMIN", a.ACL_ADMIN),
    ("PROTOCOL_DATA_PROVIDER", a.PROTOCOL_DATA_PROVIDER),
    ("DEFAULT_INCENTIVES_CONTROLLER", a.DEFAULT_INCENTIVES_CONTROLLER),
    ("EMISSION_MANAGER", a.EMISSION_MANAGER),
    ("COLLECTOR", a.COLLECTOR),
    ("L2_ENCODER", a.L2_ENCODER),
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


class TestGroupings:
    def test_core_contracts_size_matches_call_targets(self) -> None:
        # 11 entries: POOL + POOL_ADDRESSES_PROVIDER + POOL_CONFIGURATOR +
        # ORACLE + PRICE_ORACLE_SENTINEL + ACL_MANAGER + PROTOCOL_DATA_PROVIDER
        # + DEFAULT_INCENTIVES_CONTROLLER + EMISSION_MANAGER + COLLECTOR +
        # L2_ENCODER. ACL_ADMIN is intentionally excluded (it's a holder
        # address, not a call target).
        assert len(a.CORE_CONTRACTS) == 11
        assert a.POOL in a.CORE_CONTRACTS
        assert a.PROTOCOL_DATA_PROVIDER in a.CORE_CONTRACTS
        assert a.ACL_ADMIN not in a.CORE_CONTRACTS

    def test_read_only_contracts_excludes_pool_and_pool_configurator(self) -> None:
        # POOL is a transactional call target (flashLoan / liquidationCall).
        # POOL_CONFIGURATOR is governance-only; we never send to it from
        # the project, but it's also not a read-only "safe to query"
        # address in the same way the others are — exclude both from the
        # READ_ONLY set.
        assert a.POOL not in a.READ_ONLY_CONTRACTS
        assert a.POOL_CONFIGURATOR not in a.READ_ONLY_CONTRACTS

    def test_read_only_contracts_subset_of_core(self) -> None:
        assert a.READ_ONLY_CONTRACTS.issubset(a.CORE_CONTRACTS)

    def test_pool_address_matches_coordinator_config(self) -> None:
        """Sanity: POOL must match the address pinned at
        `coordinator/src/config.ts aaveV3Pool` and `Executor.sol
        AAVE_V3_POOL` — drift here would indicate one side is stale."""
        # Hard-coded from `coordinator/src/config.ts` line 113:
        #   aaveV3Pool: addrSchema.default('0x794a61358D6845594F94dc1DB02A252b5b4814aD' as Address)
        assert a.POOL == "0x794a61358D6845594F94dc1DB02A252b5b4814aD"
