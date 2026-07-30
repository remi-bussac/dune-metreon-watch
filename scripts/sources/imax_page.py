"""imax.com's film page — lists venue/format availability. Plain HTTP fetch
403'd during research recon, so this goes through the same Playwright path
as the AMC sources."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _common import check_rendered_page  # noqa: E402
from normalize import SourceResult  # noqa: E402

SOURCE_NAME = "imax_page"
LANDMARKS = ["imax"]


def check(target: dict) -> SourceResult:
    return check_rendered_page(
        url=target["imax_url"],
        target=target,
        source_name=SOURCE_NAME,
        landmarks=LANDMARKS,
        booking_url=target["imax_url"],
    )
