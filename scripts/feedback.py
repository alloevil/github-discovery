"""User feedback system - stores thumbs up/down per repo."""

import json
import os
from pathlib import Path
from datetime import datetime, timezone

FEEDBACK_FILE = Path(__file__).parent.parent / "data" / "feedback.json"


def _load_feedback() -> dict:
    """Load feedback data."""
    if FEEDBACK_FILE.exists():
        return json.loads(FEEDBACK_FILE.read_text())
    return {"repos": {}, "updated_at": ""}


def _save_feedback(data: dict):
    """Save feedback data."""
    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    FEEDBACK_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def vote(repo_full_name: str, vote_type: str, user_id: str = "anonymous") -> dict:
    """
    Record a vote for a repo.
    vote_type: 'up' or 'down'
    Returns updated vote counts.
    """
    if vote_type not in ("up", "down"):
        return {"error": "vote_type must be 'up' or 'down'"}

    data = _load_feedback()
    repos = data.setdefault("repos", {})

    if repo_full_name not in repos:
        repos[repo_full_name] = {"up": 0, "down": 0, "voters": {}}

    repo = repos[repo_full_name]
    voters = repo.setdefault("voters", {})

    # 防止同一用户重复投票
    if user_id in voters:
        old_vote = voters[user_id]
        if old_vote == vote_type:
            return {"up": repo["up"], "down": repo["down"], "message": "already_voted"}
        # 撤销旧投票
        repo[old_vote] = max(0, repo[old_vote] - 1)

    # 记录新投票
    voters[user_id] = vote_type
    repo[vote_type] = repo.get(vote_type, 0) + 1

    _save_feedback(data)
    return {"up": repo["up"], "down": repo["down"]}


def get_feedback(repo_full_name: str) -> dict:
    """Get vote counts for a repo."""
    data = _load_feedback()
    repo = data.get("repos", {}).get(repo_full_name, {})
    return {
        "up": repo.get("up", 0),
        "down": repo.get("down", 0),
    }


def get_all_feedback() -> dict:
    """Get all feedback data (for ranking)."""
    data = _load_feedback()
    result = {}
    for name, info in data.get("repos", {}).items():
        result[name] = {
            "up": info.get("up", 0),
            "down": info.get("down", 0),
            "score": info.get("up", 0) - info.get("down", 0),
        }
    return result


def get_top_voted(limit: int = 10) -> list[dict]:
    """Get top voted repos."""
    all_fb = get_all_feedback()
    sorted_repos = sorted(all_fb.items(), key=lambda x: x[1]["score"], reverse=True)
    return [{"repo": name, **info} for name, info in sorted_repos[:limit]]
