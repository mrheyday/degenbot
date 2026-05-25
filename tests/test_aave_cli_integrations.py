from __future__ import annotations

import json
from types import SimpleNamespace

from eth_abi.abi import encode

from degenbot.aave.events import ScaledTokenEventType
from degenbot.cli.aave_debug_logger import AaveDebugLogger
from degenbot.cli.aave_event_matching import OperationAwareEventMatcher
from degenbot.cli.aave_transaction_operations import Operation, OperationType, ScaledTokenEvent


def test_aave_debug_logger_writes_jsonl(tmp_path) -> None:
    logger = AaveDebugLogger()
    logger.close()

    output_path = tmp_path / "aave-debug.jsonl"
    assert logger.configure(output_path=output_path)
    logger.log_event(level="info", message="hello", block_number=123, context={"key": "value"})
    logger.close()

    lines = output_path.read_text().splitlines()
    assert len(lines) >= 2

    first = json.loads(lines[0])
    second = json.loads(lines[1])
    assert first["type"] == "session_start"
    assert second["type"] == "log"
    assert second["message"] == "hello"
    assert second["context"] == {"key": "value"}


def test_operation_aware_event_matcher_repay_consumption_policy() -> None:
    pool_event = {
        "topics": [b"\x01" * 32, b"\x02" * 32, b"\x03" * 32, b"\x04" * 32],
        "data": encode(["uint256", "bool"], [123, True]),
    }
    scaled_event = ScaledTokenEvent(
        event={
            "logIndex": 1,
            "topics": [b"\x05" * 32],
            "address": "0x0000000000000000000000000000000000000001",
        },
        event_type=ScaledTokenEventType.DEBT_MINT,
        user_address="0x0000000000000000000000000000000000000002",
        caller_address=None,
        from_address=None,
        target_address=None,
        amount=123,
        balance_increase=456,
        index=789,
    )

    class _Enricher:
        def enrich(self, *, scaled_event, operation):
            return SimpleNamespace(
                raw_amount=scaled_event.amount, scaled_amount=scaled_event.amount
            )

    operation = Operation(
        operation_id=1,
        operation_type=OperationType.REPAY,
        pool_revision=9,
        pool_event=pool_event,
        scaled_token_events=[scaled_event],
        transfer_events=[],
        balance_transfer_events=[],
    )

    matcher = OperationAwareEventMatcher(operation, _Enricher())
    result = matcher.find_match(scaled_event)
    assert result.pool_event == pool_event
    assert result.should_consume is False

    pool_event_false = {
        "topics": [b"\x01" * 32, b"\x02" * 32, b"\x03" * 32, b"\x04" * 32],
        "data": encode(["uint256", "bool"], [123, False]),
    }
    operation_false = Operation(
        operation_id=2,
        operation_type=OperationType.REPAY,
        pool_revision=9,
        pool_event=pool_event_false,
        scaled_token_events=[scaled_event],
        transfer_events=[],
        balance_transfer_events=[],
    )

    matcher_false = OperationAwareEventMatcher(operation_false, _Enricher())
    result_false = matcher_false.find_match(scaled_event)
    assert result_false.should_consume is True
