"""Sanity tests for the Arbitrum token addresses module.

Mirror of `test_dodo_addresses.py` / `test_uniswap_addresses.py` /
`test_aave_v3_addresses.py`. No network access.
"""

from __future__ import annotations

from degenbot.execution import arbitrum_token_addresses as t
from degenbot.execution import uniswap_addresses as u
from web3 import Web3

_ALL_ADDRESSES: list[tuple[str, str]] = [
    # USD-pegged stables
    ("USDC", t.USDC),
    ("USDC_E", t.USDC_E),
    ("USDT", t.USDT),
    ("DAI", t.DAI),
    ("FRAX", t.FRAX),
    ("USDE", t.USDE),
    ("SUSDE", t.SUSDE),
    ("GHO", t.GHO),
    ("LUSD", t.LUSD),
    ("MAI", t.MAI),
    # Non-USD stables
    ("EURS", t.EURS),
    # ETH-collateralized — LSTs
    ("WSTETH", t.WSTETH),
    ("RETH", t.RETH),
    ("FRXETH", t.FRXETH),
    ("SFRXETH", t.SFRXETH),
    # ETH-collateralized — LRTs
    ("WEETH", t.WEETH),
    ("EZETH", t.EZETH),
    ("RSETH", t.RSETH),
    # BTC variants
    ("WBTC", t.WBTC),
    ("TBTC", t.TBTC),
    ("CBBTC", t.CBBTC),
    # Non-stables (governance / utility)
    ("ARB", t.ARB),
    ("LINK", t.LINK),
    ("AAVE", t.AAVE),
    ("GMX", t.GMX),
    ("MORPHO", t.MORPHO),
    ("COMP", t.COMP),
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

    def test_usdc_and_usdc_e_are_distinct(self) -> None:
        """The single most common copy-paste bug: confusing native USDC
        with bridged USDC.e. Fail loudly."""
        assert t.USDC.lower() != t.USDC_E.lower()

    def test_wbtc_and_tbtc_are_distinct(self) -> None:
        """WBTC (BitGo-custodied) and tBTC (Threshold-decentralized) are
        distinct ERC20s that both peg to BTC — different risk profiles."""
        assert t.WBTC.lower() != t.TBTC.lower()


class TestStablesGroupings:
    def test_usd_pegged_excludes_susde(self) -> None:
        """sUSDe is a yield-bearing wrapper, not a 1:1 peg. It must NOT
        be in USD_PEGGED — code that filters "treat as $1" by membership
        in this set would mis-price sUSDe positions."""
        assert t.SUSDE not in t.USD_PEGGED
        assert t.SUSDE in t.ALL_STABLES

    def test_usd_pegged_has_nine_entries(self) -> None:
        # USDC, USDC_E, USDT, DAI, FRAX, USDE, GHO, LUSD, MAI
        assert len(t.USD_PEGGED) == 9
        for addr in (t.USDC, t.USDC_E, t.USDT, t.DAI, t.FRAX, t.USDE, t.GHO, t.LUSD, t.MAI):
            assert addr in t.USD_PEGGED

    def test_eur_pegged_has_one_entry(self) -> None:
        assert frozenset({t.EURS}) == t.EUR_PEGGED

    def test_usd_pegged_disjoint_from_eur_pegged(self) -> None:
        """A token in both USD_PEGGED and EUR_PEGGED would mean code
        that "treats as 1 USD" by membership filter would mis-price
        EUR-stables every time the USD/EUR cross moves."""
        assert t.USD_PEGGED.isdisjoint(t.EUR_PEGGED)

    def test_all_stables_has_eleven_entries(self) -> None:
        # USD_PEGGED (9) + SUSDE + EURS = 11
        assert len(t.ALL_STABLES) == 11
        assert t.USD_PEGGED.issubset(t.ALL_STABLES)
        assert t.EUR_PEGGED.issubset(t.ALL_STABLES)
        assert t.SUSDE in t.ALL_STABLES


class TestEthCollateralGroupings:
    def test_lsts_has_four_entries(self) -> None:
        # wstETH (Lido), rETH (Rocket Pool), frxETH + sfrxETH (Frax)
        assert frozenset({t.WSTETH, t.RETH, t.FRXETH, t.SFRXETH}) == t.LSTS

    def test_lrts_has_three_entries(self) -> None:
        assert frozenset({t.WEETH, t.EZETH, t.RSETH}) == t.LRTS

    def test_eth_collateral_is_lst_lrt_union(self) -> None:
        assert t.ETH_COLLATERAL == t.LSTS | t.LRTS
        assert len(t.ETH_COLLATERAL) == 7

    def test_lsts_and_lrts_disjoint(self) -> None:
        """An LRT is built on top of an LST conceptually, but each token
        is its own ERC20 — the two groupings should not overlap."""
        assert t.LSTS.isdisjoint(t.LRTS)


class TestBtcGroupings:
    def test_wrapped_btc_has_three_entries(self) -> None:
        # WBTC (BitGo), tBTC (Threshold), cbBTC (Coinbase)
        assert frozenset({t.WBTC, t.TBTC, t.CBBTC}) == t.WRAPPED_BTC

    def test_wbtc_tbtc_cbbtc_pairwise_distinct(self) -> None:
        """Three distinct BTC pegs with different custody / risk
        models — failing this would mean two of them share an
        address which is impossible but copy-paste bugs happen."""
        addrs = {t.WBTC.lower(), t.TBTC.lower(), t.CBBTC.lower()}
        assert len(addrs) == 3


class TestCrossCategoryDisjointness:
    """A leak from any of the per-category sets into another would
    indicate a copy-paste bug or a mis-classified token. Assert the
    full pairwise disjointness."""

    def test_stables_disjoint_from_eth_collateral(self) -> None:
        assert t.ALL_STABLES.isdisjoint(t.ETH_COLLATERAL)

    def test_stables_disjoint_from_btc(self) -> None:
        assert t.ALL_STABLES.isdisjoint(t.WRAPPED_BTC)

    def test_stables_disjoint_from_non_stables(self) -> None:
        assert t.ALL_STABLES.isdisjoint(t.NON_STABLES)

    def test_eth_collateral_disjoint_from_btc(self) -> None:
        assert t.ETH_COLLATERAL.isdisjoint(t.WRAPPED_BTC)

    def test_eth_collateral_disjoint_from_non_stables(self) -> None:
        assert t.ETH_COLLATERAL.isdisjoint(t.NON_STABLES)

    def test_btc_disjoint_from_non_stables(self) -> None:
        assert t.WRAPPED_BTC.isdisjoint(t.NON_STABLES)


class TestAllTokensUnion:
    def test_all_tokens_equals_union_of_categories(self) -> None:
        assert t.ALL_TOKENS == (t.ALL_STABLES | t.ETH_COLLATERAL | t.WRAPPED_BTC | t.NON_STABLES)

    def test_all_tokens_count_matches_per_category_sum(self) -> None:
        # 11 stables + 7 ETH-collateralized + 3 BTC variants + 6 non-stables = 27
        assert len(t.ALL_TOKENS) == 11 + 7 + 3 + 6
        assert len(t.ALL_TOKENS) == 27


class TestLendingGovernanceTokens:
    def test_lending_governance_has_three_entries(self) -> None:
        # AAVE + MORPHO + COMP — Compound + Aave + Morpho governance.
        assert frozenset({t.AAVE, t.MORPHO, t.COMP}) == t.LENDING_GOVERNANCE_TOKENS

    def test_lending_governance_subset_of_non_stables(self) -> None:
        assert t.LENDING_GOVERNANCE_TOKENS.issubset(t.NON_STABLES)

    def test_arb_link_gmx_not_in_lending_governance(self) -> None:
        """ARB / LINK / GMX are governance tokens too, but not for
        lending protocols. Must not leak into LENDING_GOVERNANCE_TOKENS."""
        assert t.ARB not in t.LENDING_GOVERNANCE_TOKENS
        assert t.LINK not in t.LENDING_GOVERNANCE_TOKENS
        assert t.GMX not in t.LENDING_GOVERNANCE_TOKENS


class TestNoCollisionWithUniswapWeth:
    """WETH9 is intentionally hosted at `uniswap_addresses.py`; this
    module must NOT define its own WETH9 — that would create two
    sources of truth for the wrapped-native address."""

    def test_no_token_in_this_module_equals_weth9(self) -> None:
        weth9_lower = u.WETH9.lower()
        for name, addr in _ALL_ADDRESSES:
            assert addr.lower() != weth9_lower, (
                f"{name} ({addr}) collides with uniswap_addresses.WETH9 ({u.WETH9}); WETH9 has a canonical home there"
            )
