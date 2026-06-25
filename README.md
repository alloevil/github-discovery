# GitHub Discovery

<p align="center">
  <img src="https://img.shields.io/github/actions/workflow/status/alloevil/github-discovery/daily.yml?branch=main&label=CI&logo=github&logoColor=white&color=00ccff" alt="CI" />
  <img src="https://img.shields.io/badge/license-MIT-00ccff?style=flat" alt="License" />
  <img src="https://img.shields.io/github/stars/alloevil/github-discovery?style=flat&logo=github&color=00ccff" alt="Stars" />
  <a href="https://alloevil.github.io/github-discovery/"><img src="https://img.shields.io/badge/website-live-00ccff?style=flat" alt="Website" /></a>
</p>

<p align="center">
  <strong>Discover trending GitHub repos before they go mainstream.</strong><br/>
  <em>5 data sources · smart scoring · anti-spam · daily email digest</em>
</p>

<p align="center">
  <a href="https://alloevil.github.io/github-discovery/">Website</a> · 
  <a href="#quick-start">Quick Start</a> · 
  <a href="#features">Features</a> · 
  <a href="#development">Development</a>
</p>

---

## What it does

GitHub Discovery automatically collects signals from 5 data sources every day, uses a smart scoring system (100 points) to filter the most promising projects, and delivers them to you via email and web.

**The problem it solves:** GitHub Trending shows you what's popular *today*. GitHub Discovery shows you what's *about to be popular* — repos with unusual growth patterns, community picks from Hacker News and Reddit, and early-stage projects gaining traction.

---

## Features

### 5 Data Sources

| Source | Signal | What it catches |
|--------|--------|-----------------|
| [GitHub Trending](https://github.com/trending) | Popularity | Daily trending repositories |
| GitHub Search | New & rising | Repos created in the last 7 days with fast star growth |
| [Hacker News](https://news.ycombinator.com/) | Community picks | GitHub repos from Show HN posts |
| [Reddit](https://reddit.com/r/programming) | Discussion | GitHub links from /r/programming hot posts |
| Rising Detection | Early signal | Unusual Fork/Watch growth patterns |

### Smart Scoring (100 points)

| Dimension | Points | What it measures |
|-----------|--------|------------------|
| **Acceleration** | 40 | Star growth rate, acceleration trend |
| **Quality** | 30 | Age, language, license, content completeness |
| **Anti-spam** | 30 | Fork ratio, description quality |
| **Code Quality** | +20 | README, CI config, commit frequency |
| **Suspicious Stars** | -15 | 1000+ stars in 1 day with no description |
| **User Feedback** | ±10 | 👍👎 voting integrated into scoring |
| **Batch Fraud** | -40 | Multiple repos from same owner growing simultaneously |

### Anti-spam

- **Star fraud detection**: 1000+ stars in 1 day with age < 1 day → flagged
- **Batch fraud detection**: Same owner with multiple repos growing at once → flagged
- **Content quality**: No description or no README → penalty
- **Cross-day dedup**: 7-day window, no duplicate recommendations

### User Feedback

- Vote on every recommendation (👍/👎)
- Feedback integrated into scoring algorithm
- localStorage persistence

### Email Subscription

- Daily curated repos delivered to your inbox
- Dark mode support (Apple Mail / iOS)
- Powered by Resend API

### GitHub Pages

- Modern, professional web interface
- Filter by date and language
- Real-time scoring display

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
│   ├── sources.py           # 5 data source collectors
│   ├── scorer.py            # Scoring algorithm
│   ├── quality.py           # Code quality detection
│   ├── dedup.py             # Cross-day deduplication (7-day window)
│   ├── feedback.py          # User feedback system
│   ├── fraud_detection.py   # Batch fraud detection
│   ├── verify_scoring.py    # Scoring verification / backtesting
│   ├── main.py              # Entry point
│   └── config.py            # Configuration
├── tests/                   # 117 unit tests
├── docs/index.html          # GitHub Pages
├── .github/workflows/       # Daily automation
├── subscribers.txt          # Email subscriber list
└── config.yaml              # Runtime configuration
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

Scoring logic is in `scripts/scorer.py`. Weights can be adjusted in `config.py`:

```python
SCORING_WEIGHTS = {
    "acceleration": 40,
    "quality": 30,
    "antispam": 30,
}
```

---

## Scoring Verification

Run backtesting to verify whether high-scored repos actually took off:

```bash
python scripts/verify_scoring.py --days 30
```

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
- [Reddit API](https://www.reddit.com/dev/api/)
- [Resend](https://resend.com/)

---

<p align="center">
  <strong>⭐ If you find this useful, please give it a star!</strong>
</p>
