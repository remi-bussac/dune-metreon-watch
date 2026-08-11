#!/bin/bash
# Runs on YOUR LAPTOP. Copies the project to the Oracle VM and sets it up.
# Safe to re-run -- use it for code updates too, not just the first install.
#
#   ./deploy/deploy.sh  <VM_PUBLIC_IP>
#
# Code is pushed with rsync rather than cloned from GitHub on purpose: the
# GitHub account is under review and the repo is not reliably reachable to
# logged-out visitors, so the VM must not depend on it.

set -euo pipefail

IP="${1:-}"
USER_NAME="${DUNE_VM_USER:-ubuntu}"      # Oracle's Ubuntu images default to 'ubuntu'
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -z "$IP" ]]; then
  echo "usage: ./deploy/deploy.sh <VM_PUBLIC_IP>"
  echo "   e.g. ./deploy/deploy.sh 141.148.x.x"
  exit 1
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
