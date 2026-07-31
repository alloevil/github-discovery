"""测试每日 star 快照与真实增速计算。"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

import snapshots


@pytest.fixture
def snapshot_file(tmp_path):
    """把快照文件重定向到临时目录。"""
    f = tmp_path / "star_snapshots.json"
    with patch.object(snapshots, "SNAPSHOT_FILE", f):
        yield f


def _repo(name, stars):
    return {"full_name": name, "stars": stars}


class TestRecordSnapshots:

    def test_creates_file_with_today_entry(self, snapshot_file):
        snapshots.record_snapshots([_repo("a/b", 100)], today="2026-07-31")
        data = json.loads(snapshot_file.read_text())
        assert data["repos"]["a/b"] == [["2026-07-31", 100]]

    def test_same_day_rerun_overwrites(self, snapshot_file):
        snapshots.record_snapshots([_repo("a/b", 100)], today="2026-07-31")
        snapshots.record_snapshots([_repo("a/b", 150)], today="2026-07-31")
        data = json.loads(snapshot_file.read_text())
        assert data["repos"]["a/b"] == [["2026-07-31", 150]]

    def test_accumulates_across_days(self, snapshot_file):
        snapshots.record_snapshots([_repo("a/b", 100)], today="2026-07-30")
        snapshots.record_snapshots([_repo("a/b", 250)], today="2026-07-31")
        data = json.loads(snapshot_file.read_text())
        assert data["repos"]["a/b"] == [["2026-07-30", 100], ["2026-07-31", 250]]

    def test_prunes_old_points_and_stale_repos(self, snapshot_file):
        snapshots.record_snapshots([_repo("old/gone", 10), _repo("a/b", 100)], today="2026-06-01")
        snapshots.record_snapshots([_repo("a/b", 500)], today="2026-07-31")
        data = json.loads(snapshot_file.read_text())
        # a/b 的 6 月点超过 30 天被裁掉，仓库保留
        assert data["repos"]["a/b"] == [["2026-07-31", 500]]
        # old/gone 最新点已过期，整体清除
        assert "old/gone" not in data["repos"]

    def test_corrupt_file_recovers(self, snapshot_file):
        snapshot_file.write_text("{not json")
        snapshots.record_snapshots([_repo("a/b", 100)], today="2026-07-31")
        data = json.loads(snapshot_file.read_text())
        assert data["repos"]["a/b"] == [["2026-07-31", 100]]


class TestGetGrowth:

    def test_no_history_returns_none(self, snapshot_file):
        assert snapshots.get_growth("a/b", 100, today="2026-07-31") is None

    def test_only_today_entry_returns_none(self, snapshot_file):
        """首次见到的仓库（只有今天的点）没有真实增速。"""
        snapshots.record_snapshots([_repo("a/b", 100)], today="2026-07-31")
        assert snapshots.get_growth("a/b", 100, today="2026-07-31") is None

    def test_one_day_delta(self, snapshot_file):
        snapshots.record_snapshots([_repo("a/b", 100)], today="2026-07-30")
        g = snapshots.get_growth("a/b", 250, today="2026-07-31")
        assert g["real_daily"] == 150.0
        assert g["span_days"] == 1
        assert g["prev_stars"] == 100

    def test_multi_day_gap_normalizes(self, snapshot_file):
        """隔 3 天才再次见到 → 增量按天数摊平。"""
        snapshots.record_snapshots([_repo("a/b", 100)], today="2026-07-28")
        g = snapshots.get_growth("a/b", 400, today="2026-07-31")
        assert g["real_daily"] == 100.0
        assert g["span_days"] == 3

    def test_uses_latest_prior_point(self, snapshot_file):
        snapshots.record_snapshots([_repo("a/b", 100)], today="2026-07-29")
        snapshots.record_snapshots([_repo("a/b", 200)], today="2026-07-30")
        g = snapshots.get_growth("a/b", 500, today="2026-07-31")
        assert g["real_daily"] == 300.0

    def test_order_independent_of_todays_record(self, snapshot_file):
        """先记录今天再查询，结果与先查询相同（不受当日点干扰）。"""
        snapshots.record_snapshots([_repo("a/b", 100)], today="2026-07-30")
        snapshots.record_snapshots([_repo("a/b", 250)], today="2026-07-31")
        g = snapshots.get_growth("a/b", 250, today="2026-07-31")
        assert g["real_daily"] == 150.0

    def test_star_loss_negative_delta(self, snapshot_file):
        """star 减少（刷量被清洗）应产生负增速，而不是崩溃。"""
        snapshots.record_snapshots([_repo("a/b", 1000)], today="2026-07-30")
        g = snapshots.get_growth("a/b", 800, today="2026-07-31")
        assert g["real_daily"] == -200.0
