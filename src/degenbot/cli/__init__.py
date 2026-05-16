import click


@click.group()
@click.version_option()
def cli() -> None: ...


from . import aave, bot, database, exchange, execution, pool  # noqa: F401, E402
