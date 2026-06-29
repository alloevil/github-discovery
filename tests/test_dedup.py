"""测试去重逻辑。"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from pathlib import Path

import dedup


class TestIsRecentlyRecommended:
    """测试跨天去重检查逻辑。"""

    def test_returns_false_for_unknown_repo(self, tmp_path):
        """未推荐过的仓库应返回 False。"""
        history_file = tmp_path / "recommend_history.json"
        history_file.write_text(json.dumps({"repos": {}, "updated_at": ""}))

        with patch.object(dedup, "HISTORY_FILE", history_file):
            assert dedup.is_recently_recommended("user/new-repo") is False

    def test_returns_true_for_recently_recommended(self, tmp_path):
        """最近 7 天内（往日）推荐过的仓库应返回 True。"""
        history_file = tmp_path / "recommend_history.json"
        data = {
            "repos": {
                "user/repo": {
                    "last_recommended": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
                    "count": 1,
                    "scores": [85],
                }
            },
            "updated_at": "",
        }
        history_file.write_text(json.dumps(data))

        with patch.object(dedup, "HISTORY_FILE", history_file):
            assert dedup.is_recently_recommended("user/repo") is True

    def test_returns_false_for_same_day_recommendation(self, tmp_path):
        """同一天（今天）已推荐的仓库应返回 False，使同日重跑可再次入选。"""
        history_file = tmp_path / "recommend_history.json"
        data = {
            "repos": {
                "user/repo": {
                    "last_recommended": datetime.now(timezone.utc).isoformat(),
                    "count": 1,
                    "scores": [85],
                }
            },
            "updated_at": "",
        }
        history_file.write_text(json.dumps(data))

        with patch.object(dedup, "HISTORY_FILE", history_file):
            assert dedup.is_recently_recommended("user/repo") is False

    def test_returns_false_for_old_recommendation(self, tmp_path):
        """超过 7 天前推荐的仓库应返回 False。"""
        history_file = tmp_path / "recommend_history.json"
        old_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        data = {
            "repos": {
                "user/old-repo": {
                    "last_recommended": old_date,
                    "count": 1,
                    "scores": [90],
                }
            },
            "updated_at": "",
        }
        history_file.write_text(json.dumps(data))

        with patch.object(dedup, "HISTORY_FILE", history_file):
            assert dedup.is_recently_recommended("user/old-repo") is False

    def test_custom_days_parameter(self, tmp_path):
        """应支持自定义天数参数。"""
        history_file = tmp_path / "recommend_history.json"
        date_5_days_ago = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        data = {
            "repos": {
                "user/repo": {
                    "last_recommended": date_5_days_ago,
                    "count": 1,
                    "scores": [80],
                }
            },
            "updated_at": "",
        }
        history_file.write_text(json.dumps(data))

        with patch.object(dedup, "HISTORY_FILE", history_file):
            # 7 天窗口内 → True
            assert dedup.is_recently_recommended("user/repo", days=7) is True
            # 3 天窗口外 → False
            assert dedup.is_recently_recommended("user/repo", days=3) is False

    def test_handles_missing_last_recommended_field(self, tmp_path):
        """last_recommended 字段缺失时应返回 False。"""
        history_file = tmp_path / "recommend_history.json"
        data = {
            "repos": {
                "user/repo": {"count": 1, "scores": []}
            },
            "updated_at": "",
        }
        history_file.write_text(json.dumps(data))

        with patch.object(dedup, "HISTORY_FILE", history_file):
            assert dedup.is_recently_recommended("user/repo") is False

    def test_handles_invalid_date_format(self, tmp_path):
        """日期格式异常时应返回 False。"""
        history_file = tmp_path / "recommend_history.json"
        data = {
            "repos": {
                "user/repo": {
                    "last_recommended": "not-a-date",
                    "count": 1,
                    "scores": [],
                }
            },
            "updated_at": "",
        }
        history_file.write_text(json.dumps(data))

        with patch.object(dedup, "HISTORY_FILE", history_file):
            assert dedup.is_recently_recommended("user/repo") is False

    def test_handles_z_suffix_in_date(self, tmp_path):
        """应正确处理带 Z 后缀的 ISO 日期。"""
        history_file = tmp_path / "recommend_history.json"
        data = {
            "repos": {
                "user/repo": {
                    "last_recommended": (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "count": 1,
                    "scores": [75],
                }
            },
            "updated_at": "",
        }
        history_file.write_text(json.dumps(data))

        with patch.object(dedup, "HISTORY_FILE", history_file):
            assert dedup.is_recently_recommended("user/repo") is True


class TestRecordRecommendation:
    """测试推荐记录写入逻辑。"""

    def test_creates_new_record(self, tmp_path):
        """首次推荐应创建新记录。"""
        history_file = tmp_path / "recommend_history.json"
        history_file.write_text(json.dumps({"repos": {}, "updated_at": ""}))

        with patch.object(dedup, "HISTORY_FILE", history_file):
            dedup.record_recommendation("user/new-repo", 92.5)

        data = json.loads(history_file.read_text())
        assert "user/new-repo" in data["repos"]
        assert data["repos"]["user/new-repo"]["count"] == 1
        assert data["repos"]["user/new-repo"]["scores"] == [92.5]
        assert "last_recommended" in data["repos"]["user/new-repo"]

    def test_increments_count_for_existing_repo(self, tmp_path):
        """重复推荐应递增计数。"""
        history_file = tmp_path / "recommend_history.json"
        data = {
            "repos": {
                "user/repo": {
                    "last_recommended": "2026-06-01T00:00:00+00:00",
                    "count": 2,
                    "scores": [80, 85],
                }
            },
            "updated_at": "",
        }
        history_file.write_text(json.dumps(data))

        with patch.object(dedup, "HISTORY_FILE", history_file):
            dedup.record_recommendation("user/repo", 90)

        data = json.loads(history_file.read_text())
        assert data["repos"]["user/repo"]["count"] == 3
        assert len(data["repos"]["user/repo"]["scores"]) == 3

    def test_limits_scores_to_30(self, tmp_path):
        """scores 列表最多保留 30 个。"""
        history_file = tmp_path / "recommend_history.json"
        data = {
            "repos": {
                "user/repo": {
                    "last_recommended": "2026-06-01T00:00:00+00:00",
                    "count": 30,
                    "scores": [80] * 30,
                }
            },
            "updated_at": "",
        }
        history_file.write_text(json.dumps(data))

        with patch.object(dedup, "HISTORY_FILE", history_file):
            dedup.record_recommendation("user/repo", 95)

        data = json.loads(history_file.read_text())
        assert len(data["repos"]["user/repo"]["scores"]) == 30
        assert data["repos"]["user/repo"]["scores"][-1] == 95


class TestCleanupOldRecords:
    """测试旧记录清理逻辑。"""

    def test_removes_old_records(self, tmp_path):
        """应删除超过 N 天的记录。"""
        history_file = tmp_path / "recommend_history.json"
        old_date = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
        recent_date = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        data = {
            "repos": {
                "user/old-repo": {"last_recommended": old_date, "count": 1, "scores": [80]},
                "user/recent-repo": {"last_recommended": recent_date, "count": 1, "scores": [90]},
            },
            "updated_at": "",
        }
        history_file.write_text(json.dumps(data))

        with patch.object(dedup, "HISTORY_FILE", history_file):
            dedup.cleanup_old_records(days=30)

        data = json.loads(history_file.read_text())
        assert "user/old-repo" not in data["repos"]
        assert "user/recent-repo" in data["repos"]

    def test_handles_empty_history(self, tmp_path):
        """空历史文件清理不应报错。"""
        history_file = tmp_path / "recommend_history.json"
        history_file.write_text(json.dumps({"repos": {}, "updated_at": ""}))

        with patch.object(dedup, "HISTORY_FILE", history_file):
            dedup.cleanup_old_records()  # 不应抛异常

    def test_removes_records_with_invalid_dates(self, tmp_path):
        """日期格式异常的记录也应被清理。"""
        history_file = tmp_path / "recommend_history.json"
        data = {
            "repos": {
                "user/bad-date": {"last_recommended": "invalid", "count": 1, "scores": []},
                "user/good-repo": {
                    "last_recommended": datetime.now(timezone.utc).isoformat(),
                    "count": 1, "scores": [85],
                },
            },
            "updated_at": "",
        }
        history_file.write_text(json.dumps(data))

        with patch.object(dedup, "HISTORY_FILE", history_file):
            dedup.cleanup_old_records(days=30)

        data = json.loads(history_file.read_text())
        assert "user/bad-date" not in data["repos"]
        assert "user/good-repo" in data["repos"]
