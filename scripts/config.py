"""Configuration for GitHub Discovery."""

import os

# GitHub API
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_API = "https://api.github.com"

# Resend API (email sending)
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
GITHUB_TRENDING_URL = "https://github.com/trending?since=daily"

# ── 订阅生命周期（issue #10）─────────────────────────────────────────
# GAS Web App 端点：subscribe（POST）/ confirm / unsubscribe（GET）共用。
# 与 docs/template.html 订阅表单指向的部署一致。
SUBSCRIBE_ENDPOINT = os.environ.get(
    "SUBSCRIBE_ENDPOINT",
    "https://script.google.com/macros/s/AKfycbzU-my3_JCqauuMwIWL2ps84hZ46lKWSeQ9zSYFay-xhoE9MaXpXH_i08roJo4fRuPf1Q/exec",
)
# 退订链接签名密钥。必须与 GAS 脚本属性 UNSUBSCRIBE_SECRET 一致，
# 否则 GAS 会拒绝 digest 邮件里生成的退订 token。
UNSUBSCRIBE_SECRET = os.environ.get("UNSUBSCRIBE_SECRET", "")

# Hacker News API
HN_API = "https://hacker-news.firebaseio.com/v0"

# Hugging Face Daily Papers — AI 论文社区热榜，~2/3 的论文直接带
# githubRepo 字段；论文热度往往领先 GitHub star 数天，是很好的早期信号。
HF_PAPERS_API = "https://huggingface.co/api/daily_papers"

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
# 深查质量加分上限（quality.check_quality），终评时按比例换算进 QUALITY_MAX 维度
QUALITY_BONUS_MAX = 20

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
