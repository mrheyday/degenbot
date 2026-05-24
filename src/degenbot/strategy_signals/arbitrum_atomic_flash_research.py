"""Compatibility wrapper for canonical degenbot atomic-flash targets."""

from __future__ import annotations

from degenbot.strategy_signals.arbitrum_atomic_flash_research import (
    ATOMIC_FLASH_TARGETS,
    AtomicFlashStatus,
    AtomicFlashTarget,
    atomic_flash_target,
    ranked_atomic_flash_targets,
    workflow_required_atomic_flash_targets,
)

__all__ = (
    "ATOMIC_FLASH_TARGETS",
    "AtomicFlashStatus",
    "AtomicFlashTarget",
    "atomic_flash_target",
    "ranked_atomic_flash_targets",
    "workflow_required_atomic_flash_targets",
)
