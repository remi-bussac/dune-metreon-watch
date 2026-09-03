#!/bin/bash
# Runs on YOUR LAPTOP. Copies the project to the Oracle VM and sets it up.
# Safe to re-run -- use it for code updates too, not just the first install.
#
#   ./deploy/deploy.sh  [VM_PUBLIC_IP]
#
# The address can be omitted once DUNE_VM_IP is set in
# ~/.dune-metreon-watch.env, which is where it belongs: this repo is public.
#
# Code is pushed with rsync rather than cloned from GitHub on purpose: the
# GitHub account is under review and the repo is not reliably reachable to
# logged-out visitors, so the VM must not depend on it.

set -euo pipefail

USER_NAME="${DUNE_VM_USER:-ubuntu}"      # Oracle's Ubuntu images default to 'ubuntu'
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${DUNE_ENV_FILE:-$HOME/.dune-metreon-watch.env}"

# The VM's address is laptop-local config and is deliberately not committed.
# This repo is public: the address on its own is not a secret, but published
# next to code that names the login user, the paths and the credentials file,
# it turns a generic port scan into a targeted one. Resolution order is
# argument, then DUNE_VM_IP from the environment, then DUNE_VM_IP out of
# ~/.dune-metreon-watch.env (the same out-of-repo file that holds the Gmail
# app password).
IP="${1:-${DUNE_VM_IP:-}}"
if [[ -z "$IP" && -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  IP="${DUNE_VM_IP:-}"
fi

if [[ -z "$IP" ]]; then
  echo "usage: ./deploy/deploy.sh [VM_PUBLIC_IP]"
  echo
  echo "No address given, and DUNE_VM_IP is not set in the environment or in"
  echo "$ENV_FILE. Either pass it once:"
  echo "    ./deploy/deploy.sh 203.0.113.10"
  echo "or set it for good, outside the repo:"
  echo "    echo 'export DUNE_VM_IP=203.0.113.10' >> $ENV_FILE"
  exit 1
fi

# Gate. Nothing reaches the VM unless the suite is green -- every false
# alert this project sent was shipped after a change that "looked fine when
# I ran it once". Skip only in a genuine emergency:  SKIP_TESTS=1 ./deploy.sh
if [[ "${SKIP_TESTS:-0}" != "1" ]]; then
  echo "==> running tests before deploying"
  if ! "$REPO_DIR/.venv/bin/python" -m pytest "$REPO_DIR/tests" -q; then
    echo
    echo "TESTS FAILED — refusing to deploy."
    echo "Fix them, or override deliberately with: SKIP_TESTS=1 $0 $IP"
    exit 1
  fi
  echo
fi

echo "==> pushing code to $USER_NAME@$IP"
# --delete keeps the VM identical to local, so a removed file here is removed
# there too. The excludes matter: .venv is x86 on the laptop and would break
# the ARM VM, and state.json must NOT be overwritten -- the VM's copy is the
# live one once it is running.
rsync -az --delete \
  --exclude '.venv/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude 'local-run.log' \
  --exclude 'state/state.json' \
  --exclude '.git/' \
  "$REPO_DIR/" "$USER_NAME@$IP:~/dune-metreon-watch/"

echo "==> ensuring a state file exists on the VM (without clobbering a live one)"
ssh "$USER_NAME@$IP" '
  mkdir -p ~/dune-metreon-watch/state
  [ -f ~/dune-metreon-watch/state/state.json ] || \
    echo "{\"sources\": {}, \"last_heartbeat_sent\": null}" > ~/dune-metreon-watch/state/state.json
'

echo "==> running bootstrap on the VM"
ssh -t "$USER_NAME@$IP" 'bash ~/dune-metreon-watch/deploy/bootstrap.sh'

echo
echo "==> done. Useful commands:"
echo "    ssh $USER_NAME@$IP 'systemctl list-timers dune-watch.timer'"
echo "    ssh $USER_NAME@$IP 'journalctl -u dune-watch.service -n 40 --no-pager'"
echo "    ssh $USER_NAME@$IP 'journalctl -u dune-watch.service -f'"
