# RUNBOOK.md — Dune: Part Three @ AMC Metreon 16 70mm Monitor

## What this actually does

Every cron tick, `.github/workflows/monitor.yml` runs `scripts/monitor.py`, which checks 5 independent sources for each active target in `config/targets.json` (currently: Dune: Part Three, and The Odyssey as a temporary live test — see below), diffs results against `state/state.json`, emails you on anything new or broken, and commits the updated state back to the repo.

**Source reliability, confirmed by live testing (last verified 2026-07-31, after reviewing the first production runs):**

| Source | Status observed live | What it means |
|---|---|---|
| `fandango` | **Reliable and validated** — the primary source | Reads Fandango's film-specific *"IMAX 70MM Experience"* page, geo-set to San Francisco, and extracts AMC Metreon 16's showtimes for every date the film offers in 70mm. Currently returns exactly the 8 known Dune showtimes (Dec 17–20 × 7:00p and 11:00p). Because the page is inherently 70mm-only, there is no regular-programming noise, and it detects both a **new date** and a **new showtime on an existing date**. |
| `reddit_rss` | **Works, rate-limit sensitive** — 1 of 2 feeds usually 403s | Each feed is fetched once per run and cached across targets. Partial coverage is reported in `last_error` rather than hidden. Leading indicator only, never a ticket alert. |
| `amc_showtimes` / `amc_film_page` | **Unreliable and unvalidated** — 403 / Queue-it waiting room from GitHub's datacenter IPs; intermittently loads from a home IP | Treat AMC output as *redundancy only, never as evidence of absence*. Its extraction path has never once successfully parsed a real showtime (AMC has been blocked every time it mattered), so an `ok (0 showtimes)` from AMC means "nothing found by unvalidated code," not "nothing on sale." Fandango is the source of truth. |
| `imax_page` | **Persistently broken** — page loads but stalls behind a cookie-consent modal it won't dismiss, rendering ~300 chars ending in a bare client-side error | Reports `parse_error`, and has already tripped the 3-strike dead-man's switch, so **expect one "⚠️ MONITOR BROKEN: imax_page" email** — that alert is correct, not a false alarm. It then goes quiet unless IMAX starts working again. |

Net effect: **Fandango is the real signal; Reddit is a leading indicator; AMC and IMAX mostly report their own broken state honestly.** That's the intended behavior of the dead-man's switch — a source that can't work says so instead of quietly returning "nothing."

### Why the Fandango source was rewritten (found during the post-deployment review)

The original implementation diffed the *theater* page's calendar — every bookable date at Metreon, for any film. Checking it against two days of real production data showed it was wrong in both directions:

- **False positives, roughly daily.** The theater calendar rolls forward as Metreon publishes ordinary programming. `2026-09-08` appeared between two consecutive runs, which would have fired a "new date!" alert with nothing to do with Dune. Over five months that is alert fatigue on the one channel that has to stay trustworthy.
- **A false negative on the case that actually matters.** Dec 17–20 2026 were *already* in that calendar (the April wave booked them). A second wave adding more Dune 70mm showtimes on those same dates changes no *date*, so the monitor would have stayed completely silent through exactly the event it exists to catch.

The rewrite watches the 70mm-specific film page instead, which lists only 70mm dates and the actual per-theater showtimes — so it is quiet by default and fires on either a new date or a new showtime. Verified by simulation: removing Dec 20 from state and re-running produced a correct 🎟️ TICKETS email naming exactly the two restored showtimes.

**One dependency to know about:** this source relies on a browser **geolocation override** (`SF_GEOLOCATION` in `scripts/browser.py`) to make Fandango show San Francisco theaters — without it the runner's own IP picks the metro and Metreon never appears. If Fandango stops honoring it, the page would show another city and "no Metreon showtimes" would be a lie. The source guards against this by requiring a `941xx` ZIP on the page and reporting `parse_error` if it's missing, so that failure surfaces as a broken-monitor alert instead of false silence.

---

## Setup

### 1. Create the GitHub repo — done

Live at https://github.com/remi-bussac/dune-metreon-watch (public, per your confirmation).

### 2. Create a dedicated Gmail account for sending, and generate its App Password

**Use a separate Gmail account for `GMAIL_ADDRESS`, not your primary one.** `GMAIL_ADDRESS` is the *sender* — its app password sits in a GitHub repo secret for the life of this project (through March 2027 per the extended timeline below), so it's worth isolating: if that secret were ever exposed, the blast radius is a throwaway account that does nothing but send you alert emails, not your real inbox, contacts, or anything else tied to your primary Google account. `ALERT_EMAIL_TO` (where alerts land) stays your real, normal inbox — it's just a plain address, no credentials attached to it at all.

1. Create a new Google account (you do this — I don't create accounts): https://accounts.google.com/signup — something like `dunemetreonwatch@gmail.com` is fine, it never needs to be checked.
2. On that new account, turn on 2-Step Verification: https://myaccount.google.com/security
3. Go to https://myaccount.google.com/apppasswords, create an app password (name it "dune-metreon-watch"), copy the 16-character value.

### 3. Set repo secrets

Do this from your own terminal (not by pasting the password into chat with me):

```bash
gh secret set GMAIL_ADDRESS --body "dunemetreonwatch@gmail.com"    # the dedicated sender account from step 2
gh secret set GMAIL_APP_PASSWORD --body "xxxxxxxxxxxxxxxx"          # that account's app password
gh secret set ALERT_EMAIL_TO --body "your-real-address@gmail.com"   # your actual inbox — no credentials needed here
```

### 4. First manual run

GitHub → your repo → Actions → "Dune Metreon 70mm monitor" → Run workflow (uses the `workflow_dispatch` trigger). Watch the log. Expect to see:
- `amc_showtimes` / `amc_film_page`: `blocked` — expected, see table above. You'll get one blocked-alert email per AMC source on this first run (that's `blocked_alert_sent` flipping from false to true; it won't re-alert every run after that, only when the state changes).
- `imax_page`: probably `ok` or `parse_error` depending on which target and the day's luck with IMAX's consent modal.
- `fandango`: `ok` with ~90 dates found on first run — this will trigger a "leading indicator" email for both targets, since every one of those dates is "new" relative to empty starting state. That's expected and correct for a first run; it will not repeat next run.
- `reddit_rss`: `ok` or `blocked` depending on current Reddit rate limits.
- A state commit (`Update monitor state [skip ci]`) should land in the repo after the run.

If the workflow fails outright (not "sources report blocked," but the *job* fails), check the Actions log — most likely cause is a missing/misnamed secret.

---

## Live test: The Odyssey (do this before trusting the pipeline for Dune)

`config/targets.json` includes The Odyssey (Metreon, IMAX 70mm) specifically as a live test target, per your request. Its IMAX 70mm run was extended through Sept 16, 2026 due to demand, so Metreon is actively adding showtimes — you should get real alerts within days.

**Heads up: The Odyssey is deliberately chatty, and that's the point.** It's a currently-playing film, so it has ~90 tracked 70mm showtimes at Metreon and its schedule rolls forward daily. Expect a 🎟️ TICKETS email fairly often while it's in the target list — each one is the pipeline genuinely working on real data. Dune: Part Three, by contrast, is an event booking with a stable 8-showtime baseline, so it should stay completely silent until an actual wave drops. **Do not calibrate your expectations for Dune based on Odyssey's volume.**

**What to check when an Odyssey alert arrives:**
1. Subject says "🎟️ TICKETS: The Odyssey 70mm at AMC Metreon 16".
2. It lists specific dates and times, and includes the direct Fandango 70mm booking URL.
3. Click through and confirm those showtimes really exist at Metreon in IMAX 70mm.

That confirms the full chain — scrape → normalize → diff → email — on real data. Once you've confirmed one, remove The Odyssey from the target list to stop the noise:

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

Single cron line in `.github/workflows/monitor.yml`. Edit it by hand at these points (GitHub Actions cron is UTC — these are pre-converted to PT, split around DST transitions so no line is ambiguous):

| Phase | Dates | Cadence | Cron |
|---|---|---|---|
| 1 | Now → Sep 30, 2026 | Hourly, ~7am–4pm PT weekdays (PDT, UTC-7) | `7 14-23 * * 1-5` *(already in the file)* |
| 2a | Oct 1 → Oct 31, 2026 | Every 15 min, 05:00–18:00 PT (PDT, UTC-7; 18:00 PT wraps past midnight UTC) | `*/15 0-1,12-23 * * *` |
| 2b | Nov 1 → Nov 30, 2026 | Every 15 min, 05:00–18:00 PT (PST, UTC-8, after the Nov 1 DST change) | `*/15 0-2,13-23 * * *` |
| 3 | Dec 1 → Dec 18, 2026 | Every 5 min, all day (PST, UTC-8) — timezone-agnostic since it's 24/7 | `*/5 * * * *` |
| 4 | Dec 19, 2026 → teardown (March 2027) | Back to hourly, ~7am–4pm PT weekdays (PST, UTC-8) | `7 15-23,0 * * 1-5` |

**Phase 4 exists because release-day isn't necessarily the last wave.** Precedent from `RESEARCH.md`: Oppenheimer got an encore 70mm re-release ~15 weeks *after* its original release; Sinners got re-release waves for 8 months after release. Dune: Part Three plausibly does the same — an extended/encore 70mm run, or a second batch of dates at Metreon, sometime in early 2027. Phase 4 is deliberately lower-intensity than the pre-release ramp: there's no research-backed forecast window for a hypothetical post-release wave the way there is for the pre-release one, so hourly is a reasonable, sustainable baseline rather than guessing at another tight window. If you spot news suggesting a specific date, tighten the cron manually for that stretch the same way phase 2/3 do.

Note: US DST resumes March 8, 2027, inside phase 4's window — the cron above is calculated for PST and will drift by an hour after that date. Not worth a mid-phase edit for an hourly catch-all check; ignore it unless you want to be precise.

Each edit is a one-line change to the `- cron:` value under `on.schedule` in `.github/workflows/monitor.yml`, then commit and push.

---

## Cost table

| Component | Cost |
|---|---|
| GitHub Actions (public repo, unlimited free minutes) | $0 — duration doesn't change this; public repos have no minutes cap regardless of run count |
| State storage (git) | $0 |
| Gmail SMTP (including the dedicated sender account) | $0 (well under the 500/day free cap) |
| Push notifications | Not used (declined) |
| SMS (Twilio, priced for the record, not implemented) | ~$1.15/mo number rental × ~8 months (Jul 2026 → Mar 2027) + negligible per-message ≈ **$9–10 total** — not implemented; email-only was the explicit choice |
| **Total** | **$0** |

Extending the run from 5 months to ~8 months doesn't change any of this — the free tiers involved (GitHub Actions on a public repo, Gmail SMTP under 500 sends/day) aren't duration-limited, only volume-limited, and this monitor's volume is trivially low either way.

---

## If AMC starts blocking the runner

It already is, confirmed on day one (see table at the top). This isn't a future contingency, it's the current baseline. What to actually do:

1. **Don't try to fight it harder.** More stealth tricks (proxies, residential IPs, CAPTCHA-solving) cross into territory this project explicitly avoids (no CAPTCHA handling, no elaborate evasion) and burns effort against a moving target. This monitor was designed with AMC being unreliable as the starting assumption, not a fallback plan.
2. **Watch the weekly heartbeat.** It shows each source's last status. If Fandango or Reddit *also* start reporting blocked, that's the real emergency — those are the sources actually carrying signal.
3. **If Fandango's calendar page structure changes** (the theater-page URL 404s, or the calendar regex stops matching), `fandango.py` will report `parse_error`, and after 3 consecutive runs you'll get a distinct "monitor broken" email naming the source. Fix: re-run the dry-run debug snippets used during development (see git history of this repo, or just load the theater page in a browser and see what changed) and update `scripts/sources/fandango.py`'s `CALENDAR_ENTRY_PATTERN` or the theater URL in `config/targets.json`.
4. **Worst case (everything blocked):** you'll get distinct blocked/broken alerts from every source rather than silence — check AMC's site manually. The forecast window in `FORECAST.md` still tells you roughly when to look.

---

## Teardown (target: end of March 2027, not Dec 18)

Don't tear down on release day — see phase 4 above, the point is to keep watching for post-release waves through Q1 2027. Revisit this decision in March 2027: if there's been no post-release wave activity and none seems likely (check recent news on the film), tear down; if something looks imminent, push the date back the same way you'd extend the cadence.

```bash
# Disable the schedule so it stops running (keeps history/audit trail intact)
```
Edit `.github/workflows/monitor.yml`, comment out or delete the `schedule:` block (keep `workflow_dispatch` if you want to re-enable manually later), commit, push.

Optionally, after confirming you don't need it anymore:

```bash
gh repo archive remi-bussac/dune-metreon-watch
```

Archiving is reversible (unarchive from repo settings) and stops any possibility of the schedule running while keeping everything — including `state/state.json`'s full history, which doubles as your dataset of exactly when things happened — intact and public.

---

## Extending to another film or venue

`config/targets.json` is already a list, not a single hardcoded film — every source module and `monitor.py` loop over it generically (this is how The Odyssey ran alongside Dune: Part Three as a live test). To watch a new film, add another object to the array:

```json
{
  "id": "some-new-film",
  "film_name": "Some New Film",
  "film_keywords": ["some new film", "some new film 2027"],
  "venue": "AMC Metreon 16",
  "format": "IMAX 70mm",
  "release_date": "2027-XX-XX",
  "amc_theatre_url": "https://www.amctheatres.com/movie-theatres/san-francisco/amc-metreon-16",
  "amc_film_url": "https://www.amctheatres.com/movies/<find-the-real-slug>",
  "imax_url": "https://www.imax.com/movie/<find-the-real-slug>",
  "fandango_film_url": "https://www.fandango.com/<film>-the-imax-70mm-experience-<year>-<id>/movie-overview",
  "active": true
}
```

**`fandango_film_url` is the one that matters** — it's the primary source. Find it by searching Fandango for the film and picking the entry explicitly titled *"<Film> - The IMAX 70MM Experience"*, not the standard entry. That separate per-format entry is what makes the source 70mm-only. If a film has no 70mm entry yet, the URL won't exist and the source will report `no_data` with a hint to check the URL — add the target once the 70mm listing appears.

`amc_theatre_url` stays the same for anything at Metreon; `amc_film_url` and `imax_url` need the new film's slug (search `site:amctheatres.com <film name>` / `site:imax.com <film name>`). For a **different venue**, change `venue` to match the theater's name exactly as Fandango renders it (e.g. `"AMC Lincoln Square 13"`) — the Fandango source matches on that string — and update `scripts/browser.py`'s `SF_GEOLOCATION` plus `fandango.py`'s `SF_ZIP_PATTERN` to that city, or the page will show the wrong metro.

Set `"active": false` on any target instead of deleting it if you want to pause without losing the config.

---

## First 90 seconds after a ticket alert fires

1. **Be already logged into AMC** (app or site) with a saved payment method — don't log in after the alert, that's seconds you don't have.
2. **Go straight to the URL in the email.** Don't browse from AMC's homepage or search — the alert email exists specifically so you skip that.
3. **Buy single seats before adjacent pairs.** Research confirms pairs/groups get harder to find far faster than single seats during a sellout — if you're buying for more than one person, consider buying seats separately if the sellout is clearly imminent, rather than holding out for adjacent seats.
4. **Don't wait for a "better" showtime.** Metreon runs one 70mm showing/day — if multiple dates are open, grab the first one that works and worry about optimizing later; every minute of deliberation is seats gone.
