"""Morpho Blue pre-liquidation discovery adapter.

This module is read-only. It mirrors the official Morpho liquidation bot's
HyperIndex query shape for `PreLiquidationContract` rows and exposes small
typed helpers the solver can use before deciding whether to build a normal
Morpho liquidation or a pre-liquidation path.

The indexed `market_id` is not the bare Morpho Blue bytes32 id. The official
HyperIndex stores it as `<chainId>-<marketId>`, for example
`42161-0x...`. Keep that distinction explicit at this boundary.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, Protocol, cast

import structlog
from web3 import Web3

from driver.execution.adapter_base import (
    AsyncGraphqlAdapterClient,
    GraphqlAdapterConfig,
    configure_execution_logging,
)

logger = structlog.get_logger(__name__).bind(
    service="solver",
    component="execution.morpho_preliquidation_adapter",
)

ARBITRUM_CHAIN_ID: Final[int] = 42161
WAD: Final[int] = 10**18
ORACLE_PRICE_SCALE: Final[int] = 10**36
ZERO_ADDRESS: Final[str] = "0x0000000000000000000000000000000000000000"

_EVM_ADDRESS_RE: Final[re.Pattern[str]] = re.compile(r"^0x[0-9a-fA-F]{40}$")
_BYTES32_RE: Final[re.Pattern[str]] = re.compile(r"^0x[0-9a-fA-F]{64}$")
_MORPHO_BLUE_ABI: Final[list[dict[str, object]]] = [
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
_ORACLE_ABI: Final[list[dict[str, object]]] = [
    {
        "type": "function",
        "name": "price",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}],
    },
]

PRELIQUIDATION_CONTRACTS_QUERY: Final[str] = """
query GetPreLiquidationContracts($marketIds: [String!]!) {
  PreLiquidationContract(where: { market_id: { _in: $marketIds } }) {
    market_id
    address
    preLltv
    preLCF1
    preLCF2
    preLIF1
    preLIF2
    preLiquidationOracle
  }
}
"""

PRELIQUIDATION_AUTHORIZATIONS_QUERY: Final[str] = """
query GetAuthorizations($chainId: Int!, $authorizees: [String!]!) {
  Authorization(
    where: {
      isAuthorized: { _eq: true }
      chainId: { _eq: $chainId }
      authorizee: { _in: $authorizees }
    }
  ) {
    authorizer
    authorizee
  }
}
"""

PRELIQUIDATION_POSITIONS_QUERY: Final[str] = """
query GetPositions($marketIds: [String!]!, $limit: Int!, $offset: Int!) {
  Position(
    where: { market_id: { _in: $marketIds }, borrowShares: { _gt: "0" } }
    limit: $limit
    offset: $offset
  ) {
    user
    market_id
    supplyShares
    borrowShares
    collateral
  }
}
"""

PRELIQUIDATION_POSITIONS_PAGE_SIZE: Final[int] = 1000


class _ContractCall(Protocol):
    def call(self) -> object: ...


class _MorphoBlueFunctions(Protocol):
    def idToMarketParams(self, market_id: bytes) -> _ContractCall: ...  # noqa: N802
    def position(self, market_id: bytes, user: str) -> _ContractCall: ...
    def market(self, market_id: bytes) -> _ContractCall: ...


class _MorphoBlueContract(Protocol):
    functions: _MorphoBlueFunctions


@dataclass(frozen=True)
class MorphoPreLiquidationContract:
    """Indexed Morpho pre-liquidation contract configuration."""

    chain_id: int
    market_id: str
    address: str
    pre_lltv: int
    pre_lcf1: int
    pre_lcf2: int
    pre_lif1: int
    pre_lif2: int
    pre_liquidation_oracle: str

    @property
    def hyperindex_market_id(self) -> str:
        """Return the official bot's indexed market id."""
        return hyperindex_market_id(self.chain_id, self.market_id)

    @property
    def hyperindex_contract_id(self) -> str:
        """Return the official bot's indexed pre-liquidation contract id."""
        return f"{self.chain_id}-{self.market_id}-{self.address}"

    @property
    def params_tuple(self) -> tuple[int, int, int, int, int, str]:
        """Return pre-liquidation params in factory event order."""
        return (
            self.pre_lltv,
            self.pre_lcf1,
            self.pre_lcf2,
            self.pre_lif1,
            self.pre_lif2,
            self.pre_liquidation_oracle,
        )

    def screening_reject_reasons(self, market_lltv: int) -> tuple[str, ...]:
        """Return deterministic reasons this config should not be targeted.

        This is intentionally conservative and local. It checks the public
        shape needed by a solver before any live authorization/position query.
        """
        reasons: list[str] = []

        if not is_bytes32(self.market_id):
            reasons.append("market_id must be a bytes32 hex string")
        if not is_address(self.address) or self.address.lower() == ZERO_ADDRESS:
            reasons.append("pre-liquidation contract address must be non-zero")
        if not is_address(self.pre_liquidation_oracle):
            reasons.append("pre-liquidation oracle must be an address")
        if market_lltv <= 0 or market_lltv > WAD:
            reasons.append("market LLTV must be in (0, 1e18]")
        else:
            if self.pre_lltv >= market_lltv:
                reasons.append("preLLTV must be below market LLTV")
            max_pre_lif = (WAD * WAD) // market_lltv
            if self.pre_lif1 > max_pre_lif or self.pre_lif2 > max_pre_lif:
                reasons.append("preLIF must not exceed 1 / market LLTV")

        if self.pre_lcf1 > self.pre_lcf2:
            reasons.append("preLCF1 must be <= preLCF2")
        if self.pre_lcf1 > WAD:
            reasons.append("preLCF1 must be <= 1e18")
        if self.pre_lif1 < WAD or self.pre_lif2 < WAD:
            reasons.append("preLIF must be >= 1e18")
        if self.pre_lif1 > self.pre_lif2:
            reasons.append("preLIF1 must be <= preLIF2")

        return tuple(reasons)


@dataclass(frozen=True)
class MorphoPreLiquidationAuthorization:
    """A Morpho authorization row for a pre-liquidation contract."""

    chain_id: int
    authorizer: str
    authorizee: str

    def matches(self, *, borrower: str, contract: str) -> bool:
        """Return true when `borrower` authorized `contract`."""
        return self.authorizer.lower() == borrower.lower() and self.authorizee.lower() == contract.lower()


@dataclass(frozen=True)
class MorphoPreLiquidationIndexedPosition:
    """Borrowing position row from the official HyperIndex schema."""

    chain_id: int
    market_id: str
    borrower: str
    indexed_supply_shares: int
    indexed_borrow_shares: int
    indexed_collateral: int

    @property
    def hyperindex_market_id(self) -> str:
        """Return the indexed `<chainId>-<marketId>` id."""
        return hyperindex_market_id(self.chain_id, self.market_id)


@dataclass(frozen=True)
class MorphoPreLiquidationEligibility:
    """Source-faithful read-side pre-liquidation eligibility result."""

    eligible: bool
    reject_reasons: tuple[str, ...]
    collateral_quoted: int
    ltv: int
    quotient: int
    pre_lcf: int
    pre_lif: int
    repayable_shares: int


@dataclass(frozen=True)
class MorphoPreLiquidationPositionSnapshot:
    """Accrued position inputs needed for pre-liquidation screening."""

    collateral_assets: int
    borrowed_assets: int
    borrow_shares: int
    collateral_price: int
    oracle_price_scale: int = ORACLE_PRICE_SCALE


@dataclass(frozen=True)
class MorphoPreLiquidationPositionInput:
    """A borrower position joined to a raw Morpho market id."""

    market_id: str
    borrower: str
    snapshot: MorphoPreLiquidationPositionSnapshot


@dataclass(frozen=True)
class MorphoPreLiquidationCandidate:
    """Eligible borrower/contract pair for read-side candidate ranking."""

    market_id: str
    borrower: str
    contract: MorphoPreLiquidationContract
    snapshot: MorphoPreLiquidationPositionSnapshot
    eligibility: MorphoPreLiquidationEligibility


class MorphoPreLiquidationClient(AsyncGraphqlAdapterClient):
    """Thin HyperIndex client for Morpho pre-liquidation registry rows."""

    def __init__(
        self,
        graphql_url: str,
        *,
        morpho_blue_address: str | None = None,
        rpc_url: str | None = None,
        timeout_sec: float = 5.0,
        bearer_token: str | None = None,
    ) -> None:
        self._morpho_blue_address = morpho_blue_address
        self._rpc_url = rpc_url
        self._web3: Web3 | None = None
        super().__init__(
            graphql_url,
            timeout_sec=timeout_sec,
            bearer_token=bearer_token,
            config=GraphqlAdapterConfig(
                http_error_event="morpho_preliquidation_http_error",
                graphql_errors_event="morpho_preliquidation_graphql_errors",
                graphql_error_prefix="Morpho pre-liquidation GraphQL errors",
                log=logger,
            ),
        )

    async def list_positions(
        self,
        market_ids: list[str],
        *,
        chain_id: int = ARBITRUM_CHAIN_ID,
        page_size: int = PRELIQUIDATION_POSITIONS_PAGE_SIZE,
    ) -> list[MorphoPreLiquidationIndexedPosition]:
        """List borrowing positions for raw or indexed HyperIndex market ids."""
        if not market_ids:
            return []
        if page_size <= 0:
            raise ValueError("page_size must be positive")

        indexed_market_ids = [ensure_hyperindex_market_id(chain_id, market_id) for market_id in market_ids]
        positions: list[MorphoPreLiquidationIndexedPosition] = []
        offset = 0
        while True:
            data = await self._query(
                PRELIQUIDATION_POSITIONS_QUERY,
                {"marketIds": indexed_market_ids, "limit": page_size, "offset": offset},
            )
            rows = data.get("Position", [])
            if not isinstance(rows, list):
                raise ValueError("Position response must be a list")
            positions.extend(pre_liquidation_position_from_graphql(row) for row in rows)
            if len(rows) < page_size:
                return positions
            offset += page_size

    async def list_contracts(
        self,
        market_ids: list[str],
        *,
        chain_id: int = ARBITRUM_CHAIN_ID,
    ) -> list[MorphoPreLiquidationContract]:
        """List pre-liquidation contracts for raw or indexed market ids."""
        if not market_ids:
            return []

        indexed_market_ids = [ensure_hyperindex_market_id(chain_id, market_id) for market_id in market_ids]
        data = await self._query(
            PRELIQUIDATION_CONTRACTS_QUERY,
            {"marketIds": indexed_market_ids},
        )
        rows = data.get("PreLiquidationContract", [])
        if not isinstance(rows, list):
            raise ValueError("PreLiquidationContract response must be a list")
        return [pre_liquidation_contract_from_graphql(row) for row in rows]

    async def list_authorizations(
        self,
        authorizees: list[str],
        *,
        chain_id: int = ARBITRUM_CHAIN_ID,
    ) -> list[MorphoPreLiquidationAuthorization]:
        """List users who authorized the supplied pre-liquidation contracts."""
        if not authorizees:
            return []

        normalized_authorizees = [normalize_address(address) for address in authorizees]
        data = await self._query(
            PRELIQUIDATION_AUTHORIZATIONS_QUERY,
            {"chainId": chain_id, "authorizees": normalized_authorizees},
        )
        rows = data.get("Authorization", [])
        if not isinstance(rows, list):
            raise ValueError("Authorization response must be a list")
        return [pre_liquidation_authorization_from_graphql(row, chain_id=chain_id) for row in rows]

    async def list_live_candidates(
        self,
        market_ids: list[str],
        *,
        chain_id: int = ARBITRUM_CHAIN_ID,
    ) -> list[MorphoPreLiquidationCandidate]:
        """Assemble read-only live pre-liquidation candidates.

        This mirrors the official bot boundary:
        HyperIndex supplies positions, pre-liquidation contracts, and borrower
        authorizations. Morpho Blue and the relevant pre-liquidation oracle are
        then read directly before eligibility math runs. No calldata is built.
        """
        contracts = await self.list_contracts(market_ids, chain_id=chain_id)
        if not contracts:
            return []

        positions = await self.list_positions(market_ids, chain_id=chain_id)
        if not positions:
            return []

        authorizations = await self.list_authorizations(
            [contract.address for contract in contracts],
            chain_id=chain_id,
        )
        authorized_pairs = {
            (authorization.authorizer.lower(), authorization.authorizee.lower(), authorization.chain_id)
            for authorization in authorizations
        }
        contracts_by_market: dict[str, list[MorphoPreLiquidationContract]] = {}
        for contract in contracts:
            contracts_by_market.setdefault(contract.market_id.lower(), []).append(contract)

        candidates: list[MorphoPreLiquidationCandidate] = []
        for position in positions:
            if position.chain_id != chain_id:
                continue
            for contract in contracts_by_market.get(position.market_id.lower(), []):
                auth_key = (position.borrower.lower(), contract.address.lower(), contract.chain_id)
                if auth_key not in authorized_pairs:
                    continue
                market_lltv, snapshot = self.read_onchain_position_snapshot(contract, position.borrower)
                eligibility = evaluate_pre_liquidation_eligibility(
                    contract,
                    market_lltv=market_lltv,
                    position=snapshot,
                )
                if not eligibility.eligible:
                    continue
                candidates.append(
                    MorphoPreLiquidationCandidate(
                        market_id=contract.market_id.lower(),
                        borrower=position.borrower,
                        contract=contract,
                        snapshot=snapshot,
                        eligibility=eligibility,
                    ),
                )

        return _dedupe_pre_liquidation_candidates(candidates)

    def read_onchain_position_snapshot(
        self,
        contract: MorphoPreLiquidationContract,
        borrower: str,
    ) -> tuple[int, MorphoPreLiquidationPositionSnapshot]:
        """Read Morpho Blue position/market and pre-liquidation oracle price."""
        if self._rpc_url is None or self._morpho_blue_address is None:
            raise ValueError("rpc_url and morpho_blue_address are required for live pre-liquidation reads")
        if not is_address(borrower) or borrower.lower() == ZERO_ADDRESS:
            raise ValueError("borrower must be a non-zero address")

        morpho = cast("_MorphoBlueContract", self._morpho_contract())
        market_id_bytes = bytes.fromhex(contract.market_id.removeprefix("0x"))
        loan_token, collateral_token, oracle, irm, lltv = cast(
            "tuple[str, str, str, str, int]",
            morpho.functions.idToMarketParams(market_id_bytes).call(),
        )
        onchain_market_id = _derive_morpho_market_id(
            loan_token=loan_token,
            collateral_token=collateral_token,
            oracle=oracle,
            irm=irm,
            lltv=int(lltv),
        )
        if onchain_market_id.lower() != contract.market_id.lower():
            raise ValueError("on-chain MarketParams do not match pre-liquidation market id")

        _supply_shares, borrow_shares, collateral = cast(
            "tuple[int, int, int]",
            morpho.functions.position(market_id_bytes, Web3.to_checksum_address(borrower)).call(),
        )
        _total_supply_assets, _total_supply_shares, total_borrow_assets, total_borrow_shares, _last_update, _fee = cast(
            "tuple[int, int, int, int, int, int]",
            morpho.functions.market(market_id_bytes).call(),
        )
        price_oracle = (
            oracle if contract.pre_liquidation_oracle.lower() == ZERO_ADDRESS else contract.pre_liquidation_oracle
        )
        collateral_price = self._oracle_price(price_oracle)

        return (
            int(lltv),
            MorphoPreLiquidationPositionSnapshot(
                collateral_assets=int(collateral),
                borrowed_assets=to_assets_up(
                    int(borrow_shares),
                    int(total_borrow_assets),
                    int(total_borrow_shares),
                ),
                borrow_shares=int(borrow_shares),
                collateral_price=collateral_price,
            ),
        )

    def _morpho_contract(self) -> object:
        if self._rpc_url is None or self._morpho_blue_address is None:
            raise ValueError("rpc_url and morpho_blue_address are required for live pre-liquidation reads")
        if self._web3 is None:
            self._web3 = Web3(Web3.HTTPProvider(self._rpc_url))
        return self._web3.eth.contract(
            address=Web3.to_checksum_address(self._morpho_blue_address),
            abi=_MORPHO_BLUE_ABI,
        )

    def _oracle_price(self, oracle_address: str) -> int:
        if self._rpc_url is None:
            raise ValueError("rpc_url is required for Morpho pre-liquidation oracle reads")
        if self._web3 is None:
            self._web3 = Web3(Web3.HTTPProvider(self._rpc_url))
        oracle = self._web3.eth.contract(
            address=Web3.to_checksum_address(oracle_address),
            abi=_ORACLE_ABI,
        )
        price = cast("int | str", oracle.functions.price().call())
        return int(price)


def hyperindex_market_id(chain_id: int, market_id: str) -> str:
    """Return official HyperIndex market id format."""
    if not is_bytes32(market_id):
        raise ValueError("market_id must be a bytes32 hex string")
    return f"{chain_id}-{market_id.lower()}"


def ensure_hyperindex_market_id(chain_id: int, market_id: str) -> str:
    """Accept raw bytes32 or `<chainId>-<bytes32>` market ids."""
    if "-" in market_id:
        prefix, raw_market_id = market_id.split("-", 1)
        if int(prefix) != chain_id:
            raise ValueError(f"market id chain {prefix} does not match requested chain {chain_id}")
        return hyperindex_market_id(chain_id, raw_market_id)
    return hyperindex_market_id(chain_id, market_id)


def pre_liquidation_contract_from_graphql(row: object) -> MorphoPreLiquidationContract:
    """Map official HyperIndex row shape to a typed contract config."""
    if not isinstance(row, dict):
        raise ValueError("PreLiquidationContract row must be an object")
    raw = cast("dict[str, object]", row)
    chain_id, market_id = split_hyperindex_market_id(_require_str(raw, "market_id"))
    return MorphoPreLiquidationContract(
        chain_id=chain_id,
        market_id=market_id,
        address=_require_str(raw, "address"),
        pre_lltv=_parse_uint(raw.get("preLltv"), "preLltv"),
        pre_lcf1=_parse_uint(raw.get("preLCF1"), "preLCF1"),
        pre_lcf2=_parse_uint(raw.get("preLCF2"), "preLCF2"),
        pre_lif1=_parse_uint(raw.get("preLIF1"), "preLIF1"),
        pre_lif2=_parse_uint(raw.get("preLIF2"), "preLIF2"),
        pre_liquidation_oracle=_require_str(raw, "preLiquidationOracle"),
    )


def pre_liquidation_authorization_from_graphql(
    row: object,
    *,
    chain_id: int,
) -> MorphoPreLiquidationAuthorization:
    """Map official HyperIndex Authorization row shape to a typed record."""
    if not isinstance(row, dict):
        raise ValueError("Authorization row must be an object")
    raw = cast("dict[str, object]", row)
    authorizer = _require_str(raw, "authorizer")
    authorizee = _require_str(raw, "authorizee")
    if not is_address(authorizer) or authorizer.lower() == ZERO_ADDRESS:
        raise ValueError("authorizer must be a non-zero address")
    if not is_address(authorizee) or authorizee.lower() == ZERO_ADDRESS:
        raise ValueError("authorizee must be a non-zero address")
    return MorphoPreLiquidationAuthorization(
        chain_id=chain_id,
        authorizer=authorizer,
        authorizee=authorizee,
    )


def pre_liquidation_position_from_graphql(row: object) -> MorphoPreLiquidationIndexedPosition:
    """Map official HyperIndex Position row shape to a typed borrowing row."""
    if not isinstance(row, dict):
        raise ValueError("Position row must be an object")
    raw = cast("dict[str, object]", row)
    chain_id, market_id = split_hyperindex_market_id(_require_str(raw, "market_id"))
    borrower = _require_str(raw, "user")
    if not is_address(borrower) or borrower.lower() == ZERO_ADDRESS:
        raise ValueError("position user must be a non-zero address")
    return MorphoPreLiquidationIndexedPosition(
        chain_id=chain_id,
        market_id=market_id,
        borrower=borrower,
        indexed_supply_shares=_parse_uint(raw.get("supplyShares"), "supplyShares"),
        indexed_borrow_shares=_parse_uint(raw.get("borrowShares"), "borrowShares"),
        indexed_collateral=_parse_uint(raw.get("collateral"), "collateral"),
    )


def authorized_contracts_for_borrower(
    contracts: list[MorphoPreLiquidationContract],
    authorizations: list[MorphoPreLiquidationAuthorization],
    borrower: str,
) -> list[MorphoPreLiquidationContract]:
    """Return pre-liquidation contracts authorized by `borrower`."""
    if not is_address(borrower) or borrower.lower() == ZERO_ADDRESS:
        raise ValueError("borrower must be a non-zero address")

    authorized_addresses = {
        authorization.authorizee.lower()
        for authorization in authorizations
        if authorization.chain_id in {contract.chain_id for contract in contracts}
        and authorization.authorizer.lower() == borrower.lower()
    }
    return [contract for contract in contracts if contract.address.lower() in authorized_addresses]


def evaluate_pre_liquidation_eligibility(
    contract: MorphoPreLiquidationContract,
    *,
    market_lltv: int,
    position: MorphoPreLiquidationPositionSnapshot,
) -> MorphoPreLiquidationEligibility:
    """Evaluate the source `PreLiquidation.preLiquidate` trigger math.

    `borrowed_assets` must already include accrued interest. The exact source
    contract converts `borrowShares` through current market totals before this
    point; callers should reuse the Morpho LP adapter's on-chain revalidation
    for that conversion.
    """
    reasons = list(contract.screening_reject_reasons(market_lltv))

    if position.collateral_assets <= 0:
        reasons.append("collateral must be positive")
    if position.borrowed_assets <= 0:
        reasons.append("borrowed assets must be positive")
    if position.borrow_shares <= 0:
        reasons.append("borrow shares must be positive")
    if position.collateral_price <= 0:
        reasons.append("collateral price must be positive")
    if position.oracle_price_scale <= 0:
        reasons.append("oracle price scale must be positive")

    if reasons:
        return MorphoPreLiquidationEligibility(
            eligible=False,
            reject_reasons=tuple(reasons),
            collateral_quoted=0,
            ltv=0,
            quotient=0,
            pre_lcf=0,
            pre_lif=0,
            repayable_shares=0,
        )

    collateral_quoted = mul_div_down(
        position.collateral_assets,
        position.collateral_price,
        position.oracle_price_scale,
    )
    if collateral_quoted == 0:
        return MorphoPreLiquidationEligibility(
            eligible=False,
            reject_reasons=("collateral quoted value is zero",),
            collateral_quoted=0,
            ltv=0,
            quotient=0,
            pre_lcf=0,
            pre_lif=0,
            repayable_shares=0,
        )

    reject_reasons: list[str] = []
    if position.borrowed_assets > wad_mul_down(collateral_quoted, market_lltv):
        reject_reasons.append("position is already standard-liquidatable")
    if position.borrowed_assets <= wad_mul_down(collateral_quoted, contract.pre_lltv):
        reject_reasons.append("position is below preLLTV")

    if reject_reasons:
        return MorphoPreLiquidationEligibility(
            eligible=False,
            reject_reasons=tuple(reject_reasons),
            collateral_quoted=collateral_quoted,
            ltv=wad_div_up(position.borrowed_assets, collateral_quoted),
            quotient=0,
            pre_lcf=0,
            pre_lif=0,
            repayable_shares=0,
        )

    ltv = wad_div_up(position.borrowed_assets, collateral_quoted)
    quotient = wad_div_down(ltv - contract.pre_lltv, market_lltv - contract.pre_lltv)
    pre_lif = wad_mul_down(quotient, contract.pre_lif2 - contract.pre_lif1) + contract.pre_lif1
    pre_lcf = wad_mul_down(quotient, contract.pre_lcf2 - contract.pre_lcf1) + contract.pre_lcf1
    repayable_shares = wad_mul_down(position.borrow_shares, pre_lcf)

    return MorphoPreLiquidationEligibility(
        eligible=repayable_shares > 0,
        reject_reasons=() if repayable_shares > 0 else ("repayable shares is zero",),
        collateral_quoted=collateral_quoted,
        ltv=ltv,
        quotient=quotient,
        pre_lcf=pre_lcf,
        pre_lif=pre_lif,
        repayable_shares=repayable_shares,
    )


def select_pre_liquidation_candidates(
    contracts: list[MorphoPreLiquidationContract],
    authorizations: list[MorphoPreLiquidationAuthorization],
    positions: list[MorphoPreLiquidationPositionInput],
    *,
    market_lltv_by_id: dict[str, int],
) -> list[MorphoPreLiquidationCandidate]:
    """Join contracts, authorizations, and positions into eligible candidates.

    Mirrors the official bot's final de-duplication behavior: sort candidates
    by the largest repayable amount, then keep only the best contract for each
    `(market, borrower)` pair.
    """
    contracts_by_market: dict[str, list[MorphoPreLiquidationContract]] = {}
    for contract in contracts:
        contracts_by_market.setdefault(contract.market_id.lower(), []).append(contract)

    authorized_pairs = {
        (authorization.authorizer.lower(), authorization.authorizee.lower(), authorization.chain_id)
        for authorization in authorizations
    }

    candidates: list[MorphoPreLiquidationCandidate] = []
    for position in positions:
        if not is_bytes32(position.market_id):
            raise ValueError("position market_id must be a bytes32 hex string")
        if not is_address(position.borrower) or position.borrower.lower() == ZERO_ADDRESS:
            raise ValueError("position borrower must be a non-zero address")

        market_id = position.market_id.lower()
        market_lltv = market_lltv_by_id.get(market_id)
        if market_lltv is None:
            continue

        for contract in contracts_by_market.get(market_id, []):
            auth_key = (position.borrower.lower(), contract.address.lower(), contract.chain_id)
            if auth_key not in authorized_pairs:
                continue

            eligibility = evaluate_pre_liquidation_eligibility(
                contract,
                market_lltv=market_lltv,
                position=position.snapshot,
            )
            if not eligibility.eligible:
                continue
            candidates.append(
                MorphoPreLiquidationCandidate(
                    market_id=market_id,
                    borrower=position.borrower,
                    contract=contract,
                    snapshot=position.snapshot,
                    eligibility=eligibility,
                ),
            )

    candidates.sort(key=lambda candidate: candidate.eligibility.repayable_shares, reverse=True)

    selected: list[MorphoPreLiquidationCandidate] = []
    seen: set[tuple[str, str]] = set()
    for candidate in candidates:
        key = (candidate.market_id, candidate.borrower.lower())
        if key in seen:
            continue
        selected.append(candidate)
        seen.add(key)
    return selected


def _dedupe_pre_liquidation_candidates(
    candidates: list[MorphoPreLiquidationCandidate],
) -> list[MorphoPreLiquidationCandidate]:
    candidates.sort(key=lambda candidate: candidate.eligibility.repayable_shares, reverse=True)
    selected: list[MorphoPreLiquidationCandidate] = []
    seen: set[tuple[str, str]] = set()
    for candidate in candidates:
        key = (candidate.market_id, candidate.borrower.lower())
        if key in seen:
            continue
        selected.append(candidate)
        seen.add(key)
    return selected


def split_hyperindex_market_id(indexed_market_id: str) -> tuple[int, str]:
    """Split `<chainId>-<marketId>` into `(chain_id, market_id)`."""
    if "-" not in indexed_market_id:
        raise ValueError("indexed market_id must be '<chainId>-<bytes32>'")
    chain_id_raw, market_id = indexed_market_id.split("-", 1)
    if not chain_id_raw.isdecimal():
        raise ValueError("indexed market_id chain id must be decimal")
    if not is_bytes32(market_id):
        raise ValueError("indexed market_id must contain a bytes32 market id")
    return int(chain_id_raw), market_id.lower()


def is_address(value: str) -> bool:
    """Return true for a 20-byte hex EVM address."""
    return bool(_EVM_ADDRESS_RE.fullmatch(value))


def is_bytes32(value: str) -> bool:
    """Return true for a bytes32 hex string."""
    return bool(_BYTES32_RE.fullmatch(value))


def normalize_address(value: str) -> str:
    """Normalize an address to lowercase hex after shape validation."""
    if not is_address(value):
        raise ValueError("address must be a 20-byte hex string")
    return value.lower()


def wad_mul_down(a: int, b: int) -> int:
    """Morpho MathLib `wMulDown`."""
    return (a * b) // WAD


def wad_div_down(a: int, b: int) -> int:
    """Morpho MathLib `wDivDown`."""
    return (a * WAD) // b


def wad_div_up(a: int, b: int) -> int:
    """Morpho MathLib `wDivUp`."""
    return (a * WAD + b - 1) // b


def mul_div_down(a: int, b: int, denominator: int) -> int:
    """Morpho MathLib `mulDivDown`."""
    return (a * b) // denominator


def to_assets_up(shares: int, total_assets: int, total_shares: int) -> int:
    """Morpho SharesMathLib `toAssetsUp` with virtual shares/assets."""
    if shares < 0 or total_assets < 0 or total_shares < 0:
        raise ValueError("shares and totals must be non-negative")
    denominator = total_shares + 10**6
    return (shares * (total_assets + 1) + denominator - 1) // denominator


def _derive_morpho_market_id(
    *,
    loan_token: str,
    collateral_token: str,
    oracle: str,
    irm: str,
    lltv: int,
) -> str:
    encoded = b"".join(
        (
            _encode_address(loan_token),
            _encode_address(collateral_token),
            _encode_address(oracle),
            _encode_address(irm),
            int(lltv).to_bytes(32, "big"),
        )
    )
    return Web3.to_hex(Web3.keccak(encoded))


def _encode_address(address: str) -> bytes:
    if not is_address(address) or address.lower() == ZERO_ADDRESS:
        raise ValueError(f"expected non-zero 20-byte address, got {address!r}")
    return bytes.fromhex(address.removeprefix("0x")).rjust(32, b"\x00")


def _require_str(row: dict[str, object], field: str) -> str:
    value = row.get(field)
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    return value


def _parse_uint(value: object, field: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be an unsigned integer")
    if isinstance(value, int):
        if value < 0:
            raise ValueError(f"{field} must be an unsigned integer")
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    raise ValueError(f"{field} must be an unsigned integer")


def main() -> None:
    """Small CLI anchor for manual smoke checks."""
    configure_execution_logging("info")
    logger.info(
        "morpho_preliquidation_adapter_ready",
        query="PreLiquidationContract",
        source="official-morpho-blue-liquidation-bot-hyperindex-schema",
    )


if __name__ == "__main__":
    main()
