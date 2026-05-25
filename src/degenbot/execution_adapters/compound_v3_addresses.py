"""Pinned Compound III Arbitrum deployment addresses."""

from __future__ import annotations

from typing import Final

COMET_USDC: Final[str] = "0x9c4ec768c28520B50860ea7a15bd7213a9fF58bf"
COMET_USDC_E: Final[str] = "0xA5EDBDD9646f8dFF606d7448e414884C7d905dCA"
COMET_USDT: Final[str] = "0xd98Be00b5D27fc98112BdE293e487f8D4cA57d07"
COMET_WETH: Final[str] = "0x6f7D514bbD4aFf3BcD1140B7344b32f063dEe486"
CONFIGURATOR: Final[str] = "0xb21b06D71c75973babdE35b49fFDAc3F82Ad3775"
REWARDS: Final[str] = "0x88730d254A2f7e6AC8388c3198aFd694bA9f7fae"

COMET_MARKETS: Final[frozenset[str]] = frozenset({COMET_USDC, COMET_USDC_E, COMET_USDT, COMET_WETH})
CORE_CONTRACTS: Final[frozenset[str]] = COMET_MARKETS | {CONFIGURATOR, REWARDS}
