"""Configuration for GitHub Discovery."""

import os

# GitHub API
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_API = "https://api.github.com"
GITHUB_TRENDING_URL = "https://github.com/trending?since=daily"

# Hacker News API
HN_API = "https://hacker-news.firebaseio.com/v0"

# Scoring thresholds
TOP_N = 10
API_DELAY = 1.0  # seconds between API calls

# Scoring weights
ACCELERATION_MAX = 40
QUALITY_MAX = 30
ANTISPAM_MAX = 30

# Anti-spam
MARKETING_WORDS = [
    "best", "ultimate", "100x", "10x", "revolutionary", "game-changing",
    "magic", "miracle", "instant", "guaranteed", "free money", "get rich",
    "dropshipping", "passive income", "side hustle", "ai-powered",
    "next-gen", "cutting-edge", "state-of-the-art", "world-class",
]

# Paths
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output"))
DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "discovery.db"))
