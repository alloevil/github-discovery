"""测试评分算法的边界情况。"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import scorer


class TestScoreAcceleration:
    """测试 star 增速评分逻辑（连续对数曲线 + 加速比 bonus）。"""

    def test_monotonic_in_velocity(self):
        """同龄仓库，日增越高分越高（连续曲线的核心性质）。"""
        scores = [
            scorer.score_acceleration({"age_days": 10, "stars": 10 * d})
            for d in (1, 5, 20, 50, 100, 300)
        ]
        assert scores == sorted(scores)
        assert scores[0] < scores[-1]

    def test_no_saturation_for_ordinary_viral(self):
        """普通爆款（age=2, 150 stars）不应再拿满分 —— 旧版饱和的根源。"""
        repo = {"age_days": 2, "stars": 150}
        assert scorer.score_acceleration(repo) < 40

    def test_max_needs_extreme_velocity_and_acceleration(self):
        """满分 40 需要极高真实日增 + 明显加速。"""
        repo = {"age_days": 10, "stars": 3000, "real_daily_stars": 900.0}
        assert scorer.score_acceleration(repo) == 40

    def test_velocity_saturates_at_cap(self):
        """速度分在饱和点封顶：再高的日增也不超过 40。"""
        repo = {"age_days": 1, "stars": 100000}
        assert scorer.score_acceleration(repo) <= 40

    def test_real_daily_overrides_lifetime_average(self):
        """有快照真实日增时应优先于终身平均。"""
        base = {"age_days": 100, "stars": 1000}          # 终身平均 10/day
        cold = dict(base, real_daily_stars=1.0)          # 实际已凉
        hot = dict(base, real_daily_stars=200.0)         # 实际在爆发
        assert scorer.score_acceleration(cold) < scorer.score_acceleration(base)
        assert scorer.score_acceleration(hot) > scorer.score_acceleration(base)

    def test_acceleration_ratio_rewards_speedup(self):
        """同样的真实日增，相对终身平均加速越明显 bonus 越高。"""
        steady = {"age_days": 10, "stars": 1000, "real_daily_stars": 100.0}   # ratio=1
        surging = {"age_days": 100, "stars": 1000, "real_daily_stars": 100.0}  # ratio=10
        assert scorer.score_acceleration(surging) > scorer.score_acceleration(steady)

    def test_young_repo_gets_freshness_credit_without_snapshot(self):
        """无快照历史时，年轻仓库获得部分加速分（终身平均≈最近速度）。"""
        young = {"age_days": 2, "stars": 100}
        old = {"age_days": 200, "stars": 10000}  # 同为 50/day
        assert scorer.score_acceleration(young) > scorer.score_acceleration(old)

    def test_negative_real_daily_zero(self):
        """star 净减少（刷量被清洗）应得 0 分。"""
        repo = {"age_days": 10, "stars": 1000, "real_daily_stars": -50.0}
        assert scorer.score_acceleration(repo) == 0

    def test_zero_stars_gets_zero(self):
        """0 star 仓库应得 0 分。"""
        repo = {"age_days": 30, "stars": 0}
        assert scorer.score_acceleration(repo) == 0

    def test_zero_age_no_crash(self):
        """age_days=0 不应除零崩溃（内部按 age=1 处理）。"""
        repo = {"age_days": 0, "stars": 100}
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


class TestMergeQualityBonus:
    """深查加分并入 quality 维度（取 max），不再 total+=bonus 后 clamp。

    旧版叠加+clamp 让 94% 上榜条目总分恒为 100（README/license 在
    score_quality 和 quality bonus 里被重复计分）——回归防线。
    """

    def _scores(self, acc=40, qual=30, anti=30):
        return {"total": acc + qual + anti, "acceleration": acc,
                "quality": qual, "antispam": anti}

    def test_full_marks_repo_no_longer_saturates(self):
        """粗排 quality 已满分（30）时，bonus 不再抬高总分。

        旧版：total=100 → min(100, 100+20)=100，94% 条目都长这样。
        """
        scores = scorer.merge_quality_bonus(self._scores(acc=35), 20)
        # bonus 20 → 换算 30，与粗排 quality 30 取 max，总分不变
        assert scores["quality"] == 30
        assert scores["total"] == 95

    def test_bonus_lifts_weak_coarse_quality(self):
        """深查信号好于粗排时，quality 提升到换算后的 bonus 值。"""
        scores = scorer.merge_quality_bonus(self._scores(qual=10), 20)
        assert scores["quality"] == 30
        assert scores["total"] == 40 + 30 + 30

    def test_low_bonus_never_lowers_quality(self):
        """深查得分低于粗排 quality 时保留粗排值（取 max 而非覆盖）。"""
        scores = scorer.merge_quality_bonus(self._scores(qual=25), 10)
        # bonus 10 → 换算 15 < 25，quality 不降
        assert scores["quality"] == 25
        assert scores["total"] == 40 + 25 + 30

    def test_zero_bonus_is_noop(self):
        scores = self._scores()
        before = dict(scores)
        assert scorer.merge_quality_bonus(scores, 0) == before
        assert "quality_bonus" not in scores

    def test_records_raw_bonus_in_breakdown(self):
        scores = scorer.merge_quality_bonus(self._scores(qual=10), 14)
        assert scores["quality_bonus"] == 14

    def test_quality_dimension_never_exceeds_max(self):
        scores = scorer.merge_quality_bonus(self._scores(qual=30), 20)
        assert scores["quality"] <= 30


class TestBuildReason:
    """理由行（issue #9）：'+852/day · Trending+HN · 3.2x accelerating'。"""

    def test_contains_daily_velocity_and_sources(self):
        repo = {"age_days": 5, "stars": 100, "real_daily_stars": 852.0,
                "sources": ["trending", "hn"]}
        reason = scorer.build_reason(repo)
        assert reason.startswith("+852/day")
        assert "Trending+HN" in reason

    def test_acceleration_shown_when_significant(self):
        # 终身平均 10/day，真实日增 32/day → 3.2x
        repo = {"age_days": 100, "stars": 1000, "real_daily_stars": 32.0,
                "source": "rising"}
        reason = scorer.build_reason(repo)
        assert "3.2x accelerating" in reason
        assert "Rising" in reason

    def test_acceleration_hidden_when_steady(self):
        """匀速（加速比 < 1.5）不展示加速比 —— 无区分价值。"""
        repo = {"age_days": 100, "stars": 1000, "real_daily_stars": 11.0,
                "source": "search"}
        assert "accelerating" not in scorer.build_reason(repo)

    def test_falls_back_to_lifetime_average_without_snapshot(self):
        repo = {"age_days": 4, "stars": 200, "source": "trending"}
        reason = scorer.build_reason(repo)
        assert reason.startswith("+50/day")
        assert "accelerating" not in reason

    def test_low_velocity_keeps_one_decimal(self):
        repo = {"age_days": 100, "stars": 250, "source": "hn"}
        assert scorer.build_reason(repo).startswith("+2.5/day")

    def test_reasons_distinguish_head_entries(self):
        """两个都可能是 100 分的头部条目，理由行必须不同。"""
        a = {"age_days": 3, "stars": 900, "real_daily_stars": 800.0, "sources": ["trending", "hn"]}
        b = {"age_days": 30, "stars": 9000, "real_daily_stars": 350.0, "sources": ["ai-trending"]}
        assert scorer.build_reason(a) != scorer.build_reason(b)
