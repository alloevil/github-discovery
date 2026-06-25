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
    异常模式：Star 暴涨但无实质内容、年龄极短但 Star 极高。
    """
    result = {
        "is_suspicious": False,
        "reason": "",
        "penalty": 0,
    }
    
    daily_stars = stars / max(1, age_days)
    
    # 1 天内超过 500 Star 且年龄小于 3 天 → 可疑
    if daily_stars > 500 and age_days < 3:
        result["is_suspicious"] = True
        result["reason"] = "star_growth_too_fast"
        result["penalty"] = -15
        return result
    
    # 检查贡献者数量（单人仓库高 Star 可能是刷的）
    time.sleep(API_DELAY)
    contributors = _gh_api(f"/repos/{repo_full_name}/contributors", {"per_page": "5"})
    if contributors and isinstance(contributors, list):
        if len(contributors) == 1 and stars > 200:
            result["is_suspicious"] = True
            result["reason"] = "single_contributor_high_stars"
            result["penalty"] = -8
    
    return result
