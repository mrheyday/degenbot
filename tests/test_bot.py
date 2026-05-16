from dataclasses import dataclass
from fractions import Fraction
from types import SimpleNamespace
from typing import Any

from degenbot.bot import BotScanConfig, DegenbotBot


@dataclass(frozen=True, slots=True)
class _Result:
    id: str
    input_amount: int
    profit_amount: int
    swap_amounts: tuple[int, ...]
    state_block: int | None


class _Strategy:
    def __init__(self, strategy_id: str, result: _Result, payloads: tuple[Any, ...]) -> None:
        self.id = strategy_id
        self._result = result
        self._payloads = payloads
        self.calculate_calls: list[dict[str, Any]] = []
        self.payload_calls: list[dict[str, Any]] = []

    def calculate(self, **kwargs: Any) -> _Result:
        self.calculate_calls.append(kwargs)
        return self._result

    def generate_payloads(self, **kwargs: Any) -> tuple[Any, ...]:
        self.payload_calls.append(kwargs)
        return self._payloads


def test_bot_ranks_by_profit_then_block_then_id() -> None:
    pool = object()
    bot = DegenbotBot(
        strategies=[
            _Strategy("b", _Result("b", 3, 9, (1,), 11), ("payload-b",)),
            _Strategy("a", _Result("a", 2, 9, (1,), 12), ("payload-a",)),
            _Strategy("c", _Result("c", 1, 5, (1,), 13), ("payload-c",)),
        ]
    )
    for strategy in bot.strategies:
        strategy.swap_pools = (pool,)

    best = bot.best(config=BotScanConfig(from_address="0x000000000000000000000000000000000000dEaD"))
    assert best is not None
    assert best.strategy_id == "a"
    assert best.profit_amount == 9
    assert best.payloads == ("payload-a",)
    assert best.swap_pools == (pool,)


def test_bot_applies_policy_and_forwards_kwargs() -> None:
    strategy = _Strategy("one", _Result("one", 7, 12, (4, 5), 42), ("payload",))
    bot = DegenbotBot(strategies=[strategy])
    state_override = object()

    best = bot.best(
        config=BotScanConfig(
            from_address="0x000000000000000000000000000000000000dEaD",
            min_profit=10,
            min_rate_of_exchange=Fraction(9, 10),
        ),
        calculate_kwargs={"state_overrides": {"0x1": state_override}},
        payload_kwargs={"recipient": "0x2"},
    )

    assert best is not None
    assert strategy.calculate_calls == [
        {
            "state_overrides": {"0x1": state_override},
            "min_rate_of_exchange": Fraction(9, 10),
        }
    ]
    assert strategy.payload_calls == [
        {
            "from_address": "0x000000000000000000000000000000000000dEaD",
            "swap_amount": 7,
            "pool_swap_amounts": (4, 5),
            "recipient": "0x2",
        }
    ]
    assert best.profit_amount == 12


def test_bot_from_pathfinding_builds_strategies(monkeypatch) -> None:
    class _Token:
        address = "0x0000000000000000000000000000000000000001"

    class _TokenManager:
        def __init__(self, *, chain_id):
            self.chain_id = chain_id

        def get_erc20token(self, address):
            return _Token()

    class _Strategy:
        def __init__(self, strategy_id: str):
            self.id = strategy_id

        def calculate(self, **kwargs: Any):
            return _Result(self.id, 1, 5, (1,), 123)

        def generate_payloads(self, **kwargs: Any):
            return ("payload",)

    curve_pool = type("CurveStableswapPool", (), {"name": "curve"})()
    other_pool = type("UniswapV2Pool", (), {"name": "lp"})()

    monkeypatch.setattr(
        "degenbot.bot.find_paths",
        lambda **kwargs: [
            [
                SimpleNamespace(address="0x1", hash=None),
                SimpleNamespace(address="0x2", hash=None),
            ]
        ],
    )
    monkeypatch.setattr(
        "degenbot.bot.pool_registry.get",
        lambda **kwargs: [other_pool, curve_pool][0 if kwargs["pool_address"] == "0x1" else 1],
    )
    monkeypatch.setattr("degenbot.bot.Erc20TokenManager", _TokenManager)
    monkeypatch.setattr(
        "degenbot.bot.UniswapCurveCycle",
        lambda **kwargs: _Strategy(kwargs["id"]),
    )
    monkeypatch.setattr(
        "degenbot.bot.UniswapLpCycle",
        lambda **kwargs: _Strategy(kwargs["id"]),
    )

    bot = DegenbotBot.from_pathfinding(chain_id=1, input_token=_Token(), max_input=99)
    assert len(bot.strategies) == 1
    assert bot.strategies[0].id == "lp -> curve"
