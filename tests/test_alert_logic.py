"""Tests for the alert DECISION logic.

Every test named test_regression_* corresponds to a bug that actually
reached the inbox. They exist so that fixing one cannot silently reintroduce
another -- which is exactly what happened twice: the fix for phantom dates
created the backfill false alert, and the fix for duplicate alerts was itself
a fix for a flaky-scrape problem that came back in a different shape.

None of this touches the network, a browser, or the clock beyond an injected
`today`. It is all pure functions over plain data, which is why it should
have existed from the first commit.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "scripts" / "sources"))

import pytest  # noqa: E402

from normalize import Showtime, diff_showtimes, venue_today  # noqa: E402
from monitor import (  # noqa: E402
    BASELINE_CADENCE, FRESH_WITHIN, MIN_LEAD_DAYS,
    alertable_showtimes, dates_gone_stale, merge_known, migrate_state,
)
from sources.fandango import (  # noqa: E402
    LABEL_CAP, NEAR_TERM_RESCAN, STALE_ROTATION, dates_to_scan,
)

# Must track the real clock, not a frozen date. merge_known prunes against
# venue_today(), so a hardcoded TODAY drifts out of its own fixtures and the
# suite starts failing on a calendar date rather than on a code change. That
# happened: TODAY was pinned to 2026-08-11 and the mention-retention test went
# red on 2026-09-08 with nothing having changed. alertable_showtimes takes
# `today` as an argument, so it does not care which day this is.
TODAY = venue_today()


def st(d: str, t: str = "19:00") -> Showtime:
    return Showtime(
        date=d, time=t, format="IMAX 70mm", venue="AMC Metreon 16", booking_url="u"
    )


def far(days: int = 60) -> str:
    """A date comfortably beyond MIN_LEAD_DAYS."""
    return (TODAY + timedelta(days=days)).isoformat()


# --------------------------------------------------------------------------
# merge_known: the union that stops flaky scrapes re-alerting
# --------------------------------------------------------------------------

def test_union_never_shrinks_on_a_partial_scrape():
    full = [st(far(), "19:00"), st(far(), "23:00"), st(far(), "15:00")]
    known = merge_known([], full, "showtime")
    assert len(known) == 3

    partial = [st(far(), "19:00")]           # a flaky pass that saw one of three
    known = merge_known(known, partial, "showtime")
    assert len(known) == 3, "a partial scrape must not erase what we already knew"


def test_regression_duplicate_alert_from_flaky_scrape():
    """Odyssey scraped 110 showtimes on some passes and 103 on others. State
    was REPLACED, so the next healthy pass re-reported the 7 as brand new and
    sent a second 'new showtimes' email with nothing released in between."""
    full = [st(far(), f"{h:02d}:00") for h in range(10, 20)]
    partial = full[:7]

    known = merge_known([], full, "showtime")
    known = merge_known(known, partial, "showtime")     # flaky pass
    reappeared = diff_showtimes([Showtime.from_dict(d) for d in known], full)

    assert reappeared == [], "showtimes we already knew must never look new again"


def test_past_showtimes_are_pruned_but_future_kept():
    past = [st("2020-01-01")]
    assert merge_known([], past, "showtime") == []

    future = [st(far())]
    assert len(merge_known([], future, "showtime")) == 1


def test_mentions_are_retained_longer_than_the_feed_window():
    """Reddit 'showtimes' carry a POST date, already in the past. Pruning them
    like showtimes would drop a post still in the RSS window, which would then
    look new again on the next pass."""
    recent_post = Showtime(
        date=(TODAY - timedelta(days=3)).isoformat(), time="12:00",
        format="reddit-mention:x", venue="r/imax", booking_url="u",
    )
    assert len(merge_known([], [recent_post], "mention")) == 1


# --------------------------------------------------------------------------
# alertable_showtimes: released vs merely-newly-readable
# --------------------------------------------------------------------------

def test_new_calendar_date_always_alerts_even_when_imminent():
    """A run extension or a new wave is the signal. It fires regardless of
    how soon the date is -- the lead-time floor must not swallow it."""
    tomorrow = (TODAY + timedelta(days=1)).isoformat()
    alerts, quiet = alertable_showtimes(
        [st(tomorrow)], scraped_dates=set(), calendar_dates={"2026-08-11"},
        evaluated_dates=set(), today=TODAY,
    )
    assert len(alerts) == 1 and quiet == []


def test_regression_backfill_does_not_alert():
    """Aug 25 was in the calendar all along but an earlier pass skipped it
    (date-confirm failure -> recorded as missed). When a later pass finally
    read it, all four showtimes looked brand new and emailed. Nothing had
    been released."""
    d = far()
    alerts, quiet = alertable_showtimes(
        [st(d, "10:00"), st(d, "14:00")],
        scraped_dates=set(),          # never successfully read this date
        calendar_dates={d},           # ...but the calendar had offered it
        evaluated_dates=set(),        # ...and we never managed to read it
        today=TODAY,
    )
    assert alerts == [], "a date the calendar already offered is not a release"
    assert len(quiet) == 2


def test_regression_cold_start_is_silent():
    """The VM came up with empty state and emailed ~170 Odyssey showtimes --
    the entire run that had been on sale for weeks."""
    everything = [st(far(i)) for i in range(10, 40)]
    alerts, quiet = alertable_showtimes(
        everything, scraped_dates=set(), calendar_dates=set(),
        evaluated_dates=set(), today=TODAY, first_pass=True,
    )
    assert alerts == [], "a target's first pass is a baseline, not news"
    assert len(quiet) == len(everything)


def test_new_time_on_an_already_scraped_date_alerts_when_far_out():
    d = far()
    alerts, _ = alertable_showtimes(
        [st(d, "15:00")], scraped_dates={d}, calendar_dates={d},
        evaluated_dates={d}, today=TODAY
    )
    assert len(alerts) == 1, "a wave adding a showtime to a known date must fire"


@pytest.mark.parametrize("lead", [0, 1, 2, 3, MIN_LEAD_DAYS - 1])
def test_regression_near_term_schedule_churn_is_suppressed(lead):
    """Measured false positives: showtimes for Aug 8 detected Aug 5 (3 days)
    and Aug 7 detected Aug 5 (2 days). A cinema finalising next week's
    times, not a release."""
    d = (TODAY + timedelta(days=lead)).isoformat()
    alerts, quiet = alertable_showtimes(
        [st(d, "11:00")], scraped_dates={d}, calendar_dates={d},
        evaluated_dates={d}, today=TODAY
    )
    assert alerts == [] and len(quiet) == 1


@pytest.mark.parametrize("lead", [MIN_LEAD_DAYS, MIN_LEAD_DAYS + 1, 30, 129])
def test_showtimes_beyond_the_lead_floor_alert(lead):
    d = (TODAY + timedelta(days=lead)).isoformat()
    alerts, _ = alertable_showtimes(
        [st(d, "11:00")], scraped_dates={d}, calendar_dates={d},
        evaluated_dates={d}, today=TODAY
    )
    assert len(alerts) == 1


def test_unparseable_date_errs_towards_telling_the_user():
    alerts, _ = alertable_showtimes(
        [st("not-a-date")], scraped_dates={"not-a-date"},
        calendar_dates={"not-a-date"}, evaluated_dates={"not-a-date"}, today=TODAY,
    )
    assert len(alerts) == 1, "when in doubt, alert rather than swallow"


# --------------------------------------------------------------------------
# The property that two separate bugs both violated
# --------------------------------------------------------------------------

def test_idempotency_second_identical_pass_alerts_nothing():
    """Run the monitor twice against unchanged input and the second pass must
    be silent. Both the duplicate-alert bug and the backfill bug were
    violations of exactly this."""
    d1, d2 = far(30), far(31)
    scrape = [st(d1, "19:00"), st(d1, "23:00"), st(d2, "19:00")]
    calendar = [d1, d2]

    # pass 1: baseline
    known = merge_known([], scrape, "showtime")
    cal = set(calendar)

    # pass 2: identical input
    new = diff_showtimes([Showtime.from_dict(x) for x in known], scrape)
    alerts, _ = alertable_showtimes(
        new, scraped_dates={x["date"] for x in known}, calendar_dates=cal,
        evaluated_dates=cal, today=TODAY
    )
    assert new == [] and alerts == []


# --------------------------------------------------------------------------
# Owner decisions, pinned so they cannot drift back silently
# --------------------------------------------------------------------------

def test_reddit_mentions_are_muted_but_still_recorded():
    """Owner's standing decision: leading-indicator emails stay OFF, while
    the source keeps running and keeps logging.

    Pinned deliberately. This flag has been flipped twice on evidence, and a
    future change should have to argue with a failing test rather than move
    it in passing. The mute is a product decision, not a bug: a
    pre-announced drop is not what this project is for, and Reddit noise
    degrades the channel that must stay trustworthy for unannounced ones.
    """
    import monitor
    assert monitor.MENTION_ALERTS_ENABLED is False, (
        "leading-indicator emails must stay muted; the source still records to state"
    )
    assert monitor.reddit_rss in monitor.SOURCE_MODULES, (
        "muted means silent, not removed -- the log must keep accumulating"
    )


# --------------------------------------------------------------------------
# staleness: a date we stopped looking at is not news when we look again
# --------------------------------------------------------------------------

def _fresh(dates, minutes_ago=5):
    stamp = (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()
    return {d: stamp for d in dates}


def test_regression_stale_date_rebaselines_silently():
    """The Sept 7-9 Odyssey false positives.

    Sept 18, 19 and 20 were each emailed on the night they drifted back into
    the rescan window, naming times that a live probe confirmed had been on
    sale for weeks. The date was known, evaluated and far out, so every
    existing guard waved it through and the lead-time floor cleared at 11 days.
    """
    d = far(11)
    alerts, quiet = alertable_showtimes(
        [st(d, "14:00")], scraped_dates={d}, calendar_dates={d},
        evaluated_dates={d}, today=TODAY, stale_dates=frozenset({d}),
    )
    assert alerts == [] and len(quiet) == 1


def test_fresh_date_still_alerts():
    """The other half. Suppressing stale dates must not suppress live ones:
    a date we read minutes ago that gains a showtime IS the wave."""
    d = far(11)
    alerts, _ = alertable_showtimes(
        [st(d, "14:00")], scraped_dates={d}, calendar_dates={d},
        evaluated_dates={d}, today=TODAY, stale_dates=frozenset(),
    )
    assert len(alerts) == 1


def test_stale_never_silences_a_brand_new_calendar_date():
    """Staleness is about dates we stopped watching. A date the calendar has
    never offered is new whenever we see it, however long since we looked."""
    d = far(11)
    alerts, _ = alertable_showtimes(
        [st(d, "14:00")], scraped_dates=set(), calendar_dates=set(),
        evaluated_dates=set(), today=TODAY, stale_dates=frozenset({d}),
    )
    assert len(alerts) == 1


@pytest.mark.parametrize("stamp", [None, "", "not-a-timestamp"])
def test_unknown_reading_time_counts_as_stale(stamp):
    """No timestamp means we cannot say when we last looked, and the safe
    reading of that is "too long ago". This is also the migration path."""
    assert dates_gone_stale({"2026-12-18": stamp}) == frozenset({"2026-12-18"})


def test_recent_reading_is_not_stale():
    assert dates_gone_stale(_fresh(["2026-12-18"])) == frozenset()


def test_reading_older_than_the_window_is_stale():
    old = (datetime.now(timezone.utc) - FRESH_WITHIN - timedelta(hours=1)).isoformat()
    assert dates_gone_stale({"2026-12-18": old}) == frozenset({"2026-12-18"})


def test_migration_turns_the_old_list_into_overdue_dates():
    """State written before this change has no reading times, so every date
    loads as stale and the first run absorbs the backlog instead of mailing
    it. That is deliberate: eleven nights of Odyssey catch-up were pending."""
    state = {"sources": {"k::fandango": {"known_evaluated_dates": ["2026-09-18"]}}}
    migrated = migrate_state(state)["sources"]["k::fandango"]["known_evaluated_dates"]
    assert migrated == {"2026-09-18": None}
    assert dates_gone_stale(migrated) == frozenset({"2026-09-18"})


# --------------------------------------------------------------------------
# dates_to_scan: the rotation that stops dates going stale in the first place
# --------------------------------------------------------------------------

def test_rotation_reaches_dates_outside_the_near_term_window():
    """Before the fix these were simply dropped, which is the whole bug."""
    all_dates = [f"2026-09-{d:02d}" for d in range(10, 26)]
    known = set(all_dates)                       # every date already has showtimes
    scanned = dates_to_scan(all_dates, known, read_times={})
    beyond = [d for d in all_dates[NEAR_TERM_RESCAN:] if d in scanned]
    assert beyond, "dates past the near-term window must still be re-read"
    assert len(scanned) == NEAR_TERM_RESCAN + STALE_ROTATION


def test_rotation_takes_the_least_recently_read_first():
    all_dates = [f"2026-09-{d:02d}" for d in range(10, 26)]
    known = set(all_dates)
    read_times = _fresh(all_dates)
    neglected = "2026-09-24"
    read_times[neglected] = "2020-01-01T00:00:00+00:00"
    assert neglected in dates_to_scan(all_dates, known, read_times)


def test_rotation_covers_everything_and_unseen_is_never_skipped():
    all_dates = [f"2026-09-{d:02d}" for d in range(10, 26)]
    known = set(all_dates[:12])                  # last four have no showtimes yet
    read_times = _fresh(all_dates)
    seen, passes = set(), 0
    while not seen.issuperset(all_dates) and passes < 50:
        for d in dates_to_scan(all_dates, known, read_times):
            seen.add(d)
            read_times[d] = datetime.now(timezone.utc).isoformat()
        passes += 1
    assert seen.issuperset(all_dates), "rotation must eventually reach every date"
    for d in all_dates[12:]:
        assert d in dates_to_scan(all_dates, known, read_times), "unseen is never rationed away"


def test_rotation_outruns_the_freshness_gate():
    """FRESH_WITHIN and STALE_ROTATION are coupled: if the rotation cannot get
    round every date inside the freshness window, every date reads as stale
    and the monitor goes permanently silent.

    This bug was born of exactly such a coupling, MIN_LEAD_DAYS against
    NEAR_TERM_RESCAN, which held by luck and had nothing asserting it. Worst
    case here is a full calendar at the slowest cadence we run.
    """
    worst_case_dates = LABEL_CAP - NEAR_TERM_RESCAN
    passes_needed = -(-worst_case_dates // STALE_ROTATION)   # ceil
    time_needed = passes_needed * BASELINE_CADENCE
    assert time_needed * 2 < FRESH_WITHIN, (
        f"rotation needs {time_needed} to cover {worst_case_dates} dates, "
        f"which is not comfortably inside FRESH_WITHIN={FRESH_WITHIN}"
    )


@pytest.mark.parametrize("junk", [None, "", 0])
def test_migration_repairs_a_non_dict_reading_map(junk):
    """The live state carried an explicit null for one reddit source. Left as
    it was it would reach set() inside process_result and raise, and a run
    that raises never reaches save_state, losing everything it found."""
    state = {"sources": {"k::reddit_rss": {"known_evaluated_dates": junk}}}
    assert migrate_state(state)["sources"]["k::reddit_rss"]["known_evaluated_dates"] == {}
