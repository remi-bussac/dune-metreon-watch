#!/bin/bash
# Continuous loop runner, intended to be run inside tmux so it survives the
# terminal window closing. This is the stopgap while the GitHub Actions
# schedule is disabled.
#
# Why tmux and not a LaunchAgent: macOS TCC lets a LaunchAgent execute a
# binary inside ~/Documents but blocks it from reading files there, so
# monitor.py can never be loaded. A tmux session inherits your interactive
# shell's permissions, which do have access, so it just works.
#
# Interval defaults to 10 minutes. Override per-session:
#   DUNE_WATCH_INTERVAL=300 bash scripts/run_loop.sh
#
# On request volume: each pass loads one Fandango page per target and then
# clicks through that film's date carousel (up to MAX_DATES per target), so
# a pass is roughly 15-20 requests. At 600s that is ~2,500/day if the laptop
# stays open all day; at 300s it doubles. Ten minutes is a deliberate middle
# ground -- fast enough to be useful, slow enough to stay defensible against
# the "honest request rate" rule this project set for itself. Dropping to 60s
# for a few hours on a known drop day is fine; a short burst and sustained
# load are different things.

set -uo pipefail

# Derived from this script's own location, not hardcoded, so the same file
# works on the laptop and on the Oracle VM.
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INTERVAL="${DUNE_WATCH_INTERVAL:-600}"
LOG="$REPO/local-run.log"

cd "$REPO" || { echo "repo not found at $REPO"; exit 1; }

trap 'echo "[$(date "+%H:%M:%S")] loop stopped after ${COUNT:-0} passes"; exit 0' INT TERM

COUNT=0
echo "==================================================================="
echo " dune-metreon-watch loop"
echo " interval : ${INTERVAL}s"
echo " log      : $LOG"
echo " stop     : tmux kill-session -t dune"
echo "==================================================================="

while true; do
  COUNT=$((COUNT + 1))
  echo "[pass $COUNT]"
  bash "$REPO/scripts/run_local.sh" 2>&1 | tee -a "$LOG"
  sleep "$INTERVAL"
done
