# FORECAST.md — Next Metreon 70mm Wave for Dune: Part Three

Based on `RESEARCH.md`'s dataset (7 events, ~9 waves, N is small — see confidence statement below).

## Ranked windows

### 1. Oct 20 – Nov 20, 2026, centered ~Nov 5–10 (primary forecast)

Four comparable *wide-release* lead times converge here:

| Analog | Lead time before release | Applied to Dec 18, 2026 |
|---|---|---|
| Oppenheimer | 50 days | Oct 29 |
| Dune: Part Two | 35 days | Nov 13 |
| Interstellar re-release | 29 days | Nov 19 |
| The Odyssey Wave 2 | 43 days | Nov 5 |

The Odyssey is the strongest single analog: it's the same "early advance/teaser wave → later broader release-window wave" two-stage structure that Dune: Part Three's own April wave already exhibits (opening-weekend-only, small venue count, framed explicitly as "the first wave"). If Dune: Part Three follows the same shape, its next wave lands ~43 days out, i.e. **~Nov 5, 2026**, with the other three analogs bracketing it Oct 29 – Nov 19.

**What this wave likely covers:** either (a) additional showtime dates at the same 19 flagship 70mm venues (Metreon's Dec 17–20 window expanding to more days), or (b) a broader nationwide on-sale for standard/digital IMAX formats with 70mm folded in. Both are plausible; either way Metreon should get new dates in this window.

### 2. A lower-probability earlier "surprise" wave, Aug–Sept 2026

Sinners had 4 separate waves, not 2, and studios/IMAX have trended toward earlier, more frequent on-sale events (Odyssey's 365-day advance wave was unprecedented). An early expansion wave — more Metreon dates added to the existing 19-venue set, without a full nationwide sale — can't be ruled out. This is exactly why cadence should already be elevated now rather than waiting for fall; it's covered by the existing hourly-from-now schedule regardless of which window turns out correct.

### 3. A final pre-release wave within ~1–2 weeks of Dec 18, 2026

Both Dune: Part Two and The Odyssey added extension/expansion waves close to their own release windows. Already covered by the December 5–10 min cadence.

## Day of week / time (Pacific)

**Best estimate: Tue–Thu, 8–11am PT.** This brackets the two most relevant data points — Dune: Part Three's own April wave (Monday, 9:00am PT) and The Odyssey's Wave 2 (Thursday, 9:00am PT), both landing right at 9am PT / 12pm ET.

**Be honest about the exceptions:** the single most relevant precedent — Dune: Part Three's own prior wave — broke the weekday-cluster pattern by landing on a **Monday**, not Tue–Thu. The Odyssey's Wave 1 was a midnight-ET (9pm PT) launch, structurally different (teaser-attached, not release-window). Two of the highest-quality, most-relevant data points in the dataset are the ones that don't fit the naive majority pattern. Treat Monday and evening-PT as live possibilities, not outliers to dismiss.

## Confidence statement

This is pattern-matching over roughly 7 events / 9 waves, most originating from the same small cluster of IMAX Corp + studio (Warner Bros/Legendary/Universal) marketing teams — which raises relevance (plausibly the same playbook, possibly overlapping people) but does not make this a statistically robust sample. **No real confidence intervals are computable from N≈9 with 2 known pattern-breakers.** The honest summary: on-sales for this class of event cluster around late-morning Pacific time, tend to land in the 3–8 week pre-release window when it's not an ultra-early teaser wave, and are announced with anywhere from 30 minutes to a few days of public notice — but Dune: Part Three's own prior wave and The Odyssey's Wave 1 both individually broke a pattern the other data would otherwise suggest. Use the Oct 20–Nov 20 window to justify tightening cadence, not as a probability to bet the whole detection strategy on — which is why the monitor polls continuously through the full window rather than concentrating effort narrowly around the point estimate.

**What would update this forecast:**
- Any leading indicator below firing (supersedes statistical inference immediately).
- An actual confirmed date reported by IMAX, AMC, or trade press.
- Evidence of a second Dune: Part Three wave already having happened between April and today (unconfirmed either way per `RESEARCH.md`) — would reset the "waves so far" count and change the interval-based reasoning.

## Leading indicators (secondary signals — spike polling frequency, don't rely on them alone)

1. **Studio/IMAX/Warner Bros/Legendary social post, or trade-press account (e.g. @DiscussingFilm-style)** announcing an imminent or already-live on-sale. Historically 30 minutes (Dune: Part Three's own precedent) to 3 days (Odyssey Wave 1) ahead — too short and inconsistent to be the primary detection method, but a reliable trigger to temporarily increase check frequency.
2. **Fandango listing appearing before AMC's own site** — user-specified historical pattern. Not independently confirmed in this research pass, but structurally plausible: Fandango's page returns 200 OK while AMC's is behind a Cloudflare/Queue-it wall, so Fandango may in practice be the first source the monitor can actually *see* even if AMC's internal systems update first.
3. **The film appearing in AMC's "Coming Soon" section for Metreon with a new date**, before tickets are purchasable — a pre-stage signal worth watching even though it wasn't cleanly isolated in the research.
4. **A dated trade-press article confirming a specific future on-sale date** ahead of time (Interstellar precedent: confirmed 30 days ahead).
5. **A Queue-it waiting-room interstitial appearing on AMC's site where a normal page used to load** — discovered during this research's technical recon (AMC's Cloudflare layer intercepts traffic spikes with a virtual waiting room). If the monitor's AMC check suddenly hits that interstitial instead of its usual response, that's strong evidence of a live traffic spike — quite possibly the drop happening in real time — and should trigger an immediate alert distinct from the normal "no showtimes yet" state.

## Cadence alignment check

The user's own cadence ramp (hourly now, 15-min Oct–Nov, 5–10 min December) already brackets the Oct 20–Nov 20 primary forecast window and covers the low-probability Aug–Sept and post-Nov-30 tails adequately given the hourly baseline starts immediately. No cadence changes are suggested beyond what's already specified — the forecast validates the existing plan rather than requiring adjustment to it.
