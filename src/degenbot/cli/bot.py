from __future__ import annotations

from fractions import Fraction

import click

from degenbot.bot import BotScanConfig, DegenbotBot
from degenbot.cli import cli


@cli.group()
def bot() -> None:
    """Deterministic arbitrage bot commands."""


@bot.command("best")
@click.option("--chain-id", required=True, type=int, help="Chain ID to scan.")
@click.option("--input-token", required=True, type=str, help="Start/end token address.")
@click.option(
    "--from-address",
    required=True,
    type=str,
    help="Execution sender address used when assembling payloads.",
)
@click.option("--min-depth", default=2, show_default=True, type=int, help="Minimum path depth.")
@click.option(
    "--max-depth",
    default=None,
    type=int,
    help="Maximum path depth. Leave unset for no upper bound.",
)
@click.option(
    "--max-input",
    default=None,
    type=int,
    help="Upper bound for the arbitrage solver input amount.",
)
@click.option(
    "--min-profit",
    default=0,
    show_default=True,
    type=int,
    help="Minimum profit required to report an opportunity.",
)
@click.option(
    "--min-rate-of-exchange",
    default=None,
    type=str,
    help="Optional minimum rate of exchange threshold (e.g. 1.01 or 9/10).",
)
def bot_best(
    *,
    chain_id: int,
    input_token: str,
    from_address: str,
    min_depth: int,
    max_depth: int | None,
    max_input: int | None,
    min_profit: int,
    min_rate_of_exchange: str | None,
) -> None:
    """Scan registered pools and print the highest-ranked opportunity."""

    bot = DegenbotBot.from_pathfinding(
        chain_id=chain_id,
        input_token=input_token,
        min_depth=min_depth,
        max_depth=max_depth,
        max_input=max_input,
    )

    rate = Fraction(min_rate_of_exchange) if min_rate_of_exchange is not None else None
    best = bot.best(
        config=BotScanConfig(
            from_address=from_address,
            min_profit=min_profit,
            min_rate_of_exchange=rate,
        )
    )

    if best is None:
        click.echo("No qualifying opportunities found.")
        return

    click.echo(f"strategy: {best.strategy_id}")
    click.echo(f"profit: {best.profit_amount}")
    click.echo(f"input_amount: {best.input_amount}")
    click.echo(f"state_block: {best.state_block}")
    click.echo(f"payloads: {len(best.payloads)}")
