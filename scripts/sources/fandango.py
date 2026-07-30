"""Fandango's AMC Metreon 16 theater page.

This does NOT use the generic keyword+70mm+time proximity extraction from
_common.py. Live testing against the real page (2026-07-30) showed why:
the theater page only renders ONE calendar day's showtimes at a time (the
selected day, defaulting to today) — so proximity text-matching only ever
sees "today," which is useless for catching an advance wave that's booking
dates months out.

What the page DOES expose without any clicking is the calendar widget's
full list of bookable dates, several months deep — including the sparse,
far-out dates that represent already-booked special/event showtimes (Dune:
Part Three's confirmed Dec 17-20, 2026 dates showed up exactly this way in
testing, dozens of weeks past the theater's regular day-to-day grid).

So the signal this source watches for is simpler and more robust than
per-showtime scraping: any NEW date appearing in that calendar list at all.
A new date is a real, confirmed change to what's bookable at Metreon — it
doesn't independently confirm which film or format, so it's surfaced as a
"mention"-kind alert (heads up, go check) rather than a hard ticket alert,
with the theater page URL included so checking takes one click.

fandango.com/robots.txt disallows /api/, /napi/*, and any ?date=-filtered
URL — this only ever loads the plain theater-page URL (no query params),
never a disallowed one.
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from browser import goto_and_classify, polite_page  # noqa: E402
from _common import _dismiss_cookie_banner  # noqa: E402
from normalize import Showtime, SourceResult  # noqa: E402

SOURCE_NAME = "fandango"
LANDMARKS = ["metreon", "fandango"]

CALENDAR_ENTRY_PATTERN = re.compile(r"\b([A-Z]{3})\n([A-Z]{3})\n(\d{2})\b")
MONTH_MAP = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}


def _parse_calendar_dates(text: str, today: date) -> list[str]:
    """Extract the calendar widget's date list, in the ISO format it's
    listed in (chronological), inferring year rollover at Dec -> Jan."""
    year = today.year
    last_month = today.month
    dates = []
    for _weekday, month_abbr, day in CALENDAR_ENTRY_PATTERN.findall(text):
        month = MONTH_MAP.get(month_abbr)
        if not month:
            continue
        if month < last_month:
            year += 1
        last_month = month
        dates.append(f"{year:04d}-{month:02d}-{int(day):02d}")
    return dates


def check(target: dict) -> SourceResult:
    url = target["fandango_theater_url"]

    with polite_page() as page:
        classification, response = goto_and_classify(page, url)
        if classification == "blocked":
            status_code = response.status if response else "?"
            reason = "403/429 response" if status_code in (403, 429) else "waiting-room/challenge interstitial"
            return SourceResult(
                source=SOURCE_NAME, target_id=target["id"], status="blocked",
                error=f"HTTP {status_code} — {reason}",
            )
        if classification == "no_data":
            return SourceResult(
                source=SOURCE_NAME, target_id=target["id"], status="no_data", error="navigation failed"
            )

        _dismiss_cookie_banner(page)
        try:
            page.wait_for_load_state("networkidle", timeout=15_000)
        except Exception:
            pass  # Fandango's page never fully idles; proceed with whatever rendered

        try:
            body_text = page.inner_text("body")
        except Exception as e:
            return SourceResult(source=SOURCE_NAME, target_id=target["id"], status="parse_error", error=str(e))

    lowered = body_text.lower()
    if not any(landmark in lowered for landmark in LANDMARKS):
        return SourceResult(
            source=SOURCE_NAME, target_id=target["id"], status="parse_error",
            error="expected page landmarks not found — page structure may have changed",
        )

    calendar_dates = _parse_calendar_dates(body_text, date.today())
    if not calendar_dates:
        # Landmarks were present (it's genuinely Metreon's page) but the
        # calendar widget itself yielded nothing — that's the structural
        # break the dead-man's switch exists for, not a normal "no showtimes."
        return SourceResult(
            source=SOURCE_NAME, target_id=target["id"], status="parse_error",
            error="page loaded but no calendar dates were extracted — widget structure may have changed",
        )

    showtimes = [
        Showtime(date=d, time="unknown", format=target["format"], venue=target["venue"], booking_url=url)
        for d in calendar_dates
    ]
    return SourceResult(source=SOURCE_NAME, target_id=target["id"], status="ok", kind="mention", showtimes=showtimes)
