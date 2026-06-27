"""代码质量信号检测"""

import time
from config import GITHUB_TOKEN, GITHUB_API, API_DELAY
import urllib.request
import json


def _gh_api(path: str, params: dict = None) -> dict | list | None:
    """Call GitHub API."""
    url = f"{GITHUB_API}{path}"
    if params:
        url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
    headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "github-discovery-bot"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def check_quality(repo_full_name: str) -> dict:
    """
    Check code quality signals for a repo.
    Returns dict with quality metrics and a 0-20 bonus score.
    """
    result = {
        "has_readme": False,
        "has_license": False,
        "has_ci": False,
        "recent_commits": 0,
        "open_issues": 0,
        "open_prs": 0,
        "quality_score": 0,
    }
    
    # 1. 检查文件结构（README, LICENSE, CI 配置）
    time.sleep(API_DELAY)
    contents = _gh_api(f"/repos/{repo_full_name}/contents")
    if contents and isinstance(contents, list):
        filenames = [f["name"].lower() for f in contents]
        result["has_readme"] = any("readme" in f for f in filenames)
        result["has_license"] = any("license" in f or "licence" in f for f in filenames)
        result["has_ci"] = any(f in filenames for f in [".github", ".travis.yml", ".circleci", "Jenkinsfile", ".gitlab-ci.yml"])
    
    # 2. 最近 commit 频率
    time.sleep(API_DELAY)
    commits = _gh_api(f"/repos/{repo_full_name}/commits", {"per_page": "1"})
    if commits and isinstance(commits, list) and len(commits) > 0:
        commit_date = commits[0].get("commit", {}).get("committer", {}).get("date", "")
        if commit_date:
            from datetime import datetime, timezone
            try:
                ct = datetime.fromisoformat(commit_date.replace("Z", "+00:00"))
                days_ago = (datetime.now(timezone.utc) - ct).days
                result["recent_commits"] = 7 if days_ago <= 1 else 5 if days_ago <= 3 else 3 if days_ago <= 7 else 0
            except (ValueError, TypeError):
                pass
    
    # 3. Issue/PR 活跃度
    time.sleep(API_DELAY)
    repo_data = _gh_api(f"/repos/{repo_full_name}")
    if repo_data:
        result["open_issues"] = repo_data.get("open_issues_count", 0)
    
    time.sleep(API_DELAY)
    prs = _gh_api(f"/repos/{repo_full_name}/pulls", {"state": "open", "per_page": "1"})
    if prs and isinstance(prs, list):
        result["open_prs"] = len(prs)
    
    # 计算质量加分（最高 20 分）
    score = 0
    score += 5 if result["has_readme"] else 0
    score += 3 if result["has_license"] else 0
    score += 4 if result["has_ci"] else 0
    score += result["recent_commits"]  # 0-7
    score += 1 if result["open_issues"] > 0 else 0  # 有 issue 说明有人用
    
    result["quality_score"] = min(20, score)
    return result


def check_star_authenticity(repo_full_name: str, stars: int, age_days: int) -> dict:
    """
    检测 Star 真实性。
    只检测高置信度的刷量模式，避免误伤优质独立项目。
    """
    result = {
        "is_suspicious": False,
        "reason": "",
        "penalty": 0,
    }
    
    daily_stars = stars / max(1, age_days)
    
    # 检测 1：年龄 <1 天且 Star >1000 → 高度可疑（新仓库暴涨）
    if age_days < 1 and stars > 1000:
        result["is_suspicious"] = True
        result["reason"] = "brand_new_repo_1k_stars_in_1_day"
        result["penalty"] = -20
        return result
    
    # 检测 2：年龄 <2 天且 Star >2000 → 可疑
    if age_days < 2 and stars > 2000:
        result["is_suspicious"] = True
        result["reason"] = "new_repo_2k_stars_in_2_days"
        result["penalty"] = -15
        return result
    
    # 检测 3：Star 增速异常（>1000/天）但无 README 或描述为空 → 可疑
    if daily_stars > 1000:
        time.sleep(API_DELAY)
        repo_data = _gh_api(f"/repos/{repo_full_name}")
        if repo_data:
            desc = (repo_data.get("description") or "").strip()
            if not desc:
                result["is_suspicious"] = True
                result["reason"] = "massive_stars_no_description"
                result["penalty"] = -15
                return result
    
    # 检测 4：同一 owner 下多个相似仓库同时暴涨 → 批量刷量
    # （这个检测成本较高，暂不实现）
    
    # 其他情况不扣分 — 宁可放过，不要误伤
    return result


# ── 内容过滤（赌博/色情/违法/恶意利用）──────────────────────────────

BLOCKED_KEYWORDS = [
    # 赌博
    "casino", "gambling", "betting", "bookie", "sportsbook",
    "slot machine", "roulette", "blackjack", "poker bot",
    "coinflip", "dice roll", "lottery", "wager",
    "prediction market", "polymarket", "betfair",
    # 球赛赌盘
    "prop market", "parlay", "spread betting",
    # 漏洞利用 / 恶意工具
    "exploit poc", "cve exploit", "vulnerability research writeup",
    "ransomware", "keylogger", "rat tool", "stealer",
    # 色情
    "porn", "nsfw", "xxx", "adult content",
]

BLOCKED_NAME_PATTERNS = [
    "casino", "gambling", "betting", "exploit-poc", "exploitarium",
    "coinflip-casino", "slot-machine",
]


def is_blocked_content(repo: dict) -> tuple:
    """
    Check if a repo should be blocked due to gambling / malicious / NSFW content.
    Returns (blocked, reason).
    """
    name = (repo.get("full_name") or repo.get("name") or "").lower()
    desc = (repo.get("description") or "").lower()
    topics = " ".join(repo.get("topics") or []).lower()
    combined = f"{name} {desc} {topics}"

    # 1. 仓库名精确匹配
    for pat in BLOCKED_NAME_PATTERNS:
        if pat in name:
            return True, f"blocked_name:{pat}"

    # 2. 描述/主题关键词匹配（需要 ≥2 个命中才触发，避免误伤）
    hits = [kw for kw in BLOCKED_KEYWORDS if kw in combined]
    if len(hits) >= 2:
        return True, f"blocked_keywords:{','.join(hits[:3])}"

    # 3. 单关键词强命中（赌博核心词，一个就够了）
    STRONG_SINGLE = ["casino", "gambling", "sportsbook", "coinflip-casino",
                     "polymarket-trading", "prop market"]
    for kw in STRONG_SINGLE:
        if kw in combined:
            return True, f"blocked_strong:{kw}"

    return False, ""
