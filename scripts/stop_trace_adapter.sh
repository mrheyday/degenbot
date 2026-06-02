#!/usr/bin/env bash
# Stop the degenbot IPC adapter daemon started by start_trace_adapter.sh.
# Graceful TERM via the pid file, falls back to matching the module string,
# then removes the Unix socket. Idempotent: safe to run when nothing is up.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOCKET_PATH="${DEGENBOT_IPC_SOCKET_PATH:-/tmp/degenbot.sock}"
PID_FILE="$REPO_ROOT/debug/adapter.pid"
PATTERN="degenbot.connection.ipc"

stopped=0

# 1) Graceful stop via recorded pid.
if [[ -f "$PID_FILE" ]]; then
  pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    echo "stopping pid $pid (TERM)"
    kill -TERM "$pid" 2>/dev/null || true
    for _ in $(seq 1 20); do
      kill -0 "$pid" 2>/dev/null || break
      sleep 0.25
    done
    if kill -0 "$pid" 2>/dev/null; then
      echo "pid $pid still alive; sending KILL"
      kill -KILL "$pid" 2>/dev/null || true
    fi
    stopped=1
  fi
  rm -f "$PID_FILE"
fi

# 2) Sweep any stray/orphaned instances (e.g. earlier foreground runs).
if pgrep -f "$PATTERN" >/dev/null 2>&1; then
  echo "stopping stray instances matching '$PATTERN'"
  pkill -TERM -f "$PATTERN" 2>/dev/null || true
  sleep 1
  pkill -KILL -f "$PATTERN" 2>/dev/null || true
  stopped=1
fi

# 3) Clear the socket (only if it is actually a socket).
if [[ -S "$SOCKET_PATH" ]]; then
  rm -f "$SOCKET_PATH"
  echo "removed socket $SOCKET_PATH"
fi

if [[ "$stopped" -eq 1 ]]; then
  echo "adapter stopped."
else
  echo "no running adapter found."
fi
