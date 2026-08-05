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
from datetime import date, datetime, timedelta, timezone
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

SOURCE_MODULES = [fandango, reddit_rss]

# Retained in the tree but NOT polled. amc_showtimes, amc_film_page and
# imax_page have never once succeeded from a GitHub runner -- every single
# CI attempt returned a Cloudflare 403 or a Queue-it waiting room. Polling
# them bought no redundancy, only refused requests: 6 per run, which at the
# planned December cadence would have been ~1,700 rejected requests a day
# against sites that had already said no. Continuing to knock is both rude
# and, from the outside, indistinguishable from abusive scraping.
#
# To re-enable one (e.g. if AMC ever stops blocking datacenter IPs), move it
# back into SOURCE_MODULES above. Nothing else needs to change.
DISABLED_SOURCES = [amc_showtimes, amc_film_page, imax_page]


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


MENTION_RETENTION = timedelta(days=30)


def merge_known(known: list[dict], current: list[Showtime], kind: str) -> list[dict]:
    """Union of what we already knew with what this run saw, pruned of
    entries that can no longer matter.

    Union, emphatically NOT replacement. Replacing meant a single flaky
    scrape shrank the known set, and the next healthy run then re-reported
    those same showtimes as brand new. That produced exactly the observed
    bug: two "new showtimes" emails for The Odyssey with nothing actually
    released in between, the second one "completing" the first. Fandango's
    scrape was measured returning 103 showtimes on some passes and 110 on
    others, so the flap was routine, not exceptional.

    Because a union never shrinks, a partial scrape is now harmless: it
    simply contributes nothing that pass.

    Pruning keeps it bounded. Showtimes in the past are dropped outright --
    they cannot be bought. Reddit mentions are kept for 30 days, comfortably
    longer than the ~3 days of posts an RSS feed actually carries, so a
    pruned post can never scroll back into the feed and re-alert."""
    today = date.today()
    merged = {tuple(sorted(d.items())): d for d in known}
    for showtime in current:
        d = showtime.to_dict()
        merged[tuple(sorted(d.items()))] = d

    if kind == "showtime":
        cutoff = today.isoformat()
    else:
        cutoff = (today - MENTION_RETENTION).isoformat()

    return sorted(
        (d for d in merged.values() if d.get("date", "") >= cutoff or d.get("date") == "unknown"),
        key=lambda d: (d.get("date", ""), d.get("time", "")),
    )


def process_result(target: dict, result: SourceResult, state: dict) -> bool:
    """Update state for one source result, sending alerts as needed.

    Returns False if an alert could not be delivered. A send failure is
    never allowed to abort the run: a transient SMTP error used to raise
    all the way out of main(), so save_state() never ran and the entire
    run's progress was lost (this actually happened — two runs died on
    SMTPAuthenticationError before the secrets were fixed). Instead the
    failure is recorded, the newly-found showtimes are deliberately NOT
    marked as known so the next run retries them, and main() exits
    non-zero at the very end so GitHub's own workflow-failure notification
    surfaces it — the one alerting channel that still works when email
    is the thing that's broken."""
    key = state_key(target["id"], result.source)
    entry = state["sources"].setdefault(key, default_source_entry())

    entry["last_status"] = result.status
    entry["last_checked_at"] = result.checked_at
    entry["last_error"] = result.error
    delivered = True

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
            try:
                if result.kind == "showtime":
                    alert.send_ticket_alert(target, alert_result)
                else:
                    alert.send_mention_alert(target, alert_result)
            except Exception as e:
                print(f"  !! alert delivery FAILED for {key}: {e}")
                entry["last_error"] = f"alert delivery failed: {e}"
                # Leave known_showtimes untouched so the next run re-detects
                # these and tries again. Better a duplicate email later than
                # a drop that was found and then silently forgotten.
                return False

        entry["known_showtimes"] = merge_known(
            entry["known_showtimes"], result.showtimes, result.kind
        )
        entry["consecutive_parse_errors"] = 0
        entry["broken_alert_sent"] = False
        entry["blocked_alert_sent"] = False

    elif result.status == "parse_error":
        entry["consecutive_parse_errors"] += 1
        if entry["consecutive_parse_errors"] >= PARSE_ERROR_THRESHOLD and not entry["broken_alert_sent"]:
            try:
                alert.send_broken_alert(
                    result.source, target["id"], entry["consecutive_parse_errors"], result.error
                )
                entry["broken_alert_sent"] = True
            except Exception as e:
                print(f"  !! broken-alert delivery FAILED for {key}: {e}")
                delivered = False

    elif result.status == "blocked":
        if not entry["blocked_alert_sent"]:
            try:
                alert.send_blocked_alert(result.source, target["id"], result.error)
                entry["blocked_alert_sent"] = True
            except Exception as e:
                print(f"  !! blocked-alert delivery FAILED for {key}: {e}")
                delivered = False

    elif result.status == "no_data":
        pass  # transient network hiccup; visible in state/heartbeat, not alert-worthy on its own

    return delivered


def build_heartbeat_summary(state: dict) -> str:
    lines = []
    for key in sorted(state["sources"]):
        entry = state["sources"][key]
        lines.append(f"  {key}: {entry['last_status']} (last checked {entry['last_checked_at']})")
    return "\n".join(lines) if lines else "  (no sources checked yet)"


def maybe_send_heartbeat(state: dict) -> bool:
    """Send the weekly proof-of-life digest if due. Returns False only if a
    due heartbeat failed to send."""
    last = state.get("last_heartbeat_sent")
    now = datetime.now(timezone.utc)
    if last is not None:
        last_dt = datetime.fromisoformat(last)
        if now - last_dt < HEARTBEAT_INTERVAL:
            return True
    try:
        alert.send_heartbeat(build_heartbeat_summary(state))
    except Exception as e:
        print(f"  !! heartbeat delivery FAILED: {e}")
        return False
    state["last_heartbeat_sent"] = now.isoformat()
    return True


def meaningful_fingerprint(state: dict) -> str:
    """Everything in state EXCEPT the per-run timestamps.

    last_checked_at changes on literally every run, so committing whenever
    state.json differs meant a commit every single run — ~288/day at the
    December cadence, which buries the handful of commits that actually
    represent something happening. Persisting only on a meaningful change
    keeps the git history usable as the audit trail it was meant to be."""
    trimmed = {
        key: {k: v for k, v in entry.items() if k != "last_checked_at"}
        for key, entry in state["sources"].items()
    }
    return json.dumps(
        {"sources": trimmed, "last_heartbeat_sent": state.get("last_heartbeat_sent")},
        sort_keys=True,
    )


def main() -> None:
    targets = load_targets()
    state = load_state()
    before = meaningful_fingerprint(state)
    all_delivered = True

    for target in targets:
        for module in SOURCE_MODULES:
            # Dates we already have showtimes for. fandango uses this to
            # decide which dates are worth spending a click on: an unseen
            # date always gets scanned, a known one only if it is near-term.
            prior = state["sources"].get(state_key(target["id"], module.SOURCE_NAME), {})
            known_dates = {s.get("date") for s in prior.get("known_showtimes", [])}
            try:
                result = module.check(target, known_dates=known_dates)
            except Exception as e:
                result = SourceResult(
                    source=module.SOURCE_NAME,
                    target_id=target["id"],
                    status="parse_error",
                    error=f"unhandled exception: {e}",
                )
            print(f"[{target['id']}] {result.source}: {result.status} ({len(result.showtimes)} showtimes)")
            if not process_result(target, result, state):
                all_delivered = False

    if not maybe_send_heartbeat(state):
        all_delivered = False

    if meaningful_fingerprint(state) != before:
        save_state(state)
        print("state changed — written to disk for commit")
    else:
        print("no meaningful state change — leaving state.json untouched")

    if not all_delivered:
        # State is already saved at this point, so nothing is lost. Exit
        # non-zero purely so the run shows up as failed and GitHub emails
        # about it -- when email delivery is what's broken, the workflow's
        # own failure notification is the only channel left.
        print("one or more alerts could not be delivered — failing the run to surface it")
        sys.exit(1)


if __name__ == "__main__":
    main()
