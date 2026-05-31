"""Deterministic collector -> strategy -> executor pipeline primitives.

This module adapts the useful Artemis shape to degenbot's execution doctrine:
collectors emit typed events, strategies emit named actions, and executors are
selected explicitly by name. There is no implicit broadcast to every executor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, Protocol

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Mapping, Sequence

FaultStage = Literal["sync", "collector", "strategy", "routing", "executor"]


@dataclass(frozen=True, slots=True)
class PipelineAction[PayloadT]:
    """Strategy output routed to exactly one named executor."""

    trace_id: str
    strategy: str
    executor: str
    payload: PayloadT


@dataclass(frozen=True, slots=True)
class PipelineFault:
    """Structured pipeline fault for telemetry and fail-closed handling."""

    stage: FaultStage
    component: str
    trace_id: str | None
    message: str


@dataclass(frozen=True, slots=True)
class PipelineMetrics:
    """Terminal metrics for a finite pipeline run."""

    events_seen: int
    actions_emitted: int
    actions_executed: int
    faults: tuple[PipelineFault, ...]


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    """Runtime policy for the deterministic pipeline."""

    continue_on_fault: bool = False


class PipelineError(RuntimeError):
    """Raised when the pipeline fails closed."""

    def __init__(self, fault: PipelineFault) -> None:
        super().__init__(f"{fault.stage}:{fault.component}:{fault.message}")
        self.fault = fault


class PipelineConfigurationError(ValueError):
    """Raised for invalid pipeline topology."""


class PipelineCollector[EventT](Protocol):
    """Source of normalized market or protocol events."""

    @property
    def name(self) -> str: ...

    def collect(self) -> AsyncIterator[EventT]: ...


class PipelineStrategy[EventT, PayloadT](Protocol):
    """Stateful strategy that converts events into routed actions."""

    @property
    def name(self) -> str: ...

    async def sync_state(self) -> None: ...

    async def process_event(self, event: EventT) -> Sequence[PipelineAction[PayloadT]]: ...


class PipelineExecutor[PayloadT](Protocol):
    """Named side-effect boundary for one action family."""

    @property
    def name(self) -> str: ...

    async def execute(self, action: PipelineAction[PayloadT]) -> None: ...


class DeterministicPipeline[EventT, PayloadT]:
    """Finite, auditable event/action pipeline.

    The pipeline is intentionally sequential. Hot-path fanout can run before or
    after this layer, but this boundary preserves deterministic ordering and
    one-action-to-one-executor routing for admission and tests.
    """

    def __init__(
        self,
        *,
        collectors: Sequence[PipelineCollector[EventT]],
        strategies: Sequence[PipelineStrategy[EventT, PayloadT]],
        executors: Sequence[PipelineExecutor[PayloadT]],
        config: PipelineConfig | None = None,
    ) -> None:
        self._collectors = tuple(collectors)
        self._strategies = tuple(strategies)
        self._executors = _index_by_name(executors, "executor")
        self._config = config or PipelineConfig()
        _require_non_empty(self._collectors, "collector")
        _require_non_empty(self._strategies, "strategy")
        _require_non_empty(self._executors, "executor")
        _assert_unique_names(self._collectors, "collector")
        _assert_unique_names(self._strategies, "strategy")

    async def run(self, *, max_events: int | None = None) -> PipelineMetrics:
        """Run collectors until exhaustion or `max_events` and return metrics."""

        if max_events is not None and max_events < 0:
            message = "max_events_negative"
            raise PipelineConfigurationError(message)

        counters = _PipelineCounters()
        for strategy in self._strategies:
            try:
                await strategy.sync_state()
            except Exception as exc:
                self._handle_fault(
                    counters,
                    PipelineFault("sync", strategy.name, None, str(exc)),
                )

        for collector in self._collectors:
            try:
                async for event in collector.collect():
                    if max_events is not None and counters.events_seen >= max_events:
                        break
                    counters.events_seen += 1
                    await self._process_event(event, counters)
            except PipelineError:
                raise
            except Exception as exc:
                self._handle_fault(
                    counters,
                    PipelineFault("collector", collector.name, None, str(exc)),
                )

        return counters.freeze()

    async def _process_event(self, event: EventT, counters: _PipelineCounters) -> None:
        for strategy in self._strategies:
            try:
                actions = await strategy.process_event(event)
            except Exception as exc:
                self._handle_fault(
                    counters,
                    PipelineFault("strategy", strategy.name, None, str(exc)),
                )
                continue

            for action in actions:
                if not self._validate_action(strategy.name, action, counters):
                    continue
                counters.actions_emitted += 1
                executor = self._executors[action.executor]
                try:
                    await executor.execute(action)
                    counters.actions_executed += 1
                except Exception as exc:
                    self._handle_fault(
                        counters,
                        PipelineFault("executor", executor.name, action.trace_id, str(exc)),
                    )

    def _validate_action(
        self,
        strategy_name: str,
        action: PipelineAction[PayloadT],
        counters: _PipelineCounters,
    ) -> bool:
        valid = True
        if not action.trace_id:
            self._handle_fault(counters, PipelineFault("strategy", strategy_name, None, "trace_id"))
            valid = False
        if action.strategy != strategy_name:
            self._handle_fault(
                counters,
                PipelineFault("strategy", strategy_name, action.trace_id, "strategy_mismatch"),
            )
            valid = False
        if action.executor not in self._executors:
            self._handle_fault(
                counters,
                PipelineFault("routing", action.executor, action.trace_id, "unknown_executor"),
            )
            valid = False
        return valid

    def _handle_fault(self, counters: _PipelineCounters, fault: PipelineFault) -> None:
        counters.faults.append(fault)
        if not self._config.continue_on_fault:
            raise PipelineError(fault)


@dataclass(slots=True)
class _PipelineCounters:
    events_seen: int = 0
    actions_emitted: int = 0
    actions_executed: int = 0
    faults: list[PipelineFault] = field(default_factory=list)

    def freeze(self) -> PipelineMetrics:
        return PipelineMetrics(
            events_seen=self.events_seen,
            actions_emitted=self.actions_emitted,
            actions_executed=self.actions_executed,
            faults=tuple(self.faults or ()),
        )


def _require_non_empty(value: Sequence[object] | Mapping[str, object], label: str) -> None:
    if not value:
        message = f"missing_{label}"
        raise PipelineConfigurationError(message)


def _assert_unique_names(components: Sequence[object], label: str) -> None:
    seen: set[str] = set()
    for component in components:
        name = str(getattr(component, "name", ""))
        if not name:
            message = f"unnamed_{label}"
            raise PipelineConfigurationError(message)
        if name in seen:
            message = f"duplicate_{label}"
            raise PipelineConfigurationError(message)
        seen.add(name)


def _index_by_name[PayloadT](
    components: Sequence[PipelineExecutor[PayloadT]],
    label: str,
) -> dict[str, PipelineExecutor[PayloadT]]:
    indexed: dict[str, PipelineExecutor[PayloadT]] = {}
    for component in components:
        name = component.name
        if not name:
            message = f"unnamed_{label}"
            raise PipelineConfigurationError(message)
        if name in indexed:
            message = f"duplicate_{label}"
            raise PipelineConfigurationError(message)
        indexed[name] = component
    return indexed


__all__ = [
    "DeterministicPipeline",
    "PipelineAction",
    "PipelineCollector",
    "PipelineConfig",
    "PipelineConfigurationError",
    "PipelineError",
    "PipelineExecutor",
    "PipelineFault",
    "PipelineMetrics",
    "PipelineStrategy",
]
