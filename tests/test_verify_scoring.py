"""测试 verify_scoring.py 的 JSON 数据加载(#7:JSON 为唯一数据源)。"""

import json
import os
from datetime import datetime, timedelta, timezone

import pytest

import verify_scoring


def _write_report(data_dir, date_str, new_entries):
    report = {
        "date": date_str,
        "generated_at": f"{date_str}T05:00:00",
        "new": new_entries,
        "repeat": [],
    }
    path = os.path.join(data_dir, f"discovery-{date_str}.json")
    with open(path, "w") as f:
        json.dump(report, f)
    return path


def _entry(full_name, stars=100, total=90, age_days=10, **extra):
    e = {
        "full_name": full_name,
        "url": f"https://github.com/{full_name}",
        "language": "Python",
        "stars": stars,
        "age_days": age_days,
        "source": "trending",
        "scores": {"total": total, "acceleration": 40, "quality": 30, "antispam": 20},
    }
    e.update(extra)
    return e


class TestLoadReposFromJson:

    def test_loads_new_entries_with_expected_fields(self, tmp_path):
        _write_report(str(tmp_path), "2026-08-10", [_entry("a/one", stars=150, total=95)])

        repos = verify_scoring.load_repos_from_json(data_dir=str(tmp_path))

        assert len(repos) == 1
        r = repos[0]
        assert r["full_name"] == "a/one"
        assert r["stars_at_discovery"] == 150
        assert r["score"] == 95
        assert r["discovered_at"] == "2026-08-10 00:00:00"
        assert r["language"] == "Python"
        assert r["source"] == "trending"
        # created_at 从 age_days 反推:2026-08-10 - 10 天
        assert r["created_at"] == "2026-07-31"

    def test_earliest_appearance_wins_for_repeat_recommendations(self, tmp_path):
        """同一仓库多天出现时,以最早一天的 star 数为回测基线。"""
        _write_report(str(tmp_path), "2026-08-01", [_entry("a/one", stars=100, total=88)])
        _write_report(str(tmp_path), "2026-08-05", [_entry("a/one", stars=400, total=92)])

        repos = verify_scoring.load_repos_from_json(data_dir=str(tmp_path))

        assert len(repos) == 1
        assert repos[0]["stars_at_discovery"] == 100
        assert repos[0]["discovered_at"] == "2026-08-01 00:00:00"

    def test_days_filter_excludes_old_reports(self, tmp_path):
        today = datetime.now(timezone.utc)
        recent = today.strftime("%Y-%m-%d")
        old = (today - timedelta(days=40)).strftime("%Y-%m-%d")
        _write_report(str(tmp_path), recent, [_entry("new/repo")])
        _write_report(str(tmp_path), old, [_entry("old/repo")])

        repos = verify_scoring.load_repos_from_json(days=30, data_dir=str(tmp_path))

        assert [r["full_name"] for r in repos] == ["new/repo"]

    def test_empty_dir_returns_empty_list(self, tmp_path):
        assert verify_scoring.load_repos_from_json(data_dir=str(tmp_path)) == []

    def test_unreadable_report_is_skipped_not_fatal(self, tmp_path):
        _write_report(str(tmp_path), "2026-08-10", [_entry("a/one")])
        with open(os.path.join(str(tmp_path), "discovery-2026-08-11.json"), "w") as f:
            f.write("{not json")

        repos = verify_scoring.load_repos_from_json(data_dir=str(tmp_path))

        assert [r["full_name"] for r in repos] == ["a/one"]

    def test_sorted_most_recent_first(self, tmp_path):
        _write_report(str(tmp_path), "2026-08-01", [_entry("a/old")])
        _write_report(str(tmp_path), "2026-08-05", [_entry("b/new")])

        repos = verify_scoring.load_repos_from_json(data_dir=str(tmp_path))

        assert [r["full_name"] for r in repos] == ["b/new", "a/old"]

    def test_loaded_entry_feeds_analyze_repo(self, tmp_path):
        """加载出的字典能直接进入 analyze_repo 计算增长率(格式契约)。"""
        _write_report(str(tmp_path), "2026-08-01", [_entry("a/one", stars=100, total=95)])
        repos = verify_scoring.load_repos_from_json(data_dir=str(tmp_path))

        result = verify_scoring.analyze_repo(repos[0], {"stars": 150, "archived": False})

        assert result["star_delta"] == 50
        assert result["growth_rate"] == 0.5
        assert result["took_off"] is True
