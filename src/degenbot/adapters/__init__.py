"""Adapter registry package.

This package is the Python-side structure for venue adapters. It mirrors
canonical contract addresses from `coordinator/src/router/registry.ts` while
keeping executable logic in the existing `driver.execution.*` modules.
"""

from degenbot.adapters.laneadapters import EXECUTION_LANES
from degenbot.adapters.readiness import (
    READINESS_EVIDENCE,
    ReadinessEvidence,
    ReadinessStatus,
    evidence_for_adapter,
    evidence_for_lane,
    readiness_evidence_for_id,
)
from degenbot.adapters.registry import (
    ALL_ADAPTERS,
    adapter_for,
    adapters_by_category,
    adapters_by_status,
    lane_for,
    lanes_by_status,
)
from degenbot.adapters.source import (
    SourceVerificationRequest,
    SourcifyStatus,
    parse_sourcify_status,
    source_verification_request,
    source_verification_requests,
)
from degenbot.adapters.templates import (
    AdapterCategory,
    AdapterStatus,
    AdapterTemplate,
    ContractBinding,
    DefiLlamaReference,
    ExecutionLane,
    ExecutionLaneTemplate,
    RegistryKey,
)

__all__ = [
    "ALL_ADAPTERS",
    "EXECUTION_LANES",
    "READINESS_EVIDENCE",
    "AdapterCategory",
    "AdapterStatus",
    "AdapterTemplate",
    "ContractBinding",
    "DefiLlamaReference",
    "ExecutionLane",
    "ExecutionLaneTemplate",
    "ReadinessEvidence",
    "ReadinessStatus",
    "RegistryKey",
    "SourceVerificationRequest",
    "SourcifyStatus",
    "adapter_for",
    "adapters_by_category",
    "adapters_by_status",
    "evidence_for_adapter",
    "evidence_for_lane",
    "lane_for",
    "lanes_by_status",
    "parse_sourcify_status",
    "readiness_evidence_for_id",
    "source_verification_request",
    "source_verification_requests",
]
