# GitHub Discovery

**GitHub Discovery** is a daily GitHub repository discovery pipeline that surfaces projects while they are still accelerating, for developers who want early signal instead of yesterday's popularity.

<p align="center">
  <img src="./assets/hero.svg" width="100%" alt="GitHub Discovery — spot trending repos before they go mainstream. 6 data sources, smart scoring, anti-spam, daily email digest.">
</p>

<p align="center">
  <img src="https://img.shields.io/github/actions/workflow/status/alloevil/github-discovery/daily.yml?branch=main&label=CI&logo=github&logoColor=white&color=00ccff" alt="CI" />
  <img src="https://img.shields.io/badge/license-MIT-00ccff?style=flat" alt="License" />
  <img src="https://img.shields.io/github/stars/alloevil/github-discovery?style=flat&logo=github&color=00ccff" alt="Stars" />
  <a href="https://alloevil.github.io/github-discovery/"><img src="https://img.shields.io/badge/website-live-00ccff?style=flat" alt="Website" /></a>
</p>

<p align="center">
  <a href="https://alloevil.github.io/github-discovery/">Website</a> · 
  <a href="#quick-start">Quick Start</a> · 
  <a href="#features">Features</a> · 
  <a href="#development">Development</a>
</p>

<p align="center">
  English | <a href="README.zh-CN.md">简体中文</a>
</p>

---

## What it is

GitHub Trending shows you what's popular **today**.

GitHub Discovery shows you what's **about to be popular** — repos with unusual growth patterns, community picks from Hacker News, and early-stage projects gaining traction.

Every day it collects signals from 6 data sources, runs them through a smart scoring system (100 points), and delivers curated results via email and web. The workflow is scheduled twice daily (04:43 and 08:43 UTC); a same-day guard makes the second run a no-op when the first one succeeded.

---

## How it works

```
  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
  │   GitHub    │  │   GitHub    │  │   Hacker    │
  │  Trending   │  │   Search    │  │    News     │
  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
         │                │                │
  ┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴──────┐
  │   Rising    │  │   AI/ML     │  │  HF Daily   │
  │  Detection  │  │  Keywords   │  │   Papers    │
  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
         │                │                │
         └────────────────┼────────────────┘
                          ▼
              ┌───────────────────────┐
              │    Smart Scorer       │
              │    (100 points)       │
              │  ─────────────────    │
              │  acceleration : 40    │
              │  quality      : 30    │
              │  anti-spam    : 30    │
              └───────────┬───────────┘
                          ▼
              ┌───────────────────────┐
              │  Cross-day Dedup      │
              │  (7-day window)       │
              └───────────┬───────────┘
                          ▼
         ┌────────────────┴────────────────┐
         ▼                                 ▼
  ┌─────────────┐                  ┌─────────────┐
  │ 📧 Email    │                  │ 🌐 GitHub   │
  │   Digest    │                  │    Pages    │
  └─────────────┘                  └─────────────┘
```

---

## Features

### 6 Data Sources

| Source | Signal | What it catches |
|--------|--------|-----------------|
| [GitHub Trending](https://github.com/trending) | Popularity | Daily trending repositories |
| GitHub Search | New & rising | Repos created in the last 7 days with fast star growth |
| [Hacker News](https://news.ycombinator.com/) | Community picks | GitHub repos from Show HN posts |
| Rising Detection | Early signal | Repos created in the last 3 days with a fork/star ratio above 0.3 and at most 0.5 — forks as an early usage signal; higher ratios are discarded as fork farms |
| AI/ML Keyword Sweep | AI focus | GitHub Search over an AI/ML keyword list, 5 keywords per day on a rotating schedule (inspired by [OSSInsight trending/ai](https://ossinsight.io/trending/ai), implemented against the GitHub Search API) |
| [HF Daily Papers](https://huggingface.co/papers) | Research signal | GitHub repos linked from trending Hugging Face papers — we assume paper upvotes lead GitHub stars by days, but no committed measurement backs that lead time yet |

### Smart Scoring (100 points)

| Dimension | Points | What it measures |
|-----------|--------|------------------|
| **Acceleration** | 40 | Real day-over-day star growth (from daily snapshots) + acceleration vs lifetime average |
| **Quality** | 30 | Age, language, license, content completeness |
| **Anti-spam** | 30 | Starts at 30 and deducts: star/fork ratio > 50, age < 3 days with 5000+ stars, marketing buzzwords, gaming-trainer or random-username patterns |
| **Code Quality** | +20 | README, CI config, commit frequency — scaled into the quality dimension rather than added on top |
| **Suspicious Stars** | -20 / -15 | Age ≤ 1 day with 1000+ stars (-20); age ≤ 2 days with 2000+ stars (-15); 1000+ stars/day with an empty description (-15) |
| **Batch Fraud** | up to -40 | Same owner with ≥ 3 repos in one batch (-15), ≥ 2 repos under 7 days old with 200+ stars (-15), template-similar descriptions (-10) |

### Anti-spam

- **Star fraud detection**: age ≤ 1 day with 1000+ stars, age ≤ 2 days with 2000+ stars, or 1000+ stars/day with an empty description → flagged
- **Batch fraud detection**: same owner with ≥ 3 repos in one batch, or ≥ 2 repos under 7 days old already past 200 stars → flagged
- **Content quality**: No description or no README → penalty
- **Cross-day dedup**: 7-day window, no duplicate recommendations across days (a same-day rerun may repeat a pick)

### Email Subscription

- Daily curated repos delivered to your inbox
- Rendered dark-only, with `color-scheme` declared for dark-aware clients (Apple Mail / iOS)
- Powered by Resend API

### RSS / Atom Feed

- Prefer a feed reader over email? Subscribe to the Atom feed:
  `https://alloevil.github.io/github-discovery/feed.xml`
- Last ~14 days of picks, regenerated with every daily run

### GitHub Pages

- Modern, professional web interface
- Filter by date and language
- Scores for the latest published run (the page is a static file rebuilt by the daily workflow)

---

## Install

Nothing to install: the pipeline uses the Python standard library only — no `pip install` and no `requirements.txt` — and CI runs Python 3.11. It does call the system `curl` binary for the Resend and Firecrawl HTTP requests.

```bash
git clone https://github.com/alloevil/github-discovery.git
cd github-discovery
python scripts/main.py   # one full run: collect → score → dedup → write output/ + data/
```

Sending the email digest needs a `RESEND_API_KEY`. Collection, scoring, the published site and the Atom feed need no key at all; `GITHUB_TOKEN` is optional and only raises the GitHub API rate limit from 60 to 5000 requests per hour. To run it as a daily automation rather than locally, follow Quick Start below.

---

## When to use it

- You want to see a library, tool or model in the days before it hits 10k stars, not after.
- You want the discovery decision to be inspectable: every recommendation carries its score, and every run's input data stays committed under `data/`.
- You want zero infrastructure — GitHub Actions plus one API key for email. No server, no database.
- You care about filtering manufactured popularity: star-authenticity checks, cross-repo batch-fraud detection and description/README quality checks all subtract from the score.

## When NOT to use it

- You want editorial judgement. This is a scoring function; it will sometimes rank a repo highly on acceleration alone.
- You want per-topic or per-user subscriptions. The six sources and their query thresholds are fixed in `scripts/sources.py` and the scoring weights in `scripts/config.py`; the site filters by date and language only after the fact.
- You want proof that a high score predicts long-term success. The committed backtest selected 20 repos with a 7-day report filter but observed their growth over roughly one day (all 20 entries have `days_since_discovery: 1`), at one point in time — enough to sanity-check the score, not enough to establish predictive power.
- You need every rising repo. Only repos that surface in one of the six sources can be scored, cross-day dedup suppresses a repo for 7 days after it is recommended, and the expensive per-repo quality and star-authenticity checks run only on the top `DEEP_CHECK_TOP_K` (20) candidates after coarse ranking.
- You want the AI/ML sweep to be exhaustive on a given day: it uses 5 keywords per day out of a rotating list, so one day covers only part of that space.

---

## Quick Start

### 1. Fork this repo

Click the **Fork** button in the top right corner.

### 2. Configure Secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret | Required | Description |
|--------|----------|-------------|
| `RESEND_API_KEY` | ✅ | [Resend](https://resend.com/) API Key for sending emails |
| `GITHUB_TOKEN` | ❌ | GitHub Personal Access Token (optional, uses GITHUB_TOKEN by default) |
| `FIRECRAWL_API_KEY` | ❌ | [Firecrawl](https://firecrawl.dev) key. Makes GitHub Trending parsing robust (scrapes the page instead of regex-matching raw HTML). Without it, Trending falls back to direct HTML scraping. |

### 3. Enable GitHub Actions

Go to **Actions** and click **I understand my workflows, go ahead and enable them**.

### 4. Test manually

Go to **Actions → Daily Discovery → Run workflow** to trigger a test run.

### 5. View results

- **GitHub Pages**: Visit `https://<your-username>.github.io/github-discovery/`
- **Email**: Subscribers receive daily digests

---

## Project Structure

```
github-discovery/
├── scripts/
│   ├── sources.py           # 6 data source collectors
│   ├── scorer.py            # Scoring algorithm
│   ├── quality.py           # Code quality detection
│   ├── anti_spam.py         # Anti-spam scoring dimension
│   ├── dedup.py             # Cross-day deduplication (7-day window)
│   ├── fraud_detection.py   # Batch fraud detection
│   ├── snapshots.py         # Daily star snapshots (real growth)
│   ├── verify_scoring.py    # Scoring verification / backtesting
│   ├── generate_site.py     # GitHub Pages site + Atom feed
│   ├── subscribe_handler.gs # Google Apps Script subscribe endpoint
│   ├── main.py              # Entry point
│   └── config.py            # Configuration
├── tests/                   # Unit tests (pytest)
├── docs/                    # GitHub Pages (index.html, feed.xml)
├── .github/workflows/       # Daily automation
└── subscribers.txt          # Email subscriber list
```

---

## Development

### Local Run

```bash
git clone https://github.com/alloevil/github-discovery.git
cd github-discovery
python scripts/main.py
```

### Run Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

### Add a New Data Source

1. Add a new `fetch_xxx()` function in `scripts/sources.py`
2. Call it in `fetch_all()`
3. Add tests in `tests/test_sources.py`
4. Submit a PR

### Scoring Algorithm

Scoring logic is in `scripts/scorer.py`. The dimension limits are constants in `scripts/config.py`:

```python
ACCELERATION_MAX = 40
QUALITY_MAX = 30
ANTISPAM_MAX = 30
QUALITY_BONUS_MAX = 20   # deep code-quality bonus, scaled into the quality dimension
DEEP_CHECK_TOP_K = 20    # how many coarse-ranked candidates get the expensive checks
```

---

## Scoring Verification

Run backtesting to verify whether high-scored repos actually took off. The
backtest reads the committed daily JSON reports (`data/discovery-*.json`),
so it works on a fresh clone with no prior run; it still needs network access,
because current star counts come from the GitHub API (anonymous, 60 req/hour,
unless `GITHUB_TOKEN` is set):

```bash
python scripts/verify_scoring.py --days 30
```

`--days N` selects reports by their date relative to *today*, so a run measures
the current window and recomputes growth against today's star counts. It does
not reproduce the committed `reports/verify-2026-06-25.json`: that snapshot's
input reports are no longer under `data/`, and its repositories' star counts
have since moved.

---

## FAQ

**How are the 100 points allocated?** Acceleration is worth up to 40 and measures real day-over-day star growth from the project's own committed snapshots plus acceleration against the repo's lifetime average. Quality is worth up to 30 (age, language, license, content completeness). Anti-spam starts at 30 and deducts for a star/fork ratio above 50, an age under 3 days with 5000+ stars, marketing buzzwords, and gaming-trainer or random-username patterns. A deep code-quality check adds a bonus of up to 20 that is scaled into the quality dimension, star-authenticity checks subtract 15 or 20, and batch fraud subtracts up to 40.

**Do I need any paid service?** Only for email. `RESEND_API_KEY` sends the digest through Resend; `FIRECRAWL_API_KEY` is optional and only makes GitHub Trending parsing more robust than regex-matching raw HTML. Everything else runs on the GitHub Actions free tier with the default `GITHUB_TOKEN`.

**Will the same repo be recommended every day while it is hot?** No. Cross-day dedup blocks any repo recommended in the previous 7 days, using the history committed at `data/recommend_history.json`; records older than 30 days are cleaned up. The history has to be a committed file because every CI run starts from a fresh checkout with no local state.

**Can I trust the numbers on the published page?** The page is a build artifact: `scripts/generate_site.py` renders `docs/index.html` from `docs/template.html` plus the committed reports, and the workflow publishes `docs/` to the `gh-pages` branch. The authoritative copies are the committed JSON under `data/`, which is what `verify_scoring.py` reads; the Markdown digests under `output/` are the human-readable copies, and the site reads the JSON first and falls back to those digests. So any claim on the page can be recomputed from a fresh clone.

**How do I add a data source?** Add a `fetch_xxx()` function in `scripts/sources.py`, call it from `fetch_all()`, and add tests in `tests/test_sources.py`. Sources return the same repo dict shape, so scoring, dedup and rendering need no changes.

---

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork this repo
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'feat: add your feature'`
4. Push the branch: `git push origin feature/your-feature`
5. Submit a Pull Request

### Contribution Ideas

- 📡 Add new data sources
- 🎯 Optimize scoring algorithm
- 🐛 Fix bugs
- 📖 Improve documentation
- ✅ Add tests

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Acknowledgements

- [GitHub API](https://docs.github.com/en/rest)
- [Hacker News API](https://github.com/HackerNews/API)
- [OSSInsight](https://ossinsight.io/) — AI/ML repository trends and analytics
- [Resend](https://resend.com/)
- [Firecrawl](https://firecrawl.dev/) — robust web scraping for GitHub Trending

---

<p align="center">
  <strong>⭐ If you find this useful, please give it a star!</strong>
</p>
