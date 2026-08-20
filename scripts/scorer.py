"""Scoring logic for GitHub repos."""

import math

from config import ACCELERATION_MAX, QUALITY_MAX, ANTISPAM_MAX, QUALITY_BONUS_MAX
from anti_spam import calculate_antiscore

# 速度分对数曲线的饱和点：真实日增达到该值时速度分拉满。
# 用对数曲线而不是阶梯，让 10/day 和 300/day 的仓库分数连续可比，
# 避免旧版"age<=3 且 stars>=100 直接满分"造成的 79% 满分饱和。
VELOCITY_SATURATION = 500  # stars/day
VELOCITY_MAX = 30          # 速度分上限（加速度分 40 中的 30）
ACCEL_BONUS_MAX = 10       # 加速比 bonus 上限（40 中的 10）


def score_acceleration(repo: dict) -> int:
    """Score based on star growth velocity + acceleration (0-40).

    速度分 (0-30)：对数曲线。优先使用快照算出的真实日增
    （repo["real_daily_stars"]，由 main.py 注入），否则退回终身平均。
    加速 bonus (0-10)：
      - 有快照数据：真实日增 / 终身平均 的加速比，连续映射；
      - 无快照数据（首次见到）：按年轻程度给部分分 —— 新仓库的
        终身平均本身就近似最近速度。
    """
    age = max(1, repo.get("age_days", 1) or 1)
    stars = repo.get("stars", 0)
    lifetime_daily = stars / age

    real_daily = repo.get("real_daily_stars")  # None = 无快照历史
    daily = real_daily if real_daily is not None else lifetime_daily
    if daily <= 0:
        return 0

    # 速度分：log 曲线，daily=VELOCITY_SATURATION 时拉满
    velocity = VELOCITY_MAX * min(1.0, math.log10(1 + daily) / math.log10(1 + VELOCITY_SATURATION))

    # 加速 bonus
    if real_daily is not None and lifetime_daily > 0:
        # 加速比 1 → 0 分（匀速），3 及以上 → 满分（明显在加速）
        ratio = real_daily / lifetime_daily
        accel = ACCEL_BONUS_MAX * min(1.0, max(0.0, (ratio - 1) / 2))
    elif age <= 3:
        accel = 6
    elif age <= 7:
        accel = 4
    elif age <= 14:
        accel = 2
    else:
        accel = 0

    return min(ACCELERATION_MAX, int(round(velocity + accel)))


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


def merge_quality_bonus(scores: dict, quality_bonus: int) -> dict:
    """把深查加分并入 quality 维度（取 max，不叠加）。

    深查的 quality_score (0-20) 与粗排 score_quality (0-30) 对 README/
    license 等信号重复计分，旧版直接 total += bonus 再 min(100) clamp，
    导致 94% 上榜条目总分恒为 100（scorer 顶部注释修掉的粗排饱和又在
    终评被造了回来）。改为：bonus 按比例换算到 QUALITY_MAX 量纲后与
    粗排 quality 取 max —— 深查是更可信的同维度信号，覆盖而非叠加。
    """
    if not quality_bonus:
        return scores
    scaled = round(quality_bonus * QUALITY_MAX / QUALITY_BONUS_MAX)
    new_quality = min(QUALITY_MAX, max(scores["quality"], scaled))
    scores["total"] += new_quality - scores["quality"]
    scores["quality"] = new_quality
    scores["quality_bonus"] = quality_bonus
    return scores


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
