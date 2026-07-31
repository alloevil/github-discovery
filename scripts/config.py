"""Configuration for GitHub Discovery."""

import os

# GitHub API
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_API = "https://api.github.com"

# Resend API (email sending)
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
GITHUB_TRENDING_URL = "https://github.com/trending?since=daily"

# Hacker News API
HN_API = "https://hacker-news.firebaseio.com/v0"

# Firecrawl (https://firecrawl.dev) — used to make GitHub Trending parsing
# robust (its raw HTML structure is brittle to regex).
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY", "")
FIRECRAWL_API = "https://api.firecrawl.dev/v2/scrape"

# Scoring thresholds
TOP_N = 10
API_DELAY = 0.3  # seconds between API calls (reduced for faster execution)
# 粗排后进入深度检查（quality/star 真实性，每个约 3 次 API 调用）的仓库数。
# 深查发生在粗排排序之后，保证配额花在分数最高的候选上，而不是抓取顺序靠前的。
DEEP_CHECK_TOP_K = 20

# Scoring weights
ACCELERATION_MAX = 40
QUALITY_MAX = 30
ANTISPAM_MAX = 30

# Anti-spam
# 注意：不要把正经项目的高频描述词放进来（曾有 "ai-powered"、
# "state-of-the-art"、"cutting-edge"、"next-gen"、"world-class"，
# 如今大量正常 AI 项目都会用，误伤面太大）。
MARKETING_WORDS = [
    "best", "ultimate", "100x", "10x", "revolutionary", "game-changing",
    "magic", "miracle", "instant", "guaranteed", "free money", "get rich",
    "dropshipping", "passive income", "side hustle",
]

# Paths
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output"))
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"))
DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "discovery.db"))
