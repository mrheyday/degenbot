from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from degenbot.pipeline import (
    DeterministicPipeline,
    PipelineAction,
    PipelineConfig,
    PipelineError,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@dataclass(slots=True)
class _Collector:
    name: str
    values: tuple[int, ...]

    async def collect(self) -> AsyncIterator[int]:
        for value in self.values:
            yield value


@dataclass(slots=True)
class _Strategy:
    name: str
    executor: str
    calls: list[str]
    bad_strategy_name: str | None = None

    async def sync_state(self) -> None:
        self.calls.append(f"sync:{self.name}")

    async def process_event(self, event: int) -> tuple[PipelineAction[int], ...]:
        self.calls.append(f"event:{self.name}:{event}")
        strategy_name = self.bad_strategy_name or self.name
        return (
            PipelineAction(
                trace_id=f"trace-{self.name}-{event}",
                strategy=strategy_name,
                executor=self.executor,
                payload=event * 10,
            ),
        )


@dataclass(slots=True)
class _Executor:
    name: str
    executed: list[PipelineAction[int]]

    async def execute(self, action: PipelineAction[int]) -> None:
        self.executed.append(action)


@pytest.mark.asyncio
async def test_pipeline_runs_strategies_in_order_and_routes_to_named_executor() -> None:
    calls: list[str] = []
    executor = _Executor("dispatch", [])
    pipeline = DeterministicPipeline(
        collectors=[_Collector("blocks", (1, 2))],
        strategies=[
            _Strategy("native_arb", "dispatch", calls),
            _Strategy("internal_match", "dispatch", calls),
        ],
        executors=[executor],
    )

    metrics = await pipeline.run()

    assert calls == [
        "sync:native_arb",
        "sync:internal_match",
        "event:native_arb:1",
        "event:internal_match:1",
        "event:native_arb:2",
        "event:internal_match:2",
    ]
    assert [action.trace_id for action in executor.executed] == [
        "trace-native_arb-1",
        "trace-internal_match-1",
        "trace-native_arb-2",
        "trace-internal_match-2",
    ]
    assert metrics.events_seen == 2
    assert metrics.actions_emitted == 4
    assert metrics.actions_executed == 4
    assert metrics.faults == ()


@pytest.mark.asyncio
async def test_pipeline_fails_closed_on_unknown_executor() -> None:
    pipeline = DeterministicPipeline(
        collectors=[_Collector("blocks", (1,))],
        strategies=[_Strategy("native_arb", "missing", [])],
        executors=[_Executor("dispatch", [])],
    )

    with pytest.raises(PipelineError) as excinfo:
        await pipeline.run()

    assert excinfo.value.fault.stage == "routing"
    assert excinfo.value.fault.component == "missing"
    assert excinfo.value.fault.message == "unknown_executor"


@pytest.mark.asyncio
async def test_pipeline_rejects_action_without_matching_strategy_provenance() -> None:
    pipeline = DeterministicPipeline(
        collectors=[_Collector("blocks", (1,))],
        strategies=[
            _Strategy(
                name="native_arb",
                executor="dispatch",
                calls=[],
                bad_strategy_name="four_leg",
            )
        ],
        executors=[_Executor("dispatch", [])],
    )

    with pytest.raises(PipelineError) as excinfo:
        await pipeline.run()

    assert excinfo.value.fault.stage == "strategy"
    assert excinfo.value.fault.component == "native_arb"
    assert excinfo.value.fault.message == "strategy_mismatch"


@pytest.mark.asyncio
async def test_pipeline_can_continue_on_fault_for_shadow_execution() -> None:
    executor = _Executor("dispatch", [])
    pipeline = DeterministicPipeline(
        collectors=[_Collector("blocks", (1, 2))],
        strategies=[
            _Strategy("native_arb", "missing", []),
            _Strategy("internal_match", "dispatch", []),
        ],
        executors=[executor],
        config=PipelineConfig(continue_on_fault=True),
    )

    metrics = await pipeline.run(max_events=1)

    assert metrics.events_seen == 1
    assert metrics.actions_emitted == 1
    assert metrics.actions_executed == 1
    assert [(fault.stage, fault.component, fault.message) for fault in metrics.faults] == [
        ("routing", "missing", "unknown_executor")
    ]
    assert [action.strategy for action in executor.executed] == ["internal_match"]
