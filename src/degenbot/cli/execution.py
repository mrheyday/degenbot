from __future__ import annotations

import json

import click

from degenbot.cli import cli
from degenbot.execution_adapters import (
    encode_compose_four_leg_calldata,
    encode_match_internal_calldata,
    encode_native_arb_calldata,
)


def _load_json(value: str) -> object:
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        msg = f"Invalid JSON payload: {exc}"
        raise click.BadParameter(msg) from exc


def _echo_hex(data: bytes) -> None:
    click.echo(f"0x{data.hex()}")


@cli.group()
def execution() -> None:
    """Execution calldata commands."""


@execution.command("native-arb")
@click.option("--flash-lender", required=True, type=str, help="Flash-loan lender address.")
@click.option("--flash-protocol", required=True, type=str, help="Flash protocol selector name.")
@click.option("--flash-token", required=True, type=str, help="Flash-loan token address.")
@click.option("--flash-amount", required=True, type=str, help="Flash-loan amount.")
@click.option(
    "--swaps-json",
    required=True,
    type=str,
    help="JSON array of swap-step objects.",
)
@click.option("--min-profit", required=True, type=str, help="Minimum profit threshold.")
@click.option("--deadline", required=True, type=str, help="Unix deadline.")
def execution_native_arb(
    *,
    flash_lender: str,
    flash_protocol: str,
    flash_token: str,
    flash_amount: str,
    swaps_json: str,
    min_profit: str,
    deadline: str,
) -> None:
    """Encode `Executor.executeNativeArb` calldata."""

    calldata = encode_native_arb_calldata(
        flash_lender=flash_lender,
        flash_protocol=flash_protocol,
        flash_token=flash_token,
        flash_amount=int(flash_amount),
        swaps=_load_json(swaps_json),
        min_profit=int(min_profit),
        deadline=int(deadline),
    )
    _echo_hex(calldata)


@execution.command("match-internal")
@click.option(
    "--cow-settlement-calldata",
    required=True,
    type=str,
    help="Hex calldata for the CoW settlement.",
)
@click.option(
    "--uniswapx-batch-calldata",
    required=True,
    type=str,
    help="Hex calldata for the UniswapX batch.",
)
@click.option(
    "--expected-token-inflows-json",
    required=True,
    type=str,
    help="JSON array of expected token inflow addresses.",
)
@click.option(
    "--expected-token-inflow-min-json",
    required=True,
    type=str,
    help="JSON array of minimum inflow amounts.",
)
@click.option("--flash-lender", required=True, type=str, help="Flash-loan lender address.")
@click.option("--flash-protocol", required=True, type=str, help="Flash protocol selector name.")
@click.option("--flash-token", required=True, type=str, help="Flash-loan token address.")
@click.option("--flash-amount", required=True, type=str, help="Flash-loan amount.")
@click.option("--min-profit", required=True, type=str, help="Minimum profit threshold.")
@click.option("--deadline", required=True, type=str, help="Unix deadline.")
def execution_match_internal(
    *,
    cow_settlement_calldata: str,
    uniswapx_batch_calldata: str,
    expected_token_inflows_json: str,
    expected_token_inflow_min_json: str,
    flash_lender: str,
    flash_protocol: str,
    flash_token: str,
    flash_amount: str,
    min_profit: str,
    deadline: str,
) -> None:
    """Encode `Executor.matchInternal` calldata."""

    calldata = encode_match_internal_calldata(
        cow_settlement_calldata=bytes.fromhex(cow_settlement_calldata.removeprefix("0x")),
        uniswapx_batch_calldata=bytes.fromhex(uniswapx_batch_calldata.removeprefix("0x")),
        expected_token_inflows=_load_json(expected_token_inflows_json),
        expected_token_inflow_min=[
            int(amount) for amount in _load_json(expected_token_inflow_min_json)
        ],
        flash_lender=flash_lender,
        flash_protocol=flash_protocol,
        flash_token=flash_token,
        flash_amount=int(flash_amount),
        min_profit=int(min_profit),
        deadline=int(deadline),
    )
    _echo_hex(calldata)


@execution.command("compose-four-leg")
@click.option(
    "--across-fill-calldata",
    required=True,
    type=str,
    help="Hex calldata for the Across fill.",
)
@click.option(
    "--arb-swaps-json",
    required=True,
    type=str,
    help="JSON array of arbitrage swap-step objects.",
)
@click.option(
    "--cow-fill-calldata",
    required=True,
    type=str,
    help="Hex calldata for the CoW fill.",
)
@click.option(
    "--uniswapx-rebalance-calldata",
    required=True,
    type=str,
    help="Hex calldata for the UniswapX rebalance.",
)
@click.option("--flash-lender", required=True, type=str, help="Flash-loan lender address.")
@click.option("--flash-protocol", required=True, type=str, help="Flash protocol selector name.")
@click.option("--flash-token", required=True, type=str, help="Flash-loan token address.")
@click.option("--flash-amount", required=True, type=str, help="Flash-loan amount.")
@click.option("--min-profit", required=True, type=str, help="Minimum profit threshold.")
@click.option("--deadline", required=True, type=str, help="Unix deadline.")
def execution_compose_four_leg(
    *,
    across_fill_calldata: str,
    arb_swaps_json: str,
    cow_fill_calldata: str,
    uniswapx_rebalance_calldata: str,
    flash_lender: str,
    flash_protocol: str,
    flash_token: str,
    flash_amount: str,
    min_profit: str,
    deadline: str,
) -> None:
    """Encode `Executor.composeFourLeg` calldata."""

    calldata = encode_compose_four_leg_calldata(
        across_fill_calldata=bytes.fromhex(across_fill_calldata.removeprefix("0x")),
        arb_swaps=_load_json(arb_swaps_json),
        cow_fill_calldata=bytes.fromhex(cow_fill_calldata.removeprefix("0x")),
        uniswapx_rebalance_calldata=bytes.fromhex(uniswapx_rebalance_calldata.removeprefix("0x")),
        flash_lender=flash_lender,
        flash_protocol=flash_protocol,
        flash_token=flash_token,
        flash_amount=int(flash_amount),
        min_profit=int(min_profit),
        deadline=int(deadline),
    )
    _echo_hex(calldata)
