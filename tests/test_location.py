"""Pinning the page to San Francisco.

On 2026-08-19 Fandango stopped honouring the location cookies. They are still
sent, still survive the load intact, and the page renders whatever metro the
IP resolves to regardless. The VM is in San Jose, so every run came back
showing 95101, where AMC Metreon 16 does not appear at all.

The danger is not the failure, it is how quietly it could have gone: a San
Jose page is a perfectly valid page with plenty of showtimes on it, none of
them Metreon's. Read naively that is "nothing on sale" forever. Two things
stop that: the location is set through the page's own control, and if that
does not take, the run is a parse_error rather than an empty result.

These tests drive a stub page, so they cover the decision logic without a
browser. The interaction itself was verified live on the VM (95101 -> 94102,
after which the theater list matched a residential SF connection exactly).
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "scripts" / "sources"))

from sources.fandango import (  # noqa: E402
    LOCATION_BUTTON_SELECTOR, LOCATION_INPUT_SELECTOR, SF_ZIP,
    _ensure_san_francisco, _page_zip,
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
    assert _ensure_san_francisco(page) is True
    assert page.actions == [], "must not touch the location control when already correct"


def test_any_941xx_counts_as_san_francisco():
    """The guard accepts the whole 941xx range, so a neighbouring SF ZIP is
    not worth a round trip to force to 94102 exactly."""
    page = FakePage("94103")
    assert _ensure_san_francisco(page) is True
    assert page.actions == []


def test_wrong_metro_is_corrected_through_the_page_control():
    """The San Jose case, which is what the VM actually sees."""
    page = FakePage("95101", zip_after_enter="94102")
    assert _ensure_san_francisco(page) is True
    assert page.actions == [
        ("click", LOCATION_BUTTON_SELECTOR),
        ("fill", SF_ZIP),
        ("press", "Enter"),
    ]


def test_returns_false_when_the_metro_does_not_change():
    """The control was there and did nothing. Callers must treat this as a
    broken monitor, never as an empty result."""
    page = FakePage("95101", zip_after_enter="95101")
    assert _ensure_san_francisco(page) is False


def test_returns_false_when_the_control_is_missing():
    """Fandango redesigns the page and the overlay button moves. Fail loudly
    rather than scraping San Jose and calling it San Francisco."""
    page = FakePage("95101", broken=[LOCATION_BUTTON_SELECTOR])
    assert _ensure_san_francisco(page) is False


def test_returns_false_when_the_input_is_missing():
    page = FakePage("95101", zip_after_enter="94102", broken=[LOCATION_INPUT_SELECTOR])
    assert _ensure_san_francisco(page) is False


def test_no_zip_on_page_at_all_is_a_failure_not_a_pass():
    """A page with no 'THEATERS NEAR' block proves nothing about location, so
    it must not be waved through."""
    page = FakePage("", zip_after_enter="")
    assert _ensure_san_francisco(page) is False
