"""Parser tests against REAL captured Fandango pages.

These run offline against tests/fixtures/, so they are deterministic --
unlike every "verification" this project relied on before, which was a
single live run against a site that behaves differently depending on
timing, load and geography. Regenerate with tests/capture_fixtures.py when
the page structure changes.
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "scripts" / "sources"))

import pytest  # noqa: E402

from sources.fandango import (  # noqa: E402
    SF_ZIP_PATTERN, _extract_showtimes, _venue_block,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text())
TARGETS = {t["id"]: t for t in json.loads((REPO / "config" / "targets.json").read_text())}


def body(name: str) -> str:
    return (FIXTURES / f"{name}.txt").read_text()


def target_for(name: str) -> dict:
    return TARGETS[MANIFEST[name]["target_id"]]


@pytest.mark.parametrize("name", sorted(MANIFEST))
def test_every_fixture_resolved_to_san_francisco(name):
    """If the geo cookies stop working the page silently shows another metro,
    and 'no Metreon showtimes' becomes a lie rather than a fact. The scraper
    treats a missing SF ZIP as parse_error for this reason."""
    assert SF_ZIP_PATTERN.search(body(name)), f"{name} did not resolve to a 941xx ZIP"


def test_metreon_showtimes_are_extracted_when_present():
    name = "odyssey_date_with_metreon"
    t = target_for(name)
    found = _extract_showtimes(body(name), t, MANIFEST[name]["selected_date"], "u")
    assert found, "Metreon is on this page; the parser must find its showtimes"
    assert all(s.venue == "AMC Metreon 16" for s in found)
    assert all(s.date == MANIFEST[name]["selected_date"] for s in found)
    assert all(s.format == "IMAX 70mm" for s in found)


def test_regression_no_showtimes_invented_when_metreon_absent():
    """Sep 12-16 were reported with Sep 11's showtimes across two separate
    bugs (stale DOM, then a URL check that passed before the content
    re-rendered). Metreon simply is not playing on this date."""
    name = "odyssey_date_without_metreon"
    t = target_for(name)
    assert _venue_block(body(name), t["venue"]) is None, "fixture should not contain Metreon"
    assert _extract_showtimes(body(name), t, MANIFEST[name]["selected_date"], "u") == []


def test_other_theatres_showtimes_are_not_attributed_to_metreon():
    """The absent-Metreon fixture DOES contain other cinemas' showtimes. The
    venue block must not pick them up -- that is how a phantom would form."""
    name = "odyssey_date_without_metreon"
    text = body(name)
    assert "mi" in text, "fixture should list some theatres"
    assert _extract_showtimes(text, target_for(name), "2026-09-13", "u") == []


def test_dune_event_page_has_no_metreon_right_now():
    """Documents current reality: Fandango does not list Metreon for Dune at
    all (its April allocation is gone), which is why the monitor reports 0
    showtimes for Dune rather than being broken."""
    name = "dune_event_date"
    assert _venue_block(body(name), TARGETS["dune-part-three"]["venue"]) is None
    assert _extract_showtimes(body(name), TARGETS["dune-part-three"], "2026-12-17", "u") == []


def test_dune_calendar_offers_the_four_event_dates():
    """The wave we are waiting for shows up as changes to this list, so the
    calendar must be readable even when no showtimes are."""
    cal = MANIFEST["dune_default_landing"]["calendar_dates"]
    for expected in ("2026-12-17", "2026-12-18", "2026-12-19", "2026-12-20"):
        assert expected in cal, f"{expected} missing from Dune's calendar"


def test_venue_block_stops_at_the_next_theatre():
    """Theatres are listed '<name> <distance> mi <formats> <times>'. Without
    cutting at the next distance marker, a neighbouring cinema's times get
    misattributed."""
    fake = (
        "AMC Metreon 16\n0.4 mi\nIMAX 70mm\n7:00p\n"
        "Some Other Theatre\n5.1 mi\nIMAX 70mm\n9:00p\n"
    )
    blk = _venue_block(fake, "AMC Metreon 16")
    assert "7:00p" in blk and "9:00p" not in blk
