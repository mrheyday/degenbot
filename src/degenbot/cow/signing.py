"""EIP-712 typed-data signing for CoW solver solutions.

The solution builder owns CoW-specific struct construction. This module is
the narrow signing boundary: it accepts a fully-formed EIP-712 typed-data
payload, validates the shape, unwraps the solver key only inside the signing
call, and returns the raw 65-byte secp256k1 signature.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Final, cast

from eth_account import Account

if TYPE_CHECKING:
    from pydantic import SecretStr


class Eip712SigningError(ValueError):
    """Raised when a solution cannot be safely signed as EIP-712 typed data."""


EIP712_SIGNATURE_LENGTH: Final[int] = 65


def sign_solution(solution: Any, private_key: SecretStr) -> bytes:
    """Sign a CoW solution with EIP-712 typed data.

    Args:
        solution: A full EIP-712 typed-data payload, or an object/dict that
            exposes one under `typedData`, `typed_data`, `eip712`, or
            `to_eip712()`.
        private_key: SecretStr-wrapped solver EOA private key. The wrapper
            is unwrapped only inside this function and never logged.

    Returns:
        Raw 65-byte secp256k1 signature (r || s || v).

    Notes:
        - We use `SecretStr` so the key never leaks via repr / structlog.
        - The typed-data domain must be constructed by the caller from the
          live chain id and deployed GPv2Settlement address.
    """
    typed_data = _extract_typed_data(solution)
    key = private_key.get_secret_value()
    if not key:
        msg = "empty solver private key"
        raise Eip712SigningError(msg)

    # eth_account's `Account` exposes sign_typed_data via @combomethod; pylint
    # mis-reads it as an unbound method that still needs an explicit `private_key`.
    signed = Account.sign_typed_data(key, full_message=typed_data)  # pylint: disable=no-value-for-parameter
    signature = getattr(signed, "signature", None)
    if not isinstance(signature, bytes | bytearray) or len(signature) != EIP712_SIGNATURE_LENGTH:
        msg = "eth-account returned an invalid signature shape"
        raise Eip712SigningError(msg)
    return bytes(signature)


def _extract_typed_data(solution: Any) -> dict[str, Any]:
    """Normalize supported solution containers into a full EIP-712 message."""
    candidate = solution
    if hasattr(candidate, "to_eip712"):
        candidate = candidate.to_eip712()
    elif hasattr(candidate, "model_dump"):
        candidate = candidate.model_dump(mode="json", by_alias=True, exclude_none=True)

    if isinstance(candidate, Mapping):
        for key in ("typedData", "typed_data", "eip712", "eip712TypedData"):
            nested = candidate.get(key)
            if isinstance(nested, Mapping):
                candidate = nested
                break

    if not isinstance(candidate, Mapping):
        msg = "solution does not expose an EIP-712 typed-data mapping"
        raise Eip712SigningError(msg)

    typed_data = _plain_dict(candidate)
    _validate_typed_data(typed_data)
    return typed_data


def _plain_dict(value: Mapping[str, Any]) -> dict[str, Any]:
    """Recursively copy mappings so downstream signing cannot mutate caller state."""
    out: dict[str, Any] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            msg = "EIP-712 typed-data keys must be strings"
            raise Eip712SigningError(msg)
        out[key] = _plain_value(item)
    return out


def _plain_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _plain_dict(cast("Mapping[str, Any]", value))
    if isinstance(value, list | tuple):
        return [_plain_value(item) for item in value]
    return value


def _validate_typed_data(typed_data: Mapping[str, Any]) -> None:
    required = ("types", "primaryType", "domain", "message")
    missing = [key for key in required if key not in typed_data]
    if missing:
        missing_fields = ", ".join(missing)
        msg = f"EIP-712 typed data missing required field(s): {missing_fields}"
        raise Eip712SigningError(
            msg,
        )

    types = typed_data["types"]
    primary_type = typed_data["primaryType"]
    domain = typed_data["domain"]
    message = typed_data["message"]

    if not isinstance(types, Mapping):
        msg = "EIP-712 `types` must be a mapping"
        raise Eip712SigningError(msg)
    if "EIP712Domain" not in types:
        msg = "EIP-712 `types` must include EIP712Domain"
        raise Eip712SigningError(msg)
    if not isinstance(primary_type, str) or not primary_type:
        msg = "EIP-712 `primaryType` must be a non-empty string"
        raise Eip712SigningError(msg)
    if primary_type not in types:
        msg = "EIP-712 `primaryType` has no matching type definition"
        raise Eip712SigningError(msg)
    if not isinstance(domain, Mapping):
        msg = "EIP-712 `domain` must be a mapping"
        raise Eip712SigningError(msg)
    if not isinstance(message, Mapping):
        msg = "EIP-712 `message` must be a mapping"
        raise Eip712SigningError(msg)
