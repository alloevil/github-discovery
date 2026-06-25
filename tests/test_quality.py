"""测试质量检测的评分逻辑。"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import quality


class TestCheckQuality:
    """测试代码质量检测评分逻辑。"""

    @patch("quality._gh_api")
    @patch("time.sleep")
    def test_full_quality_repo(self, mock_sleep, mock_api):
        """有 README、LICENSE、CI、活跃提交的仓库应得高分。"""
        # Mock contents API（返回 README、LICENSE、.github）
        mock_api.side_effect = [
            # /repos/.../contents
            [
                {"name": "README.md"},
                {"name": "LICENSE"},
                {"name": ".github"},
                {"name": "src"},
            ],
            # /repos/.../commits（1 天前的提交）
            [{"commit": {"committer": {"date": (datetime.now(timezone.utc) - timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M:%SZ")}}}],
            # /repos/...
            {"open_issues_count": 5},
            # /repos/.../pulls
            [{"number": 1}],
        ]

        result = quality.check_quality("user/repo")

        assert result["has_readme"] is True
        assert result["has_license"] is True
        assert result["has_ci"] is True
        assert result["recent_commits"] == 7  # 1 天内
        assert result["open_issues"] == 5
        assert result["quality_score"] >= 16  # 5+3+4+7+1=20, 但 capped at 20

    @patch("quality._gh_api")
    @patch("time.sleep")
    def test_minimal_repo(self, mock_sleep, mock_api):
        """无 README、无 LICENSE、无 CI 的仓库应得低分。"""
        mock_api.side_effect = [
            # contents: 只有源码文件
            [{"name": "main.py"}],
            # commits: 无提交或 30 天前
            [{"commit": {"committer": {"date": (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")}}}],
            # repo data
            {"open_issues_count": 0},
            # pulls
            [],
        ]

        result = quality.check_quality("user/repo")

        assert result["has_readme"] is False
        assert result["has_license"] is False
        assert result["has_ci"] is False
        assert result["recent_commits"] == 0
        assert result["quality_score"] == 0

    @patch("quality._gh_api")
    @patch("time.sleep")
    def test_commit_recency_scoring(self, mock_sleep, mock_api):
        """不同提交时间应获得不同分值。"""
        base_contents = [{"name": "README.md"}]

        def test_commit_days_ago(days, expected_score):
            """辅助函数：测试 N 天前提交的分值。"""
            # 重置 mock
            mock_api.reset_mock()
            mock_api.side_effect = [
                base_contents,
                [{"commit": {"committer": {"date": (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")}}}],
                {"open_issues_count": 0},
                [],
            ]
            result = quality.check_quality("user/repo")
            assert result["recent_commits"] == expected_score, f"days={days}: expected {expected_score}, got {result['recent_commits']}"

        test_commit_days_ago(0, 7)   # 今天
        test_commit_days_ago(1, 7)   # 1 天前
        test_commit_days_ago(2, 5)   # 2 天前
        test_commit_days_ago(3, 5)   # 3 天前
        test_commit_days_ago(5, 3)   # 5 天前
        test_commit_days_ago(7, 3)   # 7 天前
        test_commit_days_ago(15, 0)  # 15 天前

    @patch("quality._gh_api")
    @patch("time.sleep")
    def test_quality_score_capped_at_20(self, mock_sleep, mock_api):
        """质量加分应上限为 20。"""
        mock_api.side_effect = [
            [{"name": "README.md"}, {"name": "LICENSE"}, {"name": ".github"}],
            [{"commit": {"committer": {"date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}}}],
            {"open_issues_count": 100},
            [{"number": 1}],
        ]

        result = quality.check_quality("user/repo")
        assert result["quality_score"] == 20

    @patch("quality._gh_api")
    @patch("time.sleep")
    def test_handles_api_failure_gracefully(self, mock_sleep, mock_api):
        """API 全部失败时应返回默认值。"""
        mock_api.return_value = None

        result = quality.check_quality("user/repo")

        assert result["has_readme"] is False
        assert result["has_license"] is False
        assert result["has_ci"] is False
        assert result["quality_score"] == 0

    @patch("quality._gh_api")
    @patch("time.sleep")
    def test_detects_travis_ci(self, mock_sleep, mock_api):
        """应检测到 .travis.yml 作为 CI 配置。"""
        mock_api.side_effect = [
            [{"name": "README.md"}, {"name": ".travis.yml"}],
            [],
            {"open_issues_count": 0},
            [],
        ]

        result = quality.check_quality("user/repo")
        assert result["has_ci"] is True

    @patch("quality._gh_api")
    @patch("time.sleep")
    def test_detects_gitlab_ci(self, mock_sleep, mock_api):
        """应检测到 .gitlab-ci.yml 作为 CI 配置。"""
        mock_api.side_effect = [
            [{"name": "README.md"}, {".gitlab-ci.yml": "file"}],
            [{"name": ".gitlab-ci.yml"}],
            [],
            {"open_issues_count": 0},
            [],
        ]
        # 简化：直接用 name 字段
        mock_api.side_effect = [
            [{"name": "README.md"}, {"name": ".gitlab-ci.yml"}],
            [],
            {"open_issues_count": 0},
            [],
        ]

        result = quality.check_quality("user/repo")
        assert result["has_ci"] is True


class TestCheckStarAuthenticity:
    """测试 Star 真实性检测。"""

    @patch("quality._gh_api")
    @patch("time.sleep")
    def test_brand_new_1k_stars_suspicious(self, mock_sleep, mock_api):
        """创建 <1 天且 >1000 stars 应判定为可疑。"""
        result = quality.check_star_authenticity("user/repo", stars=1500, age_days=0)

        assert result["is_suspicious"] is True
        assert result["penalty"] == -20
        assert "1k_stars" in result["reason"]

    @patch("quality._gh_api")
    @patch("time.sleep")
    def test_2k_stars_in_2_days_suspicious(self, mock_sleep, mock_api):
        """创建 <2 天且 >2000 stars 应判定为可疑。"""
        result = quality.check_star_authenticity("user/repo", stars=3000, age_days=1)

        assert result["is_suspicious"] is True
        assert result["penalty"] == -15

    @patch("quality._gh_api")
    @patch("time.sleep")
    def test_healthy_repo_not_suspicious(self, mock_sleep, mock_api):
        """正常增长的仓库不应被判定为可疑。"""
        result = quality.check_star_authenticity("user/repo", stars=500, age_days=30)

        assert result["is_suspicious"] is False
        assert result["penalty"] == 0

    @patch("quality._gh_api")
    @patch("time.sleep")
    def test_massive_stars_no_description_suspicious(self, mock_sleep, mock_api):
        """日增 >1000 stars 且无描述应判定为可疑。"""
        mock_api.return_value = {"description": ""}

        result = quality.check_star_authenticity("user/repo", stars=15000, age_days=10)

        assert result["is_suspicious"] is True
        assert result["penalty"] == -15

    @patch("quality._gh_api")
    @patch("time.sleep")
    def test_massive_stars_with_description_not_suspicious(self, mock_sleep, mock_api):
        """日增 >1000 stars 但有描述不应判定为可疑。"""
        mock_api.return_value = {"description": "A well-documented project"}

        result = quality.check_star_authenticity("user/repo", stars=15000, age_days=10)

        # 有描述，不满足检测 3 的条件
        assert result["is_suspicious"] is False

    @patch("quality._gh_api")
    @patch("time.sleep")
    def test_exact_boundary_not_suspicious(self, mock_sleep, mock_api):
        """恰好在边界上（age_days=1, stars=1000）不应判定为可疑。"""
        # age_days < 1 需要 age_days=0；age_days=1 不满足
        result = quality.check_star_authenticity("user/repo", stars=1000, age_days=1)

        # age_days=1 不满足 <1 条件，也不满足 <2 且 >2000
        assert result["is_suspicious"] is False
