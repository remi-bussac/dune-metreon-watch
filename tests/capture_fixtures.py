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
    CARD_SCRAPE_JS, DEFAULT_ZIP, DATE_BUTTON_SELECTOR, _click_date, _ensure_metro,
)

OUT = Path(__file__).resolve().parent / "fixtures"
OUT.mkdir(exist_ok=True)

# (fixture name, target id, date to select, what it is meant to demonstrate)
WANTED = [
    ("odyssey_date_with_metreon",    "the-odyssey",     "2026-09-11", "venue present"),
    ("odyssey_date_without_metreon", "the-odyssey",     "2026-09-13", "venue absent"),
    ("dune_event_date",              "dune-part-three", "2026-12-17", "event booking"),
    ("dune_default_landing",         "dune-part-three", None,         "no date selected"),
    # The three states a date can be in, captured from the real page the day
    # after the 2026-08-18 on-sale. These are what the availability tests
    # run against, and dune_locked_only is the false alert itself, frozen.
    ("dune_on_sale_mixed",  "dune-part-three", "2026-12-18", "on sale, one time sold out"),
    ("dune_on_sale_all",    "dune-part-three", "2026-12-20", "on sale, nothing sold out"),
    ("dune_locked_only",    "dune-part-three", "2027-01-08", "listed but never released"),
]


def main() -> None:
    targets = {t["id"]: t for t in json.loads((REPO / "config" / "targets.json").read_text())}
    today = date.today()
    # Merge, never replace. A date that has rolled out of the calendar is
    # SKIPped below, and rewriting the manifest from scratch would then
    # silently delete a fixture that tests still depend on, turning a stale
    # capture into a collapsed test suite.
    manifest_path = OUT / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    for name, target_id, want_date, note in WANTED:
        target = targets[target_id]
        with polite_page() as page:
            goto_and_classify(page, target["fandango_film_url"])
            _dismiss_cookie_banner(page)
            try:
                page.wait_for_load_state("networkidle", timeout=15_000)
            except Exception:
                pass
            page.wait_for_timeout(2_500)

            # Fixtures must be captured from the metro the target is watched
            # from, or they record another city's cinemas.
            if not _ensure_metro(page, target.get("zip", DEFAULT_ZIP)):
                print(f"  SKIP {name}: could not pin the page to {target.get('zip', DEFAULT_ZIP)}")
                continue

            if want_date:
                sel = f'{DATE_BUTTON_SELECTOR}[data-show-time-date="{want_date}"]'
                if not page.locator(sel).count():
                    print(f"  SKIP {name}: no button for {want_date} (calendar moved on)")
                    continue
                # Use the monitor's own confirmed click, and believe its
                # answer. Rolling this by hand here captured 2026-12-22 while
                # the page was still showing 2026-12-15, and wrote it out as
                # a Dec 22 fixture: a test built on that would have asserted
                # against the wrong day forever. If the click cannot be
                # confirmed, there is no fixture, which is the honest result.
                if not _click_date(page, want_date, today):
                    print(f"  SKIP {name}: page never confirmed it switched to {want_date}")
                    continue
                page.wait_for_timeout(800)

            body = page.inner_text("body")
            # The structure the parser actually reads. Saved alongside the
            # text so a fixture records both what a person would have seen
            # and what the machine did.
            cards = page.evaluate(CARD_SCRAPE_JS)
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
        (OUT / f"{name}.cards.json").write_text(json.dumps(cards, indent=2) + "\n")
        manifest[name] = {
            "target_id": target_id,
            "selected_date": want_date,
            "captured_on": today.isoformat(),
            "note": note,
            "rendered_showtime_dates": sorted(set(d for d in rendered if d)),
            "calendar_dates": [c for c in cal if c],
        }
        buyable = sum(
            1 for c in cards for g in c["groups"] for s in g["showtimes"] if s["available"]
        )
        locked = sum(
            1 for c in cards for g in c["groups"] for s in g["showtimes"] if not s["available"]
        )
        print(
            f"  saved {name}  ({len(body)} chars, {len(cards)} theater card(s), "
            f"{buyable} buyable / {locked} locked across all venues)"
        )

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"\nwrote {len(manifest)} fixtures to {OUT}")


if __name__ == "__main__":
    main()
