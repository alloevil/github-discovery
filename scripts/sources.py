"""Data sources for GitHub Discovery."""

import json
import re
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from config import GITHUB_TOKEN, GITHUB_API, GITHUB_TRENDING_URL, HN_API, API_DELAY


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
        "has_readme": True,  # API repos typically have README if popular
        "created_at": created,
        "age_days": age_days,
        "daily_stars": stars / age_days if age_days > 0 else stars,
    }


# ── Source 1: GitHub Trending (HTML scraping) ──────────────────────────

def fetch_trending() -> list[dict]:
    """Scrape GitHub trending daily page."""
    print("[Source] Fetching GitHub Trending...")
    try:
        html = _fetch_url(GITHUB_TRENDING_URL, timeout=10)
    except Exception as e:
        print(f"  [WARN] Trending fetch failed: {e}")
        return []

    # Extract repo names from <h2 class="h3 ...">  <a href="/owner/repo">
    repos = re.findall(r'<h2[^>]*>\s*<a[^>]*href="(/[^/]+/[^"]+)"', html)
    if not repos:
        # fallback pattern
        repos = re.findall(r'href="(/[^/]+/[^"]+)"[^>]*class="[^"]*color-fg-default', html)

    results = []
    for path in repos[:25]:  # top 25 from trending
        full_name = path.strip("/")
        if "/" not in full_name:
            continue
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

    # Query: repos created in last 7 days, sorted by stars
    from datetime import timedelta
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

    # Get top and new stories
    try:
        top_url = f"{HN_API}/showstories.json"
        ids_json = _fetch_url(top_url, timeout=8)
        story_ids = json.loads(ids_json)[:8]  # top 10 Show HN (speed-optimized)
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

        # Extract GitHub repo URL
        gh_match = re.match(r"https?://github\.com/([^/]+/[^/]+)", url)
        if not gh_match:
            # Check title for GitHub links
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


def fetch_all() -> list[dict]:
    """Fetch from all sources, deduplicate by full_name."""
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

    # Deduplicate by full_name, keep first occurrence (prioritize trending > search > hn)
    seen = set()
    unique = []
    for r in all_repos:
        if r["full_name"] not in seen:
            seen.add(r["full_name"])
            unique.append(r)

    print(f"\n[Total] {len(unique)} unique repos from all sources")
    return unique
