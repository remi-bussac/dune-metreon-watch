# RUNBOOK.md — Dune: Part Three @ AMC Metreon 16 70mm Monitor

## What this actually does

Every cron tick, `.github/workflows/monitor.yml` runs `scripts/monitor.py`, which checks 5 independent sources for each active target in `config/targets.json` (currently: Dune: Part Three, and The Odyssey as a temporary live test — see below), diffs results against `state/state.json`, emails you on anything new or broken, and commits the updated state back to the repo.

**Source reliability, confirmed by live testing on 2026-07-30 (read this before you're surprised in November):**

| Source | Status observed live | What it means |
|---|---|---|
| `amc_showtimes` / `amc_film_page` | **Blocked** — every single request, even the AMC homepage, hits a Cloudflare "Global Safety Net" Queue-it waiting room | AMC is effectively unreachable by this monitor right now. Both AMC sources will very likely sit in "blocked" state for most/all of the 5 months. This is expected, not a bug — see "If AMC starts blocking the runner" below (spoiler: it already is, from day one). |
| `imax_page` | **Inconsistent** — one film's page loaded fine, another got stuck behind a cookie-consent modal that a real click couldn't dismiss and the page then rendered a bare client-side error | Expect intermittent `parse_error`. After 3 consecutive failures you'll get a distinct "monitor broken" email for this source specifically — that's the dead-man's switch working as designed, not something to panic about. |
| `fandango` | **Reliable** — loads cleanly, no bot wall encountered | This is the workhorse. It doesn't scrape per-showtime data (Fandango's theater page only shows one calendar day at a time); instead it diffs the *list of bookable calendar dates* at Metreon. A new date appearing at all — confirmed live to already include Dune: Part Three's known Dec 17–20, 2026 dates — is the primary signal. |
| `reddit_rss` | **Works, but rate-limit sensitive** — hitting the same feed twice within seconds got a 403 the second time | Fixed by caching each feed fetch once per process run regardless of how many targets ask for it (see `scripts/sources/reddit_rss.py`). If this degrades again in production, it'll show up as `blocked` in the heartbeat, not silently. |

Net effect: in practice, **Fandango and Reddit are your real signal**; AMC and IMAX are best-effort redundancy that will mostly report their own broken/blocked state honestly rather than pretend to work. If AMC's blocking changes (loosens or tightens further), that shows up in the weekly heartbeat digest.

---

## Setup

### 1. Create the GitHub repo

```bash
gh repo create dune-metreon-watch --public --source=. --remote=origin
```

If `gh` isn't authenticated locally, create the repo manually on github.com (public, empty, no README) and:

```bash
git remote add origin https://github.com/<you>/dune-metreon-watch.git
```

### 2. Generate a Gmail App Password (you do this, not me — it's your account setting)

1. Turn on 2-Step Verification on your Google account if it isn't already: https://myaccount.google.com/security
2. Go to https://myaccount.google.com/apppasswords
3. Create an app password (name it "dune-metreon-watch"), copy the 16-character value.

### 3. Set repo secrets

Do this from your own terminal (not by pasting the password into chat with me):

```bash
gh secret set GMAIL_ADDRESS --body "youraddress@gmail.com"
gh secret set GMAIL_APP_PASSWORD --body "xxxxxxxxxxxxxxxx"
gh secret set ALERT_EMAIL_TO --body "youraddress@gmail.com"
```

(`ALERT_EMAIL_TO` can be the same address or a different one — it's just where alerts land.)

### 4. Push

```bash
git add -A
git commit -m "Initial commit: Dune Metreon 70mm monitor"
git push -u origin main
```

### 5. First manual run

GitHub → your repo → Actions → "Dune Metreon 70mm monitor" → Run workflow (uses the `workflow_dispatch` trigger). Watch the log. Expect to see:
- `amc_showtimes` / `amc_film_page`: `blocked` — expected, see table above. You'll get one blocked-alert email per AMC source on this first run (that's `blocked_alert_sent` flipping from false to true; it won't re-alert every run after that, only when the state changes).
- `imax_page`: probably `ok` or `parse_error` depending on which target and the day's luck with IMAX's consent modal.
- `fandango`: `ok` with ~90 dates found on first run — this will trigger a "leading indicator" email for both targets, since every one of those dates is "new" relative to empty starting state. That's expected and correct for a first run; it will not repeat next run.
- `reddit_rss`: `ok` or `blocked` depending on current Reddit rate limits.
- A state commit (`Update monitor state [skip ci]`) should land in the repo after the run.

If the workflow fails outright (not "sources report blocked," but the *job* fails), check the Actions log — most likely cause is a missing/misnamed secret.

---

## Live test: The Odyssey (do this before trusting the pipeline for Dune)

`config/targets.json` includes The Odyssey (Metreon, IMAX 70mm) specifically as a live test target, per your request. As of 2026-07-30, its IMAX 70mm run was just extended through Sept 16, 2026 due to demand — new Metreon dates are actively being added to Fandango's calendar right now, so within days of turning the monitor on you should get a real "leading indicator" email when a new far-future date shows up.

**What to check when it arrives:**
1. Subject line says "👀 Leading indicator" (not "🎟️ TICKETS") — Fandango's calendar-diff source is intentionally `kind="mention"`, since a new bookable date doesn't independently confirm it's for The Odyssey vs. some other booking at Metreon.
2. The email includes the Fandango Metreon theater page URL.
3. Manually check that URL and confirm there really is a new date, and it's plausible it's an Odyssey addition (matches the ongoing run-extension pattern).

Once you've confirmed one real alert end-to-end, remove The Odyssey from the target list:

```bash
# edit config/targets.json, delete the "the-odyssey" object, then:
git add config/targets.json
git commit -m "Remove Odyssey live-test target after validating the pipeline"
git push
```

### Synthetic forced-alert test (deterministic backstop, doesn't depend on Odyssey timing)

Run locally (not in CI) to prove the *email-sending* path works independent of any live site:

```bash
source .venv/bin/activate  # or however you manage the venv
GMAIL_ADDRESS=youraddress@gmail.com \
GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx \
ALERT_EMAIL_TO=youraddress@gmail.com \
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from normalize import Showtime, SourceResult
import alert

target = {'film_name': 'TEST', 'venue': 'AMC Metreon 16', 'format': 'IMAX 70mm'}
result = SourceResult(
    source='forced-test', target_id='test', status='ok', kind='showtime',
    showtimes=[Showtime(date='2026-01-01', time='09:00', format='IMAX 70mm',
                         venue='AMC Metreon 16', booking_url='https://example.com/test')],
)
alert.send_ticket_alert(target, result)
print('Sent — check your inbox.')
"
```

You should get a real email within seconds. If this fails, the problem is your Gmail App Password / secret, not the monitor logic.

---

## Cadence

Single cron line in `.github/workflows/monitor.yml`. Edit it by hand at these points (GitHub Actions cron is UTC — these are pre-converted to PT, split around the Nov 1, 2026 PDT→PST transition so no line is ambiguous):

| Phase | Dates | Cadence | Cron |
|---|---|---|---|
| 1 | Now → Sep 30, 2026 | Hourly, ~7am–4pm PT weekdays (PDT, UTC-7) | `7 14-23 * * 1-5` *(already in the file)* |
| 2a | Oct 1 → Oct 31, 2026 | Every 15 min, 05:00–18:00 PT (PDT, UTC-7; 18:00 PT wraps past midnight UTC) | `*/15 0-1,12-23 * * *` |
| 2b | Nov 1 → Nov 30, 2026 | Every 15 min, 05:00–18:00 PT (PST, UTC-8, after the Nov 1 DST change) | `*/15 0-2,13-23 * * *` |
| 3 | Dec 1 → Dec 18, 2026 | Every 5 min, all day (PST, UTC-8) — timezone-agnostic since it's 24/7 | `*/5 * * * *` |

Each edit is a one-line change to the `- cron:` value under `on.schedule` in `.github/workflows/monitor.yml`, then commit and push.

---

## Cost table

| Component | Cost |
|---|---|
| GitHub Actions (public repo, unlimited free minutes) | $0 |
| State storage (git) | $0 |
| Gmail SMTP | $0 (well under the 500/day free cap) |
| Push notifications | Not used (declined) |
| SMS (Twilio, priced for the record, not implemented) | ~$1.15/mo number rental × 5 months + negligible per-message ≈ **$6–7 total** — not implemented; email-only was the explicit choice |
| **Total** | **$0** |

---

## If AMC starts blocking the runner

It already is, confirmed on day one (see table at the top). This isn't a future contingency, it's the current baseline. What to actually do:

1. **Don't try to fight it harder.** More stealth tricks (proxies, residential IPs, CAPTCHA-solving) cross into territory this project explicitly avoids (no CAPTCHA handling, no elaborate evasion) and burns effort against a moving target. This monitor was designed with AMC being unreliable as the starting assumption, not a fallback plan.
2. **Watch the weekly heartbeat.** It shows each source's last status. If Fandango or Reddit *also* start reporting blocked, that's the real emergency — those are the sources actually carrying signal.
3. **If Fandango's calendar page structure changes** (the theater-page URL 404s, or the calendar regex stops matching), `fandango.py` will report `parse_error`, and after 3 consecutive runs you'll get a distinct "monitor broken" email naming the source. Fix: re-run the dry-run debug snippets used during development (see git history of this repo, or just load the theater page in a browser and see what changed) and update `scripts/sources/fandango.py`'s `CALENDAR_ENTRY_PATTERN` or the theater URL in `config/targets.json`.
4. **Worst case (everything blocked):** you'll get distinct blocked/broken alerts from every source rather than silence — check AMC's site manually. The forecast window in `FORECAST.md` still tells you roughly when to look.

---

## Teardown (December 19, 2026, whether or not you got tickets)

```bash
# Disable the schedule so it stops running (keeps history/audit trail intact)
```
Edit `.github/workflows/monitor.yml`, comment out or delete the `schedule:` block (keep `workflow_dispatch` if you want to re-enable manually later), commit, push.

Optionally, after confirming you don't need it anymore:

```bash
gh repo archive <you>/dune-metreon-watch
```

Archiving is reversible (unarchive from repo settings) and stops any possibility of the schedule running while keeping everything — including `state/state.json`'s full history, which doubles as your dataset of exactly when things happened — intact and public.

---

## First 90 seconds after a ticket alert fires

1. **Be already logged into AMC** (app or site) with a saved payment method — don't log in after the alert, that's seconds you don't have.
2. **Go straight to the URL in the email.** Don't browse from AMC's homepage or search — the alert email exists specifically so you skip that.
3. **Buy single seats before adjacent pairs.** Research confirms pairs/groups get harder to find far faster than single seats during a sellout — if you're buying for more than one person, consider buying seats separately if the sellout is clearly imminent, rather than holding out for adjacent seats.
4. **Don't wait for a "better" showtime.** Metreon runs one 70mm showing/day — if multiple dates are open, grab the first one that works and worry about optimizing later; every minute of deliberation is seats gone.
