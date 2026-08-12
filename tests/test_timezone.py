"""The venue's calendar day, not the host's.

Every date in this system is a cinema-local Pacific date: Fandango's calendar
buttons, the showtimes, the pruning cutoff, the lead-time arithmetic. Reading
"today" from the host clock silently worked while the monitor ran on a laptop
in PDT, and broke the moment it moved to a UTC VM.

The failure, observed 2026-08-12: between 17:00 PDT and midnight PDT the VM's
date is already tomorrow. merge_known pruned "past" showtimes using that
date, dropping the *current* Pacific day; the next scrape re-found them,
they looked brand new, and an alert fired. Every run, for seven hours a
night. Three landed at 17:31, 17:46 and 18:02 PDT, all for Aug 11.

In December (PST, UTC-8) the broken window would be eight hours.
"""

import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "scripts" / "sources"))

import pytest  # noqa: E402

from normalize import Showtime, VENUE_TZ, venue_today, diff_showtimes  # noqa: E402
from monitor import alertable_showtimes, merge_known  # noqa: E402


def st(d, t="19:00"):
    return Showtime(date=d, time=t, format="IMAX 70mm",
                    venue="AMC Metreon 16", booking_url="u")


def test_venue_timezone_is_the_cinema_not_the_host():
    assert VENUE_TZ == ZoneInfo("America/Los_Angeles")


def test_venue_today_ignores_the_host_timezone(monkeypatch):
    """The whole point: same instant, different host TZ, same answer."""
    answers = set()
    for tz in ("UTC", "America/Los_Angeles", "Europe/Paris", "Australia/Sydney"):
        monkeypatch.setenv("TZ", tz)
        time.tzset()
        answers.add(venue_today())
    monkeypatch.delenv("TZ", raising=False)
    time.tzset()
    assert len(answers) == 1, f"venue_today() drifted with host TZ: {answers}"


@pytest.mark.parametrize("host_tz", ["UTC", "Europe/Paris", "Australia/Sydney"])
def test_venue_today_matches_pacific_calendar_day(host_tz, monkeypatch):
    monkeypatch.setenv("TZ", host_tz)
    time.tzset()
    try:
        expected = datetime.now(VENUE_TZ).date()
        assert venue_today() == expected
    finally:
        monkeypatch.delenv("TZ", raising=False)
        time.tzset()


def test_regression_evening_pacific_does_not_prune_todays_showtimes(monkeypatch):
    """18:02 PDT on Aug 11 is 01:02 UTC on Aug 12. A UTC host pruned Aug 11
    as 'past' while the cinema was still showing films that evening."""
    monkeypatch.setenv("TZ", "UTC")
    time.tzset()
    try:
        pacific_now = datetime.now(VENUE_TZ)
        todays_showtimes = [st(pacific_now.date().isoformat(), "22:00")]

        kept = merge_known([], todays_showtimes, "showtime")
        assert len(kept) == 1, (
            "a showtime later today (venue time) must not be pruned as past"
        )
    finally:
        monkeypatch.delenv("TZ", raising=False)
        time.tzset()


def test_regression_no_repeat_alert_across_the_utc_midnight_boundary(monkeypatch):
    """The exact loop that produced three identical emails 16 minutes apart:
    prune today's showtimes -> rescan finds them -> they look new -> alert."""
    monkeypatch.setenv("TZ", "UTC")
    time.tzset()
    try:
        today_pacific = datetime.now(VENUE_TZ).date().isoformat()
        scrape = [st(today_pacific, t) for t in ("10:00", "14:00", "22:00")]
        calendar = [today_pacific]

        known = merge_known([], scrape, "showtime")
        assert known, "baseline must survive the prune"

        # next pass, identical scrape
        new = diff_showtimes([Showtime.from_dict(d) for d in known], scrape)
        alerts, _ = alertable_showtimes(
            new,
            scraped_dates={d["date"] for d in known},
            calendar_dates=set(calendar),
            evaluated_dates=set(calendar),
            today=venue_today(),
        )
        assert new == [] and alerts == [], (
            "an unchanged scrape must stay silent regardless of host timezone"
        )
    finally:
        monkeypatch.delenv("TZ", raising=False)
        time.tzset()


def test_yesterdays_showtimes_are_still_pruned():
    """The prune must keep working -- past showtimes cannot be bought."""
    yesterday = (venue_today() - timedelta(days=1)).isoformat()
    assert merge_known([], [st(yesterday)], "showtime") == []
