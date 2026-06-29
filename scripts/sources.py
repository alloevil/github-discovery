"""Data sources for GitHub Discovery."""

import json
import re
import time
import subprocess
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone, timedelta
from config import (
    GITHUB_TOKEN, GITHUB_API, GITHUB_TRENDING_URL, HN_API, API_DELAY,
    FIRECRAWL_API_KEY, FIRECRAWL_API,
)


def _gh_headers():
    headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "github-discovery-bot"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers


def _gh_api(path: str, params: dict = None) -> dict | list | None:
    """Call GitHub API, return parsed JSON or None on error."""
    url = f"{GITHUB_API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=_gh_headers())
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"  [WARN] GitHub API {path} returned {e.code}: {e.read().decode()[:200]}")
        return None
    except Exception as e:
        print(f"  [WARN] GitHub API {path} error: {e}")
        return None


def _fetch_url(url: str, timeout: int = 15) -> str:
    """Fetch a URL and return text."""
    req = urllib.request.Request(url, headers={"User-Agent": "github-discovery-bot"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _firecrawl_scrape(url: str, formats: list[str] = None, timeout: int = 60) -> dict | None:
    """Scrape a URL via Firecrawl /v2/scrape. Returns the `data` dict or None.

    Uses curl (consistent with the email sender, and robust against the
    proxies/TLS quirks that sometimes trip urllib in CI). Returns None when
    no API key is configured or the request fails.
    """
    if not FIRECRAWL_API_KEY:
        return None
    payload = json.dumps({"url": url, "formats": formats or ["markdown"]})
    try:
        result = subprocess.run(
            [
                "curl", "-s", "-X", "POST", FIRECRAWL_API,
                "-H", f"Authorization: Bearer {FIRECRAWL_API_KEY}",
                "-H", "Content-Type: application/json",
                "-d", payload,
            ],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            print(f"  [WARN] Firecrawl curl failed: {result.stderr[:200]}")
            return None
        resp = json.loads(result.stdout)
        if not resp.get("success"):
            print(f"  [WARN] Firecrawl error: {str(resp)[:200]}")
            return None
        return resp.get("data", {})
    except Exception as e:
        print(f"  [WARN] Firecrawl scrape failed: {e}")
        return None


def _parse_repo(full_name: str) -> dict | None:
    """Fetch repo details from GitHub API."""
    time.sleep(API_DELAY)
    data = _gh_api(f"/repos/{full_name}")
    if not data or "id" not in data:
        return None
    return _normalize_repo(data)


def _normalize_repo(data: dict) -> dict:
    """Normalize a GitHub API repo response to our standard format."""
    created = data.get("created_at", "")
    age_days = 1
    if created:
        try:
            ct = datetime.fromisoformat(created.replace("Z", "+00:00"))
            age_days = max(1, (datetime.now(timezone.utc) - ct).days)
        except Exception:
            pass
    stars = data.get("stargazers_count", 0)
    return {
        "id": str(data["id"]),
        "full_name": data["full_name"],
        "url": data["html_url"],
        "description": data.get("description") or "",
        "language": data.get("language") or "",
        "stars": stars,
        "forks": data.get("forks_count", 0),
        "fork": data.get("fork", False),
        "license": (data.get("license") or {}).get("spdx_id", ""),
        # NOTE: real README presence is verified later by quality.check_quality()
        # for top candidates; do not assume it here.
        "created_at": created,
        "age_days": age_days,
        "daily_stars": stars / age_days if age_days > 0 else stars,
        "watchers": data.get("subscribers_count", 0),
    }


# ── Source 1: GitHub Trending (HTML scraping) ──────────────────────────

def _extract_trending_paths(html: str, markdown: str = "") -> list[str]:
    """Extract owner/repo paths from trending HTML and/or Firecrawl markdown."""
    paths = re.findall(r'<h2[^>]*>\s*<a[^>]*href="(/[^/]+/[^"]+)"', html)
    if not paths:
        paths = re.findall(r'href="(/[^/]+/[^"]+)"[^>]*class="[^"]*color-fg-default', html)
    # Fallback: Firecrawl markdown renders each repo as a heading like
    #   ## [owner / repo](https://github.com/owner/repo)
    # Match that precisely — a broad github.com/... grab also catches the
    # language-filter links (github.com/trending/abap) and avatar URLs.
    if not paths and markdown:
        paths = ["/" + m for m in re.findall(
            r'^##\s+\[.*?\]\(https://github\.com/([\w.-]+/[\w.-]+)\)',
            markdown, re.MULTILINE)]
    return paths


def fetch_trending() -> list[dict]:
    """Scrape GitHub trending daily page (Firecrawl if configured, else direct)."""
    print("[Source] Fetching GitHub Trending...")
    html, markdown = "", ""

    fc = _firecrawl_scrape(GITHUB_TRENDING_URL, formats=["markdown", "html"])
    if fc:
        html = fc.get("html", "") or ""
        markdown = fc.get("markdown", "") or ""
    else:
        try:
            html = _fetch_url(GITHUB_TRENDING_URL, timeout=10)
        except Exception as e:
            print(f"  [WARN] Trending fetch failed: {e}")
            return []

    repos = _extract_trending_paths(html, markdown)

    results = []
    seen = set()
    for path in repos[:25]:
        full_name = path.strip("/")
        if "/" not in full_name or full_name in seen:
            continue
        seen.add(full_name)
        repo = _parse_repo(full_name)
        if repo:
            results.append(repo)
        time.sleep(API_DELAY)

    print(f"  Found {len(results)} repos from trending")
    return results


# ── Source 2: GitHub Search API ─────────────────────────────────────────

def fetch_search() -> list[dict]:
    """Search for newly created repos with fast star growth."""
    print("[Source] Fetching from GitHub Search API...")
    results = []

    date_since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    queries = [
        f"created:>{date_since} stars:>50",
        f"created:>{date_since} stars:>100 language:python",
        f"created:>{date_since} stars:>100 language:typescript",
        f"created:>{date_since} stars:>100 language:rust",
    ]

    seen = set()
    for q in queries:
        time.sleep(API_DELAY)
        data = _gh_api("/search/repositories", {
            "q": q,
            "sort": "stars",
            "order": "desc",
            "per_page": "20",
        })
        if not data or "items" not in data:
            continue
        for item in data["items"]:
            if item["full_name"] in seen:
                continue
            seen.add(item["full_name"])
            results.append(_normalize_repo(item))

    print(f"  Found {len(results)} repos from search")
    return results


# ── Source 3: Hacker News Show HN ──────────────────────────────────────

def fetch_hn() -> list[dict]:
    """Monitor Show HN posts and extract GitHub repo links."""
    print("[Source] Fetching Show HN stories...")
    results = []

    try:
        top_url = f"{HN_API}/showstories.json"
        ids_json = _fetch_url(top_url, timeout=8)
        story_ids = json.loads(ids_json)[:8]
    except Exception as e:
        print(f"  [WARN] HN fetch failed: {e}")
        return []

    seen = set()
    for sid in story_ids:
        time.sleep(0.3)
        try:
            story_json = _fetch_url(f"{HN_API}/item/{sid}.json", timeout=5)
            story = json.loads(story_json)
        except Exception:
            continue

        if not story or story.get("type") != "story":
            continue

        url = story.get("url", "")
        title = story.get("title", "")

        gh_match = re.match(r"https?://github\.com/([^/]+/[^/]+)", url)
        if not gh_match:
            gh_match = re.search(r"github\.com/([^/]+/[^/\s]+)", title)

        if gh_match:
            full_name = gh_match.group(1).rstrip("/")
            if full_name in seen:
                continue
            seen.add(full_name)
            repo = _parse_repo(full_name)
            if repo:
                repo["hn_title"] = title
                repo["hn_score"] = story.get("score", 0)
                results.append(repo)

    print(f"  Found {len(results)} repos from HN")
    return results


# ── Source 5: GitHub Watch/Fork 增速异常检测 ───────────────────────────

def fetch_rising() -> list[dict]:
    """Detect repos with unusual Fork/Watch growth (early signal)."""
    print("[Source] Detecting rising repos (fork/watch signals)...")
    results = []

    date_since = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%d")

    # 搜索最近 3 天 fork 数异常高的仓库（fork > stars * 0.3 说明有实际使用）
    queries = [
        f"created:>{date_since} forks:>20 stars:>30",
        f"created:>{date_since} forks:>50",
    ]

    seen = set()
    for q in queries:
        time.sleep(API_DELAY)
        data = _gh_api("/search/repositories", {
            "q": q,
            "sort": "forks",
            "order": "desc",
            "per_page": "15",
        })
        if not data or "items" not in data:
            continue
        for item in data["items"]:
            full_name = item["full_name"]
            if full_name in seen:
                continue
            seen.add(full_name)

            repo = _normalize_repo(item)
            stars = repo.get("stars", 0)
            forks = repo.get("forks", 0)
            watchers = repo.get("watchers", 0)

            # 计算 fork/star 比率（越高说明实际使用越多）
            fork_ratio = forks / stars if stars > 0 else 0
            # 计算 watcher/star 比率（越高说明关注度越集中）
            watch_ratio = watchers / stars if stars > 0 else 0

            repo["fork_ratio"] = round(fork_ratio, 2)
            repo["watch_ratio"] = round(watch_ratio, 2)
            repo["rising_signal"] = "high_fork" if fork_ratio > 0.3 else "high_watch" if watch_ratio > 0.1 else ""

            if repo["rising_signal"]:
                results.append(repo)

    print(f"  Found {len(results)} rising repos")
    return results


def fetch_all() -> list[dict]:
    """Fetch from all sources, deduplicate by full_name."""
    if not GITHUB_TOKEN:
        print("[WARN] No GITHUB_TOKEN set — GitHub API limited to 60 req/hour. "
              "Results will likely be incomplete. Set GITHUB_TOKEN to raise the limit to 5000/hour.")

    all_repos = []

    trending = fetch_trending()
    for r in trending:
        r["source"] = "trending"
    all_repos.extend(trending)

    search = fetch_search()
    for r in search:
        r["source"] = "search"
    all_repos.extend(search)

    hn = fetch_hn()
    for r in hn:
        r["source"] = "hn"
    all_repos.extend(hn)

    rising = fetch_rising()
    for r in rising:
        r["source"] = "rising"
    all_repos.extend(rising)

    ai_trending = fetch_ai_trending()
    for r in ai_trending:
        r["source"] = "ai-trending"
    all_repos.extend(ai_trending)

    # Deduplicate by full_name, keep first occurrence
    seen = set()
    unique = []
    for r in all_repos:
        if r["full_name"] not in seen:
            seen.add(r["full_name"])
            unique.append(r)

    print(f"\n[Total] {len(unique)} unique repos from all sources")
    return unique

def fetch_ai_trending() -> list[dict]:
    """
    Find trending AI/ML repositories with fast growth.
    Inspired by OSSInsight's trending/ai page.
    """
    ai_keywords = [
        "llm", "large language model", "ai agent", "machine learning",
        "deep learning", "transformer", "gpt", "claude", "diffusion",
        "stable diffusion", "computer vision", "nlp", "reinforcement learning",
        "rag", "retrieval augmented generation", "vector database",
        "embedding", "fine-tuning", "lora", "qlora", "inference", "mlops"
    ]
    
    date_from = (datetime.now(timezone.utc) - timedelta(days=7)).strftime('%Y-%m-%d')
    all_repos = []
    
    for keyword in ai_keywords[:5]:  # 限制请求数量
        try:
            query = f'"{keyword}" created:>{date_from} stars:>50'
            data = _gh_api("/search/repositories", {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": 10
            })
            
            if data and "items" in data:
                for repo in data["items"]:
                    all_repos.append(_normalize_repo(repo))
            
            time.sleep(API_DELAY)
        except Exception as e:
            print(f"  [WARN] AI trending error for {keyword}: {e}")
            continue
    
    # 去重
    seen = set()
    unique = []
    for r in all_repos:
        if r["full_name"] not in seen:
            seen.add(r["full_name"])
            unique.append(r)
    
    # 按星标数排序
    unique.sort(key=lambda x: x.get("stars", 0), reverse=True)
    
    print(f"[AI Trending] {len(unique)} repos")
    return unique[:30]  # 返回前 30 个
