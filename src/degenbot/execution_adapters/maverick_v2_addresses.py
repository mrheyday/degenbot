"""Pinned Maverick V2 Arbitrum address and DefiLlama metadata bundle."""

from __future__ import annotations

from typing import Final

from degenbot.adapters.addresses import REGISTRY_ADDRESSES as _ADDR

ROUTER: Final[str] = _ADDR["MAVERICK_V2_ROUTER"]
QUOTER: Final[str] = _ADDR["MAVERICK_V2_QUOTER"]
REWARD_ROUTER: Final[str] = _ADDR["MAVERICK_V2_REWARD_ROUTER"]

DEFILLAMA_DIMENSION_ADAPTER_COMMIT: Final[str] = "5bfdd74e9b98d60e423453406f8e1c8dcc5d8af9"
DEFILLAMA_DIMENSION_ADAPTER_PATH: Final[str] = "dexs/maverick-v2/index.ts"
DEFILLAMA_ARBITRUM_SUBGRAPH_ID: Final[str] = "9oEipJ8CzpnQ4PnCDBQFa16AME8E9r3Kr4GurTtdUKRh"
DEFILLAMA_ARBITRUM_START_DATE: Final[str] = "2024-06-03"

EXECUTION_CONTRACTS: Final[frozenset[str]] = frozenset({
    ROUTER,
    QUOTER,
    REWARD_ROUTER,
})
