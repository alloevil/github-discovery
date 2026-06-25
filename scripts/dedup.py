"""跨天去重 - 记录已推荐的仓库，7天内不重复推荐"""

import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

HISTORY_FILE = Path(__file__).parent.parent / "data" / "recommend_history.json"


def _load_history() -> dict:
    """Load recommendation history."""
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text())
    return {"repos": {}, "updated_at": ""}


def _save_history(data: dict):
    """Save recommendation history."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    HISTORY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def is_recently_recommended(repo_full_name: str, days: int = 7) -> bool:
    """Check if a repo was recommended within the last N days."""
    data = _load_history()
    repo_data = data.get("repos", {}).get(repo_full_name)
    if not repo_data:
        return False
    
    last_recommended = repo_data.get("last_recommended", "")
    if not last_recommended:
        return False
    
    try:
        last_date = datetime.fromisoformat(last_recommended.replace("Z", "+00:00"))
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return last_date > cutoff
    except (ValueError, TypeError):
        return False


def record_recommendation(repo_full_name: str, score: float):
    """Record that a repo was recommended."""
    data = _load_history()
    repos = data.setdefault("repos", {})
    
    if repo_full_name not in repos:
        repos[repo_full_name] = {"count": 0, "scores": []}
    
    repos[repo_full_name]["last_recommended"] = datetime.now(timezone.utc).isoformat()
    repos[repo_full_name]["count"] = repos[repo_full_name].get("count", 0) + 1
    repos[repo_full_name]["scores"].append(score)
    # 只保留最近 30 天的分数
    repos[repo_full_name]["scores"] = repos[repo_full_name]["scores"][-30:]
    
    _save_history(data)


def cleanup_old_records(days: int = 30):
    """Remove records older than N days."""
    data = _load_history()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    to_remove = []
    for name, info in data.get("repos", {}).items():
        last = info.get("last_recommended", "")
        try:
            last_date = datetime.fromisoformat(last.replace("Z", "+00:00"))
            if last_date < cutoff:
                to_remove.append(name)
        except (ValueError, TypeError):
            to_remove.append(name)
    
    for name in to_remove:
        del data["repos"][name]
    
    _save_history(data)
    print(f"[Dedup] Cleaned up {len(to_remove)} old records")
