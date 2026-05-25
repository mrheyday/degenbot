"""Tests for arbitrum_token_metadata.

Validates that:
- every address in `arbitrum_token_addresses.ALL_TOKENS` (plus WETH9)
  has pinned metadata, and vice versa,
- the unusual-decimals traps (EURS=2, tBTC=18 unlike WBTC=8) are
  preserved,
- accessor functions handle EIP-55 casing variants,
- `scale_to_wei` produces the right integer.
"""

from __future__ import annotations

import pytest
from degenbot.execution import arbitrum_token_addresses as t
from degenbot.execution import arbitrum_token_metadata as m
from degenbot.execution import uniswap_addresses as u


class TestCoverage:
    """Every address in the addresses module must have metadata, and
    vice versa — drift between the two modules is the primary failure
    mode this test guards against."""

    def test_every_token_in_addresses_has_metadata(self) -> None:
        for addr in t.ALL_TOKENS:
            assert m.get_metadata(addr) is not None, f"{addr} in arbitrum_token_addresses but missing metadata"

    def test_weth9_has_metadata(self) -> None:
        meta = m.get_metadata(u.WETH9)
        assert meta.symbol == "WETH"
        assert meta.decimals == 18

    def test_known_addresses_count_matches_all_tokens_plus_weth(self) -> None:
        # ALL_TOKENS has 27; plus WETH9 = 28.
        assert len(m.known_addresses()) == len(t.ALL_TOKENS) + 1

    def test_no_metadata_entry_outside_addresses_module(self) -> None:
        """Every metadata entry must correspond to an address that's
        defined in arbitrum_token_addresses or is WETH9 from
        uniswap_addresses. A leak the other way (metadata for a token
        not pinned by an addresses module) means the metadata is
        unverifiable."""
        addresses_module_set = {addr.lower() for addr in t.ALL_TOKENS} | {u.WETH9.lower()}
        for known in m.known_addresses():
            assert known in addresses_module_set, f"metadata exists for {known} but no addresses module pins it"


class TestUnusualDecimalTraps:
    """The single biggest source of decimal-scaling bugs is treating an
    unusual-decimals token as 18-decimal. Hardcode the traps."""

    def test_eurs_is_two_decimals(self) -> None:
        assert m.decimals(t.EURS) == 2

    def test_wbtc_is_eight_decimals(self) -> None:
        assert m.decimals(t.WBTC) == 8

    def test_cbbtc_is_eight_decimals(self) -> None:
        assert m.decimals(t.CBBTC) == 8

    def test_tbtc_is_eighteen_decimals(self) -> None:
        """tBTC deliberately diverged from WBTC/cbBTC; uses 18 not 8.
        Mis-treating tBTC as 8-decimal mis-prices BTC positions by 10^10."""
        assert m.decimals(t.TBTC) == 18

    def test_six_decimal_stables(self) -> None:
        assert m.decimals(t.USDC) == 6
        assert m.decimals(t.USDC_E) == 6
        assert m.decimals(t.USDT) == 6


class TestCaseInsensitiveLookup:
    def test_uppercase_lookup_works(self) -> None:
        upper = t.USDC.upper()
        assert m.decimals(upper) == 6
        assert m.symbol(upper) == "USDC"

    def test_lowercase_lookup_works(self) -> None:
        lower = t.USDC.lower()
        assert m.decimals(lower) == 6


class TestUnknownTokenRejection:
    def test_get_metadata_raises_on_unpinned_address(self) -> None:
        random_addr = "0x0000000000000000000000000000000000000001"
        with pytest.raises(m.UnknownTokenError, match=random_addr):
            m.get_metadata(random_addr)

    def test_decimals_raises_on_unpinned_address(self) -> None:
        random_addr = "0x0000000000000000000000000000000000000002"
        with pytest.raises(m.UnknownTokenError):
            m.decimals(random_addr)


class TestScaleToWei:
    def test_int_units_six_decimals(self) -> None:
        # 100 USDC → 100_000_000 (100 * 10^6)
        assert m.scale_to_wei(t.USDC, 100) == 100_000_000

    def test_int_units_eighteen_decimals(self) -> None:
        # 1 WETH → 10^18
        assert m.scale_to_wei(u.WETH9, 1) == 10**18

    def test_int_units_eight_decimals(self) -> None:
        # 1 WBTC → 100_000_000 (10^8)
        assert m.scale_to_wei(t.WBTC, 1) == 100_000_000

    def test_int_units_two_decimals_eurs(self) -> None:
        # 50 EURS → 5000 (50 * 10^2)
        assert m.scale_to_wei(t.EURS, 50) == 5000

    def test_float_units_floor_rounding(self) -> None:
        # 0.5 USDC → 500_000 exactly
        assert m.scale_to_wei(t.USDC, 0.5) == 500_000
        # 0.1 USDC → 100_000 exactly
        assert m.scale_to_wei(t.USDC, 0.1) == 100_000

    def test_scale_to_wei_unknown_address_raises(self) -> None:
        with pytest.raises(m.UnknownTokenError):
            m.scale_to_wei("0x0000000000000000000000000000000000000003", 1)


class TestSymbolDistinctness:
    """Two distinct addresses must never share a symbol — adapters
    that log symbols would conflate USDC native with USDC.e if we
    used "USDC" for both."""

    def test_usdc_and_usdc_e_have_distinct_symbols(self) -> None:
        assert m.symbol(t.USDC) == "USDC"
        assert m.symbol(t.USDC_E) == "USDC.e"
        assert m.symbol(t.USDC) != m.symbol(t.USDC_E)

    def test_all_symbols_are_distinct(self) -> None:
        symbols = [meta.symbol for meta in (m.get_metadata(a) for a in m.known_addresses())]
        assert len(symbols) == len(set(symbols)), (
            f"duplicate symbols detected: {[s for s in symbols if symbols.count(s) > 1]}"
        )
