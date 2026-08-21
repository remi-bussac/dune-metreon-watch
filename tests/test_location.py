"""Pinning the page to the metro each venue is watched from.

On 2026-08-19 Fandango stopped honouring the location cookies. They were
still sent, still survived the load intact, and the page rendered whatever
metro the IP resolved to regardless. The VM is in San Jose, so every run came
back showing 95101, where AMC Metreon 16 does not appear at all.

The danger is not the failure, it is how quietly it could have gone: a San
Jose page is a perfectly valid page with plenty of showtimes on it, none of
them Metreon's. Read naively that is "nothing on sale" forever. Two things
stop that: the location is set through the page's own control, and if that
does not take, the run is a parse_error rather than an empty result.

Two venues are now watched from two different metros, which raises the stakes
further: Fandango caps its theater list at roughly ten cinemas by distance,
so the ZIP you ask from decides which cinemas appear at all. Regal Hacienda
Crossings sits 29.55 mi from 94102 and drops off the San Francisco page on
busy dates, which is why it is asked for from 94568 rather than sharing SF's.

These tests drive a stub page, so they cover the decision logic without a
browser. The interaction itself was verified live on the VM (95101 -> 94102,
after which the theater list matched a residential SF connection exactly) and
again from a laptop for 10001 and 94568.
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "scripts" / "sources"))

from sources.fandango import (  # noqa: E402
    DEFAULT_ZIP, LOCATION_BUTTON_SELECTOR, LOCATION_INPUT_SELECTOR,
    _ensure_metro, _page_zip,
)


class FakeLocator:
    def __init__(self, page, selector):
        self.page, self.selector = page, selector
        self.first = self

    def click(self, timeout=None):
        self.page.actions.append(("click", self.selector))
        if self.selector in self.page.broken:
            raise RuntimeError("element not found")

    def fill(self, value):
        self.page.actions.append(("fill", value))
        if self.selector in self.page.broken:
            raise RuntimeError("element not found")

    def press(self, key):
        self.page.actions.append(("press", key))
        # Typing the ZIP and hitting Enter is what re-renders the metro.
        if self.page.zip_after_enter is not None:
            self.page.zip_now = self.page.zip_after_enter


class FakePage:
    """Just enough of a Playwright page for the location logic."""

    def __init__(self, zip_now, zip_after_enter=None, broken=()):
        self.zip_now = zip_now
        self.zip_after_enter = zip_after_enter
        self.broken = set(broken)
        self.actions = []

    def inner_text(self, _selector):
        return f"Movies\nTheaters\n\nTHEATERS NEAR\n\n{self.zip_now}\nCalendar for movie times."

    def locator(self, selector):
        return FakeLocator(self, selector)

    def wait_for_timeout(self, _ms):
        pass


def test_reads_the_zip_the_page_is_showing():
    assert _page_zip(FakePage("95101")) == "95101"
    assert _page_zip(FakePage("94102")) == "94102"


def test_already_in_san_francisco_touches_nothing():
    """The normal case from a Bay Area connection. Interacting anyway would
    spend a click every run for no reason."""
    page = FakePage("94102")
    assert _ensure_metro(page, DEFAULT_ZIP) is True
    assert page.actions == [], "must not touch the location control when already correct"


def test_a_neighbouring_zip_is_not_close_enough():
    """94103 is San Francisco and would once have passed, because the old
    guard accepted the whole 941xx range. It no longer does.

    Two venues are now watched from two metros, and Fandango caps its
    theater list at roughly ten cinemas by distance, so the ZIP you ask from
    decides who makes the cut. Regal Hacienda Crossings is 29.55 mi from
    94102 and falls off the SF page on busy dates. Approximately right is
    therefore not right."""
    page = FakePage("94103", zip_after_enter=DEFAULT_ZIP)
    assert _ensure_metro(page, DEFAULT_ZIP) is True
    assert page.actions, "a near-miss ZIP must still be corrected, not accepted"


def test_dublin_is_pinned_to_its_own_metro():
    """The second venue. Asking from San Francisco would sometimes work and
    sometimes silently drop Regal Hacienda Crossings off the page, which is
    the worst kind of failure: intermittent and quiet."""
    page = FakePage("94102", zip_after_enter="94568")
    assert _ensure_metro(page, "94568") is True
    assert page.actions == [
        ("click", LOCATION_BUTTON_SELECTOR),
        ("fill", "94568"),
        ("press", "Enter"),
    ]


def test_each_target_can_ask_from_a_different_metro():
    """Nothing in the logic is San Francisco specific any more."""
    for zip_code in ("94102", "94568", "10001"):
        page = FakePage("95101", zip_after_enter=zip_code)
        assert _ensure_metro(page, zip_code) is True
        assert ("fill", zip_code) in page.actions


def test_wrong_metro_is_corrected_through_the_page_control():
    """The San Jose case, which is what the VM actually sees."""
    page = FakePage("95101", zip_after_enter="94102")
    assert _ensure_metro(page, DEFAULT_ZIP) is True
    assert page.actions == [
        ("click", LOCATION_BUTTON_SELECTOR),
        ("fill", DEFAULT_ZIP),
        ("press", "Enter"),
    ]


def test_returns_false_when_the_metro_does_not_change():
    """The control was there and did nothing. Callers must treat this as a
    broken monitor, never as an empty result."""
    page = FakePage("95101", zip_after_enter="95101")
    assert _ensure_metro(page, DEFAULT_ZIP) is False


def test_returns_false_when_the_control_is_missing():
    """Fandango redesigns the page and the overlay button moves. Fail loudly
    rather than scraping San Jose and calling it San Francisco."""
    page = FakePage("95101", broken=[LOCATION_BUTTON_SELECTOR])
    assert _ensure_metro(page, DEFAULT_ZIP) is False


def test_returns_false_when_the_input_is_missing():
    page = FakePage("95101", zip_after_enter="94102", broken=[LOCATION_INPUT_SELECTOR])
    assert _ensure_metro(page, DEFAULT_ZIP) is False


def test_no_zip_on_page_at_all_is_a_failure_not_a_pass():
    """A page with no 'THEATERS NEAR' block proves nothing about location, so
    it must not be waved through."""
    page = FakePage("", zip_after_enter="")
    assert _ensure_metro(page, DEFAULT_ZIP) is False


# --------------------------------------------------------------------------
# Target configuration: the two venues, and who polls what
# --------------------------------------------------------------------------

def test_the_configured_targets_are_coherent():
    """Guards the config itself, which is now the thing most likely to be
    edited by hand at speed while a wave is happening."""
    import json
    targets = json.loads((REPO / "config" / "targets.json").read_text())
    by_id = {t["id"]: t for t in targets}

    active = [t for t in targets if t.get("active", True)]
    assert {t["id"] for t in active} == {
        "dune-part-three", "dune-part-three-dublin", "the-odyssey",
    }, "all three targets are watched"

    # The Odyssey stays on. It was proposed for retirement on 2026-08-21 as
    # its 70mm run winds down and the owner said keep it, so this is a
    # decision pinned rather than an accident waiting to be tidied away.
    assert by_id["the-odyssey"]["active"] is True

    # Dublin is asked for from its own metro. Sharing San Francisco's is what
    # silently drops it off Fandango's distance-capped theater list, and that
    # is the failure this assertion exists to catch.
    assert by_id["dune-part-three-dublin"]["zip"] == "94568"
    assert by_id["dune-part-three"]["zip"] == "94102"
    assert by_id["dune-part-three-dublin"]["zip"] != by_id["dune-part-three"]["zip"]

    # Two venues playing the same film in the same format, plus one other
    # film at Metreon. Every target names a metro and a format.
    assert all(t.get("zip") for t in active), "a target with no ZIP cannot be trusted"
    assert {t["format"] for t in active} == {"IMAX 70mm"}
    assert by_id["dune-part-three-dublin"]["venue"] == "Regal Hacienda Crossings"


def test_dublin_does_not_duplicate_the_reddit_feed():
    """Both Dune targets are the same film, so polling Reddit twice records
    the same mentions twice for a source whose alerts are muted anyway."""
    import json, sys as _sys
    _sys.path.insert(0, str(REPO / "scripts"))
    from monitor import modules_for
    targets = {t["id"]: t for t in json.loads((REPO / "config" / "targets.json").read_text())}

    sf = [m.SOURCE_NAME for m in modules_for(targets["dune-part-three"])]
    dublin = [m.SOURCE_NAME for m in modules_for(targets["dune-part-three-dublin"])]
    assert "fandango" in sf and "reddit_rss" in sf, "the primary target keeps everything"
    assert dublin == ["fandango"], "the second venue only needs showtimes"


def test_a_target_with_no_source_list_gets_everything():
    """Default must stay 'all sources', so omitting the key is never a quiet
    way to stop watching something."""
    import sys as _sys
    _sys.path.insert(0, str(REPO / "scripts"))
    from monitor import modules_for, SOURCE_MODULES
    assert modules_for({"id": "x"}) == SOURCE_MODULES
