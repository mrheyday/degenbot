#!/usr/bin/env bash
# Start the degenbot IPC adapter daemon with full debug tracing.
# Serves the TS coordinator over a Unix socket and streams JSON logs to a file.
# Run on the host that owns the socket (your Mac), from the repo root or anywhere.
#
# Detached by default: the terminal returns immediately and the daemon survives
# logout (nohup). Set FOREGROUND=1 to run attached (Ctrl-C to stop).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Configurable; defaults match adapters/config.py.
export DEGENBOT_DEBUG="${DEGENBOT_DEBUG:-1}"          # 1 = verbose per-call tracing
export LOG_LEVEL="${LOG_LEVEL:-debug}"               # structlog level
export DEGENBOT_IPC_SOCKET_PATH="${DEGENBOT_IPC_SOCKET_PATH:-/tmp/degenbot.sock}"
# Pin the adapter to THIS checkout. An exported var beats .env and is
# cwd-independent; the relative default resolves to a nonexistent
# vendor/vendor/degenbot (module REPO_ROOT = parents[4] = .../vendor).
export DEGENBOT_SOURCE_PATH="${DEGENBOT_SOURCE_PATH:-$REPO_ROOT}"
FOREGROUND="${FOREGROUND:-0}"                         # 1 = run attached in this shell

LOG_DIR="$REPO_ROOT/debug"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/adapter-$(date +%Y%m%d-%H%M%S).jsonl"
PID_FILE="$LOG_DIR/adapter.pid"

# Already-running guard: do not start a second instance (would fight for the socket).
if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE" 2>/dev/null)" 2>/dev/null; then
  echo "ERROR: adapter already running (pid $(cat "$PID_FILE")). Stop it first:" >&2
  echo "       kill \$(cat \"$PID_FILE\")" >&2
  exit 1
fi

# Stale-socket guard: refuse to clobber a non-socket path; remove a dead socket.
if [[ -e "$DEGENBOT_IPC_SOCKET_PATH" && ! -S "$DEGENBOT_IPC_SOCKET_PATH" ]]; then
  echo "ERROR: $DEGENBOT_IPC_SOCKET_PATH exists and is not a socket; refusing to start." >&2
  exit 1
fi
[[ -S "$DEGENBOT_IPC_SOCKET_PATH" ]] && rm -f "$DEGENBOT_IPC_SOCKET_PATH"

echo "socket : $DEGENBOT_IPC_SOCKET_PATH"
echo "debug  : $DEGENBOT_DEBUG  level: $LOG_LEVEL"
echo "source : ${DEGENBOT_SOURCE_PATH:-<from .env>}"
echo "log    : $LOG_FILE"
echo "tail   : tail -f \"$LOG_FILE\" | jq ."
echo "---"

# `uv run` rebuilds the maturin Rust extension on import if needed.
if [[ "$FOREGROUND" == "1" ]]; then
  # Attached: stream to terminal and log file; Ctrl-C stops the daemon.
  exec uv run python -m degenbot.connection.ipc 2>&1 | tee "$LOG_FILE"
else
  # Detached: survive terminal close, log to file, record pid for clean stop.
  nohup uv run python -m degenbot.connection.ipc >>"$LOG_FILE" 2>&1 &
  pid=$!
  echo "$pid" >"$PID_FILE"
  echo "started: pid $pid (detached) -> $PID_FILE"
  echo "stop   : kill \$(cat \"$PID_FILE\")   # or: pkill -f degenbot.connection.ipc"
fi
