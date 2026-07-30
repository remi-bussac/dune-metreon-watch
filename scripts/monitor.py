"""Orchestrator: for every active target in config/targets.json, run every
source check, diff against state/state.json, alert on anything new or
broken, and write updated state back to disk. Invoked once per cron tick by
.github/workflows/monitor.yml — one run, no internal retry loops (that's
what "honest request rate" means here: the cadence itself is the rate
limit, not a busy-loop inside a single run).

Deliberately simple control flow — this needs to be readable cold in
November by someone who wrote it in July.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "sources"))

import alert  # noqa: E402
from normalize import Showtime, SourceResult, diff_showtimes, state_key  # noqa: E402
from sources import amc_showtimes, amc_film_page, imax_page, fandango, reddit_rss  # noqa: E402

TARGETS_PATH = REPO_ROOT / "config" / "targets.json"
STATE_PATH = REPO_ROOT / "state" / "state.json"

PARSE_ERROR_THRESHOLD = 3  # consecutive runs before the "monitor broken" alert fires
HEARTBEAT_INTERVAL = timedelta(days=7)

SOURCE_MODULES = [amc_showtimes, amc_film_page, imax_page, fandango, reddit_rss]


def load_targets() -> list[dict]:
    targets = json.loads(TARGETS_PATH.read_text())
    return [t for t in targets if t.get("active", True)]


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"sources": {}, "last_heartbeat_sent": None}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def default_source_entry() -> dict:
    return {
        "known_showtimes": [],
        "consecutive_parse_errors": 0,
        "broken_alert_sent": False,
        "blocked_alert_sent": False,
        "last_status": None,
        "last_checked_at": None,
        "last_error": None,
    }


def process_result(target: dict, result: SourceResult, state: dict) -> None:
    key = state_key(target["id"], result.source)
    entry = state["sources"].setdefault(key, default_source_entry())

    entry["last_status"] = result.status
    entry["last_checked_at"] = result.checked_at
    entry["last_error"] = result.error

    if result.status == "ok":
        known = [Showtime.from_dict(d) for d in entry["known_showtimes"]]
        new = diff_showtimes(known, result.showtimes)
        if new:
            alert_result = SourceResult(
                source=result.source,
                target_id=target["id"],
                status="ok",
                kind=result.kind,
                showtimes=new,
                checked_at=result.checked_at,
            )
            if result.kind == "showtime":
                alert.send_ticket_alert(target, alert_result)
            else:
                alert.send_mention_alert(target, alert_result)
        entry["known_showtimes"] = [s.to_dict() for s in result.showtimes]
        entry["consecutive_parse_errors"] = 0
        entry["broken_alert_sent"] = False
        entry["blocked_alert_sent"] = False

    elif result.status == "parse_error":
        entry["consecutive_parse_errors"] += 1
        if entry["consecutive_parse_errors"] >= PARSE_ERROR_THRESHOLD and not entry["broken_alert_sent"]:
            alert.send_broken_alert(result.source, target["id"], entry["consecutive_parse_errors"], result.error)
            entry["broken_alert_sent"] = True

    elif result.status == "blocked":
        if not entry["blocked_alert_sent"]:
            alert.send_blocked_alert(result.source, target["id"], result.error)
            entry["blocked_alert_sent"] = True

    elif result.status == "no_data":
        pass  # transient network hiccup; visible in state/heartbeat, not alert-worthy on its own


def build_heartbeat_summary(state: dict) -> str:
    lines = []
    for key in sorted(state["sources"]):
        entry = state["sources"][key]
        lines.append(f"  {key}: {entry['last_status']} (last checked {entry['last_checked_at']})")
    return "\n".join(lines) if lines else "  (no sources checked yet)"


def maybe_send_heartbeat(state: dict) -> None:
    last = state.get("last_heartbeat_sent")
    now = datetime.now(timezone.utc)
    if last is not None:
        last_dt = datetime.fromisoformat(last)
        if now - last_dt < HEARTBEAT_INTERVAL:
            return
    alert.send_heartbeat(build_heartbeat_summary(state))
    state["last_heartbeat_sent"] = now.isoformat()


def main() -> None:
    targets = load_targets()
    state = load_state()

    for target in targets:
        for module in SOURCE_MODULES:
            try:
                result = module.check(target)
            except Exception as e:
                result = SourceResult(
                    source=module.SOURCE_NAME,
                    target_id=target["id"],
                    status="parse_error",
                    error=f"unhandled exception: {e}",
                )
            print(f"[{target['id']}] {result.source}: {result.status} ({len(result.showtimes)} showtimes)")
            process_result(target, result, state)

    maybe_send_heartbeat(state)
    save_state(state)


if __name__ == "__main__":
    main()
