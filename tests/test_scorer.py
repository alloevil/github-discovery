"""测试评分算法的边界情况。"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import scorer


class TestScoreAcceleration:
    """测试 star 增速评分逻辑。"""

    def test_brand_new_viral_repo_gets_max_score(self):
        """创建 ≤3 天且 star ≥100 的仓库应获得满分 40。"""
        repo = {"age_days": 2, "stars": 150}
        assert scorer.score_acceleration(repo) == 40

    def test_brand_new_exact_boundary(self):
        """恰好在边界上（age=3, stars=100）应获得满分。"""
        repo = {"age_days": 3, "stars": 100}
        assert scorer.score_acceleration(repo) == 40

    def test_brand_new_just_over_boundary(self):
        """age=4 不应命中 Tier 1，但可能命中后续 tier。"""
        repo = {"age_days": 4, "stars": 100}
        result = scorer.score_acceleration(repo)
        assert result < 40

    def test_tier2_new_with_strong_traction(self):
        """7 天内 200+ stars 应命中 Tier 2 (34)。"""
        repo = {"age_days": 5, "stars": 250}
        assert scorer.score_acceleration(repo) == 34

    def test_tier3_solid_growth(self):
        """30 天内 500+ stars 应命中 Tier 3 (28)。"""
        repo = {"age_days": 20, "stars": 600}
        assert scorer.score_acceleration(repo) == 28

    def test_daily_velocity_100_plus(self):
        """日增 ≥100 stars 但命中 Tier 3 时应返回 28（tier 优先于 daily velocity）。"""
        # age=10, stars=1100 → 命中 Tier 3 (age<=30 and stars>=500) → 28
        repo = {"age_days": 10, "stars": 1100}
        assert scorer.score_acceleration(repo) == 28

    def test_daily_velocity_100_plus_pure(self):
        """不命中任何 tier 时，日增 ≥100 stars 应获得 36 分。"""
        # age=60, stars=7000 → 不命中 tier，daily=116.7 >= 100
        repo = {"age_days": 60, "stars": 7000}
        assert scorer.score_acceleration(repo) == 36  # 40 * 0.9

    def test_daily_velocity_50_plus(self):
        """日增 ≥50 stars 应获得 28 分。"""
        repo = {"age_days": 10, "stars": 500}
        assert scorer.score_acceleration(repo) == 28  # 40 * 0.7

    def test_daily_velocity_20_plus(self):
        """日增 ≥20 stars 应获得 20 分。"""
        repo = {"age_days": 10, "stars": 200}
        assert scorer.score_acceleration(repo) == 20  # 40 * 0.5

    def test_daily_velocity_10_plus(self):
        """日增 ≥10 stars 应获得 12 分。"""
        repo = {"age_days": 10, "stars": 100}
        assert scorer.score_acceleration(repo) == 12  # 40 * 0.3

    def test_daily_velocity_5_plus(self):
        """日增 ≥5 stars 应获得 6 分。"""
        repo = {"age_days": 10, "stars": 50}
        assert scorer.score_acceleration(repo) == 6  # 40 * 0.15

    def test_zero_stars_gets_zero(self):
        """0 star 仓库应得 0 分。"""
        repo = {"age_days": 30, "stars": 0}
        assert scorer.score_acceleration(repo) == 0

    def test_zero_age_no_crash(self):
        """age_days=0 不应除零崩溃。"""
        repo = {"age_days": 0, "stars": 100}
        # age=0, stars=100 → daily = stars (因为 age>0 条件为 false)
        # 但 age <= 3 and stars >= 100 → 40
        result = scorer.score_acceleration(repo)
        assert result >= 0

    def test_missing_fields_default_zero(self):
        """缺失字段应安全地默认为 0。"""
        repo = {}
        result = scorer.score_acceleration(repo)
        assert result == 0


class TestScoreQuality:
    """测试仓库质量评分逻辑。"""

    def test_perfect_repo_gets_max_score(self):
        """所有质量信号都满足时应得满分 30。"""
        repo = {
            "has_readme": True,
            "description": "A long and detailed description for this project",
            "fork": False,
            "license": "MIT",
            "language": "Python",
        }
        assert scorer.score_quality(repo) == 30

    def test_no_readme_deducts_10(self):
        """无 README 扣 10 分，短描述再扣 5 分。"""
        repo = {
            "has_readme": False,
            "description": "A long description",  # 18 chars < 20
            "fork": False,
            "license": "MIT",
            "language": "Python",
        }
        # 0 + 0(desc) + 5 + 5 + 5 = 15
        assert scorer.score_quality(repo) == 15

    def test_short_description_deducts_5(self):
        """描述 ≤20 字符扣 5 分。"""
        repo = {
            "has_readme": True,
            "description": "short",
            "fork": False,
            "license": "MIT",
            "language": "Python",
        }
        assert scorer.score_quality(repo) == 25

    def test_empty_description_deducts_5(self):
        """空描述扣 5 分。"""
        repo = {
            "has_readme": True,
            "description": "",
            "fork": False,
            "license": "MIT",
            "language": "Python",
        }
        assert scorer.score_quality(repo) == 25

    def test_fork_deducts_5(self):
        """fork 仓库扣 5 分。"""
        repo = {
            "has_readme": True,
            "description": "A long description for testing purposes",
            "fork": True,
            "license": "MIT",
            "language": "Python",
        }
        assert scorer.score_quality(repo) == 25

    def test_no_license_deducts_5(self):
        """无 license 扣 5 分。"""
        repo = {
            "has_readme": True,
            "description": "A long description for testing purposes",
            "fork": False,
            "license": "",
            "language": "Python",
        }
        assert scorer.score_quality(repo) == 25

    def test_no_language_deducts_5(self):
        """未指定语言扣 5 分。"""
        repo = {
            "has_readme": True,
            "description": "A long description for testing purposes",
            "fork": False,
            "license": "MIT",
            "language": "",
        }
        assert scorer.score_quality(repo) == 25

    def test_empty_repo_gets_minimal_score(self):
        """空仓库因 fork 默认 False 得 5 分。"""
        repo = {}
        # has_readme=False, desc="", fork=False(默认), license="", language=""
        # 0 + 0 + 5 + 0 + 0 = 5
        assert scorer.score_quality(repo) == 5

    def test_description_exactly_20_chars_not_counted(self):
        """恰好 20 字符的描述不应加分（需要 > 20）。"""
        repo = {
            "has_readme": True,
            "description": "a" * 20,  # exactly 20
            "fork": False,
            "license": "MIT",
            "language": "Python",
        }
        assert scorer.score_quality(repo) == 25  # 10 + 0 + 5 + 5 + 5

    def test_description_21_chars_counts(self):
        """21 字符的描述应加分。"""
        repo = {
            "has_readme": True,
            "description": "a" * 21,
            "fork": False,
            "license": "MIT",
            "language": "Python",
        }
        assert scorer.score_quality(repo) == 30


class TestCalculateScore:
    """测试总分计算。"""

    @patch("scorer.calculate_antiscore", return_value=30)
    def test_sums_all_components(self, mock_anti, sample_repo):
        """总分应等于 acceleration + quality + antispam。"""
        result = scorer.calculate_score(sample_repo)

        assert result["total"] == result["acceleration"] + result["quality"] + result["antispam"]
        assert result["antispam"] == 30

    @patch("scorer.calculate_antiscore", return_value=30)
    def test_score_keys_present(self, mock_anti, sample_repo):
        """返回字典应包含所有必要字段。"""
        result = scorer.calculate_score(sample_repo)

        assert "total" in result
        assert "acceleration" in result
        assert "quality" in result
        assert "antispam" in result
