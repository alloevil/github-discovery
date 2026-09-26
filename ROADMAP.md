# Roadmap

> Moved from issue #4 on 2026-09-04. Issues are for bug reports and feature requests; the roadmap lives here. To pick up an item, open an issue referencing it.

## Where we are

- **6 data sources** — GitHub Trending, GitHub Search (new & rising), Hacker News Show HN, rising fork-signal detection, AI/ML trending (OSSInsight), HF Daily Papers repo links
- **100-point scorer** — acceleration (40) + quality (30) + anti-spam (30), with code-quality bonus, suspicious-star and batch-fraud penalties, and an explainable reason line on every card
- **Cross-day dedup** with a 7-day window, deep checks budgeted to the top-K candidates after coarse ranking
- **Delivery** — daily email digest via Resend (dark-mode HTML) + GitHub Pages site with date/language filters
- **Current quality baseline** — 197 tests and 19 executable receipts; the site, feed and daily JSON are generated from committed reports. The presentation pass (light/dark themes, two-band header, merged report header, lead-card treatment) is complete; further UI work is gated by a user task or a measured defect.

## Long-term operating plan

### North star

Help a developer find a repository **before it becomes obvious**, understand why it was selected within one minute, and decide whether to try it without trusting an opaque score. The product is not a prettier trending list; it is an evidence-backed early-signal service.

### Quality bars

Every change is evaluated against these bars, in this order:

1. **Freshness** — the daily report, committed JSON, site, feed and email refer to the same run; a stale or partial run is visible and never presented as success.
2. **Evidence** — every recommendation has source provenance, score components and an explainable reason; every scoring change has a forward-only evaluation plan.
3. **Signal** — report breakout rates, lead time and source contribution include their cohort size and coverage. Thin data is reported as unknown, not converted into a marketing claim.
4. **Reliability** — reruns are idempotent, source failures are explicit, and deployment cannot publish older data over a newer daily run.
5. **Product value** — subscribers can control what they receive, stop receiving it safely, and consume the same picks through web, feed and email.

### Delivery sequence

#### Phase 0 — Instrument the system before tuning it (active)

- Add a daily source-health summary: fetched, parsed, rejected, deduplicated and finally recommended counts per source.
- Add a build-parity check covering the report date in `data/`, `docs/index.html`, `feed.xml` and the deployed commit.
- Publish watch-list coverage and mature-cohort counts next to the backtest; never compare score buckets without enough labelled observations.
- Document the single deployment path: the workflow publishes `docs/` to `gh-pages`; a manual deploy must first fast-forward to the newest daily commit.

**Exit gate:** two weeks of runs with source-health, parity and follow-up coverage reproducible from committed artifacts; no silent partial-success path.

#### Phase 1 — Establish whether the score works (next)

- Keep the current score frozen while collecting mature seven-day cohorts.
- Report score deciles, source combinations, lead time and breakout labels with `N`, coverage and confidence caveats.
- Change one scoring weight at a time, record the hypothesis before the run, and compare against a holdout period. No tuning from a single weekly table.

**Exit gate:** at least two mature cohorts and at least 20 labelled observations in any bucket used for a comparison; otherwise the result remains “not yet measurable”.

#### Phase 2 — Improve discovery coverage selectively (later)

- Add at most one new source per experiment: Product Hunt developer tools, Reddit programming/ML, or another source with a documented early-signal hypothesis.
- Measure incremental unique recommendations, overlap with existing sources, lead time, breakout rate, spam rate, API cost and failure rate.
- Keep a source only if it adds measurable signal or meaningful coverage without degrading trust; source count alone is not a success metric.

#### Phase 3 — Close the subscriber loop (after trust baseline)

- Implement per-subscriber topic/language preferences.
- Add one-click unsubscribe and double opt-in; keep the address privacy fix covered by a regression receipt.
- Add a weekly digest only after the daily digest has stable delivery and preference semantics.
- Keep web, Atom and email generated from the same report model so channels cannot disagree.

#### Phase 4 — Product experience, driven by tasks (continuous, but not the priority)

Optimize only these tasks: find today’s strongest early signal, understand its evidence, compare another day, filter to a language, and follow the source. Use browser smoke checks and content invariants; do not add tracking merely to justify visual changes.

The current visual system is the baseline. Future UI work requires one of: a reproducible accessibility/layout defect, a failed task in a browser smoke scenario, or a measured content-clarity problem. Cosmetic churn is explicitly lower priority than Phases 0–3.

#### Phase 5 — Operational hardening (ongoing)

- Make daily workflow races safe when the two scheduled runs overlap with weekly backtest commits.
- Keep generated artifacts deterministic except for intentional daily data changes.
- Keep deployment provenance visible: source commit, generated report date and `gh-pages` commit must be recoverable after every publish.

### Review cadence

- **Every daily run:** freshness, source health, parity and idempotency.
- **Weekly:** mature-cohort backtest, source contribution and watch-list coverage.
- **Monthly:** choose one phase outcome, remove stale backlog items, and explicitly decide whether the next UI pass is justified by evidence.

The backlog below is subordinate to this sequence. A checkbox is not permission to implement out of order.

## Roadmap

- [x] **RSS/Atom feed** — publish the daily picks as a feed alongside the Pages site, for people who don't want email (#5)
- [ ] **Per-subscriber topic filters** — let a subscriber say "only Rust" or "only AI/ML"; requires structuring `subscribers.txt` into per-user preferences and filtering at digest render time (#6)
- [x] **Same-day percentile** — the 100-point total saturates (median 99 at discovery), so every candidate now carries `rank_in_pool` / `pool_size` / `top_pct` computed over the whole day's pool, shown on the card and in the digest
- [x] **Trending capture** — `data/trending-*.json` records the day's trending set from today onward; lead time is forward-only, which is why the comparison could not be made before
- [x] **Follow-up observations (watch list)** — every recommendation is observed for 14 days into `data/watch_series.json`, because the snapshot store only covered repos that re-entered the candidate pool (29/463 = 6.3% of recommendations had a 7-day reading on 2026-09-14, which is not enough to test the score)
- [x] **Scoring backtest report in CI** — `scripts/backtest.py` now runs weekly and commits `reports/backtest-*.{csv,md}`: the label is a ≥200% seven-day rise, computed from the committed discovery reports and the watch series. First run (2026-09-14): 103/473 labelled (21.8%), 90–100 → 9.9% breakout (n=81), 80–89 → 18.2% (n=22) — **no evidence of predictive power yet, and the sample points the other way**; published as-is. Original item: (precision of high scores vs. actual takeoff) as a Pages sub-page so scoring changes are measured, not vibes
- [ ] **More sources** — Product Hunt dev tools and Reddit (r/programming, r/MachineLearning) are the strongest candidates; each new source is one `fetch_xxx()` in `scripts/sources.py` plus tests
- [ ] **Weekly digest mode** — a Monday roundup of the week's top 10 for low-volume subscribers

### Product

From a product review (2026-08-21) — trust and deliverability fixes for the subscription funnel:

- [x] Honor or drop the user-feedback scoring claim; make recommendation cards explainable (#9)
- [ ] Email subscription lifecycle: one-click unsubscribe + double opt-in (#10)

### Tech debt

Structural issues from a code review — worth fixing before they compound:

- [x] Decide the SQLite layer's fate: verify_scoring backtest is dead on ephemeral CI runners (#7)
- [x] Digest email leaks all subscriber addresses via a shared To header (#8)

## Non-goals

- Real-time/streaming detection — the daily cadence is the product; "before mainstream" ≠ "within the hour"
- Paid tiers or hosted multi-tenant service — this stays a fork-and-run tool

Numbered items have their own issues; unnumbered ones are open for discussion here first.
