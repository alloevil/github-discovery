"""Scoring logic for GitHub repos."""

from config import ACCELERATION_MAX, QUALITY_MAX, ANTISPAM_MAX
from anti_spam import calculate_antiscore


def score_acceleration(repo: dict) -> int:
    """Score based on star growth velocity (0-40)."""
    age = repo.get("age_days", 1)
    stars = repo.get("stars", 0)
    daily = stars / age if age > 0 else stars

    # Tier 1: brand new repo going viral
    if age <= 3 and stars >= 100:
        return ACCELERATION_MAX  # 40

    # Tier 2: very new with strong traction
    if age <= 7 and stars >= 200:
        return int(ACCELERATION_MAX * 0.85)  # 34

    # Tier 3: new with solid growth
    if age <= 30 and stars >= 500:
        return int(ACCELERATION_MAX * 0.7)  # 28

    # Score based on daily velocity
    if daily >= 100:
        return int(ACCELERATION_MAX * 0.9)
    elif daily >= 50:
        return int(ACCELERATION_MAX * 0.7)
    elif daily >= 20:
        return int(ACCELERATION_MAX * 0.5)
    elif daily >= 10:
        return int(ACCELERATION_MAX * 0.3)
    elif daily >= 5:
        return int(ACCELERATION_MAX * 0.15)
    else:
        return 0


def score_quality(repo: dict) -> int:
    """Score based on repo quality signals (0-30)."""
    score = 0

    # Has README
    if repo.get("has_readme", False):
        score += 10

    # Description length > 20 chars
    desc = repo.get("description", "")
    if desc and len(desc) > 20:
        score += 5

    # Not a fork
    if not repo.get("fork", False):
        score += 5

    # Has license
    if repo.get("license", ""):
        score += 5

    # Language specified
    if repo.get("language", ""):
        score += 5

    return score


def calculate_score(repo: dict) -> dict:
    """Calculate total score and breakdown for a repo."""
    acc = score_acceleration(repo)
    qual = score_quality(repo)
    anti = calculate_antiscore(repo)
    total = acc + qual + anti

    return {
        "total": total,
        "acceleration": acc,
        "quality": qual,
        "antispam": anti,
    }
