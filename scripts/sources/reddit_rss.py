"""r/imax and r/dune "new" RSS feeds, keyword-filtered. Free, no auth, plain
HTTPS — no browser needed (RSS is meant to be machine-read). This is a
"mention" source, not a "showtime" source: a matching post is a leading
indicator (per FORECAST.md), not confirmation tickets are actually on sale,
so it's surfaced as a distinctly-labeled alert by monitor.py rather than a
ticket alert.

Note from live testing (2026-07-30): fetching the same feed twice within a
few seconds (e.g. once per target in monitor.py's per-target loop) reliably
triggered a 403/429 on the second call that a fresh call alone did not —
Reddit appears to rate-limit repeat hits even at this trivial volume. Each
feed is therefore fetched at most once per process run and cached in
_FEED_CACHE, regardless of how many targets ask for it. This halves the
per-run request count (2 instead of 4 for 2 targets) and is the actual fix,
not just politeness — monitor.py runs each source once per target in a
single process, so this cache is exactly as long-lived as it needs to be
and is naturally empty again on the next cron tick.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import feedparser
import requests

from normalize import Showtime, SourceResult

SOURCE_NAME = "reddit_rss"

FEEDS = [
    ("r/imax", "https://www.reddit.com/r/imax/new.rss"),
    ("r/dune", "https://www.reddit.com/r/dune/new.rss"),
]

# Identifies the tool and points at the repo rather than embedding a personal
# email address -- this repo is public, and a bare address in source is both
# scraped by spammers and personal data that does not belong here.
HEADERS = {
    "User-Agent": "DuneMetreonWatch/1.0 (personal ticket-availability monitor; "
    "+https://github.com/remi-bussac/dune-metreon-watch)"
}

# A match needs the film name AND a phrase that means "tickets just became
# buyable". The old rule accepted "imax", "70mm" or a bare "ticket" as
# sufficient context, which inside r/imax matches essentially every post --
# the three things it actually caught were a photo of film strips, a show
# report from a cinema in Colorado, and a London screening announcement.
# None were Metreon on-sale signals, and all three were emailed.
#
# This source exists for exactly one job: catching an on-sale announcement
# in the ~30 minutes before Fandango lists it, which is what happened with
# Dune 3's April wave. Discussion posts cannot do that job, so they are no
# longer treated as signal at all.
#
# Evaluated against the real titles this project has actually observed. A
# first, stricter version of this list looked clean but missed a genuine
# event already in the corpus -- "IMAX 70mm showings for 'THE ODYSSEY' are
# being extended through to September 16" -- because a run extension never
# uses the words "on sale". A run extension means new dates, which is the
# single most likely shape for a Dune second wave, so the list covers
# availability EXPANDING as well as availability OPENING.
AVAILABILITY_KEYWORDS = (
    # tickets becoming buyable
    "on sale", "onsale", "on-sale", "presale", "pre-sale",
    "tickets are live", "tickets go live", "tickets are now", "tickets available",
    "tickets just went", "tickets just dropped", "ticket drop", "tickets drop",
    "booking now open", "now booking",
    # more of them becoming buyable (runs extended, showtimes added, new waves)
    "extended", "extension", "added", "adding",
    "more showtimes", "more screenings", "more dates",
    "additional showtime", "additional screening",
    "new showtimes", "new dates",
    "second wave", "next wave", "another wave",
    # after the fact, but tells you a wave happened and you need to look now
    "sold out",
)

# Reddit rate-limits unauthenticated RSS hard enough that two feeds fetched
# back-to-back reliably produce a 429 on the SECOND one. Because the feed
# order was fixed, r/dune was always the loser: every stored run showed
# "1 of 2 feeds blocked", meaning the Dune subreddit was effectively never
# being read at all. Two mitigations, both cheap:
#   - pause between feeds
#   - rotate which feed goes first, so neither is permanently starved
# Rotation is derived from the clock rather than stored state, so it needs
# no plumbing and still alternates across runs at any sane cadence.
FEED_GAP_SECONDS = 8

_FEED_CACHE: dict[str, tuple[str, object]] = {}  # url -> ("ok"|"blocked"|"error", feedparser result or None)


def _ordered_feeds() -> list[tuple[str, str]]:
    offset = (datetime.now(timezone.utc).minute // 10) % len(FEEDS)
    return FEEDS[offset:] + FEEDS[:offset]


def _fetch(subreddit: str, url: str) -> tuple[str, object]:
    if url in _FEED_CACHE:
        return _FEED_CACHE[url]

    if _FEED_CACHE:  # not the first feed this run — give Reddit a breather
        time.sleep(FEED_GAP_SECONDS)

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
    except requests.RequestException:
        result = ("error", None)
    else:
        if resp.status_code in (403, 429):
            result = ("blocked", None)
        elif resp.status_code != 200:
            result = ("error", None)
        else:
            result = ("ok", feedparser.parse(resp.content))

    _FEED_CACHE[url] = result
    return result


def _matches(title: str, summary: str, target: dict) -> bool:
    """The film must be named in the TITLE; the availability wording may be
    anywhere.

    That asymmetry is drawn from the real posts. Both announcements of the
    Aug 18 on-sale put the film in the title ("The next opportunity to get
    DUNE: PART THREE tickets...") but the actual "on sale" wording in the
    body -- so demanding both in the title would silence the single most
    valuable signal this source has produced.

    Searching the BODY for the film name is what created the noise: an
    Odyssey write-up that mentioned Dune 3 in passing was filed as Dune
    news. A post that is genuinely about a film names it up front."""
    title_l = title.lower()
    everywhere = f"{title} {summary}".lower()
    is_about_film = any(kw in title_l for kw in target["film_keywords"])
    mentions_availability = any(kw in everywhere for kw in AVAILABILITY_KEYWORDS)
    return is_about_film and mentions_availability


def check(
    target: dict,
    known_dates: set[str] | None = None,
    read_times: dict[str, str | None] | None = None,
) -> SourceResult:
    # known_dates is accepted for a uniform source signature; RSS entries are
    # deduplicated by monitor.py against the whole known set, not by date.
    successes = 0
    blocked_count = 0
    entries: list[Showtime] = []

    for subreddit, url in _ordered_feeds():
        status, parsed = _fetch(subreddit, url)

        if status == "blocked":
            blocked_count += 1
            continue
        if status != "ok":
            continue

        successes += 1
        for entry in parsed.entries:
            title = getattr(entry, "title", "")
            summary = getattr(entry, "summary", "")
            if not _matches(title, summary, target):
                continue
            published = getattr(entry, "published_parsed", None)
            if published:
                date_str = f"{published.tm_year:04d}-{published.tm_mon:02d}-{published.tm_mday:02d}"
                time_str = f"{published.tm_hour:02d}:{published.tm_min:02d}"
            else:
                date_str, time_str = "unknown", "unknown"
            entries.append(
                Showtime(
                    date=date_str,
                    time=time_str,
                    format=f"reddit-mention:{title[:80]}",
                    venue=subreddit,
                    booking_url=getattr(entry, "link", url),
                )
            )

    if successes == 0:
        status = "blocked" if blocked_count > 0 else "no_data"
        return SourceResult(
            source=SOURCE_NAME,
            target_id=target["id"],
            status=status,
            kind="mention",
            error=f"{blocked_count} feed(s) returned 403/429; rest unreachable",
        )

    error = None
    if blocked_count > 0:
        error = f"{blocked_count} of {len(FEEDS)} feeds blocked (403/429) — partial coverage only"

    return SourceResult(
        source=SOURCE_NAME,
        target_id=target["id"],
        status="ok",
        kind="mention",
        showtimes=entries,
        error=error,
    )
