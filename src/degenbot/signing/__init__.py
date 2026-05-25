"""Compatibility package for migrated signing helpers."""

from degenbot.signing.eip712 import Eip712SigningError, sign_solution

__all__ = ["Eip712SigningError", "sign_solution"]
