"""Legacy `driver.execution.degenbot_ipc` module alias."""

from __future__ import annotations

import sys

from degenbot.connection import ipc as _ipc

sys.modules[__name__] = _ipc
