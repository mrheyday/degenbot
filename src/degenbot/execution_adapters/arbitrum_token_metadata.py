"""Pinned metadata for the Arbitrum token address bundle."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Final

from degenbot.execution_adapters import arbitrum_token_addresses as t
from degenbot.execution_adapters import uniswap_addresses as u


class UnknownTokenError(KeyError):
    """Raised when a token is outside the pinned Arbitrum metadata set."""


@dataclass(frozen=True, slots=True)
class TokenMetadata:
    """Static ERC-20 metadata for deterministic amount scaling."""

    address: str
    symbol: str
    decimals: int


_METADATA: Final[dict[str, TokenMetadata]] = {
    token.address.lower(): token
    for token in (
        TokenMetadata(t.USDC, "USDC", 6),
        TokenMetadata(t.USDC_E, "USDC.e", 6),
        TokenMetadata(t.USDT, "USDT", 6),
        TokenMetadata(t.DAI, "DAI", 18),
        TokenMetadata(t.FRAX, "FRAX", 18),
        TokenMetadata(t.USDE, "USDe", 18),
        TokenMetadata(t.SUSDE, "sUSDe", 18),
        TokenMetadata(t.GHO, "GHO", 18),
        TokenMetadata(t.LUSD, "LUSD", 18),
        TokenMetadata(t.MAI, "MAI", 18),
        TokenMetadata(t.EURS, "EURS", 2),
        TokenMetadata(t.WSTETH, "wstETH", 18),
        TokenMetadata(t.RETH, "rETH", 18),
        TokenMetadata(t.FRXETH, "frxETH", 18),
        TokenMetadata(t.SFRXETH, "sfrxETH", 18),
        TokenMetadata(t.WEETH, "weETH", 18),
        TokenMetadata(t.EZETH, "ezETH", 18),
        TokenMetadata(t.RSETH, "rsETH", 18),
        TokenMetadata(t.WBTC, "WBTC", 8),
        TokenMetadata(t.TBTC, "tBTC", 18),
        TokenMetadata(t.CBBTC, "cbBTC", 8),
        TokenMetadata(t.ARB, "ARB", 18),
        TokenMetadata(t.LINK, "LINK", 18),
        TokenMetadata(t.AAVE, "AAVE", 18),
        TokenMetadata(t.GMX, "GMX", 18),
        TokenMetadata(t.MORPHO, "MORPHO", 18),
        TokenMetadata(t.COMP, "COMP", 18),
        TokenMetadata(u.WETH9, "WETH", 18),
    )
}


def get_metadata(address: str) -> TokenMetadata:
    """Return metadata for a pinned address, case-insensitively."""

    try:
        return _METADATA[address.lower()]
    except KeyError as exc:
        raise UnknownTokenError(address) from exc


def decimals(address: str) -> int:
    """Return token decimals."""

    return get_metadata(address).decimals


def symbol(address: str) -> str:
    """Return token symbol."""

    return get_metadata(address).symbol


def known_addresses() -> frozenset[str]:
    """Return lower-case addresses with pinned metadata."""

    return frozenset(_METADATA)


def scale_to_wei(address: str, units: float | Decimal | str) -> int:
    """Scale human units into raw token units with deterministic floor rounding."""

    value = Decimal(str(units))
    scale = Decimal(10) ** decimals(address)
    return int(value * scale)
