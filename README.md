# 🔥 GitHub Discovery

**Discover trending GitHub repos before they go viral.**

A daily automated tool that finds open-source projects gaining rapid traction — before they hit the mainstream trending pages. Inspired by [Changelog Nightly](https://github.com/thechangelog/nightly).

[![Daily Discovery](https://github.com/alloevil/github-discovery/actions/workflows/daily.yml/badge.svg)](https://github.com/alloevil/github-discovery/actions/workflows/daily.yml)

## How It Works

GitHub Discovery uses three data sources to find rising repos:

1. **GitHub Trending** — Scrapes the daily trending page
2. **GitHub Search API** — Finds newly created repos with fast star growth
3. **Hacker News** — Monitors "Show HN" posts linking to GitHub repos

Each candidate is scored on three dimensions:

| Dimension | Weight | What It Measures |
|-----------|--------|------------------|
| 🚀 Acceleration | 40pts | Star velocity (stars/day), repo age, growth curve |
| ✅ Quality | 30pts | README, description, license, language, non-fork |
| 🛡️ Anti-spam | 30pts | Fake star detection, marketing spam, anomaly patterns |

## Quick Start

```bash
# Clone
git clone https://github.com/alloevil/github-discovery.git
cd github-discovery

# Run
export GITHUB_TOKEN=your_token_here
python3 scripts/main.py
```

Output is saved to `output/discovery-YYYY-MM-DD.md`.

## Automated Daily Runs

The GitHub Action runs daily at 10:00 UTC and:
1. Runs the discovery script
2. Commits results to the `output/` directory
3. Publishes to GitHub Pages at `https://alloevil.github.io/github-discovery/`

## Subscribe

- **RSS**: `https://alloevil.github.io/github-discovery/feed.xml`
- **GitHub Pages**: `https://alloevil.github.io/github-discovery/`

## Project Structure

```
github-discovery/
├── scripts/
│   ├── main.py          # Entry point
│   ├── sources.py       # Data source collectors
│   ├── scorer.py        # Scoring engine
│   ├── anti_spam.py     # Anti-spam/fraud detection
│   ├── db.py            # SQLite dedup history
│   └── config.py        # Configuration
├── output/              # Generated reports (git-tracked)
├── .github/workflows/   # GitHub Actions
└── dist/                # GitHub Pages output
```

## Scoring Algorithm

**Acceleration Score (40pts)**
- `daily_stars = total_stars / repo_age_days`
- 3-day repo with 100+ stars → full marks
- 7-day repo with 200+ stars → high marks
- 30-day repo with 500+ stars → medium marks

**Anti-Spam Detection (30pts, starts at 30, deducts)**
- Star/fork ratio anomaly (>50:1) → -10
- Repo < 3 days old with 5000+ stars → -15
- Marketing keywords in description → -5

Based on research from:
- [StarScout](https://arxiv.org/abs/2412.13459) (ICSE'26) — Fake star detection
- [Launch-Day Diffusion](https://arxiv.org/abs/2511.04453) — HN launch velocity patterns
- [Predicting GitHub Popularity](https://arxiv.org/abs/1607.04342) — Star growth modeling

## License

MIT
