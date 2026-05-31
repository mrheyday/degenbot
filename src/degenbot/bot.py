from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, cast

from degenbot.arbitrage.uniswap_curve_cycle import UniswapCurveCycle
from degenbot.arbitrage.uniswap_lp_cycle import UniswapLpCycle
from degenbot.checksum_cache import get_checksum_address
from degenbot.erc20 import Erc20Token, Erc20TokenManager
from degenbot.exceptions.base import DegenbotError
from degenbot.logging import logger
from degenbot.pathfinding import find_paths
from degenbot.registry import pool_registry

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from fractions import Fraction

    from degenbot.types.aliases import BlockNumber, ChainId


if TYPE_CHECKING:
    ArbitrageStrategy = Any
else:

    class ArbitrageStrategy(Protocol):
        """
        Runtime protocol for degenbot arbitrage strategies.

        Concrete strategies expose narrower typed methods, so static checks treat
        the bot composition boundary as dynamic while runtime code keeps the
        documented shape.
        """

        id: str

        def calculate(self, **kwargs: Any) -> Any: ...

        def generate_payloads(self, **kwargs: Any) -> Sequence[Any]: ...


@dataclass(slots=True, frozen=True)
class BotOpportunity:
    """
    A ranked, execution-ready arbitrage opportunity.
    """

    strategy_id: str
    result: Any
    payloads: tuple[Any, ...]
    swap_pools: tuple[Any, ...] = ()

    @property
    def profit_amount(self) -> int:
        return int(self.result.profit_amount)

    @property
    def state_block(self) -> int | None:
        state_block = self.result.state_block
        return int(state_block) if state_block is not None else None

    @property
    def input_amount(self) -> int:
        return int(self.result.input_amount)


@dataclass(slots=True, frozen=True)
class BotScanConfig:
    """
    Shared execution policy for a bot scan.
    """

    from_address: str
    min_profit: int = 0
    min_rate_of_exchange: Fraction | None = None


class DegenbotBot:
    """
    Deterministic opportunity scanner and payload assembler.

    This class does not duplicate pool math. It composes the existing degenbot
    arbitrage strategies and emits the best execution candidates in a stable,
    sortable order.
    """

    def __init__(self, strategies: Sequence[ArbitrageStrategy]) -> None:
        if not strategies:
            msg = "At least one arbitrage strategy must be supplied."
            raise ValueError(msg)

        self._strategies = tuple(strategies)

    @classmethod
    def from_pathfinding(
        cls,
        *,
        chain_id: ChainId,
        input_token: Erc20Token | str,
        min_depth: int = 2,
        max_depth: int | None = None,
        max_input: int | None = None,
        pool_types: Sequence[type] | None = None,
        block_number: BlockNumber | None = None,
    ) -> DegenbotBot:
        """
        Build a bot from the currently registered pools and the pathfinder.

        This constructor is intentionally conservative: only paths whose pools are already
        present in the registry are converted into strategies. That keeps discovery deterministic
        and avoids mutating live state.
        """

        if isinstance(input_token, Erc20Token) or hasattr(input_token, "address"):
            token = cast("Erc20Token", input_token)
        else:
            token_manager = Erc20TokenManager(chain_id=chain_id)
            token = token_manager.get_erc20token(get_checksum_address(input_token))

        strategy_list: list[ArbitrageStrategy] = []
        seen: set[tuple[str, ...]] = set()
        find_paths_kwargs: dict[str, Any] = {
            "chain_id": chain_id,
            "start_tokens": [token.address],
            "end_tokens": [token.address],
            "min_depth": min_depth,
            "max_depth": max_depth,
        }
        if pool_types is not None:
            find_paths_kwargs["pool_types"] = pool_types

        for path in find_paths(**find_paths_kwargs):
            pools: list[Any] = []
            path_key: list[str] = []

            for step in path:
                pool = pool_registry.get(
                    chain_id=chain_id,
                    pool_address=step.address,
                    pool_id=step.hash,
                )
                if pool is None:
                    logger.debug("Skipping path step %s because the pool is not registered", step)
                    pools = []
                    break
                pools.append(pool)
                path_key.append(f"{step.address.lower()}:{step.hash or ''}")

            if not pools:
                continue

            dedupe_key = tuple(path_key)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            strategy_id = " -> ".join(pool.name for pool in pools)
            strategy: ArbitrageStrategy
            if any(pool.__class__.__name__ == "CurveStableswapPool" for pool in pools):
                strategy = UniswapCurveCycle(
                    input_token=token,
                    swap_pools=pools,
                    id=strategy_id,
                    max_input=max_input,
                )
            else:
                strategy = UniswapLpCycle(
                    input_token=token,
                    swap_pools=pools,
                    id=strategy_id,
                    max_input=max_input,
                )
            strategy_list.append(strategy)

        logger.info(
            "Built %d candidate arbitrage strategies for chain %s at block %s",
            len(strategy_list),
            chain_id,
            block_number if block_number is not None else "latest",
        )
        return cls(strategy_list)

    @property
    def strategies(self) -> tuple[ArbitrageStrategy, ...]:
        return self._strategies

    def scan(
        self,
        *,
        config: BotScanConfig,
        calculate_kwargs: Mapping[str, Any] | None = None,
        payload_kwargs: Mapping[str, Any] | None = None,
    ) -> tuple[BotOpportunity, ...]:
        """
        Evaluate every strategy, filter by profit, and rank the viable results.
        """

        calculate_kwargs = dict(calculate_kwargs or {})
        payload_kwargs = dict(payload_kwargs or {})

        if config.min_rate_of_exchange is not None:
            calculate_kwargs.setdefault("min_rate_of_exchange", config.min_rate_of_exchange)

        opportunities: list[BotOpportunity] = []

        for strategy in self._strategies:
            try:
                result = strategy.calculate(**calculate_kwargs)
            except DegenbotError as exc:
                logger.debug("Skipping strategy %s after degenbot error: %s", strategy.id, exc)
                continue
            except Exception as exc:  # pragma: no cover - defensive boundary
                logger.debug("Skipping strategy %s after unexpected error: %s", strategy.id, exc)
                continue

            if int(result.profit_amount) < config.min_profit:
                continue

            try:
                payloads = tuple(
                    strategy.generate_payloads(
                        from_address=config.from_address,
                        swap_amount=int(result.input_amount),
                        pool_swap_amounts=result.swap_amounts,
                        **payload_kwargs,
                    )
                )
            except DegenbotError as exc:
                logger.debug("Skipping payload assembly for strategy %s: %s", strategy.id, exc)
                continue
            except Exception as exc:  # pragma: no cover - defensive boundary
                logger.debug(
                    "Skipping payload assembly for strategy %s after unexpected error: %s",
                    strategy.id,
                    exc,
                )
                continue

            opportunities.append(
                BotOpportunity(
                    strategy_id=strategy.id,
                    result=result,
                    payloads=payloads,
                    swap_pools=tuple(getattr(strategy, "swap_pools", ())),
                )
            )

        return tuple(
            sorted(
                opportunities,
                key=lambda opp: (
                    -opp.profit_amount,
                    -(opp.state_block if opp.state_block is not None else -1),
                    opp.strategy_id,
                ),
            )
        )

    def best(
        self,
        *,
        config: BotScanConfig,
        calculate_kwargs: Mapping[str, Any] | None = None,
        payload_kwargs: Mapping[str, Any] | None = None,
    ) -> BotOpportunity | None:
        """
        Return the highest-ranked opportunity, or `None` if nothing qualifies.
        """

        opportunities = self.scan(
            config=config,
            calculate_kwargs=calculate_kwargs,
            payload_kwargs=payload_kwargs,
        )
        return opportunities[0] if opportunities else None
