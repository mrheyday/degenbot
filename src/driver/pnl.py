"""Legacy `driver.pnl` module alias."""

from __future__ import annotations

import sys

from degenbot import pnl as _pnl

sys.modules[__name__] = _pnl
