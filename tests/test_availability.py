"""Only alert on showtimes that can actually be bought.

The bug these tests pin down, in one sentence: on 2026-08-18 AMC published
Dec 27 2026 through Jan 14 2027 at Metreon as complete schedules with every
time marked sold out, sold only Dec 18-26, and the monitor emailed all of it
as a release.

That was not a parsing slip. The old parser read times out of the rendered
prose, and in the prose a locked showtime and a buyable one are the same
five characters. The words "sold out" appear nowhere on the page. The
distinction exists only in the markup, which is why the parser now reads the
DOM, and why the fixtures here store the scraped structure rather than text.

tests/fixtures/dune_locked_only.cards.json is that false alert preserved: a
real capture of 2027-01-08 taken the day after, when Metreon's five listed
times were, and still are, unbuyable.
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "scripts" / "sources"))

import pytest  # noqa: E402

from monitor import alertable_showtimes  # noqa: E402
from normalize import Showtime  # noqa: E402
from sources.fandango import showtimes_from_cards  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text())
TARGETS = {t["id"]: t for t in json.loads((REPO / "config" / "targets.json").read_text())}

METREON = "AMC Metreon 16"
BUY_LINK = "https://tickets.fandango.com/transaction/ticketing/mobile/jump.aspx?sdate={}%2B{}%3A{}&mid=245188&tid=aanem"


def cards(name: str) -> list[dict]:
    return json.loads((FIXTURES / f"{name}.cards.json").read_text())


def parse(name: str):
    target = TARGETS[MANIFEST[name]["target_id"]]
    return showtimes_from_cards(cards(name), target, MANIFEST[name]["selected_date"])


def card(theater: str, amenities: str, showtimes: list[dict]) -> dict:
    """A hand-built theater card, for the cases the live page cannot show us
    on demand (a stale render, a venue playing the film in two formats)."""
    return {"theater": theater, "groups": [{"amenities": amenities, "showtimes": showtimes}]}


def buyable(date: str, time: str) -> dict:
    hour, minute = time.split(":")
    return {"label": time, "available": True, "href": BUY_LINK.format(date, hour, minute)}


def locked(label: str) -> dict:
    return {"label": label, "available": False, "href": ""}


# --------------------------------------------------------------------------
# The regression itself
# --------------------------------------------------------------------------

def test_locked_date_produces_nothing_to_alert_on():
    """2027-01-08: Metreon lists five 70mm times, sells none of them.

    This exact date, captured from the live page, is what the old parser
    turned into five "new showtimes". It must now produce an empty alert
    list, and say so by putting them in the locked list instead."""
    available, unbuyable = parse("dune_locked_only")
    assert available == [], "a date nobody can buy a ticket for must not alert"
    assert len(unbuyable) == 5, "the locked times are still reported, just not as news"
    assert all(s.venue == METREON for s in unbuyable)


def test_the_whole_january_run_is_locked_not_released():
    """Generalising the above past one date. Every Metreon time the fixtures
    hold for the un-released stretch is unbuyable, so a run over them alerts
    on nothing at all."""
    for name in ("dune_locked_only", "dune_event_date"):
        available, unbuyable = parse(name)
        assert available == [], f"{name} must not yield anything alertable"
        assert unbuyable, f"{name} should still record what it saw"


def test_mixed_date_alerts_on_the_buyable_times_only():
    """2026-12-18 really did go on sale, and its 7:00p really did sell out.

    The two must not be conflated in either direction: dropping the date
    would miss the release, keeping 7:00p would send the user at a showtime
    that is gone."""
    available, unbuyable = parse("dune_on_sale_mixed")
    assert sorted(s.time for s in available) == ["02:30", "08:00", "11:30", "23:00"]
    assert [s.time for s in unbuyable] == ["19:00"]


def test_fully_available_date_keeps_every_time():
    available, unbuyable = parse("dune_on_sale_all")
    assert sorted(s.time for s in available) == ["08:30", "12:00", "15:30", "19:00", "23:00"]
    assert unbuyable == []


def test_buyable_showtimes_carry_their_own_deep_link():
    """The alert is worth more if it lands on the showtime rather than the
    film. Locked ones carry no link because there is nothing to link to."""
    available, unbuyable = parse("dune_on_sale_mixed")
    assert all(s.booking_url.startswith("https://tickets.fandango.com/") for s in available)
    assert all(s.booking_url == "" for s in unbuyable)


# --------------------------------------------------------------------------
# Late-night showtimes: the calendar day and the clock disagree on purpose
# --------------------------------------------------------------------------

def test_after_midnight_showtime_is_kept_on_the_calendar_day():
    """Metreon's 2:30a show sits under FRIDAY DEC 18 in the calendar, and its
    buy link is honestly stamped 2026-12-19+02:30.

    It must survive the date check (a naive equality test would drop it) and
    it must keep the calendar's date, because that is the convention already
    in state.json. Getting this wrong either loses a real showtime or makes
    every late show look new once."""
    available, _ = parse("dune_on_sale_mixed")
    late = [s for s in available if s.time == "02:30"]
    assert len(late) == 1, "the after-midnight show must not be dropped"
    assert late[0].date == "2026-12-18", "it belongs to the calendar day it was listed under"
    assert "sdate=2026-12-19" in late[0].booking_url, "while its link says the true clock date"


def test_showtime_stamped_two_days_out_is_rejected_as_a_stale_render():
    """The page rewrites its date optimistically and re-fetches the theater
    list afterwards, which is how Sep 13-16 once got reported carrying Sep
    11's showtimes. Each buy link now has to vouch for itself."""
    stale = [card(METREON, "IMAX® 70MM Film", [buyable("2026-12-11", "19:00")])]
    available, _ = showtimes_from_cards(stale, TARGETS["dune-part-three"], "2026-12-18")
    assert available == [], "a showtime stamped with another date is not this date's"


def test_button_marked_available_without_a_readable_link_is_not_a_release():
    no_link = [card(METREON, "IMAX® 70MM Film", [{"label": "7:00p", "available": True, "href": ""}])]
    available, _ = showtimes_from_cards(no_link, TARGETS["dune-part-three"], "2026-12-18")
    assert available == [], "nothing to verify against means nothing to act on"


# --------------------------------------------------------------------------
# Venue and format scoping
# --------------------------------------------------------------------------

def test_other_theatres_are_never_attributed_to_our_venue():
    """2027-01-08 lists Regal Edwards Fairfield with four buyable times while
    Metreon has none. Reading availability off the page as a whole would
    turn another cinema's inventory into a Metreon release."""
    available, _ = parse("dune_locked_only")
    theaters = {c["theater"] for c in cards("dune_locked_only")}
    assert any("Regal" in t for t in theaters), "fixture should contain another cinema"
    assert available == []


def test_non_70mm_format_at_our_own_venue_is_ignored():
    """The point of the whole project is IMAX 70mm. Metreon selling the same
    film on a normal screen is not the event, so an amenity group that does
    not say 70mm is skipped even at the right venue."""
    mixed_formats = {
        "theater": METREON,
        "groups": [
            {"amenities": "Reserved seating", "showtimes": [buyable("2026-12-18", "14:00")]},
            {"amenities": "IMAX® 70MM Film, Reserved seating",
             "showtimes": [buyable("2026-12-18", "19:00")]},
        ],
    }
    available, _ = showtimes_from_cards([mixed_formats], TARGETS["dune-part-three"], "2026-12-18")
    assert [s.time for s in available] == ["19:00"], "only the 70mm group counts"


def test_laser_imax_is_not_70mm():
    """AMC Bay Street shows this film in IMAX with Laser and appears on the
    same page. Close enough to fool a substring check for "IMAX", not close
    enough to be worth an alert."""
    laser = [card("AMC Bay Street 16", "IMAX with Laser, Reserved seating",
                  [buyable("2026-12-18", "19:00")])]
    available, unbuyable = showtimes_from_cards(laser, TARGETS["dune-part-three"], "2026-12-18")
    assert available == [] and unbuyable == []


# --------------------------------------------------------------------------
# End to end: the January release, when it finally comes
# --------------------------------------------------------------------------

def test_a_locked_date_going_on_sale_is_alerted():
    """The event this monitor now exists to catch.

    Jan 8 has been read on every pass and has held nothing buyable, so it is
    a known calendar date, an evaluated date, and absent from the set of
    dates we have showtimes for. The moment it yields a buyable showtime,
    that is the release, and it must not be filed as backfill."""
    released = Showtime(date="2027-01-08", time="19:00", format="IMAX 70mm",
                        venue=METREON, booking_url="https://tickets.fandango.com/x")
    alert_these, quiet = alertable_showtimes(
        [released],
        scraped_dates=set(),                       # never had a buyable time here
        calendar_dates={"2027-01-08"},             # but the date has always been offered
        evaluated_dates={"2027-01-08"},            # and we have read it, repeatedly
        today=__import__("datetime").date(2026, 8, 19),
    )
    assert alert_these == [released], "this is the on-sale, it has to fire"
    assert quiet == []


def test_locked_showtimes_never_reach_the_alert_path():
    """Belt and braces across the seam: even if a locked showtime somehow got
    as far as monitor.py, the parser is the thing that keeps it out, so the
    two lists must stay disjoint."""
    available, unbuyable = parse("dune_on_sale_mixed")
    assert not ({s.key() for s in available} & {s.key() for s in unbuyable})


@pytest.mark.parametrize("name", sorted(MANIFEST))
def test_every_fixture_has_a_card_capture(name):
    """A text-only fixture would silently exercise nothing now that the
    parser reads structure."""
    assert (FIXTURES / f"{name}.cards.json").exists(), f"{name} needs a re-capture"


# --------------------------------------------------------------------------
# The state migration, without which the fix above changes nothing on the VM
# --------------------------------------------------------------------------

def test_rebuild_drops_phantoms_and_restores_the_january_alert():
    """Reproduces the live VM's state as of 2026-08-19 and shows both the
    damage and the repair.

    Before: 2027-01-08 is recorded with the five times that will go on sale,
    so the release matches what state already holds and alerts nobody, and
    the date counts as "seen" so the click rationing stops scanning it.
    After: the date has no known showtimes, so it is scanned every run and
    its showtimes are new when they arrive."""
    import monitor
    from normalize import SourceResult

    phantom_times = ["08:30", "12:00", "15:30", "19:00", "22:30"]
    locked_jan = [Showtime("2027-01-08", t, "IMAX 70mm", METREON, "") for t in phantom_times]
    buyable_dec = [Showtime("2026-12-20", t, "IMAX 70mm", METREON, "https://tickets.fandango.com/x")
                   for t in ("08:30", "12:00")]

    state = {"sources": {"dune-part-three::fandango": {
        **monitor.default_source_entry(),
        "known_showtimes": [s.to_dict() for s in locked_jan + buyable_dec],
        "known_calendar_dates": ["2026-12-20", "2027-01-08"],
        "known_evaluated_dates": ["2026-12-20", "2027-01-08"],
    }}}
    target = TARGETS["dune-part-three"]

    known_dates = {s["date"] for s in state["sources"]["dune-part-three::fandango"]["known_showtimes"]}
    assert "2027-01-08" in known_dates, "the phantom is what makes the date look already-scanned"

    # What a healthy pass now returns: December is buyable, January is not.
    monitor.rebuild_showtime_state(target, SourceResult(
        source="fandango", target_id="dune-part-three", status="ok", kind="showtime",
        showtimes=buyable_dec, locked_showtimes=locked_jan,
    ), state)

    entry = state["sources"]["dune-part-three::fandango"]
    remaining = {s["date"] for s in entry["known_showtimes"]}
    assert remaining == {"2026-12-20"}, "only what is genuinely on sale survives"
    assert entry["known_calendar_dates"] == ["2026-12-20", "2027-01-08"], "calendar must survive"
    assert entry["known_evaluated_dates"] == ["2026-12-20", "2027-01-08"], "so must evaluated"

    # And now the release fires, which is the whole point.
    released = Showtime("2027-01-08", "19:00", "IMAX 70mm", METREON, "https://tickets.fandango.com/y")
    alert_these, _ = alertable_showtimes(
        [released],
        scraped_dates=remaining,
        calendar_dates=set(entry["known_calendar_dates"]),
        evaluated_dates=set(entry["known_evaluated_dates"]),
        today=__import__("datetime").date(2026, 8, 19),
    )
    assert alert_these == [released]


def test_rebuild_leaves_reddit_mentions_alone():
    """Mentions are pruned on a 30-day window and have nothing to do with
    availability. Rebuilding them would risk re-alerting old posts."""
    import monitor
    from normalize import SourceResult

    mention = Showtime("2026-08-03", "08:05", "reddit-mention:x", "r/imax", "https://reddit/x")
    state = {"sources": {"dune-part-three::reddit_rss": {
        **monitor.default_source_entry(),
        "known_showtimes": [mention.to_dict()],
    }}}
    monitor.rebuild_showtime_state(TARGETS["dune-part-three"], SourceResult(
        source="reddit_rss", target_id="dune-part-three", status="ok", kind="mention",
        showtimes=[],
    ), state)
    assert state["sources"]["dune-part-three::reddit_rss"]["known_showtimes"] == [mention.to_dict()]
