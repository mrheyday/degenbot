"""Structured JSON logging for Aave updater debugging.

Provides machine-parseable debug output for autonomous analysis.
"""

import contextlib
import json
import os
import sys
import traceback
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar, Self

import eth_abi.abi
from eth_typing import ChainId
from hexbytes import HexBytes
from web3.types import LogReceipt

from degenbot.aave.events import (
    AaveV3GhoDebtTokenEvent,
    AaveV3PoolConfigEvent,
    AaveV3PoolEvent,
    AaveV3ScaledTokenEvent,
    ERC20Event,
)
from degenbot.cli.aave_types import TransactionContext


class AaveDebugLogger:
    """Structured debug logger for Aave event processing."""

    _instance: ClassVar[Self]

    def __new__(cls) -> Self:
        with contextlib.suppress(AttributeError):
            return cls._instance

        cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        self._output_path: Path | None = None
        self._file_handle: Any = None
        self._chain_id: ChainId | None = None
        self._market_id: int | None = None
        self._buffer: list[dict[str, Any]] = []
        self._buffer_size: int = 100
        self._enabled: bool = False

    def configure(
        self,
        output_path: Path | str | None = None,
        chain_id: ChainId | None = None,
        market_id: int | None = None,
    ) -> bool:
        """Configure the debug logger."""
        if output_path is None:
            output_path = os.environ.get("DEGENBOT_DEBUG_OUTPUT")

        if self._output_path is not None and output_path is None:
            if chain_id is not None:
                self._chain_id = chain_id
            if market_id is not None:
                self._market_id = market_id
            return self._enabled

        if not output_path:
            self._enabled = False
            return False

        if self._file_handle is not None:
            self.close()

        self._output_path = Path(output_path)
        self._chain_id = chain_id
        self._market_id = market_id
        self._enabled = True

        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_handle = self._output_path.open("a", buffering=1, encoding="utf-8")

        self._write_entry(
            {
                "type": "session_start",
                "timestamp": datetime.now(tz=UTC).isoformat(),
                "chain_id": chain_id.value if chain_id else None,
                "market_id": market_id,
            }
        )

        return True

    def is_enabled(self) -> bool:
        """Check if debug logging is enabled."""
        return self._enabled

    def _write_entry(self, entry: dict[str, Any]) -> None:
        """Write a single log entry to the file."""
        if not self._enabled or self._file_handle is None:
            return

        entry["_chain_id"] = self._chain_id.value if self._chain_id else None
        entry["_market_id"] = self._market_id

        try:
            self._file_handle.write(json.dumps(entry, default=str) + "\n")
        except OSError as e:
            sys.stderr.write(f"Failed to write debug log: {e}\n")

    def log_event(
        self,
        *,
        level: str,
        message: str,
        tx_hash: HexBytes | str | None = None,
        block_number: int | None = None,
        user_address: str | None = None,
        user_addresses: list[str] | None = None,
        event_type: str | None = None,
        event_data: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Log a structured event."""
        if not self._enabled:
            return

        entry: dict[str, Any] = {
            "type": "log",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "level": level.upper(),
            "message": message,
            "tx_hash": tx_hash.to_0x_hex() if isinstance(tx_hash, HexBytes) else tx_hash,
            "block_number": block_number,
            "user_address": user_address,
            "event_type": event_type,
            "context": context or {},
        }

        if user_addresses is not None:
            entry["user_addresses"] = sorted(user_addresses)

        if event_data is not None:
            entry["event_data"] = event_data

        self._write_entry(entry)

    def log_transaction_start(
        self,
        *,
        tx_hash: HexBytes | str,
        block_number: int,
        event_count: int,
        context: TransactionContext | None = None,
    ) -> None:
        """Log the start of transaction processing."""
        if not self._enabled:
            return

        entry: dict[str, Any] = {
            "type": "transaction_start",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "tx_hash": tx_hash.to_0x_hex() if isinstance(tx_hash, HexBytes) else tx_hash,
            "block_number": block_number,
            "event_count": event_count,
        }

        if context is not None:
            entry["tx_context"] = self._serialize_tx_context(context)

        self._write_entry(entry)

    def log_transaction_end(
        self,
        *,
        tx_hash: HexBytes | str,
        block_number: int,
        success: bool,
        duration_ms: float | None = None,
    ) -> None:
        """Log the end of transaction processing."""
        if not self._enabled:
            return

        entry = {
            "type": "transaction_end",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "tx_hash": tx_hash.to_0x_hex() if isinstance(tx_hash, HexBytes) else tx_hash,
            "block_number": block_number,
            "success": success,
            "duration_ms": duration_ms,
        }

        self._write_entry(entry)

    def log_exception(
        self,
        *,
        exc: Exception,
        tx_context: TransactionContext | None = None,
        event: LogReceipt | None = None,
        extra_context: dict[str, Any] | None = None,
    ) -> None:
        """Log an exception with full context for replay."""
        if not self._enabled:
            return

        entry: dict[str, Any] = {
            "type": "exception",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "traceback": traceback.format_exc(),
        }

        if tx_context is not None:
            entry["tx_context"] = self._serialize_tx_context(tx_context)

        if event is not None:
            entry["event"] = self._serialize_event(event)

        if extra_context is not None:
            entry["extra_context"] = extra_context

        self._write_entry(entry)

    @staticmethod
    def _serialize_tx_context(context: TransactionContext) -> dict[str, Any]:
        """Serialize TransactionContext to a JSON-serializable dict."""
        event_topics: list[str] = []
        for event in context.events:
            topics = event.get("topics", [])
            if topics:
                first_topic = topics[0]
                event_topics.append(first_topic.to_0x_hex())

        user_addresses: set[str] = set()
        for event in context.events:
            topics = event.get("topics", [])
            if not topics:
                continue

            topic = topics[0]

            if topic == AaveV3ScaledTokenEvent.MINT.value:
                assert len(topics) == 3
                (user_addr,) = eth_abi.abi.decode(types=["address"], data=event["topics"][2])
                assert user_addr == "0x" + topics[2].hex()[-40:]
                user_addresses.add(user_addr)
            elif topic == AaveV3ScaledTokenEvent.BURN.value:
                assert len(topics) == 3
                (user_addr,) = eth_abi.abi.decode(types=["address"], data=event["topics"][1])
                assert user_addr == "0x" + topics[1].hex()[-40:]
                user_addresses.add(user_addr)
            elif topic == AaveV3ScaledTokenEvent.BALANCE_TRANSFER.value:
                assert len(topics) == 3
                (from_addr,) = eth_abi.abi.decode(types=["address"], data=event["topics"][1])
                (to_addr,) = eth_abi.abi.decode(types=["address"], data=event["topics"][2])
                assert from_addr == "0x" + topics[1].hex()[-40:]
                assert to_addr == "0x" + topics[2].hex()[-40:]
                user_addresses.add(from_addr)
                user_addresses.add(to_addr)
            elif topic == AaveV3PoolEvent.DEFICIT_CREATED.value:
                assert len(topics) == 3
                (user_addr,) = eth_abi.abi.decode(types=["address"], data=event["topics"][1])
                assert user_addr == "0x" + topics[1].hex()[-40:]
                user_addresses.add(user_addr)
            elif topic == AaveV3PoolEvent.BORROW.value:
                assert len(topics) == 4
                (user_addr,) = eth_abi.abi.decode(types=["address"], data=event["topics"][2])
                assert user_addr == "0x" + topics[2].hex()[-40:]
                user_addresses.add(user_addr)
            elif topic == AaveV3PoolEvent.REPAY.value:
                assert len(topics) == 4
                (user_addr,) = eth_abi.abi.decode(types=["address"], data=event["topics"][2])
                assert user_addr == "0x" + topics[2].hex()[-40:]
                user_addresses.add(user_addr)
            elif topic == AaveV3PoolEvent.SUPPLY.value:
                assert len(topics) == 4
                (user_addr,) = eth_abi.abi.decode(types=["address"], data=event["topics"][2])
                assert user_addr == "0x" + topics[2].hex()[-40:]
                user_addresses.add(user_addr)
            elif topic == AaveV3PoolEvent.WITHDRAW.value:
                assert len(topics) == 4
                (user_addr,) = eth_abi.abi.decode(types=["address"], data=event["topics"][2])
                assert user_addr == "0x" + topics[2].hex()[-40:]
                user_addresses.add(user_addr)
            elif topic == AaveV3PoolEvent.LIQUIDATION_CALL.value:
                assert len(topics) == 4
                (user_addr,) = eth_abi.abi.decode(types=["address"], data=event["topics"][3])
                assert user_addr == "0x" + topics[3].hex()[-40:]
                user_addresses.add(user_addr)
            elif topic == AaveV3GhoDebtTokenEvent.DISCOUNT_PERCENT_UPDATED.value:
                assert len(topics) == 2
                (user_addr,) = eth_abi.abi.decode(types=["address"], data=event["topics"][1])
                assert user_addr == "0x" + topics[1].hex()[-40:]
                user_addresses.add(user_addr)
            elif topic == AaveV3PoolEvent.USER_E_MODE_SET.value:
                assert len(topics) == 2
                (user_addr,) = eth_abi.abi.decode(types=["address"], data=event["topics"][1])
                assert user_addr == "0x" + topics[1].hex()[-40:]
                user_addresses.add(user_addr)
            elif topic in {
                AaveV3PoolConfigEvent.UPGRADED.value,
                AaveV3PoolEvent.RESERVE_DATA_UPDATED.value,
                ERC20Event.TRANSFER.value,
            }:
                pass
            else:
                msg = f"UNKNOWN EVENT: {topic.to_0x_hex()}"
                raise ValueError(msg)

        return {
            "tx_hash": context.tx_hash.to_0x_hex()
            if isinstance(context.tx_hash, HexBytes)
            else str(context.tx_hash),
            "block_number": context.block_number,
            "event_count": len(context.events),
            "event_topics": event_topics,
            "user_discounts_count": len(context.user_discounts),
            "discount_updates_count": len(context.discount_updates_by_log_index),
            "user_addresses": sorted(user_addresses),
        }

    @staticmethod
    def _serialize_event(event: LogReceipt) -> dict[str, Any]:
        """Serialize a LogReceipt event to JSON-serializable dict."""
        if event is None:
            return {}

        return {
            "address": event.get("address"),
            "blockNumber": event.get("blockNumber"),
            "blockHash": event.get("blockHash").to_0x_hex()
            if isinstance(event.get("blockHash"), HexBytes)
            else event.get("blockHash"),
            "transactionHash": event.get("transactionHash").to_0x_hex()
            if isinstance(event.get("transactionHash"), HexBytes)
            else event.get("transactionHash"),
            "logIndex": event.get("logIndex"),
            "topics": [t.to_0x_hex() for t in event.get("topics", [])],
            "data": event["data"].to_0x_hex(),
        }

    def log_block_boundary(
        self,
        *,
        block_number: int,
        event_count: int,
        user_count: int,
        user_addresses: list[str] | None = None,
    ) -> None:
        """Log block boundary processing."""
        if not self._enabled:
            return

        entry: dict[str, Any] = {
            "type": "block_boundary",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "block_number": block_number,
            "event_count": event_count,
            "user_count": user_count,
        }

        if user_addresses is not None:
            entry["user_addresses"] = sorted(user_addresses)

        self._write_entry(entry)

    def log_user_creation(
        self,
        *,
        user_address: str,
        block_number: int,
        tx_hash: HexBytes | str,
        gho_discount: int | None = None,
        e_mode: int | None = None,
    ) -> None:
        """Log when a new user is created."""
        if not self._enabled:
            return

        entry: dict[str, Any] = {
            "type": "user_creation",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "user_address": user_address,
            "block_number": block_number,
            "tx_hash": tx_hash.to_0x_hex() if isinstance(tx_hash, HexBytes) else tx_hash,
        }

        if gho_discount is not None:
            entry["gho_discount"] = gho_discount
        if e_mode is not None:
            entry["e_mode"] = e_mode

        self._write_entry(entry)

    def log_position_update(
        self,
        *,
        user_address: str,
        position_type: str,
        token_address: str,
        block_number: int,
        tx_hash: HexBytes | str,
        operation: str,
        balance_before: int,
        balance_after: int,
        balance_delta: int,
        index: int | None = None,
    ) -> None:
        """Log a position balance update."""
        if not self._enabled:
            return

        entry: dict[str, Any] = {
            "type": "position_update",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "user_address": user_address,
            "position_type": position_type,
            "token_address": token_address,
            "block_number": block_number,
            "tx_hash": tx_hash.to_0x_hex() if isinstance(tx_hash, HexBytes) else tx_hash,
            "operation": operation,
            "balance_before": balance_before,
            "balance_after": balance_after,
            "balance_delta": balance_delta,
        }

        if index is not None:
            entry["index"] = index

        self._write_entry(entry)

    def log_verification_start(
        self,
        *,
        block_number: int,
        user_addresses: list[str],
        position_type: str,
    ) -> None:
        """Log the start of position verification."""
        if not self._enabled:
            return

        entry = {
            "type": "verification_start",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "block_number": block_number,
            "user_addresses": sorted(user_addresses),
            "user_count": len(user_addresses),
            "position_type": position_type,
        }

        self._write_entry(entry)

    def log_liquidation_call(
        self,
        *,
        user_address: str,
        liquidator: str,
        collateral_asset: str,
        debt_asset: str,
        debt_to_cover: int,
        liquidated_collateral: int,
        block_number: int,
        tx_hash: HexBytes | str,
        is_gho: bool = False,
    ) -> None:
        """Log a LIQUIDATION_CALL event."""
        if not self._enabled:
            return

        entry: dict[str, Any] = {
            "type": "liquidation_call",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "user_address": user_address,
            "liquidator": liquidator,
            "collateral_asset": collateral_asset,
            "debt_asset": debt_asset,
            "debt_to_cover": debt_to_cover,
            "liquidated_collateral": liquidated_collateral,
            "block_number": block_number,
            "tx_hash": tx_hash.to_0x_hex() if isinstance(tx_hash, HexBytes) else tx_hash,
            "is_gho": is_gho,
        }

        self._write_entry(entry)

    def log_liquidation_operation_start(
        self,
        *,
        operation_id: int,
        user_address: str,
        operation_type: str,
        collateral_asset: str,
        debt_asset: str,
        debt_to_cover: int,
        liquidated_collateral: int,
        scaled_events: Sequence[AaveV3ScaledTokenEvent],
        block_number: int,
        tx_hash: HexBytes | str,
    ) -> None:
        """Log the start of liquidation operation processing."""
        if not self._enabled:
            return

        entry: dict[str, Any] = {
            "type": "liquidation_operation_start",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "operation_id": operation_id,
            "user_address": user_address,
            "operation_type": operation_type,
            "collateral_asset": collateral_asset,
            "debt_asset": debt_asset,
            "debt_to_cover": debt_to_cover,
            "liquidated_collateral": liquidated_collateral,
            "scaled_events": [event.name for event in scaled_events],
            "block_number": block_number,
            "tx_hash": tx_hash.to_0x_hex() if isinstance(tx_hash, HexBytes) else tx_hash,
        }

        self._write_entry(entry)

    def log_liquidation_match(
        self,
        *,
        operation_id: int,
        user_address: str,
        scaled_event_type: str,
        token_address: str,
        matched_amount: int,
        extraction_data: dict[str, Any],
        block_number: int,
        tx_hash: HexBytes | str,
    ) -> None:
        """Log a liquidation event match."""
        if not self._enabled:
            return

        entry: dict[str, Any] = {
            "type": "liquidation_match",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "operation_id": operation_id,
            "user_address": user_address,
            "scaled_event_type": scaled_event_type,
            "token_address": token_address,
            "matched_amount": matched_amount,
            "extraction_data": extraction_data,
            "block_number": block_number,
            "tx_hash": tx_hash.to_0x_hex() if isinstance(tx_hash, HexBytes) else tx_hash,
        }

        self._write_entry(entry)

    def log_liquidation_verification(
        self,
        *,
        operation_id: int,
        user_address: str,
        debt_asset: str,
        collateral_asset: str,
        expected_debt_burn: int,
        actual_debt_burn: int | None,
        expected_collateral_liquidation: int,
        actual_collateral_burn: int | None,
        collateral_transfers: list[dict[str, Any]],
        verified: bool,
        block_number: int,
        tx_hash: HexBytes | str,
    ) -> None:
        """Log liquidation verification results."""
        if not self._enabled:
            return

        entry: dict[str, Any] = {
            "type": "liquidation_verification",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "operation_id": operation_id,
            "user_address": user_address,
            "debt_asset": debt_asset,
            "collateral_asset": collateral_asset,
            "expected_debt_burn": expected_debt_burn,
            "actual_debt_burn": actual_debt_burn,
            "expected_collateral_liquidation": expected_collateral_liquidation,
            "actual_collateral_burn": actual_collateral_burn,
            "collateral_transfers": collateral_transfers,
            "verified": verified,
            "block_number": block_number,
            "tx_hash": tx_hash.to_0x_hex() if isinstance(tx_hash, HexBytes) else tx_hash,
        }

        self._write_entry(entry)

    def close(self) -> None:
        """Close the debug log file and write session end marker."""
        if not self._enabled or self._file_handle is None:
            return

        self._write_entry(
            {
                "type": "session_end",
                "timestamp": datetime.now(tz=UTC).isoformat(),
            }
        )

        self._file_handle.close()
        self._file_handle = None
        self._enabled = False


aave_debug_logger = AaveDebugLogger()
