"""Compatibility package for migrated solver strategies."""

from degenbot.strategies.arbitrum_atomic_flash_research import (
    ATOMIC_FLASH_TARGETS,
    AtomicFlashStatus,
    AtomicFlashTarget,
    atomic_flash_target,
    ranked_atomic_flash_targets,
    workflow_required_atomic_flash_targets,
)
from degenbot.strategies.d3_filter import D3Filter, OrderClass
from degenbot.strategies.solver_quality import Solution, SolutionBuilder

__all__ = [
    "ATOMIC_FLASH_TARGETS",
    "AtomicFlashStatus",
    "AtomicFlashTarget",
    "D3Filter",
    "OrderClass",
    "Solution",
    "SolutionBuilder",
    "atomic_flash_target",
    "ranked_atomic_flash_targets",
    "workflow_required_atomic_flash_targets",
]
