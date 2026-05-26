"""Fluid DEX Arbitrum address bundle used by opt-in pinned-block smokes.

The resolver addresses are pinned from DefiLlama dimension-adapters at the
adapter registry commit. The pool/factory/liquidity constants are retained for
the PoolT1 pinned-block smoke.
"""

from __future__ import annotations

from typing import Final

FACTORY: Final[str] = "0x4BEd3D019b62FdE741E4fCbB2DC27f9A2A4629B2"
LIQUIDITY: Final[str] = "0x52Aa899454998Be5b000Ad077a46Bbe360F4e497"
USDC_ETH_POOL_T1: Final[str] = "0x2886a01a0645390872a9eb99dAe1283664b4a3E8"

DEFILLAMA_DIMENSION_ADAPTER_COMMIT: Final[str] = "5bfdd74e9b98d60e423453406f8e1c8dcc5d8af9"
DEFILLAMA_FLUID_DEX_PATH: Final[str] = "dexs/fluid-dex/index.ts"
DEFILLAMA_FLUID_DEX_LITE_PATH: Final[str] = "dexs/fluid-dex-lite/index.ts"

DEX_RESERVES_RESOLVER: Final[str] = "0xb8f526718FF58758E256D9aD86bC194a9ff5986D"
DEX_RESOLVER: Final[str] = "0x1De42938De444d376eBc298E15D21F409b946E6D"
DIMENSION_ADAPTER_START_DATE: Final[str] = "2024-12-23"
DEX_LITE_AVAILABLE_ON_ARBITRUM: Final[bool] = False

RESOLVER_CONTRACTS: Final[frozenset[str]] = frozenset({
    DEX_RESERVES_RESOLVER,
    DEX_RESOLVER,
})
POOLT1_READ_SIDE_CONTRACTS: Final[frozenset[str]] = frozenset({
    FACTORY,
    LIQUIDITY,
    USDC_ETH_POOL_T1,
})
ALL_CONTRACTS: Final[frozenset[str]] = RESOLVER_CONTRACTS | POOLT1_READ_SIDE_CONTRACTS
