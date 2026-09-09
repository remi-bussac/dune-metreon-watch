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

Fandango publishes a separate film entry per premium format, so this page is
the film's 70mm entry: its calendar lists the dates that entry plays, and
each date lists the specific theaters and times. That gives film + format +
venue + date + time in one place, with no regular-programming noise, and it
changes when a wave adds either a new date or a new showtime on an existing
date.

It is NOT true that everything on the page is 70mm, which an earlier version
of this docstring claimed. Under a 70mm date, Fandango also lists nearby
theaters showing the same film in their own premium format: on 2026-12-18 the
page carried Apple Cinemas Van Ness (plain reserved seating), Alamo New
Mission (HDR by Barco) and AMC Bay Street (IMAX with Laser) alongside
Metreon's 70mm. So format is filtered per amenity group, per theater, and
never assumed from the URL.

Politeness: only the plain movie-overview URL is ever navigated to (no query
params — Fandango's robots.txt disallows `*?*date=*`, `/api/` and `/napi/*`,
and none of those are requested by hand). Selecting a date is a click on the
page's own calendar control, the same thing a person browsing would do.
"""

from __future__ import annotations

import re
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from browser import goto_and_classify, polite_page  # noqa: E402
from _common import _dismiss_cookie_banner  # noqa: E402
from normalize import Showtime, SourceResult, venue_today  # noqa: E402

SOURCE_NAME = "fandango"

# Setting the location the way a person does.
#
# Fandango used to honour plain location cookies, and seeding them before the
# first navigation was what pinned results to a metro. THAT STOPPED WORKING
# on 2026-08-19: the cookies were sent, survived the load intact (zip=94102,
# searchcity=SANFRANCISCO), and the page rendered another metro anyway,
# because Fandango now resolves location from the IP. The VM sits in San
# Jose, so every run came back showing 95101 with no Metreon in the results
# at all. The cookies have been removed rather than left in place: they did
# nothing, and with more than one metro to watch they were actively
# misleading, since seeding San Francisco while asking for Dublin describes
# a request the code is not making.
#
# What works instead: the resolved ZIP sits on a button ("THEATERS NEAR
# 95101") which opens an overlay with a location field. Typing a ZIP there
# and pressing Enter re-renders the whole showtimes section for that metro.
# Verified on the VM (95101 -> 94102, after which its theater list matched a
# residential SF connection exactly) and again for 10001 and 94568.
#
# Same principle the date carousel already follows. No URL Fandango
# disallows, no private API, just the control the site puts on the page for
# exactly this purpose.
DEFAULT_ZIP = "94102"  # San Francisco, for targets that do not name one
LOCATION_BUTTON_SELECTOR = "button.js-location-overlay"
LOCATION_INPUT_SELECTOR = "#setLocationSearchInput"
# Where the resolved ZIP is rendered, and the only proof the change landed.
PAGE_ZIP_PATTERN = re.compile(r"THEATERS NEAR\s+(\d{5})")
LOCATION_SETTLE_MS = 1_500
LOCATION_CONFIRM_TIMEOUT_MS = 10_000
LOCATION_POLL_MS = 500
LOCATION_BUTTON_SELECTOR = "button.js-location-overlay"
LOCATION_INPUT_SELECTOR = "#setLocationSearchInput"
# Where the resolved ZIP is rendered, and the only proof the change landed.
PAGE_ZIP_PATTERN = re.compile(r"THEATERS NEAR\s+(\d{5})")
LOCATION_SETTLE_MS = 1_500
LOCATION_CONFIRM_TIMEOUT_MS = 10_000
LOCATION_POLL_MS = 500

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

# ...and everything else was read exactly once, back when it was still unseen,
# then never again until it drifted into NEAR_TERM_RESCAN. That is how Sept 18,
# 19 and 20 came to be emailed as new on three consecutive nights when their
# times had been on sale for weeks: the state for those dates was simply old.
#
# So each pass also re-reads the few dates that have gone longest without a
# look. With 4, the eleven dates that were orphaned when this was written are
# all refreshed inside 3 passes, about 45 minutes, and no date can drift out
# of date by more than that. Deliberately small: the empty dates already get
# scanned every pass, so this only has to cover the ones that hold showtimes.
STALE_ROTATION = 4

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
FORMAT_70MM_PATTERN = re.compile(r"70\s?mm", re.IGNORECASE)

# One theater's card, and the per-format blocks inside it. Reading these
# instead of the rendered prose is what lets the parser tell a showtime you
# can buy from one that is merely printed. See AVAILABLE_CLASS below.
THEATER_CARD_SELECTOR = ".js-movie-showtime-theater"
THEATER_NAME_SELECTOR = ".shared-theater-header__name"
AMENITY_GROUP_SELECTOR = ".shared-showtimes__amenity-group"
AMENITIES_SELECTOR = ".shared-showtimes__amenities"
SHOWTIME_BTN_SELECTOR = ".showtime-btn"

# THE distinction this whole module now turns on.
#
# Fandango renders a buyable showtime and an unbuyable one with identical
# text -- "8:30a" either way -- and the words "sold out" appear NOWHERE in
# the page text, so no text-level parser can tell them apart. It exists only
# in the markup:
#
#   buyable  <a    class="... showtime-btn--available" href="tickets.fandango.com/...">
#   locked   <span class="... showtime-btn--soldout" data-type="soldout">
#
# This matters because of what AMC actually did on 2026-08-18: it published
# Dec 27 through Jan 14 at Metreon as complete schedules with every single
# time locked, and put only Dec 18-26 on sale. The old text parser read all
# of it as a release. The one alert sent that day listed 147 showtimes, of
# which 101 could never be bought, which is what "the email listed dates
# through January that I could not buy" means. Those 101 are still sitting
# on the page today, so this is a live bug, not a historical one.
AVAILABLE_CLASS = "showtime-btn--available"

# Fandango percent-encodes the buy link, so "sdate=2026-12-18%2B08%3A00"
# decodes to "2026-12-18+08:00". That stamp is the showtime's own record of
# which date and time it belongs to, which makes it proof rather than
# inference: see _date_matches.
SDATE_PATTERN = re.compile(r"[?&]sdate=(\d{4}-\d\d-\d\d)[+ ](\d\d):(\d\d)")

# The JS that lifts the whole date's structure out in one call. Kept as data
# (theater -> format group -> showtime) so everything downstream of it is
# plain Python that tests can drive without a browser.
CARD_SCRAPE_JS = f"""
() => Array.from(document.querySelectorAll('{THEATER_CARD_SELECTOR}')).map(card => {{
  const name = card.querySelector('{THEATER_NAME_SELECTOR}');
  return {{
    theater: name ? name.innerText.trim() : '',
    groups: Array.from(card.querySelectorAll('{AMENITY_GROUP_SELECTOR}')).map(group => {{
      const amenities = group.querySelector('{AMENITIES_SELECTOR}');
      return {{
        amenities: amenities ? amenities.innerText.trim() : '',
        showtimes: Array.from(group.querySelectorAll('{SHOWTIME_BTN_SELECTOR}')).map(btn => ({{
          label: (btn.innerText || '').trim(),
          available: btn.classList.contains('{AVAILABLE_CLASS}'),
          href: btn.getAttribute('href') || ''
        }}))
      }};
    }})
  }};
}});
"""


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


def _page_zip(page) -> str | None:
    """The ZIP the page says it is showing results for, or None."""
    try:
        match = PAGE_ZIP_PATTERN.search(page.inner_text("body"))
    except Exception:
        return None
    return match.group(1) if match else None


def _ensure_metro(page, zip_code: str) -> bool:
    """Make the page show `zip_code`'s results, and prove that it does.

    Returns True only if that exact ZIP is on screen when this returns.
    Every caller treats False as parse_error rather than "nothing on sale",
    because from the wrong metro the target venue is simply absent from the
    results, and reading that as "no showtimes" is a lie, not a fact. That
    confusion is what this function exists to prevent: on 2026-08-19
    Fandango stopped honouring the location cookies, the VM started
    resolving to 95101, and every run reported zero Metreon showtimes.

    The match is exact, not "some ZIP in the right city". Two venues are
    watched from two different metros now, and a page that came back with a
    neighbouring ZIP would be a page whose theater list we cannot reason
    about: the list is capped at roughly ten cinemas by distance, so which
    ZIP you ask from decides who makes the cut. Asking precisely is the only
    way that stays true as venues are added.

    Does nothing when the page already resolved to the ZIP we want, so this
    costs an interaction only where it is actually needed."""
    if _page_zip(page) == zip_code:
        return True

    try:
        page.locator(LOCATION_BUTTON_SELECTOR).first.click(timeout=5_000)
        page.wait_for_timeout(LOCATION_SETTLE_MS)
        box = page.locator(LOCATION_INPUT_SELECTOR).first
        box.fill(zip_code)
        page.wait_for_timeout(LOCATION_SETTLE_MS)
        box.press("Enter")
    except Exception:
        return False

    # Wait for a specific observable state, never a fixed sleep: the metro
    # switch re-fetches the whole theater list, and how long that takes is
    # not ours to predict.
    waited = 0
    while waited < LOCATION_CONFIRM_TIMEOUT_MS:
        page.wait_for_timeout(LOCATION_POLL_MS)
        waited += LOCATION_POLL_MS
        if _page_zip(page) == zip_code:
            return True
    return False


def _label_to_24h(label: str) -> str | None:
    """"8:30a" -> "08:30". Used only for locked showtimes, which carry no
    machine-readable stamp of their own."""
    match = TIME_PATTERN.search(label)
    if not match:
        return None
    hour, minute, meridiem = match.groups()
    h = int(hour)
    is_pm = meridiem.lower().startswith("p")
    if is_pm and h != 12:
        h += 12
    if not is_pm and h == 12:
        h = 0
    return f"{h:02d}:{minute}"


def _date_matches(stamped: str, date_str: str) -> bool:
    """Does a buy link's own sdate belong to the calendar date we asked for?

    Not a plain equality check, because a cinema's day runs past midnight.
    Metreon's 2:30a show sits under FRIDAY DEC 18 in the calendar but its
    link is stamped sdate=2026-12-19+02:30, which is the honest wall-clock
    answer. So the day after is accepted too, and the showtime keeps the
    calendar's date -- the same business-day convention already in
    state.json, so nothing already known re-alerts as new.

    Anything further out means the page still had another date on screen
    when we read it. That is the stale-render bug that once reported Sep
    13-16 with Sep 11's showtimes, and here it is caught by the showtime
    itself rather than by anything we infer about the page."""
    try:
        wanted = date.fromisoformat(date_str)
    except ValueError:
        return False
    return stamped in (date_str, (wanted + timedelta(days=1)).isoformat())


def showtimes_from_cards(
    cards: list[dict], target: dict, date_str: str
) -> tuple[list[Showtime], list[Showtime]]:
    """One date's scraped theater cards -> (buyable, locked) for our venue.

    Only the first list is ever alerted on. The second is kept so a run can
    say out loud how much of what it saw was unbuyable, which is the number
    that used to be silently emailed as news.

    Three filters, in order, and each one has drawn blood before:

      venue    the card's own theater name. Was a text slice between
               "29.55 mi" distance markers, which is how a neighbouring
               cinema's times could land under Metreon's name.
      format   the amenity group's own text must say 70mm. The page lists
               other theaters in their own premium formats (IMAX with
               Laser, HDR by Barco), and a laser IMAX seat is not what this
               is watching for.
      buyable  the class on the button. See AVAILABLE_CLASS.
    """
    venue = target["venue"].lower()
    available: dict[tuple, Showtime] = {}
    locked: dict[tuple, Showtime] = {}

    for card in cards:
        if venue not in (card.get("theater") or "").lower():
            continue
        for group in card.get("groups") or []:
            if not FORMAT_70MM_PATTERN.search(group.get("amenities") or ""):
                continue
            for button in group.get("showtimes") or []:
                if button.get("available"):
                    href = unquote(button.get("href") or "")
                    match = SDATE_PATTERN.search(href)
                    if not match:
                        # Marked buyable but carries no link we can read.
                        # Not proof of a release, so it is not treated as one.
                        continue
                    stamped, hour, minute = match.groups()
                    if not _date_matches(stamped, date_str):
                        continue
                    showtime = Showtime(
                        date=date_str,
                        time=f"{hour}:{minute}",
                        format=target["format"],
                        venue=target["venue"],
                        # The deep link for THIS showtime, not the generic
                        # film page. The stamp in it is a content hash, not
                        # a session token (verified stable across separate
                        # page loads), so it is safe to keep in state.
                        booking_url=button.get("href") or "",
                    )
                    available[showtime.key()] = showtime
                else:
                    time_24h = _label_to_24h(button.get("label") or "")
                    if time_24h is None:
                        continue
                    showtime = Showtime(
                        date=date_str,
                        time=time_24h,
                        format=target["format"],
                        venue=target["venue"],
                        booking_url="",  # there is nothing to link to
                    )
                    locked[showtime.key()] = showtime

    return list(available.values()), list(locked.values())


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


def dates_to_scan(
    all_dates: list[str],
    known_dates: set[str],
    read_times: dict[str, str | None],
) -> list[str]:
    """Which dates this pass spends a click on, in calendar order.

    Three slices, and the third is the one that stops state going stale:

      unseen     no showtimes recorded yet. A run being extended or a wave
                 opening looks like this, so it is never skipped.
      near_term  the NEAR_TERM_RESCAN nearest dates that do have showtimes,
                 where same-day times get added.
      stale      the STALE_ROTATION dates, out of everything left, that have
                 gone longest without a reading.

    Without that third slice a far-future date was read once, while it was
    still unseen, and then not again until it drifted into near_term, by which
    time weeks of changes had piled up and surfaced together looking like a
    release. A date with no recorded reading sorts first: unknown means overdue.
    """
    unseen = [d for d in all_dates if d not in known_dates]
    near_term = [d for d in all_dates if d in known_dates][:NEAR_TERM_RESCAN]
    rest = [d for d in all_dates if d not in set(unseen) | set(near_term)]
    stale = sorted(rest, key=lambda d: read_times.get(d) or "")[:STALE_ROTATION]
    wanted = set(unseen) | set(near_term) | set(stale)
    return [d for d in all_dates if d in wanted]


def check(
    target: dict,
    known_dates: set[str] | None = None,
    read_times: dict[str, str | None] | None = None,
) -> SourceResult:
    url = target["fandango_film_url"]
    today = venue_today()
    known_dates = known_dates or set()
    read_times = read_times or {}
    # The metro to ask from. Metreon is watched from San Francisco and Regal
    # Hacienda Crossings from Dublin, and because the theater list is capped
    # by distance, asking from the wrong one can drop a venue off the page
    # entirely even on a date it is playing.
    zip_code = target.get("zip", DEFAULT_ZIP)

    with polite_page() as page:
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

        # Before anything is read, including the calendar: a different metro
        # offers different dates, so getting this wrong would poison the
        # calendar diff as well as the showtimes.
        if not _ensure_metro(page, zip_code):
            return SourceResult(
                source=SOURCE_NAME, target_id=target["id"], status="parse_error",
                error=f"page is showing ZIP {_page_zip(page)}, not the {zip_code} we asked "
                      f"for, and the location control did not fix it — venue results "
                      f"cannot be trusted",
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

        # Ration the clicks. A brand-new date -- a run being extended, or a
        # new wave opening -- is always scanned the very run it appears; the
        # rest is the rotation described on dates_to_scan.
        wanted_dates = dates_to_scan(all_dates, known_dates, read_times)

        showtimes: list[Showtime] = []
        locked: list[Showtime] = []
        missed: list[str] = []
        for date_str in wanted_dates:
            # Re-resolve the button every iteration and match on its parsed
            # date rather than reusing an index: clicking re-renders the
            # date carousel, which invalidates previously-held handles (this
            # is why an index-based loop silently dropped the last date).
            if not _click_date(page, date_str, today):
                missed.append(date_str)
                continue

            # Belt: if the DOM is stamped with dates and ours is not among
            # them, the click has not landed and everything on screen belongs
            # to some other date. This is the check that would have stopped
            # the Sep 13-16 alert.
            rendered = set(_rendered_showtime_dates(page))
            if rendered and date_str not in rendered:
                missed.append(date_str)
                continue

            try:
                cards = page.evaluate(CARD_SCRAPE_JS)
            except Exception:
                missed.append(date_str)
                continue

            # Braces: every buyable showtime is then checked against its own
            # sdate stamp, so a stale render cannot smuggle another date's
            # showtimes in here even if the belt above passes. That per-
            # showtime proof replaces an older guard which treated "times in
            # the prose but no date-stamped element" as contradictory: with
            # nothing left reading prose, the absence of a seat-map button
            # proves nothing, and rejecting on it risked dropping a real
            # release at a theater that simply has no seat map.
            found, found_locked = showtimes_from_cards(cards, target, date_str)
            showtimes.extend(found)
            locked.extend(found_locked)

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
        showtimes=showtimes, locked_showtimes=locked, calendar_dates=all_dates,
        evaluated_dates=[d for d in wanted_dates if d not in missed], error=error,
    )
