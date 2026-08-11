"""Does this thing actually fire when Dune's wave lands?

Until these existed, that question had no evidence behind it. The Dune path
has never been exercised on a real change -- Fandango does not currently
list Metreon for Dune at all, so every live run has returned 0. Every bug we
found came through The Odyssey.

These simulate the wave against the REAL decision path (process_result, the
same function production calls) with the alert layer captured instead of
sent. What is stubbed is only the network and SMTP; the logic under test is
production code.
"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "scripts" / "sources"))

import pytest  # noqa: E402

import alert as alert_module  # noqa: E402
import monitor  # noqa: E402
from normalize import Showtime, SourceResult  # noqa: E402

DUNE = {t["id"]: t for t in json.loads((REPO / "config" / "targets.json").read_text())}[
    "dune-part-three"
]
WAVE_DATES = ["2026-12-17", "2026-12-18", "2026-12-19", "2026-12-20"]


@pytest.fixture
def sent(monkeypatch):
    """Capture what would have been emailed."""
    box = []
    monkeypatch.setattr(alert_module, "send_ticket_alert",
                        lambda t, r: box.append(("ticket", t, r)))
    monkeypatch.setattr(alert_module, "send_mention_alert",
                        lambda t, r: box.append(("mention", t, r)))
    monkeypatch.setattr(alert_module, "send_blocked_alert",
                        lambda *a, **k: box.append(("blocked",)))
    monkeypatch.setattr(alert_module, "send_broken_alert",
                        lambda *a, **k: box.append(("broken",)))
    return box


def st(d, t):
    return Showtime(date=d, time=t, format="IMAX 70mm",
                    venue="AMC Metreon 16", booking_url=DUNE["fandango_film_url"])


def result(showtimes, calendar, evaluated=None):
    """A healthy pass: every date the calendar offered was successfully read.

    evaluated defaults to the whole calendar because that is what a clean
    scan does -- it visits each date and records what it found, including
    finding nothing. Passing a smaller set models dates that were skipped
    (a failed date-confirm), which is the backfill case."""
    return SourceResult(
        source="fandango", target_id="dune-part-three", status="ok",
        kind="showtime", showtimes=showtimes, calendar_dates=calendar,
        evaluated_dates=list(calendar) if evaluated is None else list(evaluated),
    )


def fresh_state():
    return {"sources": {}, "last_heartbeat_sent": None}


def baseline(state, sent):
    """Today's reality: Fandango offers Dune's four dates but lists no
    Metreon showtimes on them."""
    monitor.process_result(DUNE, result([], WAVE_DATES), state)
    sent.clear()
    return state


# --------------------------------------------------------------------------

def test_wave_on_existing_dates_fires(sent):
    """The most likely shape: Metreon's allocation returns on Dec 17-20."""
    state = baseline(fresh_state(), sent)

    wave = [st(d, t) for d in WAVE_DATES for t in ("19:00", "23:00")]
    monitor.process_result(DUNE, result(wave, WAVE_DATES), state)

    assert len(sent) == 1, "a wave must produce exactly one alert"
    kind, target, res = sent[0]
    assert kind == "ticket"
    assert target["film_name"] == "Dune: Part Three"
    assert len(res.showtimes) == 8
    assert {s.date for s in res.showtimes} == set(WAVE_DATES)


def test_wave_adding_new_dates_fires(sent):
    """A second wave extending into Dec 21-23."""
    state = baseline(fresh_state(), sent)
    extra = ["2026-12-21", "2026-12-22", "2026-12-23"]

    wave = [st(d, "19:00") for d in extra]
    monitor.process_result(DUNE, result(wave, WAVE_DATES + extra), state)

    assert len(sent) == 1
    assert {s.date for s in sent[0][2].showtimes} == set(extra)


def test_wave_adding_a_time_to_a_known_date_fires(sent):
    """The shape a horizon-only rule would have missed: no new date, just a
    3pm added to a date already on sale."""
    state = fresh_state()
    monitor.process_result(DUNE, result([], WAVE_DATES), state)
    monitor.process_result(
        DUNE, result([st(d, "19:00") for d in WAVE_DATES], WAVE_DATES), state)
    sent.clear()

    monitor.process_result(
        DUNE,
        result([st(d, "19:00") for d in WAVE_DATES] + [st("2026-12-18", "15:00")],
               WAVE_DATES),
        state,
    )
    assert len(sent) == 1
    assert [(s.date, s.time) for s in sent[0][2].showtimes] == [("2026-12-18", "15:00")]


def test_the_alert_contains_a_working_booking_url(sent):
    """A summary-only alert is useless at 9am on drop day."""
    state = baseline(fresh_state(), sent)
    monitor.process_result(DUNE, result([st("2026-12-17", "19:00")], WAVE_DATES), state)

    url = sent[0][2].showtimes[0].booking_url
    assert url.startswith("https://www.fandango.com/")
    assert "dune-part-three" in url


def test_wave_still_fires_after_a_blocked_pass(sent):
    """Fandango rate-limits us in bursts. A block immediately before the wave
    must not swallow it."""
    state = baseline(fresh_state(), sent)

    monitor.process_result(
        DUNE,
        SourceResult(source="fandango", target_id="dune-part-three",
                     status="blocked", error="HTTP 403"),
        state,
    )
    sent.clear()

    monitor.process_result(DUNE, result([st("2026-12-17", "19:00")], WAVE_DATES), state)
    assert len(sent) == 1 and sent[0][0] == "ticket"


def test_wave_is_not_re_announced_on_the_next_pass(sent):
    """One alert per wave, not one per pass until December."""
    state = baseline(fresh_state(), sent)
    wave = [st(d, "19:00") for d in WAVE_DATES]

    monitor.process_result(DUNE, result(wave, WAVE_DATES), state)
    assert len(sent) == 1
    sent.clear()

    for _ in range(5):
        monitor.process_result(DUNE, result(wave, WAVE_DATES), state)
    assert sent == [], "an unchanged wave must not re-alert every pass"


def test_a_late_wave_inside_the_lead_floor_still_fires(sent):
    """MIN_LEAD_DAYS suppresses churn on already-scraped dates. A wave that
    lands close to the screening must not be suppressed with it -- so it has
    to arrive as a new date or an unseen date, which is what actually
    happens. This pins the behaviour so a future tweak to the floor cannot
    silently swallow a late drop."""
    state = fresh_state()
    soon = (date.today() + timedelta(days=2)).isoformat()
    monitor.process_result(DUNE, result([], [soon]), state)   # calendar knows it
    sent.clear()

    # brand-new date appearing two days out
    later = (date.today() + timedelta(days=3)).isoformat()
    monitor.process_result(DUNE, result([st(later, "19:00")], [soon, later]), state)
    assert len(sent) == 1, "a newly-offered date must fire regardless of lead time"


def test_nothing_fires_when_nothing_changes(sent):
    state = baseline(fresh_state(), sent)
    for _ in range(3):
        monitor.process_result(DUNE, result([], WAVE_DATES), state)
    assert sent == []
