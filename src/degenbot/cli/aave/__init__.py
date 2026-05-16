"""Aave V3 CLI subpackage for market management and position tracking."""

from degenbot.cli.aave import commands
from degenbot.cli.aave.commands import aave
from degenbot.cli.aave_debug_logger import AaveDebugLogger, aave_debug_logger
from degenbot.cli.aave_event_matching import (
    EventConsumptionPolicy,
    EventMatchResult,
    MatchConfig,
    OperationAwareEventMatcher,
)
from degenbot.cli.aave.constants import (
    AAVE_EVENT_TOPIC_TO_CATEGORY,
    GHO_DISCOUNT_DEPRECATION_REVISION,
    POSITION_RISK_DISPLAY_LIMIT,
    SCALED_AMOUNT_POOL_REVISION,
    UserOperation,
    WadRayMathLibrary,
)
from degenbot.cli.aave.event_fetchers import (
    fetch_address_provider_events,
    fetch_discount_config_events,
    fetch_oracle_events,
    fetch_pool_events,
    fetch_reserve_initialization_events,
    fetch_scaled_token_events,
    fetch_stk_aave_events,
)
from degenbot.cli.aave.types import TokenType, TransactionContext

__all__ = [
    "AAVE_EVENT_TOPIC_TO_CATEGORY",
    "GHO_DISCOUNT_DEPRECATION_REVISION",
    "POSITION_RISK_DISPLAY_LIMIT",
    "SCALED_AMOUNT_POOL_REVISION",
    "AaveDebugLogger",
    "TokenType",
    "TransactionContext",
    "UserOperation",
    "WadRayMathLibrary",
    "aave_debug_logger",
    "aave",
    "commands",
    "EventConsumptionPolicy",
    "EventMatchResult",
    "fetch_address_provider_events",
    "fetch_discount_config_events",
    "fetch_oracle_events",
    "fetch_pool_events",
    "fetch_reserve_initialization_events",
    "fetch_scaled_token_events",
    "fetch_stk_aave_events",
    "MatchConfig",
    "OperationAwareEventMatcher",
]
