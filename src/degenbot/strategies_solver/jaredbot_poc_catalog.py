"""Compatibility wrapper for the canonical degenbot JaredBot POC catalog."""

from __future__ import annotations

from degenbot.strategy_signals.jaredbot_poc_catalog import (
    JAREDBOT_POCS,
    CapitalMode,
    JaredBotPoc,
    PocStage,
    PocStatus,
    executable_pocs,
    poc_for_skill,
    pocs_for_status,
    workflow_required_pocs,
)

__all__ = (
    "JAREDBOT_POCS",
    "CapitalMode",
    "JaredBotPoc",
    "PocStage",
    "PocStatus",
    "executable_pocs",
    "poc_for_skill",
    "pocs_for_status",
    "workflow_required_pocs",
)
