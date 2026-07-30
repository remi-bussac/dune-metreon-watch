# RESEARCH.md — 70mm / IMAX 70mm Ticket On-Sale Timing Dataset

Research date: 2026-07-30. Compiled from three parallel research passes over IMAX/AMC press releases, trade press, and site reconnaissance. Every claim below is either sourced inline or explicitly marked **UNVERIFIED**. Nothing is filled in with a plausible-sounding guess.

**Method note on Reddit:** the plan called for using r/imax and r/dune thread timestamps as primary evidence. Despite repeated attempts (direct fetch and web search), no specific Reddit threads for any of these events were retrievable — Reddit blocked direct programmatic fetches (403 / "network security" interstitial) and general web search did not surface indexed permalinks. This is a real gap, not a decision to skip Reddit; the monitor itself will still poll Reddit's RSS feeds going forward (see `FORECAST.md` and the monitor code), since RSS access from a script may behave differently than ad hoc web fetches/search did during this research pass.

---

## Summary table

| Event | On-sale (local) | Day | Release date | Lead time | Pre-announced? | Announce→sale gap | Sellout (flagship venue) | # Waves | Confidence |
|---|---|---|---|---|---|---|---|---|---|
| Oppenheimer 70mm (2023) | ~Jun 1, 2023 (exact time unverified) | Thu | Jul 21, 2023 | 50 days | No distinct pre-announcement found | ≈0 (simultaneous) | "sold out for 3-wk run" by wk4, no timestamp | 2 | Medium |
| Dune: Part Two 70mm (2024) | Jan 26, 2024 (~2pm ET, imprecise) | Fri | Mar 1, 2024 | 35 days | Format announced Nov 20, 2023 | 67 days | "essentially all sold out" by release day, no timestamp | 2 (+ extension wave 74d later) | Medium |
| Interstellar 70mm re-release (2024) | Nov 7, 2024 (some preload night before) | Thu | Dec 6, 2024 | 29 days | Yes, date confirmed 30d ahead | 30 days | Lincoln Sq: <15 shows left in <15h; fully sold in 24h | 2 (+ IMAX-digital wave 5d later) | Medium-High |
| The Odyssey Wave 1 (2025) | Jul 17, 2025, 12:00am ET = **9:00pm PT Jul 16** | Thu (Wed night PT) | Jul 17, 2026 | 365 days | Yes, leaked/reported 3 days ahead | 3 days | Lincoln Sq/TCL/BFI: <20 min; Metreon: front-2-rows-only within hours | 1 | High |
| The Odyssey Wave 2 (2026) | Jun 4, 2026, 12:00pm ET = **9:00am PT** | Thu | Jul 17, 2026 | 43 days | Yes, 1 day ahead | 1 day | Nationwide site/app crash; per-venue time unverified | 1 (+ standard-format wave 5d later) | High |
| Sinners 70mm (2025) | By Mar 27, 2025 (exact time unverified) | Thu (unverified) | Apr 18, 2025 | ≥22 days | Unverified | Unverified | Unverified | 4 total (orig + May/Oct/Dec re-releases) | Low |
| **Dune: Part Three (2026) — the wave that already happened** | **Apr 6, 2026, 9:00am PT** (12:00pm ET) | **Mon** | Dec 18, 2026 | 256 days (~8.5 mo) | Yes, ~30 min ahead | **~30 minutes** | Lincoln Sq: ~30min; Metreon: no exact timestamp, resale listings within minutes | 1 confirmed so far | **High — direct precedent** |

---

## 1. Oppenheimer (2023)

- Film release: Friday, Jul 21, 2023. Source: [Fandango](https://www.fandango.com/movie-news/oppenheimer-premium-format-tickets-on-sale-now-754822)
- Premium-format (incl. IMAX 70mm) on-sale: Thursday, Jun 1, 2023. Article timestamp 5:00am PT — likely a CMS publish time, not a verified clock-time for on-sale. **UNVERIFIED at the minute level.** Source: same as above.
- Standard-format wave: Thursday, Jun 8, 2023 — 7 days after the premium wave. Source: [Fandango](https://www.fandango.com/movie-news/tickets-for-all-oppenheimer-formats-on-sale-now-754827)
- Lead time: 50 days (Jun 1 → Jul 21).
- Pre-announcement: **not found** — no press release or IMAX post precedes the Jun 1 on-sale; the full 30-theater 70mm venue list was reported ~Jun 5, i.e. *after* on-sale. Sources: [Y.M. Cinema Magazine, Jun 5, 2023](https://ymcinema.com/2023/06/05/oppenheimer-imax-70mm-screening-at-only-30-theaters-worldwide/), [FlatpanelsHD](https://www.flatpanelshd.com/news.php?subaction=showfull&id=1685963488)
- 70mm venues included **AMC Metreon 16 (San Francisco)** and AMC Lincoln Square 13 (New York). Source: [in70mm.com cinema database](https://www.in70mm.com/presents/1970_imax/2023_oppenheimer/cinema/)
- Sellout: no precise timestamp. A first-person account four weeks post-on-sale reports Lincoln Square "sold out for the three-week run except some front-row seats." Source: [The Tin Man blog, Jul 25, 2023](http://www.tinmanic.com/archives/2023/07/25/oppenheimer-at-amc-lincoln-square-imax-70mm/). Scalped tickets $499–$1,400 by late July corroborate rapid sellout without giving a timestamp. Source: [ScreenRant, Jul 26, 2023](https://screenrant.com/oppenheimer-movie-70mm-tickets-craigslist-prices/)
- Context: run extended through Aug 31, 2023 ([Variety](https://variety.com/2023/film/news/oppenheimer-imax-70mm-extended-tickets-1235689899/)); a one-week 70mm encore ran Nov 3–9, 2023 at 6 venues including Metreon and Lincoln Square, explicitly because those sold out fastest originally ([Variety](https://variety.com/2023/film/news/christopher-nolan-oppenheimer-imax-re-release-1235774308/)).

## 2. Dune: Part Two (2024)

- Film release: Friday, Mar 1, 2024. Source: [IMAX](https://www.imax.com/news/dune-part-two-imax-70mm-film-tickets-now-on-sale)
- 70mm on-sale: press release published Thu Jan 25, 2024 announcing tickets go live "1/26" (Fri); coverage confirms tickets live by 4:17pm ET Jan 26. Sources: [Bleeding Cool, Jan 26, 2024, 4:17pm CST](https://bleedingcool.com/movies/dune-part-two-70mm-imax-release-announced-tickets-on-sale-tv-spot/), [IMAX](https://www.imax.com/news/dune-part-two-imax-70mm-film-tickets-now-on-sale)
- Lead time: ~35 days.
- Pre-announcement: the 70mm format decision itself was announced Nov 20, 2023 — 67 days ahead of on-sale, credited to Oppenheimer's success. Source: [The Credits/MPA, Nov 20, 2023](https://www.motionpictures.org/2023/11/dune-part-two-moves-up-two-weeks-secures-imax-70mm-screens/)
- 70mm venues: 12 flagship theaters worldwide including **AMC Metreon 16** and AMC Lincoln Square 13. Source: [Y.M. Cinema Magazine, Jan 31, 2024](https://ymcinema.com/2024/01/31/dune-part-two-imax-70mm-screening-at-only-12-theaters-worldwide/)
- Second wave: Apr 8, 2024 — a 2-week run extension; 70mm tickets for the two flagship venues (LA CityWalk, NYC Lincoln Square) on sale same-day, other ~20 IMAX-digital markets went on sale 7 days later (Apr 15) — an internal stagger within the wave. Source: [IMAX press release mirror, Apr 8, 2024](https://markets.financialcontent.com/clarkebroadcasting.mymotherlode/article/bizwire-2024-4-8-imax-extends-theatrical-run-of-dune-part-two-in-theaters-across-north-america-in-response-to-high-fan-demand)
- Sellout: no precise timestamp. Variety reports fans booking a 3:15am Lincoln Square screening on release day specifically because "essentially every other 70mm IMAX showing was sold out." Source: [Variety, Mar 1, 2024](https://variety.com/2024/film/news/dune-2-imax-70mm-3-am-1235927960/)

## 3. Interstellar 10th-anniversary 70mm re-release (2024)

- Engagement: Dec 6–13, 2024 (one week). Source: [attractionsmagazine.com](https://attractionsmagazine.com/interstellar-imax-70mm-10th-anniversary-tickets/)
- On-sale: Thursday, Nov 7, 2024. No exact clock time found; an IMAX spokesperson said AMC "began to preload tickets online the night before," so functional availability at some theaters began the evening of Nov 6. Sources: [Gothamist, Nov 27, 2024](https://gothamist.com/arts-entertainment/interstellar-tickets-are-selling-for-215-in-nyc-10-years-after-its-release), [IMAX press release](https://www.imax.com/news/interstellar-IMAX-Exclusive-IMAX-70mm-film)
- Lead time: 29 days.
- Pre-announcement chain (multi-stage):
  1. Original re-release date (Sept 27, 2024) announced at CinemaCon, reported Apr 11, 2024, 10:49am PT. Source: [Variety](https://variety.com/2024/film/news/interstellar-imax-70-mm-rerelease-fall-2024-christopher-nolan-1235967907/)
  2. Date pushed to Dec 6, 2024, reported Aug 7, 2024, 12:37pm PT. Source: [Variety](https://variety.com/2024/film/news/christopher-nolan-interstellar-10th-anniversary-rerelease-delayed-70mm-prints-1236098730/)
  3. The specific Nov 7 on-sale date was publicly confirmed by Oct 8, 2024 — 30 days ahead. Source: [Collider, Oct 8, 2024](https://collider.com/interstellar-10th-anniversary-imax-screenings/)
- Waves: 2 — 70mm film Nov 7; IMAX-digital tickets Nov 12 (moderate confidence — corroborated only via aggregator search summary, primary IMAX page not independently opened).
- 70mm venues: 8 US cities + 2 Canadian, including **AMC Metreon 16** and AMC Lincoln Square 13. Source: [IMAX press release](https://www.imax.com/news/interstellar-IMAX-Exclusive-IMAX-70mm-film)
- Sellout — best-documented of the pre-2026 events:
  - Fewer than 15 showings remained at Lincoln Square within 15 hours of on-sale. Source: [Kotaku, Nov 8, 2024](https://kotaku.com/interstellar-10th-anniversary-imax-return-tickets-1851694027)
  - All 24 Lincoln Square screenings sold out within 24 hours; resale up to $215. Source: [Gothamist, Nov 27, 2024](https://gothamist.com/arts-entertainment/interstellar-tickets-are-selling-for-215-in-nyc-10-years-after-its-release)
  - Rollout was inconsistent across platforms — some fans got AMC-app tickets before Fandango listings appeared, hours later. Same Gothamist source.

## 4. The Odyssey (2026) — Wave 1: teaser-attached advance sale

- On-sale: Thursday, Jul 17, 2025, 12:00am ET = **9:00pm PT Wednesday Jul 16, 2025**. Source: [Hollywood Reporter](https://www.hollywoodreporter.com/movies/movie-news/christopher-nolan-odyssey-tickets-on-sale-a-year-out-1236318177/); PT framing corroborated by [CBS News Sacramento, 11:21pm PDT Jul 16](https://www.cbsnews.com/sacramento/news/the-odyssey-christopher-nolan-imax-70mm-july-2026-tickets)
- Format: IMAX 70mm screens specifically. Source: [Hollywood Reporter](https://www.hollywoodreporter.com/movies/movie-news/christopher-nolan-odyssey-sells-out-year-early-1236319117/)
- Film release: Jul 17, 2026 → **lead time exactly 365 days**, first time in history tickets sold a full year ahead. Source: same HR article.
- Pre-announcement: [World of Reel, Jul 14, 2025](https://www.worldofreel.com/blog/2025/7/14/the-odyssey-70mm-imax-tickets-are-going-on-sale-a-year-in-advance-this-thursday-july-17) reported the date 3 days ahead; some chains (Harkins, Cinemark) posted 70mm showtimes even earlier than the official studio/IMAX comment. Universal/IMAX declined to comment when asked directly. Source: [AOL](https://www.aol.com/odyssey-imax-tickets-sale-christopher-180000230.html)
- Teaser trailer (theatrical-only, attached to Jurassic World: Rebirth) released Jul 1, 2025 — 16 days before on-sale. **UNVERIFIED at primary-source level**, only secondary corroboration found.
- Sellout: ~95% of seats nationally within 1 hour (~$1.5M sales). Source: [Hollywood Reporter](https://www.hollywoodreporter.com/movies/movie-news/christopher-nolan-odyssey-sells-out-year-early-1236319117/). Lincoln Square/TCL Chinese/BFI IMAX: under 20 minutes. Source: [Y.M. Cinema Magazine](https://ymcinema.com/2025/07/18/imax-70mm-tickets-for-christopher-nolans-the-odyssey-are-already-selling-out/). **AMC Metreon 16**: "only the front two rows had seats remaining" within hours of the launch. Source: [CBS News Sacramento](https://www.cbsnews.com/sacramento/news/the-odyssey-christopher-nolan-imax-70mm-july-2026-tickets)
- Scope: ~26 locations (16 US, 6 Canada, 2 UK, 1 Australia, 1 Czech Republic), covering opening-weekend-only screenings (the film wasn't finished editing yet).
- Resale: $300–$400 vs $25–28 face value within a day. Source: [Hollywood Reporter](https://www.hollywoodreporter.com/movies/movie-news/christopher-nolan-odyssey-sells-out-year-early-1236319117/)

## 5. The Odyssey (2026) — Wave 2: release-window sale

- On-sale: Thursday, Jun 4, 2026, 12:00pm ET = **9:00am PT**. Source: [Gizmodo](https://gizmodo.com/the-odyssey-movie-tickets-imax-on-sale-date-christopher-nolan-2000767127)
- Pre-announcement: social post Jun 3, 2026 — 1 day ahead. Same source.
- Standard/all-format tickets: Jun 9, 2026 (third tier). Source: [ResetEra](https://www.resetera.com/threads/new-poster-for-the-odyssey-tickets-for-all-plf-and-imax-formats-on-sale-now-standard-tickets-june-9.1538464/)
- Lead time: 43 days (Jun 4 → Jul 17 release).
- Scope: covered showtimes beyond opening weekend (Wave 1 was opening-weekend-only). Same Gizmodo source.
- Demand: AMC's and Fandango's sites/apps crashed; AMC queue wait exceeded an hour before being "paused entirely." Highest studio PLF/IMAX presale AMC had recorded since 2022. Sources: [Forbes](https://www.forbes.com/sites/bennyhareven/2026/06/05/us-cinema-website-crash-as-tickets-for-the-odyssey-go-on-sale/), [Rolling Stone](https://www.rollingstone.com/tv-movies/tv-movie-news/christopher-nolan-the-odyssey-ticketing-fiasco-1235572583/), [Variety](https://variety.com/2026/film/news/the-odyssey-amc-app-ticket-demand-christopher-nolan-epic-1236766869/). No Metreon/Lincoln-Square-specific sellout timestamp found — **UNVERIFIED at venue level**.
- UK sub-wave: separate on-sale Jun 15, 2026. Source: [Forbes](https://www.forbes.com/sites/bennyhareven/2026/06/05/us-cinema-website-crash-as-tickets-for-the-odyssey-go-on-sale/)
- Resale up to $1,000–$1,500 on eBay. Sources: [Eastern Herald](https://easternherald.com/2026/06/07/odyssey-christopher-nolan-imax-70mm-ticket-crash-amc-ebay-resale/), [GamesRadar+](https://www.gamesradar.com/entertainment/action-movies/the-odyssey-fans-crash-multiple-sites-in-the-hunt-for-imax-70mm-tickets-which-are-now-being-resold-for-up-to-usd1000-online/)

## 5b. The Odyssey — post-release IMAX 70mm run extension (2026, discovered incidentally)

Directly relevant to the monitor's live-test design (see `FORECAST.md`): as of the research date (Jul 30, 2026), The Odyssey's IMAX 70mm run — originally slated to end Aug 19, 2026 — was just extended through **Sept 16, 2026** due to sustained demand, with showtimes "selling out seven weeks in advance" and some flagship theaters adding 2am/6am shows. Sources: [CNBC, Jul 30, 2026](https://www.cnbc.com/2026/07/30/the-odyssey-70mm-imax-run-extended-until-september.html), [Forbes, Jul 30, 2026](https://www.forbes.com/sites/antoniopequenoiv/2026/07/30/coveted-the-odyssey-imax-70mm-screenings-extended-after-weeks-of-sold-out-showings/), [Variety](https://variety.com/2026/film/news/the-odyssey-imax-70mm-showtimes-will-there-be-more-tickets-1236816709/). Metreon 16 showtimes confirmed for the initial run: 2pm Jul 16 (preview) and 7pm Jul 17–19, 2026, per aggregated search results referencing [AMC's Odyssey pages](https://www.amctheatres.com/movies/the-odyssey-80679/showtimes) and [Fandango](https://www.fandango.com/the-odyssey-the-imax-70mm-experience-2026-241386/movie-overview).

## 6. Sinners (2025)

- Release: Apr 18, 2025 wide; early-access IMAX 70mm event screenings Apr 16, 2025. Source: [AMC Theatres](https://www.amctheatres.com/movies/sinners-early-access-imax-70mm-event-79855)
- On-sale: confirmed live by Mar 27, 2025 (Forbes publish date) — **exact date/time UNVERIFIED**, only "late March 2025" confirmed. Source: [Forbes](https://www.forbes.com/sites/bennyhareven/2025/03/27/imax-70mmtickets-for-sinners-are-now-on-sale-at-least-in-the-usa/)
- Lead time: ≥22 days (likely more, exact on-sale date not pinned down).
- Pre-announcement / sellout time at Lincoln Square or Metreon for the original run: **UNVERIFIED**, no source found despite extensive searching.
- Subsequent waves (this is the best-documented multi-wave case in the dataset):
  - Wave 2: limited re-release May 15–21, 2025, 9 select IMAX 70mm theaters. Source: [AOL](https://www.aol.com/entertainment/sinners-sets-imax-70mm-release-162458479.html)
  - Wave 3: one-week return Oct 30, 2025, 10 named 70mm venues including **AMC Lincoln Square** and **AMC Metreon**. Source: [BusinessWire, Oct 21, 2025, 1:00pm EDT](https://www.businesswire.com/news/home/20251021876000/en/Ryan-Coogler%E2%80%99s-Visually-Groundbreaking-Hit-Sinners-Returns-to-IMAX%C2%AE-70MM-and-IMAX%C2%AE-Theatres)
  - Wave 4: returned Dec 12, 2025 (one week, paired with One Battle After Another promotion). Source: [Bloody Disgusting](https://bloody-disgusting.com/movie/3918916/ryan-cooglers-sinners-return-to-imax-70mm-theaters-in-december/)
- No sellout-time or announcement-gap data found for any Sinners wave.

## 7. Dune: Part Three (2026) — the April wave (direct precedent)

This is the same film and venue the monitor targets, so it's the highest-weight data point in the dataset.

- On-sale: **Monday, Apr 6, 2026, 9:00am PT** (12:00pm ET), per the official Dune Instagram/Facebook post: "Tickets on sale at 9am PT." Source: [facebook.com/dune](https://www.facebook.com/dune/posts/be-the-first-to-get-tickets-to-experience-dune-part-three-in-imax-70mm-tickets-o/1284176247141749/). Corroborated by a firsthand account: tickets "went on sale minutes before their scheduled time at 12 p.m. [ET]." Source: [FlickNerd, Apr 7, 2026](https://flicknerd.com/2026/04/07/dune-part-three-sells-out-limited-imax-70mm-screenings-months-before-release-the-eventification-of-moviegoing/)
- Format: IMAX 70mm, opening-weekend-only, one 7:00pm local showing/day per theater, Dec 17–20, 2026. Source: [JoBlo](https://www.joblo.com/dune-part-three-70mm-imax/)
- Release date: Dec 18, 2026 → lead time ~256 days, explicitly framed by press as "eight months early." Source: [FanBolt](https://www.fanbolt.com/172694/dune-part-three-imax-70mm-tickets-sell-out-in-minutes-eight-months-early/)
- Pre-announcement: an X/Twitter post from @DiscussingFilm — *"Warner Bros has just announced that IMAX 70mm tickets for 'DUNE: PART 3' go on sale in 30 MINUTES"* — corroborated independently by the FlickNerd firsthand account ("received Instagram notification that tickets were going to go on sale in a half hour"). **Announcement came first, ~30 minutes ahead of on-sale.** Source: [x.com/DiscussingFilm/status/2041176929781338174](https://x.com/DiscussingFilm/status/2041176929781338174) (reconstructed from search snippet, tweet itself 402'd on fetch)
- Sellout: "sold out within minutes" broadly reported. Sources: [SlashFilm](https://www.slashfilm.com/2141644/dune-3-imax-70mm-tickets-reselling-price-hike/), [FanBolt](https://www.fanbolt.com/172694/dune-part-three-imax-70mm-tickets-sell-out-in-minutes-eight-months-early/). More granular: Lincoln Square's 7pm Dec 18 show sold out within ~30 minutes of the FlickNerd author's own purchase. **AMC Metreon 16: no exact sellout timestamp found** — eBay resale listings for Metreon seats ($2,100 for 3 seats) appeared "within minutes of the first batch selling out." Sources: [FanBolt](https://www.fanbolt.com/172694/dune-part-three-imax-70mm-tickets-sell-out-in-minutes-eight-months-early/), [eBay listings](https://www.ebay.com/itm/178036314966). A conflicting "sold out in under 12 hours" claim from a lower-confidence aggregator is **discounted** in favor of the "minutes" reports from established outlets.
- Scope: 19 initial locations worldwide (15 US incl. 2 in SF, 2 Canada, Melbourne, London), explicitly called "the first wave" by press, with a notification signup mentioned for future waves. Sources: [Hollywood Reporter](https://www.hollywoodreporter.com/movies/movie-news/dune-part-three-imax-tickets-1236556474/), [Nerdist via Facebook](https://www.facebook.com/Nerdist/posts/the-first-wave-of-dune-part-three-imax-70mm-sold-out-in-minutes-but-you-can-sign/1377735714381922/)
- Not every showing sold out immediately — some 7pm and 10:45pm Dec 17 showings at a handful of theaters reportedly remained available after the initial rush (source for the specific theater list not independently re-verified — **UNVERIFIED**).
- Regional staggering: Melbourne had a separate on-sale (reported 3pm PT per a JoBlo-cited social post) — **UNVERIFIED exact mechanism**, but confirms the wave wasn't one single global timestamp.
- **Waves so far: 1 confirmed.** Multiple outlets call it "the first wave" and imply more are coming, but no source confirms a second wave has actually happened between April and the Jul 30, 2026 research date.

## 8. Bonus / flagged cases

- **F1: The Movie (2025):** IMAX premiere tickets on sale May 21, 2025; expanded after selling out in 25 markets; re-release tickets Aug 8, 2025. **Likely NOT true 70mm film** (standard digital IMAX 1.90:1) — included only for completeness, not counted in the summary table. Sources: [Formula1.com](https://corp.formula1.com/f1-the-movie-fan-first-premiere-screenings-expanded-and-general-tickets-go-on-sale-tomorrow/), [Variety](https://variety.com/2025/film/news/f1-imax-return-rerelease-tickets-1236480603/)
- **drop70mm.com ("IMAX Tracker"):** a third-party community tracker already monitoring Dune: Part Three and The Odyssey IMAX 70mm availability at AMC Metreon, Lincoln Square, and CityWalk Hollywood. Confirms independently that "AMC's queue is blocking our tracker" — i.e. a second party hit the same Cloudflare/Queue-it wall documented in the technical recon below. Not used as a monitored signal per user decision (see `FORECAST.md`), cited here for completeness. Source: [drop70mm.com](https://drop70mm.com)

---

## Technical reconnaissance (site behavior, for the monitor build)

- **amctheatres.com** — every direct fetch attempt (robots.txt, Metreon theater page, Dune film page) was intercepted by a **Cloudflare "Global Safety Net" Queue-it virtual waiting room** or returned a plain **403 Forbidden**. No crawl-delay or disallow list could be confirmed since robots.txt itself was blocked.
- **fandango.com/robots.txt** — retrieved successfully (200 OK). Disallows `/api/`, `/napi/*`, `/account/*`, and any URL with `?date=`/`?sdate=`/`?filter=my-theaters` query params. No crawl-delay directive. The Dune/Odyssey movie-overview pages return 200 OK but are client-rendered ("Loading calendar…" placeholder, no embedded JSON visible to a plain HTML fetch).
- **imax.com/robots.txt** and film pages — 403 Forbidden on every attempt.

**Implication:** a plain-HTTP scraper (`requests`/BeautifulSoup) cannot see AMC or IMAX at all, and can reach Fandango's shell but not its data. The monitor needs real headless-browser rendering (Playwright/Chromium) for AMC, IMAX, and Fandango — this is documented as the core architecture decision in `FORECAST.md`'s companion planning and in the monitor code itself.

## Could not verify (open gaps)

- Exact clock times for Oppenheimer, Dune: Part Two, and Sinners on-sales (only day-level or approximate times found).
- Any Reddit thread timestamps for any event (Reddit blocked all direct/search-based retrieval during this research pass).
- Precise minutes/hours-to-sellout for AMC Metreon 16 specifically, for any event — every case with a Metreon-specific data point describes qualitative scarcity ("front two rows only," "resale listings within minutes") rather than a measured timestamp.
- Whether a second Dune: Part Three wave has occurred between April and July 2026 — no source found confirming or denying this as of the research date.
- The exact mechanism behind regional on-sale staggering (e.g. Melbourne's separate time for Dune: Part Three).
