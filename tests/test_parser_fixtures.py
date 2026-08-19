"""Parser tests against REAL captured Fandango pages.

These run offline against tests/fixtures/, so they are deterministic --
unlike every "verification" this project relied on before, which was a
single live run against a site that behaves differently depending on
timing, load and geography. Regenerate with tests/capture_fixtures.py when
the page structure changes.

Each fixture is two files: <name>.txt is the rendered text, still used for
the things that really are text (the ZIP guard), and <name>.cards.json is
the structure the parser reads. Availability lives in the structure alone,
which is why it has its own suite in test_availability.py.
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "scripts" / "sources"))

import pytest  # noqa: E402

from sources.fandango import SF_ZIP_PATTERN, showtimes_from_cards  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text())
TARGETS = {t["id"]: t for t in json.loads((REPO / "config" / "targets.json").read_text())}


def body(name: str) -> str:
    return (FIXTURES / f"{name}.txt").read_text()


def cards(name: str) -> list[dict]:
    return json.loads((FIXTURES / f"{name}.cards.json").read_text())


def target_for(name: str) -> dict:
    return TARGETS[MANIFEST[name]["target_id"]]


def parse(name: str):
    return showtimes_from_cards(cards(name), target_for(name), MANIFEST[name]["selected_date"])


@pytest.mark.parametrize("name", sorted(MANIFEST))
def test_every_fixture_resolved_to_san_francisco(name):
    """If the geo cookies stop working the page silently shows another metro,
    and 'no Metreon showtimes' becomes a lie rather than a fact. The scraper
    treats a missing SF ZIP as parse_error for this reason."""
    assert SF_ZIP_PATTERN.search(body(name)), f"{name} did not resolve to a 941xx ZIP"


def test_metreon_showtimes_are_extracted_when_present():
    name = "odyssey_date_with_metreon"
    found, _ = parse(name)
    assert found, "Metreon is on this page; the parser must find its showtimes"
    assert all(s.venue == "AMC Metreon 16" for s in found)
    assert all(s.date == MANIFEST[name]["selected_date"] for s in found)
    assert all(s.format == "IMAX 70mm" for s in found)


def test_regression_no_showtimes_invented_when_metreon_absent():
    """Sep 12-16 were reported with Sep 11's showtimes across two separate
    bugs (stale DOM, then a URL check that passed before the content
    re-rendered). Metreon simply is not playing on this date."""
    name = "odyssey_date_without_metreon"
    assert not any("Metreon" in c["theater"] for c in cards(name)), "fixture should lack Metreon"
    assert parse(name) == ([], [])


def test_other_theatres_showtimes_are_not_attributed_to_metreon():
    """Both fixtures carry Regal Hacienda Crossings, which plays the same
    film in the same 70mm format ten minutes off Metreon's times. It is the
    single most confusable thing on the page, so it is the test: a phantom
    would show up as 10:10 sitting next to Metreon's 10:00."""
    with_metreon, _ = parse("odyssey_date_with_metreon")
    assert sorted(s.time for s in with_metreon) == ["10:00", "14:00", "18:00", "22:00"]
    assert not any(s.time.endswith(":10") for s in with_metreon), "Regal's times leaked in"

    without_metreon, _ = parse("odyssey_date_without_metreon")
    assert any("Regal" in c["theater"] for c in cards("odyssey_date_without_metreon"))
    assert without_metreon == [], "Regal alone on the page must yield nothing for Metreon"


def test_dune_event_date_lists_metreon_but_sells_nothing():
    """Reality as of 2026-08-19, and a correction to what this file used to
    assert. Metreon is no longer absent from Dune's page: after the Aug 18
    on-sale it lists Dec 17's two shows, both sold out. "Listed" and "on
    sale" are now different things, and only the second is news."""
    name = "dune_event_date"
    assert any("Metreon" in c["theater"] for c in cards(name)), "Metreon is back on the page"
    available, unbuyable = parse(name)
    assert available == [], "Dec 17 previews are gone, so there is nothing to alert"
    assert sorted(s.time for s in unbuyable) == ["19:00", "23:00"]


def test_dune_calendar_covers_the_released_and_unreleased_stretch():
    """The wave we are waiting for shows up as changes to this list, so the
    calendar must be readable even when no showtimes are. Dec 18-26 is what
    went on sale on Aug 18; everything past it is published and locked, and
    is the next thing to open."""
    cal = MANIFEST["dune_default_landing"]["calendar_dates"]
    for expected in ("2026-12-18", "2026-12-26", "2026-12-27", "2027-01-14"):
        assert expected in cal, f"{expected} missing from Dune's calendar"


def test_venue_matching_does_not_bleed_between_cards():
    """Replaces a test of the old prose-slicing parser, which cut the page
    between "29.55 mi" distance markers and could run one theater's block
    into the next. Cards cannot bleed, and this is what pins that."""
    two = [
        {"theater": "AMC Metreon 16", "groups": [{
            "amenities": "IMAX® 70MM Film",
            "showtimes": [{"label": "7:00p", "available": False, "href": ""}]}]},
        {"theater": "Some Other Theatre", "groups": [{
            "amenities": "IMAX® 70MM Film",
            "showtimes": [{"label": "9:00p", "available": False, "href": ""}]}]},
    ]
    _, unbuyable = showtimes_from_cards(two, TARGETS["dune-part-three"], "2026-12-18")
    assert [s.time for s in unbuyable] == ["19:00"]
