import pytest
from click.testing import CliRunner

from degenbot.bot import BotOpportunity
from degenbot.cli import cli
from degenbot.version import __version__


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_cli_help(runner: CliRunner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "bot" in result.output


def test_cli_version(runner: CliRunner):
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


# TODO: create fake database for reset/upgrade tests


def test_cli_database_reset(runner: CliRunner):
    result = runner.invoke(cli, ["database", "reset"], input="n")
    assert result.exit_code == 1

    result = runner.invoke(cli, ["database", "reset"], input="")
    assert result.exit_code == 1


def test_cli_database_upgrade(runner: CliRunner):
    result = runner.invoke(cli, ["database", "upgrade"], input="n")
    assert result.exit_code == 1

    result = runner.invoke(cli, ["database", "upgrade"], input="")
    assert result.exit_code == 1


def test_cli_bot_best(monkeypatch: pytest.MonkeyPatch, runner: CliRunner) -> None:
    class _FakeBot:
        def best(self, **kwargs):
            return BotOpportunity(
                strategy_id="WETH -> DAI -> WETH",
                result=type(
                    "R",
                    (),
                    {
                        "profit_amount": 123,
                        "input_amount": 456,
                        "state_block": 789,
                    },
                )(),
                payloads=("payload",),
            )

    monkeypatch.setattr(
        "degenbot.cli.bot.DegenbotBot.from_pathfinding",
        lambda **kwargs: _FakeBot(),
    )

    result = runner.invoke(
        cli,
        [
            "bot",
            "best",
            "--chain-id",
            "1",
            "--input-token",
            "0x0000000000000000000000000000000000000001",
            "--from-address",
            "0x000000000000000000000000000000000000dEaD",
        ],
    )

    assert result.exit_code == 0
    assert "strategy: WETH -> DAI -> WETH" in result.output


def test_cli_aave_update_help(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["aave", "update", "--help"])
    assert result.exit_code == 0
    assert "--debug-output" in result.output


@pytest.mark.parametrize(
    "aave_command",
    [
        "ethereum_aave_v3",
        "arbitrum_aave_v3",
    ],
)
def test_cli_aave_activation_commands_are_registered(
    runner: CliRunner,
    aave_command: str,
) -> None:
    activate_result = runner.invoke(cli, ["aave", "activate", aave_command, "--help"])
    assert activate_result.exit_code == 0

    deactivate_result = runner.invoke(cli, ["aave", "deactivate", aave_command, "--help"])
    assert deactivate_result.exit_code == 0


@pytest.mark.parametrize(
    "exchange_command",
    [
        "arbitrum_camelot_v2",
        "arbitrum_camelot_v3",
        "arbitrum_curve_stableswap_ng",
        "arbitrum_sushiswap_v2",
        "arbitrum_sushiswap_v3",
        "arbitrum_uniswap_v2",
        "arbitrum_uniswap_v3",
        "arbitrum_uniswap_v4",
    ],
)
def test_cli_arbitrum_exchange_commands_are_registered(
    runner: CliRunner,
    exchange_command: str,
) -> None:
    activate_result = runner.invoke(cli, ["exchange", "activate", exchange_command, "--help"])
    assert activate_result.exit_code == 0

    deactivate_result = runner.invoke(cli, ["exchange", "deactivate", exchange_command, "--help"])
    assert deactivate_result.exit_code == 0
