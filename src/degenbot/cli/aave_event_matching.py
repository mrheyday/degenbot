"""Aave V3 event matching framework."""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Protocol

from eth_abi.abi import decode
from web3.types import LogReceipt

from degenbot.aave.events import AaveV3PoolEvent, ScaledTokenEventType
from degenbot.aave.models import EnrichedScaledTokenEvent
from degenbot.cli.aave_transaction_operations import Operation, OperationType, ScaledTokenEvent

if TYPE_CHECKING:
    from degenbot.aave.enrichment import ScaledEventEnricher


class TransactionContext(Protocol):
    """Protocol for transaction context."""

    last_withdraw_amount: int


class EventConsumptionPolicy(Enum):
    """Policy for consuming pool events after matching."""

    CONSUMABLE = auto()
    REUSABLE = auto()
    CONDITIONAL = auto()


@dataclass(frozen=True)
class MatchConfig:
    """Configuration for matching a scaled token event to pool events."""

    target_event: ScaledTokenEventType
    pool_event_types: list[AaveV3PoolEvent] = field(default_factory=list)
    consumption_policy: EventConsumptionPolicy = EventConsumptionPolicy.CONSUMABLE
    consumption_condition: Callable[[LogReceipt], bool] | None = None


@dataclass(frozen=True)
class EventMatchResult:
    """Result of a successful event match with enriched scaled amounts."""

    pool_event: LogReceipt | None
    should_consume: bool
    enriched_event: EnrichedScaledTokenEvent


class OperationAwareEventMatcher:
    """Event matcher that works within operation context."""

    def __init__(
        self,
        operation: Operation,
        enricher: "ScaledEventEnricher",
        tx_context: TransactionContext | None = None,
    ) -> None:
        self.operation = operation
        self.enricher = enricher
        self.tx_context = tx_context

    def find_match(self, scaled_event: ScaledTokenEvent) -> EventMatchResult:
        """Find pool event match within operation context and enrich with scaled amounts."""

        matchers = {
            OperationType.SUPPLY: self._match_supply,
            OperationType.WITHDRAW: self._match_withdraw,
            OperationType.BORROW: self._match_borrow,
            OperationType.GHO_BORROW: self._match_gho_borrow,
            OperationType.REPAY: self._match_repay,
            OperationType.REPAY_WITH_ATOKENS: self._match_repay_with_atokens,
            OperationType.GHO_REPAY: self._match_gho_repay,
            OperationType.LIQUIDATION: self._match_liquidation,
            OperationType.GHO_LIQUIDATION: self._match_gho_liquidation,
            OperationType.GHO_FLASH_LOAN: self._match_flash_loan,
            OperationType.INTEREST_ACCRUAL: self._match_interest_accrual,
            OperationType.BALANCE_TRANSFER: self._match_balance_transfer,
        }

        matcher = matchers.get(self.operation.operation_type, self._default_match)
        pool_event, should_consume = matcher(scaled_event=scaled_event)

        enriched_event = self.enricher.enrich(
            scaled_event=scaled_event,
            operation=self.operation,
        )

        return EventMatchResult(
            pool_event=pool_event,
            should_consume=should_consume,
            enriched_event=enriched_event,
        )

    def _match_supply(self, scaled_event: ScaledTokenEvent) -> tuple[LogReceipt | None, bool]:
        return (self.operation.pool_event, True)

    def _match_withdraw(self, scaled_event: ScaledTokenEvent) -> tuple[LogReceipt | None, bool]:
        return (self.operation.pool_event, True)

    def _match_borrow(self, scaled_event: ScaledTokenEvent) -> tuple[LogReceipt | None, bool]:
        return (self.operation.pool_event, True)

    def _match_gho_borrow(self, scaled_event: ScaledTokenEvent) -> tuple[LogReceipt | None, bool]:
        return (self.operation.pool_event, True)

    def _match_repay(self, scaled_event: ScaledTokenEvent) -> tuple[LogReceipt | None, bool]:
        extraction_data = self._extract_repay_data()
        use_a_tokens = extraction_data.get("use_a_tokens", False)
        return (self.operation.pool_event, not use_a_tokens)

    def _match_repay_with_atokens(
        self,
        scaled_event: ScaledTokenEvent,
    ) -> tuple[LogReceipt | None, bool]:
        return (self.operation.pool_event, False)

    def _match_gho_repay(self, scaled_event: ScaledTokenEvent) -> tuple[LogReceipt | None, bool]:
        return (self.operation.pool_event, True)

    def _match_liquidation(
        self,
        scaled_event: ScaledTokenEvent,
    ) -> tuple[LogReceipt | None, bool]:
        return (self.operation.pool_event, False)

    def _match_gho_liquidation(
        self,
        scaled_event: ScaledTokenEvent,
    ) -> tuple[LogReceipt | None, bool]:
        return (self.operation.pool_event, False)

    def _match_flash_loan(
        self,
        scaled_event: ScaledTokenEvent,
    ) -> tuple[LogReceipt | None, bool]:
        return (self.operation.pool_event, False)

    def _match_interest_accrual(
        self,
        scaled_event: ScaledTokenEvent,
    ) -> tuple[LogReceipt | None, bool]:
        return (self.operation.pool_event, False)

    def _match_balance_transfer(
        self,
        scaled_event: ScaledTokenEvent,
    ) -> tuple[LogReceipt | None, bool]:
        return (self.operation.pool_event, False)

    def _default_match(self, scaled_event: ScaledTokenEvent) -> tuple[LogReceipt | None, bool]:
        return (self.operation.pool_event, True)

    def _extract_supply_data(self) -> dict[str, int]:
        assert self.operation.pool_event is not None

        _, raw_amount = decode(
            types=["address", "uint256"],
            data=self.operation.pool_event["data"],
        )
        return {"raw_amount": raw_amount}

    def _extract_withdraw_data(self) -> dict[str, int]:
        assert self.operation.pool_event is not None

        (raw_amount,) = decode(
            types=["uint256"],
            data=self.operation.pool_event["data"],
        )
        return {"raw_amount": raw_amount}

    def _extract_borrow_data(self) -> dict[str, int]:
        assert self.operation.pool_event is not None

        _, raw_amount, _, _ = decode(
            types=["address", "uint256", "uint8", "uint256"],
            data=self.operation.pool_event["data"],
        )
        return {"raw_amount": raw_amount}

    def _extract_repay_data(self) -> dict[str, int | bool]:
        assert self.operation.pool_event is not None

        raw_amount, use_a_tokens = decode(
            types=["uint256", "bool"],
            data=self.operation.pool_event["data"],
        )
        return {"raw_amount": raw_amount, "use_a_tokens": use_a_tokens}

    def _extract_liquidation_data(self) -> dict[str, int]:
        assert self.operation.pool_event is not None

        debt_to_cover, liquidated_collateral_amount, _, _ = decode(
            types=["uint256", "uint256", "address", "bool"],
            data=self.operation.pool_event["data"],
        )
        return {
            "debt_to_cover": debt_to_cover,
            "liquidated_collateral_amount": liquidated_collateral_amount,
        }
