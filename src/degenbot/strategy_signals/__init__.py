"""Strategy-signal catalogs and candidate metadata."""

from .arbitrum_atomic_flash_research import (
    ATOMIC_FLASH_TARGETS,
    AtomicFlashStatus,
    AtomicFlashTarget,
    atomic_flash_target,
    ranked_atomic_flash_targets,
    workflow_required_atomic_flash_targets,
)
from .jaredbot_poc_catalog import (
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
    "ATOMIC_FLASH_TARGETS",
    "JAREDBOT_POCS",
    "AtomicFlashStatus",
    "AtomicFlashTarget",
    "CapitalMode",
    "JaredBotPoc",
    "PocStage",
    "PocStatus",
    "atomic_flash_target",
    "executable_pocs",
    "poc_for_skill",
    "pocs_for_status",
    "ranked_atomic_flash_targets",
    "workflow_required_atomic_flash_targets",
    "workflow_required_pocs",
)
