"""AMC Metreon 16 theatre page, filtered to the target film. This is the
primary source — it's the actual page the user will click "buy" from."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _common import check_rendered_page  # noqa: E402
from normalize import SourceResult  # noqa: E402

SOURCE_NAME = "amc_showtimes"
LANDMARKS = ["metreon", "amc"]


def check(target: dict) -> SourceResult:
    return check_rendered_page(
        url=target["amc_theatre_url"],
        target=target,
        source_name=SOURCE_NAME,
        landmarks=LANDMARKS,
        booking_url=target["amc_theatre_url"],
    )
