"""Shared extraction logic for the three Playwright-based sources (AMC
showtimes, AMC film page, Fandango). imax.com is similar enough to reuse
this too. Kept in one place so all four sources are diffed/debugged the
same way, per the "one shared browser-automation module" architecture
decision in the plan.

Extraction strategy, in preference order (per the user's explicit ask to
prefer embedded JSON over CSS selectors):
  1. Any embedded JSON payload on the page (script tags: __NEXT_DATA__,
     application/json, __APOLLO_STATE__) — if the target film's keywords
     appear inside it, treat that as a strong signal and pass the raw JSON
     text into the same proximity-based extractor as step 2 (still more
     stable than the DOM re-rendering, since JSON payload key order/text
     tends to survive small CSS/layout changes).
  2. Rendered page text (page.inner_text("body")) with keyword + nearby
     time + nearby "70mm" proximity matching.

This is a best-effort v1 tuned against real page structure during the
manual dry-run (see RUNBOOK.md); it is deliberately simple/readable rather
than a fully general HTML-scraping framework.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from browser import goto_and_classify, polite_page  # noqa: E402
from normalize import Showtime, SourceResult  # noqa: E402

JSON_BLOB_PATTERN = re.compile(
    r'<script[^>]+(?:id="__NEXT_DATA__"|type="application/json")[^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)

MIN_REAL_PAGE_CHARS = 600  # below this, a page is presumed stuck behind a modal/error, not real content

FORMAT_70MM_PATTERN = re.compile(r"70\s?mm", re.IGNORECASE)
DATE_PATTERN = re.compile(
    r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2})\b",
    re.IGNORECASE,
)
# Matches both "7:00 PM" and Fandango's compact "7:00p" / "10:30a" (no "M",
# single-letter meridiem) — confirmed live on fandango.com/amc-metreon-16
# (2026-07-30) that the full "AM"/"PM" form never appears, only the short one.
TIME_PATTERN = re.compile(r"\b(1[0-2]|0?[1-9]):([0-5][0-9])\s*([AaPp])\.?[Mm]?\b")

MONTHS = {
    m: i + 1
    for i, m in enumerate(
        ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    )
}


def _extract_json_blobs(html: str) -> list[str]:
    return [m.strip() for m in JSON_BLOB_PATTERN.findall(html) if m.strip()]


def _to_24h(hour: str, minute: str, meridiem: str) -> str:
    h = int(hour)
    is_pm = meridiem.lower().startswith("p")
    if is_pm and h != 12:
        h += 12
    if not is_pm and h == 12:
        h = 0
    return f"{h:02d}:{minute}"


def _nearest_date(text: str, pos: int, year_hint: int) -> str | None:
    """Find the closest month/day token to `pos` within a window, return ISO date."""
    window = text[max(0, pos - 200) : pos + 200]
    best = None
    best_dist = None
    center = min(200, pos)
    for match in DATE_PATTERN.finditer(window):
        dist = abs(match.start() - center)
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best = match
    if not best:
        return None
    month = MONTHS.get(best.group(1)[:3].lower())
    day = int(best.group(2))
    if not month:
        return None
    return f"{year_hint:04d}-{month:02d}-{day:02d}"


def extract_showtimes_from_text(
    text: str, target: dict, source_name: str, booking_url: str
) -> list[Showtime]:
    """Proximity-based extraction: for every occurrence of a film keyword,
    look at a window of surrounding text for a "70mm" token and a time
    token. Both must be present for a candidate to count — this is what
    keeps the monitor scoped to 70mm only, per the hard constraint."""
    year_hint = int(target["release_date"][:4])
    lowered = text.lower()
    found: dict[tuple, Showtime] = {}

    for keyword in target["film_keywords"]:
        start = 0
        kw = keyword.lower()
        while True:
            idx = lowered.find(kw, start)
            if idx == -1:
                break
            start = idx + len(kw)
            window = text[max(0, idx - 300) : idx + 300]
            if not FORMAT_70MM_PATTERN.search(window):
                continue
            for time_match in TIME_PATTERN.finditer(window):
                time_str = _to_24h(*time_match.groups())
                date_str = _nearest_date(text, idx, year_hint) or target["release_date"]
                st = Showtime(
                    date=date_str,
                    time=time_str,
                    format=target["format"],
                    venue=target["venue"],
                    booking_url=booking_url,
                )
                found[st.key()] = st

    return list(found.values())


COOKIE_ACCEPT_TEXTS = ["Accept All", "Accept all", "I Accept", "Accept", "I Agree", "Got it"]


def _dismiss_cookie_banner(page) -> None:
    """Best-effort click on a common consent-accept button. Several sites
    (imax.com observed directly) gate their real content behind a consent
    modal — the page 'loads' but the app never renders past it. Failure
    here is silent and non-fatal; extraction just proceeds with whatever
    is on the page either way."""
    for text in COOKIE_ACCEPT_TEXTS:
        try:
            button = page.get_by_text(text, exact=False).first
            if button.is_visible(timeout=1_000):
                button.click(timeout=1_000)
                page.wait_for_timeout(500)
                return
        except Exception:
            continue


def check_rendered_page(
    url: str,
    target: dict,
    source_name: str,
    landmarks: list[str],
    booking_url: str | None = None,
) -> SourceResult:
    """Load `url` in a real browser, verify the page landed somewhere
    recognizable (landmarks), then extract 70mm showtimes for `target`."""
    booking_url = booking_url or url

    with polite_page() as page:
        classification, response = goto_and_classify(page, url)
        if classification == "blocked":
            status_code = response.status if response else "?"
            reason = "403/429 response" if status_code in (403, 429) else "waiting-room/challenge interstitial"
            return SourceResult(
                source=source_name,
                target_id=target["id"],
                status="blocked",
                error=f"HTTP {status_code} — {reason}",
            )
        if classification == "no_data":
            return SourceResult(
                source=source_name, target_id=target["id"], status="no_data", error="navigation failed"
            )

        _dismiss_cookie_banner(page)

        # Let client-rendered pages (Fandango, IMAX) finish hydrating.
        try:
            page.wait_for_load_state("networkidle", timeout=15_000)
        except Exception:
            pass  # best-effort; some sites never go fully idle (polling widgets etc.)

        try:
            html = page.content()
            body_text = page.inner_text("body")
        except Exception as e:
            return SourceResult(
                source=source_name, target_id=target["id"], status="parse_error", error=str(e)
            )

    lowered_body = body_text.lower()
    landmark_hit = any(landmark.lower() in lowered_body for landmark in landmarks)
    # A real movie/theater page has far more text than a bare cookie-consent
    # modal — observed directly on imax.com (2026-07-30): stuck behind a
    # privacy dialog, "imax" still appears in the boilerplate text, but the
    # whole page is under 300 characters and ends in a bare "Error". Without
    # this floor, that state silently reports as "ok, 0 showtimes" —
    # indistinguishable from "genuinely nothing on sale."
    if not landmark_hit or len(body_text) < MIN_REAL_PAGE_CHARS:
        return SourceResult(
            source=source_name,
            target_id=target["id"],
            status="parse_error",
            error=(
                "expected page landmarks not found"
                if not landmark_hit
                else f"page rendered only {len(body_text)} chars — likely stuck behind a modal/error, not real content"
            ),
        )

    # Prefer embedded JSON text if present (per user's stated preference);
    # fall back to the rendered body text either way if JSON yields nothing.
    search_text = body_text
    for blob in _extract_json_blobs(html):
        try:
            json.loads(blob)  # validate it's real JSON before trusting it
        except Exception:
            continue
        search_text = blob + "\n" + body_text
        break

    showtimes = extract_showtimes_from_text(search_text, target, source_name, booking_url)
    return SourceResult(source=source_name, target_id=target["id"], status="ok", showtimes=showtimes)
