# dune-metreon-watch

A personal, single-user notifier that emails me when IMAX 70mm tickets for
**Dune: Part Three** go on sale at **AMC Metreon 16** in San Francisco.

That's the whole thing. It's one person trying not to miss a ticket on-sale
for one film at one cinema.

## What it does

Every scheduled run it reads two public pages, compares them to what it saw
last time, and emails me only if something changed:

| Source | What it reads |
|---|---|
| Fandango | The film's public *"IMAX 70MM Experience"* showtimes page |
| Reddit | `r/imax` and `r/dune` public `new.rss` feeds |

If a new showtime appears, I get an email with a link and I go buy a ticket
myself, in a normal browser, like anyone else.

## What it deliberately does NOT do

- **It never buys, holds, or reserves anything.** There is no checkout code,
  no cart automation, no payment handling, no seat locking. Its only output
  is an email to its owner.
- **It stores no credentials for any ticketing site.** It has no account on
  AMC, Fandango, or IMAX and never logs in anywhere.
- **It does not solve CAPTCHAs** or attempt to defeat bot protection. If a
  site returns 403/429 or shows a waiting-room page, that is recorded as
  "blocked" and the run moves on. Sources that blocked this tool have been
  switched off entirely rather than retried — see `DISABLED_SOURCES` in
  `scripts/monitor.py`.
- **It does not impersonate a human.** It sends a self-identifying
  user-agent naming the tool and linking to this repo.
- **It respects robots.txt.** Fandango disallows `/api/`, `/napi/*` and
  `?date=`-style URLs; this only ever loads the plain public page URL and
  never constructs a disallowed request.
- **It is low volume.** A handful of requests per run, single-threaded, no
  parallel fetching, no retry storms.

## Automation notice

Commits authored by `dune-metreon-watch-bot` are this repo's own scheduled
job writing `state/state.json` — the small file it diffs against to decide
whether anything changed. They are the audit trail, not activity padding.
State is only committed when something meaningful actually changes.

## Layout

```
config/targets.json    what to watch (film, venue, format, URLs)
scripts/monitor.py     orchestrator: check -> diff -> alert -> save state
scripts/sources/       one module per source
state/state.json       last-seen showtimes, committed as the audit trail
RESEARCH.md            dataset of past 70mm on-sale timings
FORECAST.md            when the next wave is likely, and confidence
RUNBOOK.md             setup, testing, cost, teardown
```

Secrets (the sending mailbox and its app password) live in GitHub Actions
repository secrets, never in this repo.
