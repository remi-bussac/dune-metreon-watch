# dune-metreon-watch

A personal, single-user notifier that emails me when IMAX 70mm tickets go on
sale for the films and venues listed in `config/targets.json` — currently
**Dune: Part Three** at **AMC Metreon 16** (San Francisco) and **Regal
Hacienda Crossings** (Dublin), and **The Odyssey** at AMC Metreon 16.

That's the whole thing. It's one person trying not to miss a ticket on-sale
for a short list of IMAX 70mm releases at a couple of nearby cinemas.

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

## Where it runs

This runs on a small Oracle Cloud Always Free VM, driven by a systemd timer
(`dune-watch.timer` / `dune-watch.service`). It previously ran on GitHub
Actions and, briefly, a laptop LaunchAgent; both were retired in favor of a
host that isn't affected by the laptop sleeping or the Actions schedule
being unreliable (see `RUNBOOK.md` and commit `4ba748b`). The VM keeps its
own `state/state.json` and never commits or pushes it, so the copy of
`state/state.json` in this repo and the git history are **not** a live
record of what the monitor has done — see `RUNBOOK.md` for how to read the
real logs (`journalctl -u dune-watch.service`).

## Layout

```
config/targets.json    what to watch (film, venue, format, URLs)
scripts/monitor.py     orchestrator: check -> diff -> alert -> save state
scripts/sources/       one module per source
scripts/alert.py       Gmail SMTP alerting
scripts/browser.py     shared Playwright helper for sources that need a page render
state/state.json       last-seen showtimes on disk; stale unless read from the VM
deploy/                Oracle VM setup and deploy script (deploy/ORACLE_SETUP.md)
RESEARCH.md            dataset of past 70mm on-sale timings
FORECAST.md            when the next wave is likely, and confidence
RUNBOOK.md             setup, testing, cost, teardown
```

Secrets (the sending mailbox and its app password) live in an env file on
the VM (`~/.dune-metreon-watch.env`), never in this repo.
