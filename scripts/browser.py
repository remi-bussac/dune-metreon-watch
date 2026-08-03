"""Shared Playwright helper.

The browser identifies itself honestly. Earlier versions of this file
spoofed a real Chrome user-agent, passed
--disable-blink-features=AutomationControlled, and overrode
navigator.webdriver. All of that existed for one reason: trying to get past
AMC's Cloudflare/Queue-it wall. It never worked from a CI runner, and it is
not needed by any source that does work — verified 2026-08-02 that the
Fandango source returns byte-identical results with every one of those
tricks removed, because its San Francisco location comes from ordinary
cookies rather than from looking like a human.

So the tricks are gone. What is left reads two public pages, says who it is,
and stops when told no.
"""

from __future__ import annotations

from contextlib import contextmanager

from playwright.sync_api import sync_playwright, Page, Response

# Self-identifying: names the tool and points at the repo, so anyone looking
# at their logs can see exactly what this is and how to contact the owner.
USER_AGENT = (
    "Mozilla/5.0 (compatible; DuneMetreonWatch/1.0; "
    "+https://github.com/remi-bussac/dune-metreon-watch)"
)

# Downtown San Francisco. Not a disguise -- the thing being monitored is a
# San Francisco cinema, so this is simply the correct location to ask about.
SF_GEOLOCATION = {"latitude": 37.7853, "longitude": -122.4056}

QUEUE_IT_MARKERS = (
    "queue-it",
    "you are now in line",
    "global safety net",
)

CHALLENGE_MARKERS = (
    "just a moment",
    "performing security verification",
    "checking your browser",
)


@contextmanager
def polite_page():
    """Yields a single Playwright page. One page per call, closed on exit —
    no shared/reused browser state across sources."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="en-US",
            timezone_id="America/Los_Angeles",
            user_agent=USER_AGENT,
            geolocation=SF_GEOLOCATION,
            permissions=["geolocation"],
        )
        page = context.new_page()
        try:
            yield page
        finally:
            context.close()
            browser.close()


def goto_and_classify(page: Page, url: str, timeout_ms: int = 30_000) -> tuple[str, Response | None]:
    """Navigate once, no retries. Returns (classification, response) where
    classification is one of: "ok", "blocked", "no_data" (network/timeout
    failure, distinct from a real block).

    Detecting a block is the point here — a site that says no gets taken at
    its word and reported as blocked, never worked around."""
    try:
        response = page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
    except Exception:
        return "no_data", None

    if response is None:
        return "no_data", None

    if response.status in (403, 429):
        return "blocked", response

    body_sample = ""
    try:
        body_sample = page.content()[:20_000].lower()
    except Exception:
        pass
    if any(marker in body_sample for marker in QUEUE_IT_MARKERS):
        return "blocked", response
    if any(marker in body_sample for marker in CHALLENGE_MARKERS):
        return "blocked", response

    return "ok", response
