"""Morpho Blue lending-pool read adapter for the Python solver.

Mirrors the AaveV4 adapter pattern: thin async wrapper around an external
data source, exposes structured methods for the solver loop to call. Source
is the Morpho GraphQL API (`https://api.morpho.org/graphql`).

**Scope (v1):** READ-ONLY. This adapter is for market discovery, position
reads, and liquidation-target enumeration — not transaction submission.
Flash-loan tx construction lives in `morpho_flashloan_adapter.py`. The
on-chain callback receiver is `Executor.sol::onMorphoFlashLoan` per
`docs/architecture/05` §5.5.

**Architecture:** Morpho Blue is a singleton lending market on Arbitrum at
the address held in `Executor.sol`'s `MORPHO_BLUE` immutable. Each market is
an isolated tuple of (loan token, collateral token, LLTV, IRM, oracle); the
market id is the keccak256 of the encoded MarketParams struct.

Decimal handling: Morpho GraphQL returns APY / index / asset totals as
decimal strings. We preserve them unchanged on the wire; consumers convert
to `Decimal` (exact) or scaled `int` only when needed. Never coerce through
`float` per §07 decimal note.

Default endpoint: `.env.example` sets
`MORPHO_API_URL=https://api.morpho.org/graphql` plus
`MORPHO_PRIORITY_MARKET_IDS` for hot-path market ids.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Literal, Protocol, cast

import structlog
from web3 import Web3

from driver.execution.adapter_base import (
    AsyncGraphqlAdapterClient,
    GraphqlAdapterConfig,
    configure_execution_logging,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

logger = structlog.get_logger(__name__).bind(
    service="solver",
    component="execution.morpho_lp_adapter",
)

type JsonObject = dict[str, object]
type MorphoBadDebtClassification = Literal["collateralized", "bad_debt"]

_EVM_ADDRESS_BYTES = 20
_BYTES32_BYTES = 32
_ARBITRUM_CHAIN_ID = 42161
_GRAPHQL_PAGE_SIZE = 100
_WAD = 10**18
_ORACLE_PRICE_SCALE = 10**36
_VIRTUAL_SHARES = 10**6
_VIRTUAL_ASSETS = 1
_LIQUIDATION_CURSOR = 3 * 10**17
_MAX_LIQUIDATION_INCENTIVE_FACTOR = 115 * 10**16
_LIQUIDATE_SELECTOR = Web3.keccak(
    text="liquidate((address,address,address,address,uint256),address,uint256,uint256,bytes)"
)[:4]
_MORPHO_BLUE_ABI: list[dict[str, object]] = [
    {
        "type": "function",
        "name": "idToMarketParams",
        "stateMutability": "view",
        "inputs": [{"name": "id", "type": "bytes32"}],
        "outputs": [
            {"name": "loanToken", "type": "address"},
            {"name": "collateralToken", "type": "address"},
            {"name": "oracle", "type": "address"},
            {"name": "irm", "type": "address"},
            {"name": "lltv", "type": "uint256"},
        ],
    },
    {
        "type": "function",
        "name": "position",
        "stateMutability": "view",
        "inputs": [{"name": "id", "type": "bytes32"}, {"name": "user", "type": "address"}],
        "outputs": [
            {"name": "supplyShares", "type": "uint256"},
            {"name": "borrowShares", "type": "uint128"},
            {"name": "collateral", "type": "uint128"},
        ],
    },
    {
        "type": "function",
        "name": "market",
        "stateMutability": "view",
        "inputs": [{"name": "id", "type": "bytes32"}],
        "outputs": [
            {"name": "totalSupplyAssets", "type": "uint128"},
            {"name": "totalSupplyShares", "type": "uint128"},
            {"name": "totalBorrowAssets", "type": "uint128"},
            {"name": "totalBorrowShares", "type": "uint128"},
            {"name": "lastUpdate", "type": "uint128"},
            {"name": "fee", "type": "uint128"},
        ],
    },
]
_ORACLE_ABI: list[dict[str, object]] = [
    {
        "type": "function",
        "name": "price",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}],
    },
]

_LISTED_MARKETS_QUERY = """
query ListedMarkets($chainIds: [Int!], $first: Int, $skip: Int) {
  markets(
    first: $first
    skip: $skip
    orderBy: SupplyAssetsUsd
    orderDirection: Desc
    where: { listed: true, isIdle: false, chainId_in: $chainIds }
  ) {
    items {
      marketId
      lltv
      irmAddress
      oracle { address }
      loanAsset { address symbol decimals }
      collateralAsset { address symbol decimals }
      state {
        supplyApy
        borrowApy
        borrowAssets
        supplyAssets
        fee
        utilization
        timestamp
      }
    }
  }
}
"""

_MARKET_BY_ID_QUERY = """
query MarketById($marketId: String!, $chainId: Int!) {
  marketById(marketId: $marketId, chainId: $chainId) {
    marketId
    lltv
    irmAddress
    oracle { address }
    loanAsset { address symbol decimals }
    collateralAsset { address symbol decimals }
    state {
      supplyApy
      borrowApy
      borrowAssets
      supplyAssets
      fee
      utilization
      timestamp
    }
  }
}
"""

_PRIORITY_MARKETS_QUERY = """
query PriorityMarkets($marketIds: [String!], $chainIds: [Int!]) {
  markets(
    first: 100
    orderBy: SupplyAssetsUsd
    orderDirection: Desc
    where: { uniqueKey_in: $marketIds, isIdle: false, chainId_in: $chainIds }
  ) {
    items {
      marketId
      lltv
      irmAddress
      oracle { address }
      loanAsset { address symbol decimals }
      collateralAsset { address symbol decimals }
      state {
        supplyApy
        borrowApy
        borrowAssets
        supplyAssets
        fee
        utilization
        timestamp
      }
    }
  }
}
"""

_MARKET_POSITION_QUERY = """
query MarketPosition($marketId: String!, $user: String!, $chainId: Int!) {
  marketPosition(marketUniqueKey: $marketId, userAddress: $user, chainId: $chainId) {
    healthFactor
    market { marketId }
    user { address }
    state {
      supplyShares
      borrowShares
      collateral
      supplyAssets
      borrowAssets
      borrowAssetsUsd
      collateralUsd
    }
  }
}
"""

_RISKY_MARKET_POSITIONS_QUERY = """
query RiskyMarketPositions(
  $marketIds: [String!],
  $chainIds: [Int!],
  $maxHealthFactor: Float!,
  $first: Int,
  $skip: Int
) {
  marketPositions(
    first: $first
    skip: $skip
    orderBy: HealthFactor
    orderDirection: Asc
    where: {
      marketUniqueKey_in: $marketIds,
      chainId_in: $chainIds,
      borrowShares_gte: "1",
      healthFactor_lte: $maxHealthFactor
    }
  ) {
    items {
      healthFactor
      market { marketId }
      user { address }
      state {
        supplyShares
        borrowShares
        collateral
        supplyAssets
        borrowAssets
        borrowAssetsUsd
        collateralUsd
      }
    }
  }
}
"""


class _ContractCall(Protocol):
    def call(self) -> object: ...


class _MorphoBlueFunctions(Protocol):
    def idToMarketParams(self, market_id: bytes) -> _ContractCall: ...  # noqa: N802
    def position(self, market_id: bytes, user: str) -> _ContractCall: ...
    def market(self, market_id: bytes) -> _ContractCall: ...


class _MorphoBlueContract(Protocol):
    functions: _MorphoBlueFunctions


class _OracleFunctions(Protocol):
    def price(self) -> _ContractCall: ...


class _OracleContract(Protocol):
    functions: _OracleFunctions


# ---------------------------------------------------------------------------
# Wire types — exact-decimal preserving
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MorphoMarketParams:
    """Canonical Morpho Blue MarketParams tuple.

    The on-chain market id is `keccak256(abi.encode(MarketParams))`, where
    `MarketParams = (loanToken, collateralToken, oracle, irm, lltv)`.
    """

    loan_token: str
    collateral_token: str
    oracle: str
    irm: str
    lltv: int

    def id(self) -> str:
        """Return the Morpho `Id` bytes32 hex string for this MarketParams tuple."""
        if self.lltv < 0:
            raise ValueError("Morpho market LLTV must be non-negative")
        encoded = b"".join(
            (
                _encode_address(self.loan_token),
                _encode_address(self.collateral_token),
                _encode_address(self.oracle),
                _encode_address(self.irm),
                self.lltv.to_bytes(32, "big"),
            )
        )
        return Web3.to_hex(Web3.keccak(encoded))


@dataclass(frozen=True)
class MorphoMarket:
    """A single Morpho Blue market. Exact decimals preserved as strings.

    `id` is the bytes32 market id (hex string, 0x-prefixed). The 5-tuple
    (loan_token, collateral_token, oracle_address, irm_address, lltv) is
    the canonical MarketParams; the id is keccak256 of that encoding.
    """

    id: str  # bytes32 hex
    loan_token: str
    collateral_token: str
    lltv: int  # liquidation LTV in 1e18-scaled wad
    irm_address: str
    oracle_address: str
    supply_apy_str: str
    borrow_apy_str: str
    total_supply_assets_str: str
    total_borrow_assets_str: str
    fee_str: str
    last_update_ts: int
    loan_token_symbol: str = ""
    loan_token_decimals: int = 0
    collateral_token_symbol: str = ""
    collateral_token_decimals: int = 0
    utilization_str: str = "0"

    @property
    def supply_apy(self) -> Decimal:
        return Decimal(self.supply_apy_str)

    @property
    def borrow_apy(self) -> Decimal:
        return Decimal(self.borrow_apy_str)

    @property
    def total_supply_assets(self) -> int:
        # Morpho returns asset totals as integer strings (wei-scaled).
        return int(self.total_supply_assets_str)

    @property
    def total_borrow_assets(self) -> int:
        return int(self.total_borrow_assets_str)

    @property
    def fee(self) -> Decimal:
        return Decimal(self.fee_str)

    @property
    def utilization(self) -> Decimal:
        return Decimal(self.utilization_str)

    @property
    def market_params(self) -> MorphoMarketParams:
        return MorphoMarketParams(
            loan_token=self.loan_token,
            collateral_token=self.collateral_token,
            oracle=self.oracle_address,
            irm=self.irm_address,
            lltv=self.lltv,
        )

    @property
    def derived_id(self) -> str:
        return self.market_params.id()

    @property
    def liquidation_incentive_factor_wad(self) -> int:
        """Morpho Blue LIF for this market, scaled by 1e18."""
        return liquidation_incentive_factor_wad(self.lltv)

    @property
    def liquidation_bonus_bps(self) -> int:
        """Liquidation bonus in basis points, floored."""
        return liquidation_bonus_bps(self.lltv)


@dataclass(frozen=True)
class MorphoPosition:
    """A user's position within one Morpho Blue market.

    `supply_shares_str` and `borrow_shares_str` are share-denominated and
    must be converted to assets via the market's index. `collateral_str` is
    asset-denominated (collateral token native units).
    """

    market_id: str
    user: str
    supply_shares_str: str
    borrow_shares_str: str
    collateral_str: str
    supply_assets_str: str = "0"
    borrow_assets_str: str = "0"
    borrow_assets_usd_str: str = "0"
    collateral_usd_str: str = "0"
    health_factor_str: str = "0"

    @property
    def supply_shares(self) -> int:
        return int(self.supply_shares_str)

    @property
    def borrow_shares(self) -> int:
        return int(self.borrow_shares_str)

    @property
    def collateral(self) -> int:
        return int(self.collateral_str)

    @property
    def supply_assets(self) -> int:
        return int(self.supply_assets_str)

    @property
    def borrow_assets(self) -> int:
        return int(self.borrow_assets_str)

    @property
    def borrow_assets_usd(self) -> Decimal:
        return Decimal(self.borrow_assets_usd_str)

    @property
    def collateral_usd(self) -> Decimal:
        return Decimal(self.collateral_usd_str)

    @property
    def health_factor(self) -> Decimal:
        return Decimal(self.health_factor_str)


@dataclass(frozen=True)
class MorphoLiquidationCandidate:
    """Read-side liquidation candidate; execution must revalidate on-chain."""

    market: MorphoMarket
    position: MorphoPosition

    @property
    def health_factor(self) -> Decimal:
        return self.position.health_factor

    @property
    def borrower(self) -> str:
        return self.position.user

    @property
    def repay_shares(self) -> int:
        return self.position.borrow_shares


@dataclass(frozen=True)
class MorphoLiquidationPriority:
    """Screening priority for a Morpho liquidation candidate.

    This is not an execution proof. It ranks indexed candidates using
    source-faithful Morpho LIF math plus explicit cost/risk inputs before the
    on-chain revalidation and swap-back quote stages.
    """

    candidate: MorphoLiquidationCandidate
    liquidation_bonus_bps: int
    borrow_assets_usd: Decimal
    collateral_usd: Decimal
    gross_bonus_usd: Decimal
    estimated_flash_fee_usd: Decimal
    estimated_swap_cost_usd: Decimal
    estimated_gas_cost_usd: Decimal
    oracle_risk_penalty_usd: Decimal
    net_edge_usd: Decimal
    bad_debt_risk: bool
    swap_back_liquidity_usd: Decimal | None
    swap_back_liquidity_shortfall_usd: Decimal

    @property
    def health_factor(self) -> Decimal:
        return self.candidate.health_factor

    @property
    def borrower(self) -> str:
        return self.candidate.borrower

    @property
    def market_id(self) -> str:
        return self.candidate.market.id


@dataclass(frozen=True)
class MorphoLiquidationRiskCosts:
    """Explicit risk/cost components attached to a liquidation payload."""

    estimated_flash_fee_usd: Decimal
    estimated_swap_cost_usd: Decimal
    estimated_gas_cost_usd: Decimal
    oracle_risk_penalty_usd: Decimal
    swap_back_liquidity_usd: Decimal | None
    swap_back_liquidity_shortfall_usd: Decimal

    def to_wire(self) -> JsonObject:
        """Return deterministic JSON-ready cost fields."""
        return {
            "estimatedFlashFeeUsd": _decimal_to_wire(self.estimated_flash_fee_usd),
            "estimatedSwapCostUsd": _decimal_to_wire(self.estimated_swap_cost_usd),
            "estimatedGasCostUsd": _decimal_to_wire(self.estimated_gas_cost_usd),
            "oracleRiskPenaltyUsd": _decimal_to_wire(self.oracle_risk_penalty_usd),
            "swapBackLiquidityUsd": (
                None if self.swap_back_liquidity_usd is None else _decimal_to_wire(self.swap_back_liquidity_usd)
            ),
            "swapBackLiquidityShortfallUsd": _decimal_to_wire(self.swap_back_liquidity_shortfall_usd),
        }


@dataclass(frozen=True)
class MorphoStandardLiquidationCandidatePayload:
    """Read-only Stage 1 payload for standard Morpho Blue liquidation.

    This deliberately stops before executable route composition. The Morpho
    adapter owns the protocol math and ranking provenance; `degenbot_ipc.py`
    owns only the outer NDJSON Opportunity envelope.
    """

    market_id: str
    market_params: MorphoMarketParams
    borrower: str
    repaid_shares: int
    loan_token: str
    collateral_token: str
    repay_assets: int
    expected_collateral_seized: int | None
    health_factor_wad: int
    liquidation_bonus_bps: int
    borrow_assets_usd: Decimal
    collateral_usd: Decimal
    gross_bonus_usd: Decimal
    ranking_score_usd: Decimal
    risk_costs: MorphoLiquidationRiskCosts
    bad_debt_classification: MorphoBadDebtClassification

    def to_wire(self) -> JsonObject:
        """Return the stable Python-side payload consumed by IPC helpers."""
        return {
            "payloadVersion": 1,
            "marketId": self.market_id,
            "marketParams": _market_params_to_wire(self.market_params),
            "borrower": self.borrower,
            "repaidShares": str(self.repaid_shares),
            "loanToken": self.loan_token,
            "collateralToken": self.collateral_token,
            "repayAssets": str(self.repay_assets),
            "expectedCollateralSeized": (
                None if self.expected_collateral_seized is None else str(self.expected_collateral_seized)
            ),
            "healthFactorWad": str(self.health_factor_wad),
            "liquidationBonusBps": self.liquidation_bonus_bps,
            "borrowAssetsUsd": _decimal_to_wire(self.borrow_assets_usd),
            "collateralUsd": _decimal_to_wire(self.collateral_usd),
            "grossBonusUsd": _decimal_to_wire(self.gross_bonus_usd),
            "rankingScoreUsd": _decimal_to_wire(self.ranking_score_usd),
            "riskCosts": self.risk_costs.to_wire(),
            "badDebtClassification": self.bad_debt_classification,
        }


@dataclass(frozen=True)
class MorphoLiquidationRankingConfig:
    """Cost and policy inputs for first-pass Morpho liquidation ranking."""

    estimated_gas_cost_usd: Decimal = Decimal("0")
    flash_fee_bps_by_loan_token: Mapping[str, int] | None = None
    swap_cost_bps_by_collateral_token: Mapping[str, int] | None = None
    oracle_risk_bps_by_market_id: Mapping[str, int] | None = None
    swap_back_liquidity_usd_by_collateral_token: Mapping[str, Decimal] | None = None
    include_bad_debt: bool = False
    require_swap_back_liquidity: bool = True
    min_net_edge_usd: Decimal = Decimal("0")


@dataclass(frozen=True)
class MorphoLiquidationLiveRiskFeeds:
    """Live risk/cost feeds converted into screening-ranker policy inputs."""

    estimated_gas_units: int
    gas_price_wei: int
    eth_price_usd: Decimal
    flash_fee_bps_by_loan_token: Mapping[str, int] | None = None
    swap_cost_bps_by_collateral_token: Mapping[str, int] | None = None
    oracle_risk_bps_by_market_id: Mapping[str, int] | None = None
    swap_back_liquidity_usd_by_collateral_token: Mapping[str, Decimal] | None = None
    include_bad_debt: bool = False
    require_swap_back_liquidity: bool = True
    min_net_edge_usd: Decimal = Decimal("0")


@dataclass(frozen=True)
class MorphoOnchainPosition:
    supply_shares: int
    borrow_shares: int
    collateral: int


@dataclass(frozen=True)
class MorphoOnchainMarketState:
    total_supply_assets: int
    total_supply_shares: int
    total_borrow_assets: int
    total_borrow_shares: int
    last_update: int
    fee: int


@dataclass(frozen=True)
class MorphoLiquidationRevalidation:
    """On-chain revalidation result for a GraphQL liquidation candidate."""

    candidate: MorphoLiquidationCandidate
    market_params: MorphoMarketParams | None
    position: MorphoOnchainPosition | None
    market_state: MorphoOnchainMarketState | None
    reasons: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return len(self.reasons) == 0


@dataclass(frozen=True)
class MorphoLiquidationPlan:
    """Standard Morpho Blue liquidation calldata after on-chain revalidation.

    Uses the `repaidShares` path (`seizedAssets = 0`) so the Executor/solver
    controls the exact debt-share amount being repaid. The on-chain Morpho
    contract computes seized collateral from the fresh market state during
    execution.
    """

    revalidation: MorphoLiquidationRevalidation
    collateral_price: int
    borrowed_assets: int
    repay_assets: int
    collateral_value_assets: int
    max_borrow_assets: int
    health_factor_wad: int
    repay_shares: int
    calldata: bytes

    @property
    def healthy(self) -> bool:
        return self.max_borrow_assets >= self.borrowed_assets

    @property
    def borrower(self) -> str:
        return self.revalidation.candidate.borrower

    @property
    def market_id(self) -> str:
        return self.revalidation.candidate.market.id

    def to_executor_swap_step(self, *, morpho_blue_address: str, amount_out_min: int) -> MorphoLiquidationSwapStep:
        """Return a coordinator/degenbot-compatible MorphoBlue action step."""
        if amount_out_min < 0:
            raise ValueError(f"amount_out_min must be non-negative, got {amount_out_min}")
        market = self.revalidation.candidate.market
        return MorphoLiquidationSwapStep(
            pool=morpho_blue_address,
            router=morpho_blue_address,
            call_data=Web3.to_hex(self.calldata),
            token_in=market.loan_token,
            token_out=market.collateral_token,
            amount_in=self.repay_assets,
            amount_out_min=amount_out_min,
            zero_for_one=False,
            dex="MorphoBlue",
        )


@dataclass(frozen=True)
class MorphoLiquidationSwapStep:
    """Executable step shape matching the degenbot/coordinator IPC `SwapStep`."""

    pool: str
    router: str
    call_data: str
    token_in: str
    token_out: str
    amount_in: int
    amount_out_min: int
    zero_for_one: bool
    dex: str


@dataclass(frozen=True)
class MorphoSwapBackQuote:
    """Executable exact-sell quote for seized collateral -> flash token."""

    source: str
    sell_token: str
    buy_token: str
    sell_amount: int
    buy_amount: int
    router: str
    calldata: str
    estimated_gas: int = 0


@dataclass(frozen=True)
class MorphoListedToken:
    """Token metadata from `morpho-org/morpho-blue-api-metadata`."""

    chain_id: int
    address: str
    symbol: str
    decimals: int
    tags: tuple[str, ...]


@dataclass(frozen=True)
class MorphoApiMetadata:
    """Static Morpho API metadata used for screening, not market accounting.

    Source: `https://github.com/morpho-org/morpho-blue-api-metadata`.
    This repository does not carry full MarketParams; use it to filter tokens,
    vault seeds, explicit blacklists, and red warnings before live GraphQL or
    on-chain reads.
    """

    chain_id: int
    listed_tokens: dict[str, MorphoListedToken]
    vault_v2_addresses: frozenset[str]
    legacy_vault_addresses: frozenset[str]
    market_blacklist: frozenset[str]
    red_market_warnings: frozenset[str]
    red_vault_warnings: frozenset[str]

    @classmethod
    def load(cls, metadata_dir: Path, *, chain_id: int = _ARBITRUM_CHAIN_ID) -> MorphoApiMetadata:
        tokens = {
            token.address.lower(): token
            for token in _load_listed_tokens(metadata_dir / "tokens.json", chain_id=chain_id)
        }
        return cls(
            chain_id=chain_id,
            listed_tokens=tokens,
            vault_v2_addresses=_load_address_set(metadata_dir / "vaults-v2-listing.json", chain_id=chain_id),
            legacy_vault_addresses=_load_address_set(metadata_dir / "vaults-listing.json", chain_id=chain_id),
            market_blacklist=_load_market_id_set(metadata_dir / "markets-blacklist.json", chain_id=chain_id),
            red_market_warnings=_load_red_warning_targets(
                metadata_dir / "custom-warnings.json",
                chain_id=chain_id,
                target_field="marketId",
            ),
            red_vault_warnings=_load_red_warning_targets(
                metadata_dir / "custom-warnings.json",
                chain_id=chain_id,
                target_field="vaultAddress",
            ),
        )

    def is_token_listed(self, token: str) -> bool:
        return token.lower() in self.listed_tokens

    def should_skip_market(self, market_id: str) -> bool:
        normalized = market_id.lower()
        return normalized in self.market_blacklist or normalized in self.red_market_warnings

    def should_skip_vault(self, vault: str) -> bool:
        return vault.lower() in self.red_vault_warnings


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class MorphoLpClient(AsyncGraphqlAdapterClient):
    """Async Morpho Blue GraphQL client.

    Construct once per solver instance. Uses a shared `httpx.AsyncClient` for
    keepalive across calls. Caller owns the lifecycle (`async with`).

    Args:
        morpho_blue_address: Morpho Blue singleton address on Arbitrum (the
            on-chain contract). Recorded for logging / sanity, not used by
            the GraphQL stubs.
        morpho_api_url: GraphQL endpoint (canonical: api.morpho.org/graphql).
        timeout_sec: per-request httpx timeout.
        bearer_token: optional auth (Morpho's public API does not currently
            require one; reserved for future paid tiers).
        rpc_url: reserved for direct on-chain reads via web3.py. Not used by
            the GraphQL stubs; surfaced for forward-compat with on-chain
            position queries that bypass the indexer.
    """

    def __init__(
        self,
        morpho_blue_address: str,
        morpho_api_url: str,
        *,
        timeout_sec: float = 5.0,
        bearer_token: str | None = None,
        rpc_url: str | None = None,
    ) -> None:
        self._morpho_blue_address = morpho_blue_address
        self._rpc_url = rpc_url
        self._web3: Web3 | None = None
        super().__init__(
            morpho_api_url,
            timeout_sec=timeout_sec,
            bearer_token=bearer_token,
            config=GraphqlAdapterConfig(
                http_error_event="morpho_graphql_error",
                graphql_errors_event="morpho_graphql_errors",
                graphql_error_prefix="Morpho GraphQL errors",
                log=logger,
                log_context={
                    "morpho_blue_address": morpho_blue_address,
                    "morpho_api_url": morpho_api_url,
                },
            ),
        )

    # -- queries --------------------------------------------------------------

    async def list_markets(self) -> list[MorphoMarket]:
        """Fetch all Morpho Blue markets on the configured chain."""
        markets: list[MorphoMarket] = []
        skip = 0
        while True:
            data = await self._query(
                _LISTED_MARKETS_QUERY,
                {"chainIds": [_ARBITRUM_CHAIN_ID], "first": _GRAPHQL_PAGE_SIZE, "skip": skip},
            )
            items = _extract_items(data, "markets")
            markets.extend(_market_from_graphql(item) for item in items)
            if len(items) < _GRAPHQL_PAGE_SIZE:
                return markets
            skip += _GRAPHQL_PAGE_SIZE

    async def get_market(self, market_id: str) -> MorphoMarket:
        """Fetch one market by bytes32 id."""
        data = await self._query(
            _MARKET_BY_ID_QUERY,
            {"marketId": market_id, "chainId": _ARBITRUM_CHAIN_ID},
        )
        market = data.get("marketById")
        if market is None:
            raise ValueError(f"Morpho market not found: {market_id}")
        if not isinstance(market, dict):
            raise ValueError("unexpected Morpho marketById response")
        return _market_from_graphql(market)

    async def get_position(self, market_id: str, user: str) -> MorphoPosition:
        """Fetch a user's position in one market."""
        data = await self._query(
            _MARKET_POSITION_QUERY,
            {"marketId": market_id, "user": user, "chainId": _ARBITRUM_CHAIN_ID},
        )
        position = data.get("marketPosition")
        if position is None:
            raise ValueError(f"Morpho position not found: market={market_id} user={user}")
        if not isinstance(position, dict):
            raise ValueError("unexpected Morpho marketPosition response")
        return _position_from_graphql(position)

    async def get_priority_markets(self, market_ids: list[str]) -> list[MorphoMarket]:
        """Fetch multiple priority markets in one round-trip.

        Per `MORPHO_PRIORITY_MARKET_IDS` env var (comma-separated bytes32
        ids). The solver loop hot-paths these markets first.
        """
        if not market_ids:
            return []
        data = await self._query(
            _PRIORITY_MARKETS_QUERY,
            {"marketIds": market_ids, "chainIds": [_ARBITRUM_CHAIN_ID]},
        )
        return [_market_from_graphql(item) for item in _extract_items(data, "markets")]

    async def list_liquidation_candidates(
        self,
        markets: list[MorphoMarket],
        *,
        max_health_factor: Decimal = Decimal("1"),
        page_size: int = _GRAPHQL_PAGE_SIZE,
    ) -> list[MorphoLiquidationCandidate]:
        """List risky positions for the supplied markets.

        This is a read-side screen only. Morpho docs warn that liquidation can
        be griefed by a small front-run repay, so every candidate must be
        revalidated against live chain state immediately before submission.
        """
        if not markets:
            return []
        market_by_id = {market.id.lower(): market for market in markets}
        candidates: list[MorphoLiquidationCandidate] = []
        skip = 0
        while True:
            data = await self._query(
                _RISKY_MARKET_POSITIONS_QUERY,
                {
                    "marketIds": list(market_by_id),
                    "chainIds": [_ARBITRUM_CHAIN_ID],
                    "maxHealthFactor": float(max_health_factor),
                    "first": page_size,
                    "skip": skip,
                },
            )
            items = _extract_items(data, "marketPositions")
            for item in items:
                position = _position_from_graphql(item)
                market = market_by_id.get(position.market_id.lower())
                if market is not None:
                    candidates.append(MorphoLiquidationCandidate(market=market, position=position))
            if len(items) < page_size:
                return candidates
            skip += page_size

    def revalidate_liquidation_candidate_onchain(
        self,
        candidate: MorphoLiquidationCandidate,
    ) -> MorphoLiquidationRevalidation:
        """Read Morpho Blue directly before liquidation tx construction.

        This checks the market tuple and the borrower's current share balance.
        It deliberately does not recompute health from oracle values; that
        belongs in the transaction-planning/simulation layer after fresh
        market + position reads.
        """
        contract = self._morpho_contract()
        market_id = _bytes32(candidate.market.id)
        borrower = Web3.to_checksum_address(candidate.borrower)
        reasons: list[str] = []
        market_params: MorphoMarketParams | None = None
        position: MorphoOnchainPosition | None = None
        market_state: MorphoOnchainMarketState | None = None

        try:
            loan_token, collateral_token, oracle, irm, lltv = cast(
                "tuple[str, str, str, str, int]",
                contract.functions.idToMarketParams(market_id).call(),
            )
            market_params = MorphoMarketParams(
                loan_token=loan_token,
                collateral_token=collateral_token,
                oracle=oracle,
                irm=irm,
                lltv=int(lltv),
            )
            if market_params.id().lower() != candidate.market.id.lower():
                reasons.append("market_params_id_mismatch")
            if loan_token.lower() != candidate.market.loan_token.lower():
                reasons.append("loan_token_mismatch")
            if collateral_token.lower() != candidate.market.collateral_token.lower():
                reasons.append("collateral_token_mismatch")
            if oracle.lower() != candidate.market.oracle_address.lower():
                reasons.append("oracle_mismatch")
            if irm.lower() != candidate.market.irm_address.lower():
                reasons.append("irm_mismatch")
            if int(lltv) != candidate.market.lltv:
                reasons.append("lltv_mismatch")
        except ValueError:
            reasons.append("market_not_created_or_zero_params")

        supply_shares, borrow_shares, collateral = cast(
            "tuple[int, int, int]",
            contract.functions.position(market_id, borrower).call(),
        )
        position = MorphoOnchainPosition(
            supply_shares=int(supply_shares),
            borrow_shares=int(borrow_shares),
            collateral=int(collateral),
        )
        if position.borrow_shares == 0:
            reasons.append("no_borrow_shares")
        if position.borrow_shares < candidate.repay_shares:
            reasons.append("candidate_repay_shares_exceed_onchain_borrow_shares")

        total_supply_assets, total_supply_shares, total_borrow_assets, total_borrow_shares, last_update, fee = cast(
            "tuple[int, int, int, int, int, int]",
            contract.functions.market(market_id).call(),
        )
        market_state = MorphoOnchainMarketState(
            total_supply_assets=int(total_supply_assets),
            total_supply_shares=int(total_supply_shares),
            total_borrow_assets=int(total_borrow_assets),
            total_borrow_shares=int(total_borrow_shares),
            last_update=int(last_update),
            fee=int(fee),
        )
        if market_state.total_borrow_shares == 0:
            reasons.append("market_has_no_borrow_shares")

        return MorphoLiquidationRevalidation(
            candidate=candidate,
            market_params=market_params,
            position=position,
            market_state=market_state,
            reasons=tuple(reasons),
        )

    def plan_standard_liquidation(
        self,
        candidate: MorphoLiquidationCandidate,
        *,
        max_repay_shares: int | None = None,
        data: bytes = b"",
    ) -> MorphoLiquidationPlan:
        """Build standard Morpho Blue `liquidate` calldata for a candidate.

        This is the live-readiness bridge after GraphQL screening:

        1. revalidate `idToMarketParams`, `position`, and `market` on-chain;
        2. read the market oracle directly;
        3. recompute Morpho's healthy check with virtual-share rounding;
        4. emit calldata for `liquidate(marketParams, borrower, 0, repayShares, data)`.

        Raises `ValueError` for stale/healthy candidates or invalid repay
        sizing. The returned calldata targets the Morpho Blue singleton, not
        the Executor; transaction composition remains the coordinator's job.
        """
        revalidation = self.revalidate_liquidation_candidate_onchain(candidate)
        if not revalidation.valid:
            raise ValueError("cannot plan Morpho liquidation for invalid candidate: " + ", ".join(revalidation.reasons))
        if revalidation.market_params is None or revalidation.position is None or revalidation.market_state is None:
            raise ValueError("cannot plan Morpho liquidation without complete on-chain revalidation")

        collateral_price = self._oracle_price(revalidation.market_params.oracle)
        return build_standard_liquidation_plan(
            revalidation,
            collateral_price=collateral_price,
            max_repay_shares=max_repay_shares,
            data=data,
        )

    def _morpho_contract(self) -> _MorphoBlueContract:
        if self._rpc_url is None:
            raise ValueError("rpc_url is required for Morpho on-chain revalidation")
        if self._web3 is None:
            self._web3 = Web3(Web3.HTTPProvider(self._rpc_url))
        return cast(
            "_MorphoBlueContract",
            self._web3.eth.contract(
                address=Web3.to_checksum_address(self._morpho_blue_address),
                abi=_MORPHO_BLUE_ABI,
            ),
        )

    def _oracle_price(self, oracle_address: str) -> int:
        if self._rpc_url is None:
            raise ValueError("rpc_url is required for Morpho oracle reads")
        if self._web3 is None:
            self._web3 = Web3(Web3.HTTPProvider(self._rpc_url))
        oracle = cast(
            "_OracleContract",
            self._web3.eth.contract(
                address=Web3.to_checksum_address(oracle_address),
                abi=_ORACLE_ABI,
            ),
        )
        price = cast("int | str", oracle.functions.price().call())
        return int(price)


def configure_logging(level: str) -> None:
    """Mirror the AaveV4 adapter logging configuration."""
    configure_execution_logging(level)


def _encode_address(address: str) -> bytes:
    try:
        raw = bytes.fromhex(address.removeprefix("0x"))
    except ValueError as exc:
        raise ValueError(f"invalid address hex: {address!r}") from exc
    if len(raw) != _EVM_ADDRESS_BYTES or int.from_bytes(raw, "big") == 0:
        raise ValueError(f"expected non-zero 20-byte address, got {address!r}")
    return raw.rjust(32, b"\x00")


def _bytes32(value: str) -> bytes:
    raw = bytes.fromhex(value.removeprefix("0x"))
    if len(raw) != _BYTES32_BYTES:
        raise ValueError(f"expected bytes32 hex string, got {value!r}")
    return raw


def filter_markets_for_metadata(
    markets: list[MorphoMarket],
    metadata: MorphoApiMetadata,
    *,
    require_listed_tokens: bool = True,
) -> list[MorphoMarket]:
    """Apply cached Morpho metadata as a fail-closed screening layer."""
    filtered: list[MorphoMarket] = []
    for market in markets:
        if metadata.should_skip_market(market.id):
            continue
        if require_listed_tokens and (
            not metadata.is_token_listed(market.loan_token) or not metadata.is_token_listed(market.collateral_token)
        ):
            continue
        filtered.append(market)
    return filtered


def rank_liquidation_candidates_for_screening(
    candidates: list[MorphoLiquidationCandidate],
    *,
    config: MorphoLiquidationRankingConfig | None = None,
) -> list[MorphoLiquidationPriority]:
    """Rank Morpho liquidation candidates for the next validation stage.

    The first-pass GraphQL list is health-factor ordered, but Morpho's profit
    surface is mostly driven by LLTV-derived LIF, repay size, execution costs,
    swap-back capacity, bad-debt policy, and oracle risk. This helper makes
    those gates explicit while staying read-only.

    `swap_back_liquidity_usd_by_collateral_token` is an optional fail-closed
    proxy until exact seized-collateral swap-back quotes are generated. When
    supplied with `require_swap_back_liquidity=True`, missing or insufficient
    collateral-token liquidity filters the candidate out.
    """
    config = config or MorphoLiquidationRankingConfig()
    if config.estimated_gas_cost_usd < 0:
        raise ValueError(f"estimated_gas_cost_usd must be non-negative, got {config.estimated_gas_cost_usd}")
    if config.min_net_edge_usd < 0:
        raise ValueError(f"min_net_edge_usd must be non-negative, got {config.min_net_edge_usd}")

    priorities: list[MorphoLiquidationPriority] = []
    for candidate in candidates:
        market = candidate.market
        position = candidate.position
        borrow_usd = position.borrow_assets_usd
        collateral_usd = position.collateral_usd
        if borrow_usd <= 0:
            continue

        bad_debt_risk = collateral_usd < borrow_usd
        if bad_debt_risk and not config.include_bad_debt:
            continue

        swap_back_liquidity_usd: Decimal | None = None
        swap_back_shortfall_usd = Decimal("0")
        if config.swap_back_liquidity_usd_by_collateral_token is not None:
            swap_back_liquidity_usd = _decimal_mapping_value(
                config.swap_back_liquidity_usd_by_collateral_token,
                market.collateral_token,
            )
            swap_back_shortfall_usd = max(borrow_usd - swap_back_liquidity_usd, Decimal("0"))
            if config.require_swap_back_liquidity and swap_back_shortfall_usd > 0:
                continue

        bonus_bps = market.liquidation_bonus_bps
        gross_bonus_usd = _usd_cost_from_bps(borrow_usd, bonus_bps, "liquidation_bonus_bps")
        estimated_flash_fee_usd = _usd_cost_from_bps(
            borrow_usd,
            _bps_mapping_value(config.flash_fee_bps_by_loan_token, market.loan_token),
            "flash_fee_bps",
        )
        estimated_swap_cost_usd = _usd_cost_from_bps(
            borrow_usd,
            _bps_mapping_value(config.swap_cost_bps_by_collateral_token, market.collateral_token),
            "swap_cost_bps",
        )
        oracle_risk_penalty_usd = _usd_cost_from_bps(
            borrow_usd,
            _bps_mapping_value(config.oracle_risk_bps_by_market_id, market.id),
            "oracle_risk_bps",
        )
        net_edge_usd = (
            gross_bonus_usd
            - estimated_flash_fee_usd
            - estimated_swap_cost_usd
            - config.estimated_gas_cost_usd
            - oracle_risk_penalty_usd
        )
        if net_edge_usd < config.min_net_edge_usd:
            continue

        priorities.append(
            MorphoLiquidationPriority(
                candidate=candidate,
                liquidation_bonus_bps=bonus_bps,
                borrow_assets_usd=borrow_usd,
                collateral_usd=collateral_usd,
                gross_bonus_usd=gross_bonus_usd,
                estimated_flash_fee_usd=estimated_flash_fee_usd,
                estimated_swap_cost_usd=estimated_swap_cost_usd,
                estimated_gas_cost_usd=config.estimated_gas_cost_usd,
                oracle_risk_penalty_usd=oracle_risk_penalty_usd,
                net_edge_usd=net_edge_usd,
                bad_debt_risk=bad_debt_risk,
                swap_back_liquidity_usd=swap_back_liquidity_usd,
                swap_back_liquidity_shortfall_usd=swap_back_shortfall_usd,
            )
        )

    priorities.sort(
        key=lambda priority: (
            -priority.net_edge_usd,
            -Decimal(priority.liquidation_bonus_bps),
            -priority.borrow_assets_usd,
            priority.health_factor,
            priority.market_id.lower(),
            priority.borrower.lower(),
        )
    )
    return priorities


def ranking_config_from_live_risk_feeds(
    feeds: MorphoLiquidationLiveRiskFeeds,
) -> MorphoLiquidationRankingConfig:
    """Convert live gas/liquidity/risk feeds into ranker config.

    This is intentionally pure. Quote sources, gas oracles, and oracle-risk
    classifiers live outside the ranker; this helper only normalizes those
    live inputs into the deterministic screening policy shape.
    """
    if feeds.estimated_gas_units < 0:
        raise ValueError(f"estimated_gas_units must be non-negative, got {feeds.estimated_gas_units}")
    if feeds.gas_price_wei < 0:
        raise ValueError(f"gas_price_wei must be non-negative, got {feeds.gas_price_wei}")
    if feeds.eth_price_usd < 0:
        raise ValueError(f"eth_price_usd must be non-negative, got {feeds.eth_price_usd}")
    estimated_gas_cost_usd = (
        Decimal(feeds.estimated_gas_units) * Decimal(feeds.gas_price_wei) * feeds.eth_price_usd / Decimal(10**18)
    )
    return MorphoLiquidationRankingConfig(
        estimated_gas_cost_usd=estimated_gas_cost_usd,
        flash_fee_bps_by_loan_token=feeds.flash_fee_bps_by_loan_token,
        swap_cost_bps_by_collateral_token=feeds.swap_cost_bps_by_collateral_token,
        oracle_risk_bps_by_market_id=feeds.oracle_risk_bps_by_market_id,
        swap_back_liquidity_usd_by_collateral_token=feeds.swap_back_liquidity_usd_by_collateral_token,
        include_bad_debt=feeds.include_bad_debt,
        require_swap_back_liquidity=feeds.require_swap_back_liquidity,
        min_net_edge_usd=feeds.min_net_edge_usd,
    )


def liquidation_incentive_factor_wad(lltv: int) -> int:
    """Return Morpho Blue's liquidation incentive factor for an LLTV.

    Source formula from `Morpho.sol`:
    `min(MAX_LIF, WAD / (WAD - LIQUIDATION_CURSOR * (WAD - lltv)))`.

    All arithmetic mirrors Solidity's wad `wMulDown` / `wDivDown` rounding.
    """
    if lltv < 0 or lltv >= _WAD:
        raise ValueError(f"Morpho LLTV must be in [0, 1e18), got {lltv}")
    denominator = _WAD - _mul_div_down(_LIQUIDATION_CURSOR, _WAD - lltv, _WAD)
    if denominator <= 0:
        raise ValueError(f"Morpho LIF denominator must be positive, got {denominator}")
    return min(_MAX_LIQUIDATION_INCENTIVE_FACTOR, _mul_div_down(_WAD, _WAD, denominator))


def liquidation_bonus_bps(lltv: int) -> int:
    """Return the Morpho Blue liquidation bonus in basis points, floored."""
    lif = liquidation_incentive_factor_wad(lltv)
    return _mul_div_down(lif - _WAD, 10_000, _WAD)


def build_standard_liquidation_plan(
    revalidation: MorphoLiquidationRevalidation,
    *,
    collateral_price: int,
    max_repay_shares: int | None = None,
    data: bytes = b"",
) -> MorphoLiquidationPlan:
    """Pure standard Morpho Blue liquidation planner.

    Mirrors Morpho Blue's `_isHealthy` calculation:

    - borrowed assets = `borrowShares.toAssetsUp(totalBorrowAssets, totalBorrowShares)`
    - collateral value = `collateral * oracle.price() / ORACLE_PRICE_SCALE`
    - max borrow = `collateralValue * lltv / WAD`

    The plan uses the `repaidShares` branch of `liquidate`, so `seizedAssets`
    is encoded as zero and the on-chain contract derives seized collateral at
    execution time from the then-current state.
    """
    if not revalidation.valid:
        raise ValueError(
            "cannot build Morpho liquidation plan for invalid revalidation: " + ", ".join(revalidation.reasons)
        )
    if revalidation.market_params is None or revalidation.position is None or revalidation.market_state is None:
        raise ValueError("cannot build Morpho liquidation plan without complete revalidation")
    if collateral_price <= 0:
        raise ValueError(f"Morpho oracle price must be > 0, got {collateral_price}")

    position = revalidation.position
    market_state = revalidation.market_state
    market_params = revalidation.market_params
    borrowed_assets = _to_assets_up(
        position.borrow_shares,
        market_state.total_borrow_assets,
        market_state.total_borrow_shares,
    )
    collateral_value_assets = _mul_div_down(
        position.collateral,
        collateral_price,
        _ORACLE_PRICE_SCALE,
    )
    max_borrow_assets = _mul_div_down(collateral_value_assets, market_params.lltv, _WAD)
    health_factor_wad = _mul_div_down(max_borrow_assets, _WAD, borrowed_assets) if borrowed_assets > 0 else 2**256 - 1
    if max_borrow_assets >= borrowed_assets:
        raise ValueError("cannot liquidate healthy Morpho position")

    repay_shares = position.borrow_shares
    if max_repay_shares is not None:
        if max_repay_shares <= 0:
            raise ValueError(f"max_repay_shares must be > 0, got {max_repay_shares}")
        repay_shares = min(repay_shares, max_repay_shares)
    if repay_shares <= 0:
        raise ValueError("Morpho liquidation repay_shares must be > 0")
    repay_assets = _to_assets_up(
        repay_shares,
        market_state.total_borrow_assets,
        market_state.total_borrow_shares,
    )

    calldata = encode_morpho_liquidate_calldata(
        market_params,
        borrower=revalidation.candidate.borrower,
        seized_assets=0,
        repaid_shares=repay_shares,
        data=data,
    )
    return MorphoLiquidationPlan(
        revalidation=revalidation,
        collateral_price=collateral_price,
        borrowed_assets=borrowed_assets,
        repay_assets=repay_assets,
        collateral_value_assets=collateral_value_assets,
        max_borrow_assets=max_borrow_assets,
        health_factor_wad=health_factor_wad,
        repay_shares=repay_shares,
        calldata=calldata,
    )


def build_standard_liquidation_candidate_payload(
    priority: MorphoLiquidationPriority,
    plan: MorphoLiquidationPlan,
    *,
    expected_collateral_seized: int | None = None,
) -> MorphoStandardLiquidationCandidatePayload:
    """Build the deterministic Stage 1 standard-liquidation candidate payload.

    `priority` supplies the LIF-aware economic ranking and explicit risk
    costs. `plan` supplies on-chain revalidation, selected `repaidShares`, and
    exact Morpho health math. Both inputs are already read-only; this helper
    performs no RPC and is safe for offline fixture tests.
    """
    if priority.candidate != plan.revalidation.candidate:
        raise ValueError("ranking priority and liquidation plan must reference the same Morpho candidate")
    if not plan.revalidation.valid:
        raise ValueError("cannot build payload from invalid Morpho revalidation")
    if plan.revalidation.market_params is None:
        raise ValueError("cannot build payload without full on-chain MarketParams")
    if plan.repay_shares <= 0:
        raise ValueError("Morpho standard-liquidation payload requires repaidShares > 0")

    market = priority.candidate.market
    market_params = plan.revalidation.market_params
    if market_params.loan_token.lower() != market.loan_token.lower():
        raise ValueError("payload MarketParams loan token must match ranked market")
    if market_params.collateral_token.lower() != market.collateral_token.lower():
        raise ValueError("payload MarketParams collateral token must match ranked market")

    resolved_expected_collateral = (
        estimate_standard_liquidation_collateral_seized(plan)
        if expected_collateral_seized is None
        else expected_collateral_seized
    )
    if resolved_expected_collateral < 0:
        raise ValueError(f"expected_collateral_seized must be non-negative, got {resolved_expected_collateral}")

    return MorphoStandardLiquidationCandidatePayload(
        market_id=priority.market_id,
        market_params=market_params,
        borrower=priority.borrower,
        repaid_shares=plan.repay_shares,
        loan_token=market.loan_token,
        collateral_token=market.collateral_token,
        repay_assets=plan.repay_assets,
        expected_collateral_seized=resolved_expected_collateral,
        health_factor_wad=plan.health_factor_wad,
        liquidation_bonus_bps=priority.liquidation_bonus_bps,
        borrow_assets_usd=priority.borrow_assets_usd,
        collateral_usd=priority.collateral_usd,
        gross_bonus_usd=priority.gross_bonus_usd,
        ranking_score_usd=priority.net_edge_usd,
        risk_costs=MorphoLiquidationRiskCosts(
            estimated_flash_fee_usd=priority.estimated_flash_fee_usd,
            estimated_swap_cost_usd=priority.estimated_swap_cost_usd,
            estimated_gas_cost_usd=priority.estimated_gas_cost_usd,
            oracle_risk_penalty_usd=priority.oracle_risk_penalty_usd,
            swap_back_liquidity_usd=priority.swap_back_liquidity_usd,
            swap_back_liquidity_shortfall_usd=priority.swap_back_liquidity_shortfall_usd,
        ),
        bad_debt_classification="bad_debt" if priority.bad_debt_risk else "collateralized",
    )


def estimate_standard_liquidation_collateral_seized(plan: MorphoLiquidationPlan) -> int:
    """Estimate Morpho's `seizedAssets` for a repaid-shares liquidation plan.

    Mirrors Morpho Blue's `repaidShares > 0` branch:
    `shares.toAssetsDown(...).wMulDown(LIF).mulDivDown(ORACLE_PRICE_SCALE, price)`.
    The returned value is a planning estimate only; Morpho recomputes it
    inside `liquidate` against the latest accrued market state.
    """
    if plan.revalidation.market_params is None or plan.revalidation.market_state is None:
        raise ValueError("cannot estimate seized collateral without MarketParams and market state")
    if plan.collateral_price <= 0:
        raise ValueError(f"Morpho oracle price must be > 0, got {plan.collateral_price}")
    repaid_assets_down = _to_assets_down(
        plan.repay_shares,
        plan.revalidation.market_state.total_borrow_assets,
        plan.revalidation.market_state.total_borrow_shares,
    )
    lif = liquidation_incentive_factor_wad(plan.revalidation.market_params.lltv)
    liquidation_bonus_assets = _mul_div_down(repaid_assets_down, lif, _WAD)
    return _mul_div_down(liquidation_bonus_assets, _ORACLE_PRICE_SCALE, plan.collateral_price)


def compose_standard_liquidation_executor_path(
    plan: MorphoLiquidationPlan,
    *,
    morpho_blue_address: str,
    swap_back_quote: MorphoSwapBackQuote,
) -> tuple[MorphoLiquidationSwapStep, MorphoLiquidationSwapStep]:
    """Compose liquidation + collateral swap-back into Executor swap steps.

    `swap_back_quote` must be an executable exact-sell quote from seized
    collateral into the flash token. The Morpho step's `amountOutMin` is set
    to the quote sell amount so the aggregator calldata cannot execute unless
    the liquidation seized at least the collateral amount embedded in the
    quote. The second step uses `amount_in = 0`, so Executor approves the
    actual carry from the liquidation step while the router calldata still
    controls the exact amount spent.
    """
    market = plan.revalidation.candidate.market
    if swap_back_quote.sell_token.lower() != market.collateral_token.lower():
        raise ValueError("swap-back quote sell_token must match Morpho collateral token")
    if swap_back_quote.buy_token.lower() != market.loan_token.lower():
        raise ValueError("swap-back quote buy_token must match Morpho loan/flash token")
    sell_amount = swap_back_quote.sell_amount
    buy_amount = swap_back_quote.buy_amount
    if sell_amount <= 0:
        raise ValueError(f"swap-back quote sell_amount must be > 0, got {sell_amount}")
    if buy_amount <= 0:
        raise ValueError(f"swap-back quote buy_amount must be > 0, got {buy_amount}")
    if not swap_back_quote.calldata or swap_back_quote.calldata == "0x":
        raise ValueError("swap-back quote must include executable calldata")

    liquidation_step = plan.to_executor_swap_step(
        morpho_blue_address=morpho_blue_address,
        amount_out_min=sell_amount,
    )
    swap_back_step = MorphoLiquidationSwapStep(
        pool=swap_back_quote.router,
        router=swap_back_quote.router,
        call_data=swap_back_quote.calldata,
        token_in=market.collateral_token,
        token_out=market.loan_token,
        amount_in=0,
        amount_out_min=buy_amount,
        zero_for_one=False,
        dex="AggregatorV6",
    )
    return liquidation_step, swap_back_step


def encode_morpho_liquidate_calldata(
    market_params: MorphoMarketParams,
    *,
    borrower: str,
    seized_assets: int,
    repaid_shares: int,
    data: bytes = b"",
) -> bytes:
    """ABI-encode Morpho Blue `liquidate` calldata.

    Signature:
    `liquidate((address,address,address,address,uint256),address,uint256,uint256,bytes)`.
    """
    if seized_assets < 0:
        raise ValueError(f"seized_assets must be non-negative, got {seized_assets}")
    if repaid_shares < 0:
        raise ValueError(f"repaid_shares must be non-negative, got {repaid_shares}")
    if (seized_assets == 0) == (repaid_shares == 0):
        raise ValueError("Morpho liquidate requires exactly one of seized_assets or repaid_shares to be zero")

    head = b"".join(
        (
            _encode_address(market_params.loan_token),
            _encode_address(market_params.collateral_token),
            _encode_address(market_params.oracle),
            _encode_address(market_params.irm),
            _encode_uint256(market_params.lltv),
            _encode_address(borrower),
            _encode_uint256(seized_assets),
            _encode_uint256(repaid_shares),
            _encode_uint256(9 * _BYTES32_BYTES),
        )
    )
    return _LIQUIDATE_SELECTOR + head + _encode_bytes(data)


def _extract_items(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    container = data.get(key)
    if not isinstance(container, dict):
        raise ValueError(f"unexpected Morpho GraphQL response: missing {key}")
    items = container.get("items")
    if not isinstance(items, list):
        raise ValueError(f"unexpected Morpho GraphQL response: missing {key}.items")
    return [cast("dict[str, Any]", item) for item in items if isinstance(item, dict)]


def _market_from_graphql(item: dict[str, Any]) -> MorphoMarket:
    state = _object_field(item, "state")
    loan_asset = _object_field(item, "loanAsset")
    collateral_asset = _object_field(item, "collateralAsset")
    oracle = _object_field(item, "oracle")
    return MorphoMarket(
        id=_string_field(item, "marketId"),
        loan_token=_string_field(loan_asset, "address"),
        collateral_token=_string_field(collateral_asset, "address"),
        lltv=_int_field(item, "lltv"),
        irm_address=_string_field(item, "irmAddress"),
        oracle_address=_string_field(oracle, "address"),
        supply_apy_str=_decimal_string_field(state, "supplyApy"),
        borrow_apy_str=_decimal_string_field(state, "borrowApy"),
        total_supply_assets_str=_int_string_field(state, "supplyAssets"),
        total_borrow_assets_str=_int_string_field(state, "borrowAssets"),
        fee_str=_decimal_string_field(state, "fee"),
        last_update_ts=_int_field(state, "timestamp"),
        loan_token_symbol=_string_field(loan_asset, "symbol"),
        loan_token_decimals=_int_field(loan_asset, "decimals"),
        collateral_token_symbol=_string_field(collateral_asset, "symbol"),
        collateral_token_decimals=_int_field(collateral_asset, "decimals"),
        utilization_str=_decimal_string_field(state, "utilization"),
    )


def _position_from_graphql(item: dict[str, Any]) -> MorphoPosition:
    state = _object_field(item, "state")
    market = _object_field(item, "market")
    user = _object_field(item, "user")
    return MorphoPosition(
        market_id=_string_field(market, "marketId"),
        user=_string_field(user, "address"),
        supply_shares_str=_int_string_field(state, "supplyShares"),
        borrow_shares_str=_int_string_field(state, "borrowShares"),
        collateral_str=_int_string_field(state, "collateral"),
        supply_assets_str=_int_string_field(state, "supplyAssets"),
        borrow_assets_str=_int_string_field(state, "borrowAssets"),
        borrow_assets_usd_str=_decimal_string_field(state, "borrowAssetsUsd"),
        collateral_usd_str=_decimal_string_field(state, "collateralUsd"),
        health_factor_str=_decimal_string_field(item, "healthFactor"),
    )


def _object_field(item: dict[str, Any], key: str) -> dict[str, Any]:
    value = item.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"expected object field in Morpho GraphQL response: {key}")
    return cast("dict[str, Any]", value)


def _string_field(item: dict[str, Any], key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or value == "":
        raise ValueError(f"expected non-empty string field in Morpho GraphQL response: {key}")
    return value


def _int_field(item: dict[str, Any], key: str) -> int:
    value = item.get(key)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value)
    raise ValueError(f"expected integer field in Morpho GraphQL response: {key}")


def _int_string_field(item: dict[str, Any], key: str) -> str:
    value = item.get(key)
    if isinstance(value, int | str):
        return str(value)
    raise ValueError(f"expected integer-like field in Morpho GraphQL response: {key}")


def _decimal_string_field(item: dict[str, Any], key: str) -> str:
    value = item.get(key)
    if isinstance(value, int | str):
        return str(value)
    if isinstance(value, float):
        return Decimal(str(value)).to_eng_string()
    raise ValueError(f"expected decimal-like field in Morpho GraphQL response: {key}")


def _market_params_to_wire(market_params: MorphoMarketParams) -> JsonObject:
    return {
        "loanToken": market_params.loan_token,
        "collateralToken": market_params.collateral_token,
        "oracle": market_params.oracle,
        "irm": market_params.irm,
        "lltv": str(market_params.lltv),
    }


def _decimal_to_wire(value: Decimal) -> str:
    return value.to_eng_string()


def _bps_mapping_value(mapping: Mapping[str, int] | None, key: str) -> int:
    if mapping is None:
        return 0
    value = mapping.get(key.lower(), mapping.get(key, 0))
    if value < 0:
        raise ValueError(f"basis-point input must be non-negative, got {value}")
    return value


def _decimal_mapping_value(mapping: Mapping[str, Decimal], key: str) -> Decimal:
    value = mapping.get(key.lower(), mapping.get(key, Decimal("0")))
    if value < 0:
        raise ValueError(f"USD liquidity input must be non-negative, got {value}")
    return value


def _usd_cost_from_bps(notional_usd: Decimal, bps: int, label: str) -> Decimal:
    if bps < 0:
        raise ValueError(f"{label} must be non-negative, got {bps}")
    return notional_usd * Decimal(bps) / Decimal(10_000)


def _read_json_objects(path: Path) -> list[dict[str, object]]:
    try:
        raw = json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise ValueError(f"missing Morpho metadata file: {path}") from exc
    if not isinstance(raw, list):
        raise ValueError(f"expected JSON array in Morpho metadata file: {path}")
    objects: list[dict[str, object]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError(f"expected object entries in Morpho metadata file: {path}")
        objects.append(item)
    return objects


def _load_listed_tokens(path: Path, *, chain_id: int) -> list[MorphoListedToken]:
    tokens: list[MorphoListedToken] = []
    for item in _read_json_objects(path):
        if item.get("chainId") != chain_id or item.get("isListed") is not True:
            continue
        metadata = item.get("metadata")
        tags_raw = metadata.get("tags", []) if isinstance(metadata, dict) else []
        tags = tuple(tag for tag in tags_raw if isinstance(tag, str)) if isinstance(tags_raw, list) else ()
        tokens.append(
            MorphoListedToken(
                chain_id=chain_id,
                address=_metadata_str(item, "address"),
                symbol=_metadata_str(item, "symbol"),
                decimals=_metadata_int(item, "decimals"),
                tags=tags,
            )
        )
    return tokens


def _load_address_set(path: Path, *, chain_id: int) -> frozenset[str]:
    return frozenset(
        _metadata_str(item, "address").lower() for item in _read_json_objects(path) if item.get("chainId") == chain_id
    )


def _load_market_id_set(path: Path, *, chain_id: int) -> frozenset[str]:
    return frozenset(
        _metadata_str(item, "id").lower() for item in _read_json_objects(path) if item.get("chainId") == chain_id
    )


def _load_red_warning_targets(path: Path, *, chain_id: int, target_field: str) -> frozenset[str]:
    return frozenset(
        _metadata_str(item, target_field).lower()
        for item in _read_json_objects(path)
        if item.get("chainId") == chain_id and item.get("level") == "red" and isinstance(item.get(target_field), str)
    )


def _metadata_str(item: dict[str, object], key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or value == "":
        raise ValueError(f"expected non-empty string metadata field: {key}")
    return value


def _metadata_int(item: dict[str, object], key: str) -> int:
    value = item.get(key)
    if not isinstance(value, int):
        raise ValueError(f"expected integer metadata field: {key}")
    return value


def _to_assets_up(shares: int, total_assets: int, total_shares: int) -> int:
    return _mul_div_up(shares, total_assets + _VIRTUAL_ASSETS, total_shares + _VIRTUAL_SHARES)


def _to_assets_down(shares: int, total_assets: int, total_shares: int) -> int:
    return _mul_div_down(shares, total_assets + _VIRTUAL_ASSETS, total_shares + _VIRTUAL_SHARES)


def _mul_div_down(x: int, y: int, denominator: int) -> int:
    if denominator <= 0:
        raise ValueError("denominator must be > 0")
    return x * y // denominator


def _mul_div_up(x: int, y: int, denominator: int) -> int:
    if denominator <= 0:
        raise ValueError("denominator must be > 0")
    product = x * y
    return (product + denominator - 1) // denominator


def _encode_uint256(value: int) -> bytes:
    if not 0 <= value < 2**256:
        raise ValueError(f"expected uint256-compatible value, got {value}")
    return value.to_bytes(32, "big")


def _encode_bytes(value: bytes) -> bytes:
    padding = (-len(value)) % _BYTES32_BYTES
    return _encode_uint256(len(value)) + value + (b"\x00" * padding)
