"""测试批量刷量检测逻辑。"""

import pytest
from unittest.mock import patch

import anti_spam


class TestCheckStarForkRatio:
    """测试 Star/Fork 比率异常检测。"""

    def test_normal_ratio_no_deduction(self):
        """正常比率（stars/forks ≤ 50）不应扣分。"""
        repo = {"stars": 100, "forks": 10}
        assert anti_spam.check_star_fork_ratio(repo) == 0

    def test_suspiciously_high_ratio_deducts(self):
        """异常高比率（stars/forks > 50）应扣 10 分。"""
        repo = {"stars": 1000, "forks": 10}  # ratio = 100
        assert anti_spam.check_star_fork_ratio(repo) == 10

    def test_exactly_at_boundary(self):
        """恰好在边界（ratio=50）不应扣分。"""
        repo = {"stars": 500, "forks": 10}  # ratio = 50
        assert anti_spam.check_star_fork_ratio(repo) == 0

    def test_just_over_boundary(self):
        """刚超过边界（ratio=51）应扣分。"""
        repo = {"stars": 510, "forks": 10}  # ratio = 51
        assert anti_spam.check_star_fork_ratio(repo) == 10

    def test_zero_forks_no_crash(self):
        """forks=0 时不应除零崩溃。"""
        repo = {"stars": 1000, "forks": 0}
        assert anti_spam.check_star_fork_ratio(repo) == 0

    def test_zero_stars_no_crash(self):
        """stars=0 时不应报错。"""
        repo = {"stars": 0, "forks": 5}
        assert anti_spam.check_star_fork_ratio(repo) == 0


class TestCheckSuddenStars:
    """测试新仓库暴涨 star 检测。"""

    def test_new_repo_too_many_stars(self):
        """创建 <3 天且 >5000 stars 应扣 15 分。"""
        repo = {"age_days": 1, "stars": 6000}
        assert anti_spam.check_sudden_stars(repo) == 15

    def test_old_repo_no_deduction(self):
        """老仓库不应触发此检测。"""
        repo = {"age_days": 30, "stars": 10000}
        assert anti_spam.check_sudden_stars(repo) == 0

    def test_new_repo_few_stars_no_deduction(self):
        """新仓库但 star 不多不应扣分。"""
        repo = {"age_days": 1, "stars": 100}
        assert anti_spam.check_sudden_stars(repo) == 0

    def test_exactly_at_boundary(self):
        """恰好在边界（age=3, stars=5000）不应扣分。"""
        repo = {"age_days": 3, "stars": 5000}
        assert anti_spam.check_sudden_stars(repo) == 0

    def test_just_under_boundary(self):
        """刚好低于边界（age=2, stars=5001）应扣分。"""
        repo = {"age_days": 2, "stars": 5001}
        assert anti_spam.check_sudden_stars(repo) == 15


class TestCheckMarketingWords:
    """测试营销关键词检测。"""

    def test_no_marketing_words(self):
        """无营销词不应扣分。"""
        repo = {"description": "A simple CLI tool for managing files"}
        assert anti_spam.check_marketing_words(repo) == 0

    def test_one_marketing_word(self):
        """1 个营销词应扣 5 分。"""
        repo = {"description": "The best tool for developers"}
        assert anti_spam.check_marketing_words(repo) == 5

    def test_three_or_more_marketing_words(self):
        """≥3 个营销词应扣 10 分。"""
        repo = {"description": "Best revolutionary game-changing ultimate tool"}
        assert anti_spam.check_marketing_words(repo) == 10

    def test_case_insensitive(self):
        """检测应不区分大小写。"""
        repo = {"description": "BEST tool ever made"}
        assert anti_spam.check_marketing_words(repo) == 5

    def test_empty_description(self):
        """空描述不应扣分。"""
        repo = {"description": ""}
        assert anti_spam.check_marketing_words(repo) == 0

    def test_none_description(self):
        """None 描述不应报错。"""
        repo = {"description": None}
        assert anti_spam.check_marketing_words(repo) == 0

    def test_word_boundary_matching(self):
        """应使用词边界匹配，避免子串误匹配。"""
        # "best" 不应匹配 "bestseller" 中的 "best"
        repo = {"description": "A bestseller book list"}
        # 但实际实现用的是 \b 模式，"bestseller" 中的 "best" 后面没有词边界
        # 所以不应扣分
        result = anti_spam.check_marketing_words(repo)
        assert result == 0


class TestCheckSuspiciousPattern:
    """测试可疑模式检测。"""

    def test_trainer_pattern_detected(self):
        """含 trainer 关键词的仓库应扣 10 分。"""
        repo = {"full_name": "user/game-trainer", "description": ""}
        assert anti_spam.check_suspicious_pattern(repo) == 10

    def test_cheat_pattern_detected(self):
        """含 cheat 关键词应扣分。"""
        repo = {"full_name": "user/cheat-engine", "description": ""}
        assert anti_spam.check_suspicious_pattern(repo) == 10

    def test_aimbot_pattern_detected(self):
        """含 aimbot 关键词应扣分。"""
        repo = {"full_name": "user/aimbot-tool", "description": "an aimbot for games"}
        assert anti_spam.check_suspicious_pattern(repo) == 10

    def test_suspicious_username_with_numbers(self):
        """用户名含 >30% 数字应扣 5 分。"""
        # "xjkq83ab" → 8 chars, 2 digits (25%) → 不够
        repo = {"full_name": "xjkq83ab/project", "description": ""}
        # 2/8 = 0.25，不满足 >0.3
        assert anti_spam.check_suspicious_pattern(repo) == 0

    def test_highly_numeric_username(self):
        """用户名含大量数字应扣分。"""
        # "abc1234567" → 10 chars, 7 digits (70%)
        repo = {"full_name": "abc1234567/project", "description": ""}
        assert anti_spam.check_suspicious_pattern(repo) == 5

    def test_short_username_not_suspicious(self):
        """短用户名即使数字多也不应扣分（len ≤ 8）。"""
        repo = {"full_name": "a1b2c3/project", "description": ""}
        # len("a1b2c3") = 6, 不满足 >8
        assert anti_spam.check_suspicious_pattern(repo) == 0

    def test_normal_repo_no_deduction(self):
        """正常仓库不应扣分。"""
        repo = {"full_name": "torvalds/linux", "description": "Linux kernel"}
        assert anti_spam.check_suspicious_pattern(repo) == 0


class TestCalculateAntiscore:
    """测试反垃圾总分计算。"""

    def test_clean_repo_gets_full_score(self):
        """无任何可疑信号的仓库应获得满分 30。"""
        repo = {
            "full_name": "user/clean-project",
            "description": "A simple open source tool",
            "stars": 200,
            "forks": 20,
            "age_days": 30,
        }
        assert anti_spam.calculate_antiscore(repo) == 30

    def test_multiple_penalties_accumulate(self):
        """多个可疑信号应叠加扣分。"""
        repo = {
            "full_name": "xjkq83ab/game-trainer",  # suspicious username + trainer
            "description": "Best revolutionary game-changing ultimate cheat tool",  # 5+ marketing words
            "stars": 6000,
            "forks": 5,  # ratio=1200 > 50
            "age_days": 1,  # sudden stars
        }
        score = anti_spam.calculate_antiscore(repo)
        # 30 - 10(ratio) - 15(sudden) - 10(marketing) - 10(trainer) = -15 → max(0, -15) = 0
        assert score == 0

    def test_score_never_negative(self):
        """总分不应低于 0。"""
        repo = {
            "full_name": "abc1234567/trainer-cheat-hack",
            "description": "Best revolutionary game-changing ultimate 10x magic miracle tool",
            "stars": 10000,
            "forks": 1,
            "age_days": 1,
        }
        score = anti_spam.calculate_antiscore(repo)
        assert score >= 0

    def test_partial_penalties(self):
        """部分可疑信号应部分扣分。"""
        repo = {
            "full_name": "user/normal-project",
            "description": "The best tool",  # 1 marketing word → -5
            "stars": 200,
            "forks": 20,
            "age_days": 30,
        }
        assert anti_spam.calculate_antiscore(repo) == 25  # 30 - 5
