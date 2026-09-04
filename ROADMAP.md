# Roadmap

> Moved from issue #4 on 2026-09-04. Issues are for bug reports and feature requests; the roadmap lives here. To pick up an item, open an issue referencing it.

## Where we are

- **6 data sources** — GitHub Trending, GitHub Search (new & rising), Hacker News Show HN, rising fork/watch detection, AI/ML trending (OSSInsight), HF Daily Papers repo links
- **100-point scorer** — acceleration (40) + quality (30) + anti-spam (30), with code-quality bonus, suspicious-star and batch-fraud penalties, and an explainable reason line on every card
- **Cross-day dedup** with a 7-day window, deep checks budgeted to the top-K candidates after coarse ranking
- **Delivery** — daily email digest via Resend (dark-mode HTML) + GitHub Pages site with date/language filters
- **117 unit tests**, fully automated on GitHub Actions — fork-and-go, no server

## Roadmap

- [x] **RSS/Atom feed** — publish the daily picks as a feed alongside the Pages site, for people who don't want email (#5)
- [ ] **Per-subscriber topic filters** — let a subscriber say "only Rust" or "only AI/ML"; requires structuring `subscribers.txt` into per-user preferences and filtering at digest render time (#6)
- [ ] **Scoring backtest report in CI** — `verify_scoring.py --days 30` exists but runs manually; publish a weekly backtest summary (precision of high scores vs. actual takeoff) as a Pages sub-page so scoring changes are measured, not vibes
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
