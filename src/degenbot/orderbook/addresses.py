"""Canonical CoW Protocol core contract addresses."""

from __future__ import annotations

from typing import Final

GPV2_SETTLEMENT: Final[str] = "0x9008D19f58AAbD9eD0D60971565AA8510560ab41"
GPV2_ALLOW_LIST_AUTHENTICATION: Final[str] = "0x5b5B4C6c4d9C2f5E2B9b7772d2d75E5F2D6c8f6C"
GPV2_VAULT_RELAYER: Final[str] = "0xC92E8bdf79f0507f65a392b0ab4667716BFE0110"

SETTLEMENT: Final[str] = GPV2_SETTLEMENT
ALLOW_LIST_AUTHENTICATION: Final[str] = GPV2_ALLOW_LIST_AUTHENTICATION
VAULT_RELAYER: Final[str] = GPV2_VAULT_RELAYER

CHAINS_WITH_CANONICAL_DEPLOYMENT: Final[tuple[str, ...]] = (
    "arbitrum_one",
    "base",
    "ethereum",
    "gnosis",
    "sepolia",
)
