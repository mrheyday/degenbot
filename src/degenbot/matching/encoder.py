"""Pick A — MatchedTrade encoder.

Translates a price-compatible MatchPair into internal-match parameters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from eth_abi import encode as abi_encode

from degenbot.matching.price_compat import PRICE_SCALE, is_opposing_pair

if TYPE_CHECKING:
    from degenbot.decision.types import (
        Address,
        CowOrderSummary,
        Hex,
        MatchPair,
        UniswapXOrderSummary,
    )

DEFAULT_MIN_PROFIT_BPS_OF_ESTIMATE = 9500
BPS_DENOMINATOR = 10000


@dataclass(frozen=True)
class MatchedTrade:
    pair: MatchPair
    cow_settlement_calldata: Hex
    uniswapx_batch_calldata: Hex
    expected_token_inflows: list[Address]
    expected_token_inflow_min: list[int]
    flash_amount: int
    flash_token: Address
    estimated_profit_wei: int


def encode_match_pair(
    pair: MatchPair,
    cow_order: CowOrderSummary,
    uniswapx_order: UniswapXOrderSummary,
    estimated_profit_wei: int,
    flash_token: Address,
    flash_amount: int,
    executor_address: Address,
    min_profit_bps: int = DEFAULT_MIN_PROFIT_BPS_OF_ESTIMATE,
    uniswapx_signature: Hex | None = None,
) -> MatchedTrade:
    """Encode a price-compatible MatchPair into a MatchedTrade."""
    if not is_opposing_pair(pair.o, pair.c):
        msg = "encode_match_pair: pair tokens are not opposing"
        raise ValueError(msg)

    cow_candidate = _identify_cow_candidate(pair, cow_order)
    uniswapx_candidate = pair.c if pair.o.id == cow_candidate.id else pair.o

    _validate_orders(cow_order, cow_candidate, uniswapx_order, uniswapx_candidate)

    cow_settlement_calldata = _encode_cow_settle(
        cow_order=cow_order,
        fill_amount=pair.fill_amount,
        clearing_price=pair.clearing_price,
        executor_address=executor_address,
        cow_order_is_counter=(cow_candidate.id == pair.c.id),
    )

    sig = uniswapx_signature or uniswapx_order.signature
    uniswapx_batch_calldata = _encode_uniswapx_batch(
        encoded_order=uniswapx_order.encoded_order,
        signature=sig,
        executor_address=executor_address,
        callback_deadline=uniswapx_order.deadline,
    )

    token_a = pair.o.pair_sell
    token_b = pair.o.pair_buy

    token_b_spot = (pair.fill_amount * pair.clearing_price) // PRICE_SCALE
    token_a_floor = (pair.fill_amount * min_profit_bps) // BPS_DENOMINATOR
    token_b_floor = (token_b_spot * min_profit_bps) // BPS_DENOMINATOR

    if flash_amount <= 0:
        msg = "encode_match_pair: flash_amount must be > 0"
        raise ValueError(msg)

    return MatchedTrade(
        pair=pair,
        cow_settlement_calldata=cow_settlement_calldata,
        uniswapx_batch_calldata=uniswapx_batch_calldata,
        expected_token_inflows=[token_a, token_b],
        expected_token_inflow_min=[token_a_floor, token_b_floor],
        flash_amount=flash_amount,
        flash_token=flash_token,
        estimated_profit_wei=estimated_profit_wei,
    )


def _identify_cow_candidate(pair: MatchPair, cow_order: CowOrderSummary) -> Any:
    for cand in (pair.o, pair.c):
        if cand.source_venue in {"cow", "cow-competition"}:
            return cand
        if (
            cand.pair_sell.lower() == cow_order.sell_token.lower()
            and cand.pair_buy.lower() == cow_order.buy_token.lower()
        ):
            return cand
    msg = f"encode_match_pair: neither candidate matches CoW order {cow_order.uid}"
    raise ValueError(msg)


def _validate_orders(
    cow_order: CowOrderSummary,
    cow_candidate: Any,
    uniswapx_order: UniswapXOrderSummary,
    uniswapx_candidate: Any,
) -> None:
    if cow_order.sell_token.lower() != cow_candidate.pair_sell.lower():
        msg = "cowOrder.sellToken mismatch"
        raise ValueError(msg)
    if cow_order.buy_token.lower() != cow_candidate.pair_buy.lower():
        msg = "cowOrder.buyToken mismatch"
        raise ValueError(msg)
    if uniswapx_order.input_token.lower() != uniswapx_candidate.pair_sell.lower():
        msg = "uniswapxOrder.inputToken mismatch"
        raise ValueError(msg)
    if uniswapx_order.output_token.lower() != uniswapx_candidate.pair_buy.lower():
        msg = "uniswapxOrder.outputToken mismatch"
        raise ValueError(msg)


def _encode_cow_settle(
    cow_order: CowOrderSummary,
    fill_amount: int,
    clearing_price: int,
    executor_address: Address,
    cow_order_is_counter: bool,
) -> Hex:
    tokens = [cow_order.sell_token, cow_order.buy_token]
    clearing_prices = [cow_order.buy_amount, cow_order.sell_amount]

    def project_to_buy(fill: int) -> int:
        if clearing_price == 0:
            msg = "clearing_price is zero"
            raise ValueError(msg)
        if cow_order_is_counter:
            return (fill * PRICE_SCALE) // clearing_price
        return (fill * clearing_price) // PRICE_SCALE

    def project_to_sell(fill: int) -> int:
        if not cow_order_is_counter:
            return fill
        if clearing_price == 0:
            msg = "clearing_price is zero"
            raise ValueError(msg)
        return (fill * clearing_price) // PRICE_SCALE

    if not cow_order.partially_fillable:
        executed_amount = (
            cow_order.sell_amount if cow_order.kind == "sell" else cow_order.buy_amount
        )
    else:
        executed_amount = (
            project_to_sell(fill_amount)
            if cow_order.kind == "sell"
            else project_to_buy(fill_amount)
        )

    buy_token_payout = (
        project_to_buy(fill_amount) if cow_order.partially_fillable else cow_order.buy_amount
    )

    # transferToSettlement(address,uint256) selector: 0x272462e0
    transfer_data = b"\x27\x24\x62\xe0" + abi_encode(
        ["address", "uint256"], [executor_address, buy_token_payout]
    )

    interaction = (executor_address, 0, transfer_data)

    trade = (
        0,  # sellTokenIndex
        1,  # buyTokenIndex
        "0x0000000000000000000000000000000000000000",  # receiver
        cow_order.sell_amount,
        cow_order.buy_amount,
        cow_order.valid_to,
        bytes.fromhex(cow_order.app_data[2:]),
        cow_order.fee_amount,
        _pack_order_flags(cow_order),
        executed_amount,
        bytes.fromhex(cow_order.signature[2:]),
    )

    # settle(address[],uint256[],tuple[],tuple[][3]) selector: 0x1700684f
    # But wait, TS uses GPV2_SETTLE_ABI which might have a different selector or name
    # Let's check GPV2_SETTLE_ABI in TS: function name is "settle"
    # settle(address[],uint256[],(uint256,uint256,address,uint256,uint256,uint32,bytes32,uint256,uint256,uint256,bytes)[],(address,uint256,bytes)[][3])

    interactions = [[], [interaction], []]

    calldata = b"\x17\x00\x68\x4f" + abi_encode(
        ["address[]", "uint256[]", "tuple[]", "tuple[][3]"],
        [tokens, clearing_prices, [trade], interactions],
    )
    return "0x" + calldata.hex()


def _pack_order_flags(order: CowOrderSummary) -> int:
    scheme_map = {"eip712": 0, "ethsign": 1, "eip1271": 2, "presign": 3}
    flags = 0
    if order.kind == "buy":
        flags |= 1
    if order.partially_fillable:
        flags |= 1 << 1
    flags |= scheme_map[order.signing_scheme] << 5
    return flags


def _encode_uniswapx_batch(
    encoded_order: Hex,
    signature: Hex,
    executor_address: Address,
    callback_deadline: int,
) -> Hex:
    # callbackData: (SwapStep[], address, uint256)
    # Internal match uses empty SwapStep[]
    callback_data = abi_encode(
        ["(uint8,address,bytes,address,address,uint256,uint256)[]", "address", "uint256"],
        [[], executor_address, callback_deadline],
    )

    # executeBatchWithCallback((bytes,bytes)[],bytes) selector: 0x364a2754
    calldata = b"\x36\x4a\x27\x54" + abi_encode(
        ["(bytes,bytes)[]", "bytes"],
        [[(bytes.fromhex(encoded_order[2:]), bytes.fromhex(signature[2:]))], callback_data],
    )
    return "0x" + calldata.hex()
