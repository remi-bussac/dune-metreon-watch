"""Shared Playwright helper. One browser context config used by every
source module that needs real rendering (AMC, IMAX, Fandango) so bot-facing
behavior (UA, viewport, locale) is consistent and defined in exactly one
place.

Contact info is embedded in the UA per the "polite scraping" requirement —
real UA, honest rate (cron controls that, not this file), no parallel
hammering (each source is a single page load, no retries in a loop).
"""

from __future__ import annotations

from contextlib import contextmanager

from playwright.sync_api import sync_playwright, Page, Response

CONTACT = "personal ticket-availability monitor; contact remi.bussac@gmail.com"

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

# A real, current desktop Chrome UA. Confirmed by live testing (2026-07-30)
# that Playwright's default headless fingerprint gets a flat 403 from AMC,
# while this UA + disabling the automation flag + hiding navigator.webdriver
# gets through to real content on Fandango and (usually) imax.com. AMC still
# routes through a site-wide Queue-it wall regardless — see RUNBOOK.md for
# what that means operationally.
REALISTIC_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)


# Downtown San Francisco. Fandango resolves the browser's geolocation to a
# nearby ZIP and shows "theaters near" that ZIP — without this the runner's
# own IP decides, which puts you in the wrong metro entirely (a local test
# from a Bay Area ISP still resolved to 95050 / Santa Clara, with no Metreon
# in the results). Setting it explicitly is what makes the Fandango film-page
# source return AMC Metreon 16 at all. Verified 2026-07-31: overriding these
# coords flipped the page from 95050 to 94102 and surfaced Metreon.
SF_GEOLOCATION = {"latitude": 37.7853, "longitude": -122.4056}


@contextmanager
def polite_page():
    """Yields a single Playwright page configured to look like a real
    Chrome browser in San Francisco rather than bare automation. One page
    per call, closed on exit — no shared/reused browser state across
    sources."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="en-US",
            timezone_id="America/Los_Angeles",
            user_agent=REALISTIC_UA,
            geolocation=SF_GEOLOCATION,
            permissions=["geolocation"],
        )
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        try:
            yield page
        finally:
            context.close()
            browser.close()


def goto_and_classify(page: Page, url: str, timeout_ms: int = 30_000) -> tuple[str, Response | None]:
    """Navigate once, no retries. Returns (classification, response) where
    classification is one of: "ok", "blocked", "no_data" (network/timeout
    failure, distinct from a real block)."""
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
