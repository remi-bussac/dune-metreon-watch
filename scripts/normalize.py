"""Shared showtime schema and diff logic.

Every source module (scripts/sources/*.py) returns a SourceResult. monitor.py
diffs each result's showtimes against state/state.json to decide whether a
new showtime appeared, and updates state accordingly. Keeping this in one
small module means every source is compared the same way, and the diff logic
is unit-testable without touching a browser.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

Status = Literal["ok", "no_data", "blocked", "parse_error"]


@dataclass(frozen=True)
class Showtime:
    date: str  # ISO date, e.g. "2026-12-18"
    time: str  # 24h local time, e.g. "19:00"
    format: str  # e.g. "IMAX 70mm"
    venue: str  # e.g. "AMC Metreon 16"
    booking_url: str

    def key(self) -> tuple:
        return (self.date, self.time, self.format, self.venue)

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "time": self.time,
            "format": self.format,
            "venue": self.venue,
            "booking_url": self.booking_url,
        }

    @staticmethod
    def from_dict(d: dict) -> "Showtime":
        return Showtime(
            date=d["date"],
            time=d["time"],
            format=d["format"],
            venue=d["venue"],
            booking_url=d["booking_url"],
        )


Kind = Literal["showtime", "mention"]


@dataclass
class SourceResult:
    source: str  # e.g. "amc_showtimes"
    target_id: str  # e.g. "dune-part-three"
    status: Status
    # "showtime": a real bookable showtime was found (AMC/IMAX/Fandango) —
    # triggers the urgent ticket alert. "mention": a Reddit post matched
    # keywords — a leading indicator, not confirmation of an on-sale, so it
    # gets a distinctly-labeled, lower-certainty alert.
    kind: Kind = "showtime"
    showtimes: list[Showtime] = field(default_factory=list)
    error: str | None = None
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target_id": self.target_id,
            "status": self.status,
            "kind": self.kind,
            "showtimes": [s.to_dict() for s in self.showtimes],
            "error": self.error,
            "checked_at": self.checked_at,
        }


def state_key(target_id: str, source: str) -> str:
    return f"{target_id}::{source}"


def diff_showtimes(known: list[Showtime], current: list[Showtime]) -> list[Showtime]:
    """Return showtimes present in `current` but not in `known`."""
    known_keys = {s.key() for s in known}
    return [s for s in current if s.key() not in known_keys]
