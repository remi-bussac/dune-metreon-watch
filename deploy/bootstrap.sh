#!/bin/bash
# Runs ON the Oracle VM, once, to prepare it. Safe to re-run.
#
# Installs Python, the project dependencies and a headless Chromium, then
# registers a systemd timer that runs the monitor on an interval.
#
# Deliberately not clever: every step prints what it is doing, so when this
# is read cold in November it is obvious where it got to.

set -euo pipefail

APP_DIR="$HOME/dune-metreon-watch"
ENV_FILE="$HOME/.dune-metreon-watch.env"

echo "==> 1/6  system packages"
sudo apt-get update -qq
# python3-venv for the virtualenv; the rest are Chromium's shared-library
# dependencies. On ARM64 Ubuntu, Playwright's --with-deps covers most of
# these, but installing them explicitly makes failures readable.
sudo apt-get install -y -qq python3-venv python3-pip rsync ca-certificates

echo "==> 2/6  virtualenv"
cd "$APP_DIR"
python3 -m venv .venv
./.venv/bin/pip install --quiet --upgrade pip
./.venv/bin/pip install --quiet -r scripts/requirements.txt

echo "==> 3/6  headless Chromium (this is the slow step, a few minutes)"
# --with-deps pulls the OS libraries Chromium needs. On arm64 Playwright
# ships its own Chromium build, so this is the same path as on x86.
sudo ./.venv/bin/playwright install-deps chromium
./.venv/bin/playwright install chromium

echo "==> 4/6  checking credentials file"
if [[ ! -f "$ENV_FILE" ]]; then
  # NOTE the format: bare KEY=value, no "export". systemd's EnvironmentFile
  # parses KEY=value and does NOT understand shell syntax -- an "export"
  # prefix silently becomes part of the variable name and the monitor then
  # fails to authenticate. Plain KEY=value also still works with `source`.
  # Addresses are placeholders, not real ones. This file is committed, so a
  # real address here is published to anyone who can read the repo and gets
  # harvested by spam crawlers -- the same reason the Reddit user-agent
  # points at the repo URL rather than a mailbox.
  cat > "$ENV_FILE" <<'EOF'
# Credentials for dune-metreon-watch.
# Format is deliberately bare KEY=value (no "export") so systemd can read it.
GMAIL_ADDRESS=YOUR_SENDER_ACCOUNT@gmail.com
GMAIL_APP_PASSWORD=PUT_YOUR_16_CHAR_APP_PASSWORD_HERE
ALERT_EMAIL_TO=WHERE_ALERTS_SHOULD_LAND@example.com
EOF
  chmod 600 "$ENV_FILE"
  echo "    created $ENV_FILE  <-- YOU MUST EDIT THIS AND ADD THE PASSWORD"
else
  echo "    $ENV_FILE already exists, leaving it alone"
fi

echo "==> 5/6  systemd units"
sudo cp "$APP_DIR/deploy/dune-watch.service" /etc/systemd/system/
sudo cp "$APP_DIR/deploy/dune-watch.timer"   /etc/systemd/system/
sudo sed -i "s|__USER__|$USER|g; s|__HOME__|$HOME|g" \
     /etc/systemd/system/dune-watch.service
sudo systemctl daemon-reload
sudo systemctl enable --now dune-watch.timer

echo "==> 6/6  smoke test (one full pass -- takes 1-2 minutes, please wait)"
if grep -q PUT_YOUR_16_CHAR "$ENV_FILE"; then
  echo "    SKIPPED: password not filled in yet. Edit $ENV_FILE then run:"
  echo "        sudo systemctl start dune-watch.service"
else
  set +e
  sudo systemctl start dune-watch.service   # oneshot: this blocks until the pass finishes
  set -e
  echo "    --- last 15 log lines ---"
  journalctl -u dune-watch.service -n 15 --no-pager
fi

echo
echo "DONE."
echo "  next run   : systemctl list-timers dune-watch.timer"
echo "  live logs  : journalctl -u dune-watch.service -f"
echo "  last run   : journalctl -u dune-watch.service -n 40 --no-pager"
