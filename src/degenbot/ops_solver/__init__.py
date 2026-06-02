"""ApeWorx-based operational scripts.

Isolated from the main solver loop. Foundry remains the canonical
contract development framework per PROGRESS.md; ApeWorx here is the
Python-side ops complement only.

See README.md in this directory for use cases and constraints.
"""

from degenbot.ops_solver.execution_policy import (
    ALLOWED_STRICT_TRANSPORTS,
    ExecutionPolicyContext,
    ExecutionPolicyViolation,
    StrictExecutionPolicyError,
    enforce_execution_policy,
    execution_policy_context_from_plan,
    normalize_transport,
    validate_execution_policy,
)
from degenbot.ops_solver.strict_dispatch import compose_strict_dispatch_envelope

__all__ = [
    "ALLOWED_STRICT_TRANSPORTS",
    "ExecutionPolicyContext",
    "ExecutionPolicyViolation",
    "StrictExecutionPolicyError",
    "compose_strict_dispatch_envelope",
    "enforce_execution_policy",
    "execution_policy_context_from_plan",
    "normalize_transport",
    "validate_execution_policy",
]
