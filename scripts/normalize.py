"""Shared showtime schema and diff logic.

Every source module (scripts/sources/*.py) returns a SourceResult. monitor.py
diffs each result's showtimes against state/state.json to decide whether a
new showtime appeared, and updates state accordingly. Keeping this in one
small module means every source is compared the same way, and the diff logic
is unit-testable without touching a browser.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Literal
from zoneinfo import ZoneInfo

# Every date this system handles is a cinema-local date: Fandango's calendar
# buttons, the showtimes themselves, the "is it in the past" cutoff, the
# lead-time arithmetic. So "today" must mean today AT THE VENUE, never on
# whatever machine happens to be running.
#
# Reading date.today() worked by accident while this ran on a laptop in PDT
# and broke the day it moved to a UTC VM: from 17:00 Pacific onward the host
# was already on tomorrow's date, so merge_known pruned the CURRENT Pacific
# day's showtimes as "past", the next scrape re-found them, and they looked
# brand new. Three identical alerts landed 16 minutes apart on 2026-08-11
# before this was caught. In December (PST) the broken window is 8 hours.
VENUE_TZ = ZoneInfo("America/Los_Angeles")


def venue_today() -> date:
    """Today's date at the cinema, independent of the host's timezone."""
    return datetime.now(VENUE_TZ).date()

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
    # Every date the source's calendar OFFERED this run, whether or not we
    # managed to read its showtimes. Reading these costs nothing (they are
    # button labels, no clicks), and they are what lets monitor.py tell
    # "the calendar gained a date" from "we finally read a date it already
    # had" -- the distinction the Aug 25 false alert turned on.
    calendar_dates: list[str] = field(default_factory=list)
    # Dates we actually managed to READ this pass (confirmed + parsed),
    # whether or not they held showtimes for our venue. The difference
    # between "we checked and it was empty" and "we never managed to check"
    # is what separates a real release from a backfill.
    evaluated_dates: list[str] = field(default_factory=list)
    error: str | None = None
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target_id": self.target_id,
            "status": self.status,
            "kind": self.kind,
            "showtimes": [s.to_dict() for s in self.showtimes],
            "calendar_dates": self.calendar_dates,
            "evaluated_dates": self.evaluated_dates,
            "error": self.error,
            "checked_at": self.checked_at,
        }


def state_key(target_id: str, source: str) -> str:
    return f"{target_id}::{source}"


def diff_showtimes(known: list[Showtime], current: list[Showtime]) -> list[Showtime]:
    """Return showtimes present in `current` but not in `known`."""
    known_keys = {s.key() for s in known}
    return [s for s in current if s.key() not in known_keys]
