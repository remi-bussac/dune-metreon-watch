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

EXTRA_KEYWORDS = ("70mm", "70 mm", "ticket", "on sale", "onsale", "imax")

_FEED_CACHE: dict[str, tuple[str, object]] = {}  # url -> ("ok"|"blocked"|"error", feedparser result or None)


def _fetch(subreddit: str, url: str) -> tuple[str, object]:
    if url in _FEED_CACHE:
        return _FEED_CACHE[url]

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
    text = f"{title} {summary}".lower()
    has_film = any(kw in text for kw in target["film_keywords"])
    has_context = any(kw in text for kw in EXTRA_KEYWORDS)
    return has_film and has_context


def check(target: dict) -> SourceResult:
    successes = 0
    blocked_count = 0
    entries: list[Showtime] = []

    for subreddit, url in FEEDS:
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
