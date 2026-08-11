"""Fandango's film-specific "IMAX 70MM Experience" page, geo-set to SF.

This is the monitor's highest-signal source. It replaced an earlier version
that diffed the *theater* page's calendar (every bookable date at Metreon,
for any film). That approach was wrong in both directions, confirmed against
real data on 2026-07-31:

  - False positives, daily: the theater calendar rolls forward as Metreon
    publishes regular programming, so a brand-new date appeared essentially
    every day (2026-09-08 showed up between two consecutive runs) and fired
    a "new date!" alert that had nothing to do with Dune.
  - False negative on the case that actually matters: Dec 17-20 2026 were
    ALREADY in that calendar (the April wave booked them). A second wave
    adding more Dune 70mm showtimes on those same dates changes no *date*,
    so the old source would have stayed completely silent through exactly
    the event this monitor exists to catch.

Fandango publishes a separate film entry per premium format, so the "IMAX
70MM Experience" page is inherently scoped to 70mm — its calendar lists only
dates that have 70mm showtimes (currently exactly Dec 17-20), and each date
lists the specific theaters and times. That gives film + format + venue +
date + time in one place, with no regular-programming noise, and it changes
when a wave adds either a new date or a new showtime on an existing date.

Politeness: only the plain movie-overview URL is ever navigated to (no query
params — Fandango's robots.txt disallows `*?*date=*`, `/api/` and `/napi/*`,
and none of those are requested by hand). Selecting a date is a click on the
page's own calendar control, the same thing a person browsing would do.
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

# Fandango stores the visitor's chosen location in plain cookies. Seeding
# them before the first navigation is what actually pins results to San
# Francisco. The browser geolocation override in browser.py is NOT enough
# on its own: it works from a residential IP but was observed failing on a
# GitHub runner (2026-07-31), where Fandango fell back to the datacenter's
# IP location and returned a different metro with no Metreon in it. These
# values were captured from a real session that had resolved to SF.
SF_LOCATION_COOKIES = [
    {"name": "zip", "value": "94102"},
    {"name": "akamai_set_zip", "value": "true"},
    {"name": "searchcity", "value": "SANFRANCISCO"},
    {"name": "searchstate", "value": "CA"},
    {"name": "searchlocation",
     "value": "lat%3D37.7795%26long%3D-122.4195%26name%3DSANFRANCISCO%252C%2520CA"},
]

# Proves the location actually took effect. Fandango renders the resolved
# ZIP under "THEATERS NEAR"; 941xx is San Francisco. If this is missing the
# page is showing some other metro, and "no Metreon showtimes" would be a
# lie rather than a fact — so it's reported as parse_error and picked up by
# the dead-man's switch instead of being read as "nothing on sale."
SF_ZIP_PATTERN = re.compile(r"\b941\d\d\b")

DATE_BUTTON_SELECTOR = "button.date-picker__button"

# How many calendar buttons we will even look at. Reading a button's label
# is free -- no click, no request -- so this is set high enough to see an
# entire engagement. The old limit of 12 applied to *reading* as well as
# clicking, which silently capped The Odyssey at Aug 5-16 while its run
# actually extended into mid-September. The truncation was recorded in the
# result's error field and never surfaced anywhere the user would see it.
LABEL_CAP = 60

# Clicking a date IS a request, so clicks are rationed. Every date we have
# never seen before is always scanned (a new date is the signal we care
# about most), plus the nearest few known dates, where same-day showtimes
# get added. Everything else is skipped: monitor.py unions results across
# runs, so a date scanned once stays known even when later passes skip it.
NEAR_TERM_RESCAN = 6

# How long to wait for the page to confirm it switched to the requested date
# before giving up and recording it as missed. Generous, because the failure
# this guards against showed up on a laptop waking from sleep.
DATE_CONFIRM_TIMEOUT_MS = 12_000
DATE_CONFIRM_POLL_MS = 400

# How long the showtime list must stay empty before we believe the date
# genuinely has no screenings, rather than the fetch simply being in flight.
EMPTY_SETTLE_MS = 2_500

# Fandango reflects the selected date in its own URL. We never construct such
# a URL ourselves -- robots.txt disallows ?date= -- we only read the one the
# site sets after a normal click, as proof of which date is on screen.
URL_DATE_PATTERN = re.compile(r"[?&]date=(\d{4}-\d\d-\d\d)")

MONTH_NAMES = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}
BUTTON_DATE_PATTERN = re.compile(
    r"(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+(\d{1,2})",
    re.IGNORECASE,
)
TIME_PATTERN = re.compile(r"\b(1[0-2]|0?[1-9]):([0-5][0-9])\s*([AaPp])\.?[Mm]?\b")
DISTANCE_PATTERN = re.compile(r"\d+\.\d+\s*mi")
FORMAT_70MM_PATTERN = re.compile(r"70\s?mm", re.IGNORECASE)


def _button_date(label: str, today: date) -> str | None:
    """"SATURDAY, DECEMBER 19 SAT DEC 19" -> "2026-12-19". Year is inferred
    relative to today, so this stays correct across a year boundary (a wave
    landing in early 2027 for a Dec 2026 film)."""
    match = BUTTON_DATE_PATTERN.search(label)
    if not match:
        return None
    month = MONTH_NAMES[match.group(1).lower()]
    day = int(match.group(2))
    year = today.year
    if month < today.month - 1:  # e.g. today is Nov, button says "JANUARY" -> next year
        year += 1
    return f"{year:04d}-{month:02d}-{day:02d}"


def _venue_block(body_text: str, venue: str) -> str | None:
    """Slice out just the target venue's section of the results list.

    Fandango lists each theater as "<name> / <distance> mi / <formats> /
    <times>", so the block ends where the *next* theater's distance marker
    begins. Without this cut, a neighbouring theater's showtimes would be
    misattributed to Metreon."""
    start = body_text.lower().find(venue.lower())
    if start == -1:
        return None
    rest = body_text[start:]
    distances = list(DISTANCE_PATTERN.finditer(rest))
    if len(distances) >= 2:
        rest = rest[: distances[1].start()]  # first distance is this venue's own
    return rest


def _extract_showtimes(body_text: str, target: dict, date_str: str, url: str) -> list[Showtime]:
    block = _venue_block(body_text, target["venue"])
    if not block or not FORMAT_70MM_PATTERN.search(block):
        return []
    out = {}
    for match in TIME_PATTERN.finditer(block):
        hour, minute, meridiem = match.groups()
        h = int(hour)
        is_pm = meridiem.lower().startswith("p")
        if is_pm and h != 12:
            h += 12
        if not is_pm and h == 12:
            h = 0
        st = Showtime(
            date=date_str,
            time=f"{h:02d}:{minute}",
            format=target["format"],
            venue=target["venue"],
            booking_url=url,
        )
        out[st.key()] = st
    return list(out.values())


def _rendered_showtime_dates(page) -> list[str]:
    """Dates stamped on the showtime elements currently in the DOM.

    Every bookable showtime carries data-showtime-date. This is the only
    signal tied to the *content*, which is what we actually parse."""
    try:
        return page.eval_on_selector_all(
            "[data-showtime-date]",
            "els => els.map(e => e.getAttribute('data-showtime-date'))",
        )
    except Exception:
        return []


def _content_state(page, date_str: str) -> str:
    """Is the rendered showtime list the one we asked for?

    "ready" - showtimes are present and every one belongs to date_str
    "stale" - showtimes are present but some belong to another date
    "empty" - no showtimes in the DOM at all: either this date genuinely has
              none, or the fetch has not landed yet. Indistinguishable from a
              single sample, so the caller waits it out.
    """
    dates = set(_rendered_showtime_dates(page))
    if not dates:
        return "empty"
    return "ready" if dates == {date_str} else "stale"


def _click_date(page, date_str: str, today: date) -> bool:
    """Select `date_str` and CONFIRM the page is really showing it.

    Returns False if the button is missing, the click fails, or the page
    never actually switches to that date -- in which case the caller records
    the date as missed rather than reading whatever happens to be on screen.

    Verified against the CONTENT, deliberately not against the URL. Fandango
    rewrites ?date=... optimistically the moment you click, before the
    theatre list is re-fetched. An earlier version of this check trusted that
    URL and still produced a false alert -- Sep 13 through Sep 16 were
    reported with Sep 11's showtimes, because the URL had already flipped
    while the DOM had not. The only trustworthy signal is the date stamped on
    the showtime elements we actually parse.

    Sleeping longer was never the fix: the race is unbounded, so any fixed
    delay is a guess. This waits for a specific observable state instead."""
    try:
        button = page.locator(f'{DATE_BUTTON_SELECTOR}[data-show-time-date="{date_str}"]').first
        if not button.count():
            return False
        button.scroll_into_view_if_needed(timeout=3_000)  # carousel may have it off-screen
        button.click(timeout=5_000)
    except Exception:
        return False

    waited = 0
    empty_for = 0
    while waited < DATE_CONFIRM_TIMEOUT_MS:
        page.wait_for_timeout(DATE_CONFIRM_POLL_MS)
        waited += DATE_CONFIRM_POLL_MS
        state = _content_state(page, date_str)

        if state == "ready":
            return True
        if state == "stale":
            empty_for = 0          # previous date still on screen; keep waiting
            continue
        # "empty": no showtimes rendered. Could be a date with no screenings
        # anywhere, or a fetch still in flight. Only believe it once it has
        # stayed empty long enough that a pending fetch would have landed.
        empty_for += DATE_CONFIRM_POLL_MS
        if empty_for >= EMPTY_SETTLE_MS:
            return True            # genuinely nothing on this date

    return False


def check(target: dict, known_dates: set[str] | None = None) -> SourceResult:
    url = target["fandango_film_url"]
    today = date.today()
    known_dates = known_dates or set()

    with polite_page() as page:
        page.context.add_cookies(
            [dict(c, domain=".fandango.com", path="/") for c in SF_LOCATION_COOKIES]
        )
        classification, response = goto_and_classify(page, url)
        if classification == "blocked":
            status_code = response.status if response else "?"
            return SourceResult(
                source=SOURCE_NAME, target_id=target["id"], status="blocked",
                error=f"HTTP {status_code} — blocked or challenge interstitial",
            )
        if classification == "no_data":
            return SourceResult(
                source=SOURCE_NAME, target_id=target["id"], status="no_data",
                error="navigation failed (film page may have moved — check fandango_film_url)",
            )

        _dismiss_cookie_banner(page)
        try:
            page.wait_for_load_state("networkidle", timeout=15_000)
        except Exception:
            pass  # Fandango never fully idles; proceed with what rendered
        page.wait_for_timeout(1_500)

        try:
            body_text = page.inner_text("body")
        except Exception as e:
            return SourceResult(
                source=SOURCE_NAME, target_id=target["id"], status="parse_error", error=str(e)
            )

        if not SF_ZIP_PATTERN.search(body_text):
            return SourceResult(
                source=SOURCE_NAME, target_id=target["id"], status="parse_error",
                error="no San Francisco ZIP on page — geolocation override may have stopped "
                      "working, so venue results cannot be trusted",
            )

        try:
            buttons = page.locator(DATE_BUTTON_SELECTOR)
            labels = [buttons.nth(i).inner_text() for i in range(min(buttons.count(), LABEL_CAP))]
        except Exception as e:
            return SourceResult(
                source=SOURCE_NAME, target_id=target["id"], status="parse_error",
                error=f"could not read calendar controls: {e}",
            )

        if not labels:
            # No 70mm dates offered at all. Real and meaningful for a film
            # between waves — not an error.
            return SourceResult(source=SOURCE_NAME, target_id=target["id"], status="ok", showtimes=[])

        all_dates = [d for d in (_button_date(lbl, today) for lbl in labels) if d]

        # Ration the clicks: every date we have never seen, plus the nearest
        # few we have, in calendar order. A brand-new date -- a run being
        # extended, or a new wave opening -- is always scanned the very run
        # it appears. Known far-future dates are left alone; monitor.py's
        # union means they stay known regardless.
        unseen = [d for d in all_dates if d not in known_dates]
        near_term = [d for d in all_dates if d in known_dates][:NEAR_TERM_RESCAN]
        wanted_dates = [d for d in all_dates if d in set(unseen) | set(near_term)]

        showtimes: list[Showtime] = []
        missed: list[str] = []
        for date_str in wanted_dates:
            # Re-resolve the button every iteration and match on its parsed
            # date rather than reusing an index: clicking re-renders the
            # date carousel, which invalidates previously-held handles (this
            # is why an index-based loop silently dropped the last date).
            if not _click_date(page, date_str, today):
                missed.append(date_str)
                continue
            try:
                day_text = page.inner_text("body")
            except Exception:
                missed.append(date_str)
                continue

            # Last line of defence. The text scrape reads a venue block out of
            # rendered prose, which cannot itself prove which date that prose
            # belongs to. The showtime elements CAN: each is stamped with its
            # own date. If nothing in the DOM is stamped with the date we
            # asked for, then whatever text is on screen belongs to some other
            # date, and emitting it would invent showtimes that do not exist.
            # This is the check that would have stopped the Sep 13-16 alert.
            rendered = set(_rendered_showtime_dates(page))
            if rendered and date_str not in rendered:
                missed.append(date_str)
                continue

            found = _extract_showtimes(day_text, target, date_str, url)
            if found and not rendered:
                # Text says there are showtimes but no showtime element carries
                # a date. Contradictory -- trust the DOM, not the prose.
                missed.append(date_str)
                continue
            showtimes.extend(found)

        error = None
        if missed:
            error = f"could not read {len(missed)} of {len(wanted_dates)} dates: {', '.join(missed)}"
        if len(labels) >= LABEL_CAP:
            note = (
                f"calendar hit LABEL_CAP={LABEL_CAP}; dates beyond that are not even "
                f"being listed — raise the cap"
            )
            error = f"{error}; {note}" if error else note

    return SourceResult(
        source=SOURCE_NAME, target_id=target["id"], status="ok", kind="showtime",
        showtimes=showtimes, calendar_dates=all_dates,
        evaluated_dates=[d for d in wanted_dates if d not in missed], error=error,
    )
