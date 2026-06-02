"""Pydantic models for the CoW Solver Engine API.

Schema source:
[`cowprotocol/services::crates/solvers/openapi.yml`](https://github.com/cowprotocol/services/blob/main/crates/solvers/openapi.yml)

## Wire-format conventions

* All `U256`-class amounts (token amounts, prices, gas) arrive as **decimal
  strings**. Models parse to `int` via the `BigIntStr` alias; downstream
  math is `int`-typed.
* Field names on the wire are camelCase (e.g. `effectiveGasPrice`).
  Models use snake_case Python identifiers and `Field(alias=...)` to
  bridge. `model_config = ConfigDict(populate_by_name=True,
  alias_generator=...)` would also work but explicit aliases keep
  the mapping searchable.
* `deadline` is ISO-8601 with timezone — pydantic parses to `datetime`.
* The solver doesn't need to interpret every liquidity-pool variant
  (constantProduct / weightedProduct / stable / concentratedLiquidity /
  limitOrder); we use `model_extra='allow'` and pass through.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — runtime-validated by pydantic
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, PlainSerializer


def _parse_bigint(value: object) -> int:
    """Coerce a wire `U256`/`BigInt` field to `int`.

    Accepts:
        * `int` — passthrough
        * `str` — decimal, `0x`-prefixed hex, or scientific (`1e18`)

    Some CoW serializers emit scientific notation for large round numbers
    (e.g. `"1e18"` for 10^18). Decimal-string-only would reject those —
    we route through `Decimal` to handle both shapes losslessly. Decimals
    that don't represent an integer (e.g. `"1.5"`) raise.
    """
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        s = value.strip()
        if s.startswith(("0x", "0X")):
            return int(s, 16)
        if "e" in s or "E" in s or "." in s:
            d = Decimal(s)
            if d != d.to_integral_value():
                msg = f"non-integer BigInt source: {s!r}"
                raise ValueError(msg)
            return int(d)
        return int(s)
    msg = f"unsupported BigInt source: {type(value).__name__}"
    raise TypeError(msg)


BigIntStr = Annotated[
    int,
    BeforeValidator(_parse_bigint),
    PlainSerializer(str, return_type=str, when_used="json"),
]
"""A wire-format big integer (U128/U256/uint).

Decodes to Python `int` for in-memory math; serializes back to a decimal
string in JSON mode so the wire shape matches CoW's OpenAPI conventions
(orderbook BigUint, /solve scores/prices/amounts). Python-native dumps
(`model_dump()` without `mode="json"`) keep the value as `int` for
introspection and deep-equality assertions.
"""


class OrderKind(StrEnum):
    """Buy = fixed buy_amount, variable sell_amount; sell = inverse."""

    SELL = "sell"
    BUY = "buy"


class OrderClass(StrEnum):
    """Order classification per CoW orderbook taxonomy."""

    MARKET = "market"
    LIMIT = "limit"
    LIQUIDITY = "liquidity"


class SigningScheme(StrEnum):
    """How the order owner signed."""

    EIP712 = "eip712"
    ETH_SIGN = "ethSign"
    PRESIGN = "preSign"
    EIP1271 = "eip1271"


class SellTokenBalance(StrEnum):
    """Source of the user's sellToken balance at settlement time."""

    ERC20 = "erc20"
    EXTERNAL = "external"
    INTERNAL = "internal"


class BuyTokenBalance(StrEnum):
    """Where the buyToken is delivered."""

    ERC20 = "erc20"
    INTERNAL = "internal"


class TokenInfo(BaseModel):
    """Per-token metadata appearing in the auction's `tokens` map."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    decimals: int | None = None
    symbol: str | None = None
    reference_price: BigIntStr | None = Field(default=None, alias="referencePrice")
    available_balance: BigIntStr | None = Field(default=None, alias="availableBalance")
    trusted: bool | None = None


class Order(BaseModel):
    """A solvable CoW order included in the auction."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    uid: str
    sell_token: str = Field(alias="sellToken")
    buy_token: str = Field(alias="buyToken")
    sell_amount: BigIntStr = Field(alias="sellAmount")
    full_sell_amount: BigIntStr | None = Field(default=None, alias="fullSellAmount")
    buy_amount: BigIntStr = Field(alias="buyAmount")
    full_buy_amount: BigIntStr = Field(alias="fullBuyAmount")
    fee_policies: list[dict[str, Any]] | None = Field(default=None, alias="feePolicies")
    valid_to: int = Field(alias="validTo")
    kind: OrderKind
    receiver: str | None = None
    owner: str
    partially_fillable: bool = Field(alias="partiallyFillable")
    pre_interactions: list[dict[str, Any]] = Field(default_factory=list, alias="preInteractions")
    post_interactions: list[dict[str, Any]] = Field(default_factory=list, alias="postInteractions")
    sell_token_source: SellTokenBalance = Field(
        default=SellTokenBalance.ERC20, alias="sellTokenSource"
    )
    buy_token_destination: BuyTokenBalance = Field(
        default=BuyTokenBalance.ERC20, alias="buyTokenDestination"
    )
    order_class: OrderClass = Field(alias="class")
    app_data: str = Field(alias="appData")
    flashloan_hint: dict[str, Any] | None = Field(default=None, alias="flashloanHint")
    signing_scheme: SigningScheme = Field(alias="signingScheme")
    signature: str


class Auction(BaseModel):
    """The auction the CoW driver POSTs to `/solve`.

    `liquidity` is intentionally typed loosely — the CoW catalog of pool
    variants is large and orthogonal to the protocol contract; passing
    through unchanged is enough for the POC. Concrete pool models land
    once the SolutionBuilder needs to compute against them.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str | None = None
    tokens: dict[str, TokenInfo]
    orders: list[Order]
    liquidity: list[dict[str, Any]]
    effective_gas_price: BigIntStr = Field(alias="effectiveGasPrice")
    deadline: datetime
    surplus_capturing_jit_order_owners: list[str] = Field(alias="surplusCapturingJitOrderOwners")


class Call(BaseModel):
    """A pre/post settlement contract call."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    target: str
    value: BigIntStr
    call_data: str = Field(alias="callData")


class Asset(BaseModel):
    """Token amount consumed or produced by a custom interaction."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    token: str
    amount: BigIntStr


class Allowance(BaseModel):
    """Token allowance required by a custom interaction."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    token: str
    spender: str
    amount: BigIntStr


class JitTradeOrder(BaseModel):
    """JIT-order payload embedded in a CoW solver solution."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    sell_token: str = Field(alias="sellToken")
    buy_token: str = Field(alias="buyToken")
    receiver: str
    sell_amount: BigIntStr = Field(alias="sellAmount")
    buy_amount: BigIntStr = Field(alias="buyAmount")
    valid_to: int = Field(alias="validTo")
    app_data: str = Field(alias="appData")
    kind: OrderKind
    sell_token_balance: SellTokenBalance = Field(alias="sellTokenBalance")
    buy_token_balance: BuyTokenBalance = Field(alias="buyTokenBalance")
    signing_scheme: SigningScheme = Field(alias="signingScheme")
    signature: str


class Interaction(BaseModel):
    """A liquidity or custom interaction inside a settlement."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    kind: Literal["liquidity", "custom"] | None = None
    internalize: bool | None = None
    id: str | None = None
    input_token: str | None = Field(default=None, alias="inputToken")
    output_token: str | None = Field(default=None, alias="outputToken")
    input_amount: BigIntStr | None = Field(default=None, alias="inputAmount")
    output_amount: BigIntStr | None = Field(default=None, alias="outputAmount")
    target: str | None = None
    value: BigIntStr | None = None
    call_data: str | None = Field(default=None, alias="callData")
    allowances: list[Allowance] = Field(default_factory=list)
    inputs: list[Asset] = Field(default_factory=list)
    outputs: list[Asset] = Field(default_factory=list)


class Trade(BaseModel):
    """A fulfillment, JIT trade, or legacy settlement-shaped trade."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    kind: str | None = None
    order: str | JitTradeOrder | dict[str, Any] | None = None
    executed_amount: BigIntStr | None = Field(default=None, alias="executedAmount")
    fee: BigIntStr | None = None

    sell_token_index: int | None = Field(default=None, alias="sellTokenIndex")
    buy_token_index: int | None = Field(default=None, alias="buyTokenIndex")
    receiver: str | None = None
    sell_amount: BigIntStr | None = Field(default=None, alias="sellAmount")
    buy_amount: BigIntStr | None = Field(default=None, alias="buyAmount")
    valid_to: int | None = Field(default=None, alias="validTo")
    app_data: str | None = Field(default=None, alias="appData")
    fee_amount: BigIntStr | None = Field(default=None, alias="feeAmount")
    flags: int | None = None
    signature: str | None = None

    sell_token: str | None = Field(default=None, alias="sellToken")
    buy_token: str | None = Field(default=None, alias="buyToken")
    amount: BigIntStr | None = None
    order_uid: str | None = Field(default=None, alias="orderUid")


class Solution(BaseModel):
    """A computed solution for the auction.

    The empty-solutions POC returns `[]` — a structurally-valid response
    that says "I'm online but have nothing for this auction". Production
    solving plugs into `SolutionBuilder.build` and constructs real
    `Solution`s with non-empty `trades` + `interactions`.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    # OpenAPI declares `id` as `number`, not integer — accept both shapes
    # and let downstream code handle the float case explicitly. Pydantic
    # rejects `7.0` for `int` even though the spec permits it.
    id: int | float
    prices: dict[str, BigIntStr]
    trades: list[Trade]
    interactions: list[Interaction]
    pre_interactions: list[Call] | None = Field(default=None, alias="preInteractions")
    post_interactions: list[Call] | None = Field(default=None, alias="postInteractions")
    gas: int | None = None
    max_fee_per_gas: BigIntStr | None = Field(default=None, alias="maxFeePerGas")
    max_priority_fee_per_gas: BigIntStr | None = Field(default=None, alias="maxPriorityFeePerGas")
    flashloans: dict[str, dict[str, Any]] | None = None


class CompetitionSolution(BaseModel):
    """A signed solution submitted to the CoW Competition API.

    Used by external solvers to push solutions instead of waiting for
    the pull-based /solve request.
    """

    model_config = ConfigDict(populate_by_name=True)

    solution: Solution
    signature: str

    def model_dump_wire(self) -> dict[str, Any]:
        """Serialize for outbound HTTP."""
        wire = _to_wire(self.model_dump(by_alias=True, exclude_none=True, mode="json"))
        assert isinstance(wire, dict)
        return wire


class SolveRequest(BaseModel):
    """Wrapper for the `/solve` POST body.

    The CoW driver posts the bare Auction object; this class exists so
    handlers can keep the request/response symmetry.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")


# Type alias — POST /solve body IS the Auction. Kept distinct for clarity
# at handler boundaries.
SolveRequestBody = Auction


class SolveResponse(BaseModel):
    """Response body for `/solve`."""

    model_config = ConfigDict(populate_by_name=True)

    solutions: list[Solution] = Field(default_factory=list)

    def model_dump_wire(self) -> dict[str, Any]:
        """Serialize to camelCase JSON-ready dict for outbound HTTP.

        BigInt/U256 fields are emitted as decimal strings (CoW wire
        convention). pydantic's default `model_dump(by_alias=True)`
        handles aliases; we post-process bigint fields here.
        """
        wire = _to_wire(self.model_dump(by_alias=True, exclude_none=True, mode="json"))
        assert isinstance(wire, dict)
        return wire


def _to_wire(value: Any) -> Any:
    """Recursively coerce `int` outside of small enum-like fields to str.

    CoW wire convention: token amounts, prices, gas — all decimal strings.
    For the POC we apply a simple rule: any `int >= 2**32` becomes a
    decimal string. Smaller ints (gas units, ids, etc.) stay as numbers.
    """
    if isinstance(value, dict):
        return {k: _to_wire(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_wire(v) for v in value]
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value >= 2**32:
        return str(value)
    return value


# -- /quote (CoW driver GET) ------------------------------------------------
#
# Spec: <https://github.com/cowprotocol/services/blob/main/crates/driver/openapi.yml>
# Local mirror: `/tmp/cow-driver-openapi.yml`.
#
# The CoW driver calls `GET /quote` with the four query parameters below.
# We honor the JIT-aware `QuoteResponse` shape (clearingPrices + solver
# required; everything else optional). The legacy shape is still spec-valid
# but we generate the new one.


class DriverQuoteRequest(BaseModel):
    """`GET /quote` query parameters per CoW Driver OpenAPI.

    Wire names are camelCase (`sellToken`, `buyToken`); Python uses
    snake_case via field aliases. `amount` is a decimal-string `TokenAmount`
    (`BigUint`) on the wire; we parse to `int`. Unknown fields are rejected
    to surface contract drift early.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    sell_token: str = Field(alias="sellToken")
    buy_token: str = Field(alias="buyToken")
    kind: Literal["buy", "sell"]
    amount: BigIntStr
    deadline: datetime


class JitOrder(BaseModel):
    """JIT-order entry inside a `QuoteResponse`."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    sell_token: str | None = Field(default=None, alias="sellToken")
    buy_token: str | None = Field(default=None, alias="buyToken")
    sell_amount: BigIntStr | None = Field(default=None, alias="sellAmount")
    buy_amount: BigIntStr | None = Field(default=None, alias="buyAmount")
    executed_amount: BigIntStr | None = Field(default=None, alias="executedAmount")
    receiver: str | None = None
    valid_to: int | None = Field(default=None, alias="validTo")
    side: Literal["buy", "sell"] | None = None


class DriverQuoteResponse(BaseModel):
    """JIT-aware `QuoteResponse` per CoW Driver OpenAPI.

    Required: `clearingPrices`, `solver`. Everything else optional. JSON
    serialization uses camelCase aliases; BigUint values become decimal
    strings through `model_dump_wire`.
    """

    model_config = ConfigDict(populate_by_name=True)

    clearing_prices: dict[str, BigIntStr] = Field(alias="clearingPrices")
    solver: str
    pre_interactions: list[Call] | None = Field(default=None, alias="preInteractions")
    interactions: list[Interaction] | None = None
    gas: int | None = None
    tx_origin: str | None = Field(default=None, alias="txOrigin")
    jit_orders: list[JitOrder] | None = Field(default=None, alias="jitOrders")

    def model_dump_wire(self) -> dict[str, Any]:
        """Serialize to camelCase JSON-ready dict with BigInt→str coercion."""
        wire = _to_wire(self.model_dump(by_alias=True, exclude_none=True, mode="json"))
        assert isinstance(wire, dict)
        return wire


class DriverError(BaseModel):
    """`Error` shape from the CoW Driver spec — `kind` + `description`."""

    model_config = ConfigDict(populate_by_name=True)

    kind: str
    description: str
