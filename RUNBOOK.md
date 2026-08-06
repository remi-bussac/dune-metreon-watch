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

**One dependency to know about — how the monitor gets San Francisco results.** Fandango decides which metro to show you, and by default a GitHub runner gets whatever metro its datacenter IP resolves to, which does not contain Metreon. Two mechanisms pin it to SF:

1. **Location cookies** (`SF_LOCATION_COOKIES` in `scripts/sources/fandango.py`) — `zip`, `searchcity`, `searchstate`, `searchlocation`, seeded before the first navigation. This is the one that actually works in CI.
2. **Browser geolocation override** (`SF_GEOLOCATION` in `scripts/browser.py`) — belt-and-braces; sufficient on a home IP, but *not* on a GitHub runner.

This was found the hard way: geolocation alone worked locally, then returned `parse_error` on the first real CI run because Fandango fell back to IP-based location. That's the ZIP guard doing its job — the source requires a `941xx` ZIP on the page and reports `parse_error` if it's missing, so a location failure surfaces as a broken-monitor alert instead of a silent, false "no showtimes." If you ever see that error again, the cookies have stopped working and the fix is to re-capture them from a real browser session (see the probe approach in this repo's git history).

---

## Setup

### 1. Create the GitHub repo — done

Live at https://github.com/remi-bussac/dune-metreon-watch (public, per your confirmation).

### 2. Create a dedicated Gmail account for sending, and generate its App Password

**Use a separate Gmail account for `GMAIL_ADDRESS`, not your primary one.** `GMAIL_ADDRESS` is the *sender* — its app password sits in a GitHub repo secret for the life of this project (through March 2027 per the extended timeline below), so it's worth isolating: if that secret were ever exposed, the blast radius is a throwaway account that does nothing but send you alert emails, not your real inbox, contacts, or anything else tied to your primary Google account. `ALERT_EMAIL_TO` (where alerts land) stays your real, normal inbox — it's just a plain address, no credentials attached to it at all.

1. Create a new Google account (you do this — I don't create accounts): https://accounts.google.com/signup. It never needs to be checked. **Write down the exact address you end up with** — the one you want is often taken, and a mismatch here produces a confusing SMTP error later (see Troubleshooting).
2. On that new account, turn on 2-Step Verification: https://myaccount.google.com/security
3. Go to https://myaccount.google.com/apppasswords, create an app password (name it "dune-metreon-watch"), copy the 16-character value.

### 3. Set repo secrets

Do this from your own terminal (not by pasting the password into chat with me):

```bash
gh secret set GMAIL_ADDRESS --body "YOUR-SENDER-ACCOUNT@gmail.com"  # the dedicated sender account from step 2
gh secret set GMAIL_APP_PASSWORD --body "xxxxxxxxxxxxxxxx"          # that account's app password
gh secret set ALERT_EMAIL_TO --body "your-real-address@gmail.com"   # your actual inbox — no credentials needed here
```

### 4. First manual run — done, and this is the current steady state

GitHub → your repo → Actions → "Dune Metreon 70mm monitor" → Run workflow (uses the `workflow_dispatch` trigger). As of the last verified run (2026-07-31, 1m34s, green), a healthy run looks like:

```
[dune-part-three] amc_showtimes: blocked (0 showtimes)
[dune-part-three] amc_film_page: blocked (0 showtimes)
[dune-part-three] imax_page:     blocked (0 showtimes)
[dune-part-three] fandango:      ok (8 showtimes)      <-- the one that matters
[dune-part-three] reddit_rss:    ok (1 showtimes)
[the-odyssey]     fandango:      ok (90 showtimes)
```

- **`fandango: ok (8 showtimes)` for Dune is the health check.** That's Dec 17–20 × 7:00p and 11:00p — the existing April wave. If that number changes, something real happened. If it ever reads `parse_error`, the location cookies or page structure broke (see below) — it does *not* mean tickets vanished.
- `blocked` on the AMC and IMAX sources is expected and permanent-ish, not a failure.
- You'll get one blocked/broken email per affected source the first time each enters that state, then silence until it changes.
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
| 1 | Now → Sep 30, 2026 | Hourly, 24/7 | `7 * * * *` *(current)* |
| 2 | Oct 1 → Nov 30, 2026 | Every 15 min, 24/7 | `*/15 * * * *` |
| 3 | Dec 1 → Dec 18, 2026 | Every 5 min, 24/7 | `*/5 * * * *` |
| 4 | Dec 19, 2026 → teardown (March 2027) | Back to hourly, 24/7 | `7 * * * *` |

**Why 24/7 rather than business hours on weekdays.** The original schedule ran 07:00–16:00 PT Mon–Fri, which left a 15-hour blind spot every night and a **63-hour blind spot every weekend** (Fri 16:07 PT → Mon 07:07 PT). Checking the dataset, *no* on-sale in `RESEARCH.md` has ever landed on a weekend — all nine were Mon–Fri, mostly Thursday — so the weekend risk is not that a wave *starts* on a Saturday. It's that a Friday-evening drop, or new showtimes added over a weekend (which happens routinely, especially for a film mid-run like The Odyssey), would sit undetected for two and a half days. Dune 3's own April wave was announced 30 minutes ahead and sold out in minutes; a 63-hour gap is not survivable against that. Since Actions minutes are free on a public repo and each run is now only two sources, closing the gap costs nothing.

Note the 24/7 schedules are also DST-proof, which the old hour-bounded ones were not.

**Phase 4 exists because release-day isn't necessarily the last wave.** Precedent from `RESEARCH.md`: Oppenheimer got an encore 70mm re-release ~15 weeks *after* its original release; Sinners got re-release waves for 8 months after release. Dune: Part Three plausibly does the same — an extended/encore 70mm run, or a second batch of dates at Metreon, sometime in early 2027. Phase 4 is deliberately lower-intensity than the pre-release ramp: there's no research-backed forecast window for a hypothetical post-release wave the way there is for the pre-release one, so hourly is a reasonable, sustainable baseline rather than guessing at another tight window. If you spot news suggesting a specific date, tighten the cron manually for that stretch the same way phase 2/3 do.

Note: US DST resumes March 8, 2027, inside phase 4's window — the cron above is calculated for PST and will drift by an hour after that date. Not worth a mid-phase edit for an hourly catch-all check; ignore it unless you want to be precise.

Each edit is a one-line change to the `- cron:` value under `on.schedule` in `.github/workflows/monitor.yml`, then commit and push.

---

## Running by hand (while the Actions schedule is off)

One-time: put the app password into `~/.dune-metreon-watch.env` (already created, mode 0600, deliberately **outside** the repo so it can never be committed). Replace the `PUT_YOUR_...` placeholder.

Then a check is one command:

```bash
bash scripts/run_local.sh
```

It loads the credentials, runs the monitor, appends to `local-run.log` (gitignored), and alerts exactly as CI would. If the password isn't filled in it prints a `SKIP:` line and exits cleanly rather than erroring.

State accumulates in `state/state.json` across manual runs and is *not* auto-committed — commit it once, by hand, whenever you like.

### Continuous loop in tmux (the actual stopgap)

Rather than remembering to run it, keep a loop alive in tmux. It inherits your interactive shell's permissions, so it sidesteps the TCC problem below entirely, and it survives closing the terminal window.

```bash
tmux new-session -d -s dune "bash /Users/remibussac/Documents/PERSO/Watcher-AMC/scripts/run_loop.sh"
```

| Task | Command |
|---|---|
| Watch it live | `tmux attach -t dune` (detach again with `Ctrl-B` then `D`) |
| Tail without attaching | `tail -f local-run.log` |
| Stop it | `tmux kill-session -t dune` |
| Is it running? | `tmux ls` |
| Faster interval | `DUNE_WATCH_INTERVAL=300 tmux new-session -d -s dune "bash .../run_loop.sh"` |

Default interval is **600s (10 minutes)**. Each pass is roughly 15–20 requests (one Fandango page per target, then a click per date in that film's carousel), so 10 minutes is about 2,500 requests/day with the laptop open all day. Five minutes doubles that. Ten is a deliberate middle ground against this project's own "honest request rate" rule. Dropping to 60s for a few hours on a known drop day is fine — a short burst and sustained load are different things.

**It does not survive a reboot or logout.** Re-run the `tmux new-session` command after restarting. Laptop sleep just pauses it; it picks up on wake.

**A macOS LaunchAgent was evaluated and rejected.** It can't work from this location: macOS TCC lets a LaunchAgent execute a binary inside `~/Documents` but blocks it from *reading* files there, so `monitor.py` can never be loaded. The only fixes were moving the repo out of `~/Documents`, or granting Full Disk Access to `/bin/bash` — which would give every script bash ever runs full disk access, a bad trade for a temporary job. tmux avoids the whole problem.

---

## Why you get an email (and why you don't)

A 🎟️ ticket alert fires when a `(date, time, format, venue)` combination is seen that has **never** been seen before. That means:

| Event | Email? |
|---|---|
| New date appears (run extended, new wave) | ✅ **Always**, regardless of how soon it is |
| New time on a known date, **≥6 days** out | ✅ Yes |
| New time on a known date, **<6 days** out | ❌ No — routine schedule churn |
| Seats freed up on a showtime already known | ❌ No — availability is never read |
| A showtime disappears | ❌ No — only additions alert |
| A flaky scrape misses some showtimes | ❌ No — see below |

**Where the 6-day cutoff comes from.** A cinema finalising next week's times and a real ticket wave both look like "new showtimes"; only lead time separates them. Measured from actual false positives this produced — showtimes for Aug 8 detected Aug 5 (3 days), and Aug 7 detected Aug 5 (2 days) — against `RESEARCH.md`, where the shortest lead of any real 70mm wave on record is 22 days (Sinners) and the rest run 29–256. Anything from 4 to 21 separates them cleanly. 6 sits at the cautious end: 2× clear of observed churn, still fires on anything a week or more out, deliberately trading some false positives for a lower chance of a miss. US cinemas schedule weekly, so churn at 4–7 days is plausible on a week not yet seen; if that appears, raise `MIN_LEAD_DAYS` in `monitor.py` toward 14.

Note the suppression only ever applies to a **date already known**. Everything about Dune is unaffected until roughly Dec 11, since its dates sit ~130 days out.

**The known set is a union, never a replacement.** Early on it *was* a replacement, and that caused a real bug: Fandango's scrape returned 103 showtimes on some passes and 110 on others, so a flaky pass shrank the known set and the next healthy pass re-reported those 7 as brand new. The symptom was two "new showtimes" emails with nothing actually released in between, the second appearing to "complete" the first. A union cannot do this — a partial scrape simply contributes nothing.

Past showtimes are pruned (they can't be bought); Reddit mentions are kept 30 days, far longer than the ~3 days of posts a feed carries, so a pruned post can't scroll back and re-alert.

**Clicks are rationed, coverage is not.** Reading a date button's label is free, so all dates up to `LABEL_CAP=60` are listed every run. Clicking is a request, so only *unseen* dates plus the nearest `NEAR_TERM_RESCAN=6` known ones get scanned. A brand-new date is always scanned the run it appears. This is both cheaper and more complete than the old fixed `MAX_DATES=12`, which silently capped The Odyssey at Aug 5–16 while its run reached mid-September.

### What the Reddit source can and cannot see

Worth being blunt, because it is easy to over-trust:

- **It reads posts, not comments.** `new.rss` lists top-level submissions only. If on-sale news breaks as a *comment* inside an existing megathread — a very common pattern for big releases — this source will never see it. There is no cheap fix; treat it as a known blind spot and rely on Fandango as the primary signal.
- **Reddit rate-limits it.** Two feeds fetched back to back reliably 429 the second one. Because the order used to be fixed, r/dune was *always* the loser, and every stored run read `1 of 2 feeds blocked` — meaning the Dune subreddit was effectively never monitored. The order now rotates and there is a pause between feeds, so each subreddit gets read roughly every other run instead of one being permanently dark. This is a mitigation, not a cure: expect to still see `1 of 2 feeds blocked` regularly.
- **It only sees the ~25 most recent posts.** Fine at r/imax's ~9 posts/day, but a burst could push a post out of the window between checks.
- **It is a bonus, not a safety net.** Its whole value is the ~30 minutes between an announcement and Fandango listing the showtimes. Fandango is what actually guarantees you find out.

**Reddit alerts require availability wording**, not just a film mention. `ONSALE_KEYWORDS` demands phrasing like "on sale", "presale", "tickets are live". The earlier rule accepted "imax" or "70mm" as context, which inside r/imax matches nearly every post — it emailed a photo of film strips, a Colorado show report, and a London screening announcement, none of them Metreon on-sale signals. This source exists solely to catch an announcement in the ~30 minutes before Fandango lists it; discussion posts can't do that job.

---

## Troubleshooting

### `535 5.7.8 Username and Password not accepted`

SMTP is rejecting the credential **pair**, not the monitor. The message reads like a bad password, but in practice it is almost always one of these, in order of likelihood:

1. **`GMAIL_ADDRESS` is not the account the app password belongs to.** This is the common one, and it bit this project once already: a placeholder address was left in the config while the real sender account had a different name. Easiest way to find the true address: open any alert email the monitor has already sent successfully and read its `From:` header.
2. **The app password was generated while signed into a different Google account** (e.g. your personal one). App passwords are per-account. Regenerate while signed into the sender account specifically.
3. **2-Step Verification is off** on the sender account. App passwords do not exist without it.
4. ~~Password pasted with spaces~~ — handled in code now; `alert.py` strips whitespace, so either form works.

Isolate it in one step, which tests auth only and sends nothing:

```bash
source ~/.dune-metreon-watch.env && .venv/bin/python -c "
import os, smtplib
a=os.environ['GMAIL_ADDRESS'].strip(); p=''.join(os.environ['GMAIL_APP_PASSWORD'].split())
s=smtplib.SMTP_SSL('smtp.gmail.com',465,timeout=20); s.login(a,p); print('LOGIN OK for',a); s.quit()"
```

If that prints `LOGIN OK`, the credentials are fine and any remaining failure is elsewhere.

**A failed send is not a lost drop.** `monitor.py` deliberately leaves newly-found showtimes out of `known_showtimes` when delivery fails, so the next run re-detects and re-sends them. You get a duplicate email later rather than a silently forgotten drop.

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
