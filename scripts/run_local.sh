#!/bin/bash
# Local stopgap runner, driven by the macOS LaunchAgent
# (~/Library/LaunchAgents/com.remibussac.dune-metreon-watch.plist).
#
# Exists because the GitHub Actions schedule is disabled while the account
# review is open. This runs whenever the laptop is awake -- partial
# coverage, but far better than nothing.
#
# Credentials live OUTSIDE the repo, in ~/.dune-metreon-watch.env, so an
# app password can never be committed to a public repository by accident.

set -uo pipefail

# Derived from this script's own location, not hardcoded, so the same file
# works on the laptop and on the Oracle VM.
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$HOME/.dune-metreon-watch.env"
STAMP="$(date '+%Y-%m-%d %H:%M:%S %Z')"

cd "$REPO" || { echo "[$STAMP] repo not found at $REPO"; exit 0; }

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[$STAMP] SKIP: $ENV_FILE not found — create it to enable local runs"
  exit 0
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

if [[ "${GMAIL_APP_PASSWORD:-}" == "PUT_YOUR_16_CHAR_APP_PASSWORD_HERE" || -z "${GMAIL_APP_PASSWORD:-}" ]]; then
  echo "[$STAMP] SKIP: GMAIL_APP_PASSWORD not filled in yet in $ENV_FILE"
  exit 0
fi

export GMAIL_ADDRESS GMAIL_APP_PASSWORD ALERT_EMAIL_TO

echo "[$STAMP] --- run start ---"
"$REPO/.venv/bin/python" "$REPO/scripts/monitor.py"
STATUS=$?
echo "[$STAMP] --- run end (exit $STATUS) ---"

# Deliberately does NOT git commit. State accumulates on disk and gets
# committed once, by hand, rather than generating hundreds of local commits
# during the outage.
exit 0
