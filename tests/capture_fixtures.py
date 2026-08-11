"""Capture real Fandango page states as fixtures, so the parser can be
tested offline and deterministically.

Run manually when the page structure changes:
    .venv/bin/python tests/capture_fixtures.py

This hits the network on purpose -- it is the one place that does. Every
other test reads what this wrote. The point is that the tricky cases
(a date with no Metreon showtimes, a date with them, Dune's event dates)
stop depending on what the live site happens to be doing today.
"""

import json
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "scripts" / "sources"))

from browser import goto_and_classify, polite_page  # noqa: E402
from sources._common import _dismiss_cookie_banner  # noqa: E402
from sources.fandango import (  # noqa: E402
    SF_LOCATION_COOKIES, DATE_BUTTON_SELECTOR,
    DATE_CONFIRM_POLL_MS, DATE_CONFIRM_TIMEOUT_MS, _content_state,
)

OUT = Path(__file__).resolve().parent / "fixtures"
OUT.mkdir(exist_ok=True)

# (fixture name, target id, date to select, what it is meant to demonstrate)
WANTED = [
    ("odyssey_date_with_metreon",    "the-odyssey",     "2026-09-11", "venue present"),
    ("odyssey_date_without_metreon", "the-odyssey",     "2026-09-13", "venue absent"),
    ("dune_event_date",              "dune-part-three", "2026-12-17", "event booking"),
    ("dune_default_landing",         "dune-part-three", None,         "no date selected"),
]


def main() -> None:
    targets = {t["id"]: t for t in json.loads((REPO / "config" / "targets.json").read_text())}
    today = date.today()
    manifest = {}

    for name, target_id, want_date, note in WANTED:
        target = targets[target_id]
        with polite_page() as page:
            page.context.add_cookies(
                [dict(c, domain=".fandango.com", path="/") for c in SF_LOCATION_COOKIES]
            )
            goto_and_classify(page, target["fandango_film_url"])
            _dismiss_cookie_banner(page)
            try:
                page.wait_for_load_state("networkidle", timeout=15_000)
            except Exception:
                pass
            page.wait_for_timeout(2_500)

            if want_date:
                sel = f'{DATE_BUTTON_SELECTOR}[data-show-time-date="{want_date}"]'
                if not page.locator(sel).count():
                    print(f"  SKIP {name}: no button for {want_date} (calendar moved on)")
                    continue
                page.locator(sel).first.scroll_into_view_if_needed(timeout=3_000)
                page.locator(sel).first.click(timeout=5_000)
                waited = 0
                while waited < DATE_CONFIRM_TIMEOUT_MS:
                    page.wait_for_timeout(DATE_CONFIRM_POLL_MS)
                    waited += DATE_CONFIRM_POLL_MS
                    if _content_state(page, want_date) in ("ready", "empty"):
                        break
                page.wait_for_timeout(800)

            body = page.inner_text("body")
            rendered = page.eval_on_selector_all(
                "[data-showtime-date]",
                "els => els.map(e => e.getAttribute('data-showtime-date'))",
            )
            buttons = page.locator(DATE_BUTTON_SELECTOR)
            cal = [
                buttons.nth(i).get_attribute("data-show-time-date")
                for i in range(buttons.count())
            ]

        (OUT / f"{name}.txt").write_text(body)
        manifest[name] = {
            "target_id": target_id,
            "selected_date": want_date,
            "captured_on": today.isoformat(),
            "note": note,
            "rendered_showtime_dates": sorted(set(d for d in rendered if d)),
            "calendar_dates": [c for c in cal if c],
        }
        print(f"  saved {name}.txt  ({len(body)} chars, {len(set(rendered))} rendered date(s))")

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"\nwrote {len(manifest)} fixtures to {OUT}")


if __name__ == "__main__":
    main()
