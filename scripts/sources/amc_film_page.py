"""AMC's film detail page (Metreon set as the relevant theatre in the page's
own theatre picker, where the site supports it). Deliberately redundant with
amc_showtimes.py's theatre-page approach — if AMC restructures one page
without touching the other, this source keeps the monitor alive."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _common import check_rendered_page  # noqa: E402
from normalize import SourceResult  # noqa: E402

SOURCE_NAME = "amc_film_page"
LANDMARKS = ["amc"]


def check(target: dict) -> SourceResult:
    return check_rendered_page(
        url=target["amc_film_url"],
        target=target,
        source_name=SOURCE_NAME,
        landmarks=LANDMARKS,
        booking_url=target["amc_film_url"],
    )
