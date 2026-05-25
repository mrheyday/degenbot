"""Compatibility exports for EIP-712 solver signing."""

from __future__ import annotations

import sys
import types
from importlib import import_module
from importlib.util import find_spec

from degenbot.cow import signing as _impl
from degenbot.cow.signing import Eip712SigningError, sign_solution

if "driver" in sys.modules:
    _driver = sys.modules["driver"]
elif find_spec("driver") is not None:
    _driver = import_module("driver")
else:
    _driver = sys.modules.setdefault("driver", types.ModuleType("driver"))
_driver_signing = sys.modules.setdefault("driver.signing", types.ModuleType("driver.signing"))
_driver.signing = _driver_signing
_driver_signing.eip712 = _impl
sys.modules.setdefault("driver.signing.eip712", _impl)

__all__ = ["Eip712SigningError", "sign_solution"]
