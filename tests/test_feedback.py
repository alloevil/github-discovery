"""测试反馈系统的投票和去重逻辑。"""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import patch
from pathlib import Path

import feedback


class TestVote:
    """测试投票逻辑。"""

    def test_first_vote_up(self, tmp_path):
        """首次 up 投票应正确记录。"""
        fb_file = tmp_path / "feedback.json"
        fb_file.write_text(json.dumps({"repos": {}, "updated_at": ""}))

        with patch.object(feedback, "FEEDBACK_FILE", fb_file):
            result = feedback.vote("user/repo", "up", "user1")

        assert result["up"] == 1
        assert result["down"] == 0

    def test_first_vote_down(self, tmp_path):
        """首次 down 投票应正确记录。"""
        fb_file = tmp_path / "feedback.json"
        fb_file.write_text(json.dumps({"repos": {}, "updated_at": ""}))

        with patch.object(feedback, "FEEDBACK_FILE", fb_file):
            result = feedback.vote("user/repo", "down", "user1")

        assert result["up"] == 0
        assert result["down"] == 1

    def test_duplicate_vote_returns_already_voted(self, tmp_path):
        """同一用户重复相同投票应返回 already_voted。"""
        fb_file = tmp_path / "feedback.json"
        fb_file.write_text(json.dumps({"repos": {}, "updated_at": ""}))

        with patch.object(feedback, "FEEDBACK_FILE", fb_file):
            feedback.vote("user/repo", "up", "user1")
            result = feedback.vote("user/repo", "up", "user1")

        assert result["message"] == "already_voted"
        assert result["up"] == 1  # 不应增加

    def test_vote_switch_up_to_down(self, tmp_path):
        """用户从 up 切换到 down 应正确更新计数。"""
        fb_file = tmp_path / "feedback.json"
        fb_file.write_text(json.dumps({"repos": {}, "updated_at": ""}))

        with patch.object(feedback, "FEEDBACK_FILE", fb_file):
            feedback.vote("user/repo", "up", "user1")
            result = feedback.vote("user/repo", "down", "user1")

        assert result["up"] == 0
        assert result["down"] == 1

    def test_vote_switch_down_to_up(self, tmp_path):
        """用户从 down 切换到 up 应正确更新计数。"""
        fb_file = tmp_path / "feedback.json"
        fb_file.write_text(json.dumps({"repos": {}, "updated_at": ""}))

        with patch.object(feedback, "FEEDBACK_FILE", fb_file):
            feedback.vote("user/repo", "down", "user1")
            result = feedback.vote("user/repo", "up", "user1")

        assert result["up"] == 1
        assert result["down"] == 0

    def test_invalid_vote_type_returns_error(self, tmp_path):
        """无效投票类型应返回错误。"""
        fb_file = tmp_path / "feedback.json"
        fb_file.write_text(json.dumps({"repos": {}, "updated_at": ""}))

        with patch.object(feedback, "FEEDBACK_FILE", fb_file):
            result = feedback.vote("user/repo", "invalid", "user1")

        assert "error" in result

    def test_multiple_users_vote(self, tmp_path):
        """不同用户投票应独立计数。"""
        fb_file = tmp_path / "feedback.json"
        fb_file.write_text(json.dumps({"repos": {}, "updated_at": ""}))

        with patch.object(feedback, "FEEDBACK_FILE", fb_file):
            feedback.vote("user/repo", "up", "user1")
            feedback.vote("user/repo", "up", "user2")
            feedback.vote("user/repo", "down", "user3")
            result = feedback.vote("user/repo", "up", "user4")

        assert result["up"] == 3
        assert result["down"] == 1

    def test_down_vote_floor_at_zero(self, tmp_path):
        """down 计数不应低于 0。"""
        fb_file = tmp_path / "feedback.json"
        # 预设一个异常状态：down=0 但 user1 记录为 up
        data = {
            "repos": {
                "user/repo": {"up": 1, "down": 0, "voters": {"user1": "up"}}
            },
            "updated_at": "",
        }
        fb_file.write_text(json.dumps(data))

        with patch.object(feedback, "FEEDBACK_FILE", fb_file):
            # user1 从 up 切到 down
            result = feedback.vote("user/repo", "down", "user1")

        assert result["up"] == 0
        assert result["down"] == 1

    def test_anonymous_user_default(self, tmp_path):
        """未指定 user_id 时应使用 anonymous。"""
        fb_file = tmp_path / "feedback.json"
        fb_file.write_text(json.dumps({"repos": {}, "updated_at": ""}))

        with patch.object(feedback, "FEEDBACK_FILE", fb_file):
            feedback.vote("user/repo", "up")
            # 同样 anonymous 用户再次投票应触发 already_voted
            result = feedback.vote("user/repo", "up")

        assert result["message"] == "already_voted"


class TestGetFeedback:
    """测试反馈查询逻辑。"""

    def test_returns_counts_for_existing_repo(self, tmp_path):
        """已有投票记录的仓库应返回正确计数。"""
        fb_file = tmp_path / "feedback.json"
        data = {
            "repos": {
                "user/repo": {"up": 5, "down": 2, "voters": {}}
            },
            "updated_at": "",
        }
        fb_file.write_text(json.dumps(data))

        with patch.object(feedback, "FEEDBACK_FILE", fb_file):
            result = feedback.get_feedback("user/repo")

        assert result["up"] == 5
        assert result["down"] == 2

    def test_returns_zeros_for_unknown_repo(self, tmp_path):
        """无记录的仓库应返回 0。"""
        fb_file = tmp_path / "feedback.json"
        fb_file.write_text(json.dumps({"repos": {}, "updated_at": ""}))

        with patch.object(feedback, "FEEDBACK_FILE", fb_file):
            result = feedback.get_feedback("user/unknown")

        assert result["up"] == 0
        assert result["down"] == 0


class TestGetAllFeedback:
    """测试全量反馈获取。"""

    def test_calculates_net_score(self, tmp_path):
        """应计算每个仓库的净得分（up - down）。"""
        fb_file = tmp_path / "feedback.json"
        data = {
            "repos": {
                "user/repo1": {"up": 10, "down": 3, "voters": {}},
                "user/repo2": {"up": 2, "down": 5, "voters": {}},
            },
            "updated_at": "",
        }
        fb_file.write_text(json.dumps(data))

        with patch.object(feedback, "FEEDBACK_FILE", fb_file):
            result = feedback.get_all_feedback()

        assert result["user/repo1"]["score"] == 7
        assert result["user/repo2"]["score"] == -3


class TestGetTopVoted:
    """测试热门投票排序。"""

    def test_returns_sorted_by_net_score(self, tmp_path):
        """应按净得分降序排列。"""
        fb_file = tmp_path / "feedback.json"
        data = {
            "repos": {
                "user/repo1": {"up": 5, "down": 1, "voters": {}},
                "user/repo2": {"up": 10, "down": 2, "voters": {}},
                "user/repo3": {"up": 1, "down": 0, "voters": {}},
            },
            "updated_at": "",
        }
        fb_file.write_text(json.dumps(data))

        with patch.object(feedback, "FEEDBACK_FILE", fb_file):
            result = feedback.get_top_voted(limit=2)

        assert len(result) == 2
        assert result[0]["repo"] == "user/repo2"  # score=8
        assert result[1]["repo"] == "user/repo1"  # score=4

    def test_respects_limit(self, tmp_path):
        """应遵守 limit 参数。"""
        fb_file = tmp_path / "feedback.json"
        data = {
            "repos": {f"user/repo{i}": {"up": i, "down": 0, "voters": {}} for i in range(10)},
            "updated_at": "",
        }
        fb_file.write_text(json.dumps(data))

        with patch.object(feedback, "FEEDBACK_FILE", fb_file):
            result = feedback.get_top_voted(limit=3)

        assert len(result) == 3
