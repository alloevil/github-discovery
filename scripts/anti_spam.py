"""Anti-spam scoring for GitHub repos."""

import re
from config import MARKETING_WORDS


def check_star_fork_ratio(repo: dict) -> int:
    """Check if star/fork ratio is suspiciously high. Returns deduction (0 or 10)."""
    stars = repo.get("stars", 0)
    forks = repo.get("forks", 0)
    if forks > 0 and stars / forks > 50:
        return 10
    return 0


def check_sudden_stars(repo: dict) -> int:
    """Check if repo is too new with too many stars. Returns deduction (0 or 15)."""
    age = repo.get("age_days", 1)
    stars = repo.get("stars", 0)
    if age < 3 and stars > 5000:
        return 15
    return 0


def check_marketing_words(repo: dict) -> int:
    """Check description for marketing buzzwords. Returns deduction (0-10)."""
    desc = (repo.get("description") or "").lower()
    hits = sum(1 for word in MARKETING_WORDS if re.search(r'\b' + re.escape(word) + r'\b', desc))
    if hits >= 3:
        return 10
    elif hits >= 1:
        return 5
    return 0


def check_suspicious_pattern(repo: dict) -> int:
    """Check for suspicious patterns like duplicate repos or gaming trainers. Returns deduction (0-10)."""
    name = repo.get("full_name", "").lower()
    desc = (repo.get("description") or "").lower()

    # Check for gaming trainer patterns
    trainer_patterns = ["trainer", "cheat", "hack", "mod menu", "aimbot"]
    if any(p in name or p in desc for p in trainer_patterns):
        return 10

    # Check for suspicious username patterns (random numbers/letters)
    username = name.split("/")[0] if "/" in name else ""
    if username and len(username) > 8 and sum(c.isdigit() for c in username) > len(username) * 0.3:
        return 5

    return 0


def calculate_antiscore(repo: dict) -> int:
    """Calculate anti-spam score. Starts at 30, deduct for suspicious patterns."""
    score = 30
    score -= check_star_fork_ratio(repo)
    score -= check_sudden_stars(repo)
    score -= check_marketing_words(repo)
    score -= check_suspicious_pattern(repo)
    return max(0, score)
