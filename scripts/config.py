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

# Paths
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output"))
DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "discovery.db"))
