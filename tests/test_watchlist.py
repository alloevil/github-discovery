"""测试 watch list：推荐之后的持续观察与标签覆盖度。

这个模块存在的理由是一个测量结果：原有 star_snapshots.json 只记「当天又出现在候选池里」
的仓库，于是 463 个被推荐过的仓库里只有 29 个（6.3%）能拿到推荐日 +7 天的读数，而
「它有没有爆发」这个标签正是回测的前提。测试守的就是这条：观察序列必须真的累积起来。
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

import watchlist


@pytest.fixture
def wl(tmp_path):
    """把两个数据文件重定向到临时目录（以及 discovery 文件的扫描目录）。"""
    data = tmp_path / "data"
    data.mkdir()
    with patch.object(watchlist, "DATA", data), \
         patch.object(watchlist, "WATCHLIST_FILE", data / "watchlist.json"), \
         patch.object(watchlist, "SERIES_FILE", data / "watch_series.json"), \
         patch.object(watchlist, "record_snapshots", lambda *a, **k: None):
        yield data


def _obs(name, stars=100, forks=5, issues=1, commits=3, contributors=2):
    return {"full_name": name, "stars": stars, "forks": forks, "open_issues": issues,
            "commits_7d": commits, "contributors_7d": contributors, "pushed_at": "2026-09-14T00:00:00Z"}


class TestAddDiscoveries:

    def test_records_the_window_from_the_discovery_date(self, wl):
        assert watchlist.add_discoveries([{"full_name": "a/b", "stars": 42}], today="2026-09-14") == 1
        entry = json.loads((wl / "watchlist.json").read_text())["repos"]["a/b"]
        assert entry["first_seen"] == "2026-09-14"
        assert entry["until"] == "2026-09-28"  # WATCH_DAYS
        assert entry["stars_at_discovery"] == 42

    def test_reseeing_a_repo_does_not_reset_its_clock(self, wl):
        watchlist.add_discoveries([{"full_name": "a/b", "stars": 42}], today="2026-09-14")
        watchlist.add_discoveries([{"full_name": "a/b", "stars": 900}], today="2026-09-20")
        entry = json.loads((wl / "watchlist.json").read_text())["repos"]["a/b"]
        assert entry["first_seen"] == "2026-09-14" and entry["stars_at_discovery"] == 42


class TestDue:

    def test_expired_and_already_observed_are_not_due(self, wl):
        watchlist.add_discoveries([{"full_name": "old/x"}], today="2026-08-01")   # 窗口 08-15 结束
        watchlist.add_discoveries([{"full_name": "new/y"}], today="2026-09-10")   # 仍在窗口内
        watchlist.add_discoveries([{"full_name": "fresh/z"}], today="2026-09-14")  # 今天已观察
        watchlist.record([_obs("fresh/z")], today="2026-09-14")
        # old/x 的窗口 08-15 就结束了；new/y 仍在窗口内且今天没观察过；fresh/z 今天已观察
        assert watchlist.due(today="2026-09-14") == ["new/y"]

    def test_limit_takes_the_windows_closing_first(self, wl):
        watchlist.add_discoveries([{"full_name": "a/1"}], today="2026-09-01")
        watchlist.add_discoveries([{"full_name": "a/2"}], today="2026-09-10")
        assert watchlist.due(today="2026-09-14", limit=1) == ["a/1"]


class TestRecord:

    def test_same_day_rerun_replaces_the_point(self, wl):
        watchlist.record([_obs("a/b", stars=10)], today="2026-09-14")
        watchlist.record([_obs("a/b", stars=11)], today="2026-09-14")
        series = json.loads((wl / "watch_series.json").read_text())["repos"]["a/b"]
        assert len(series) == 1 and series[0]["stars"] == 11

    def test_incomplete_observations_are_dropped(self, wl):
        assert watchlist.record([{"full_name": "a/b", "stars": 1}], today="2026-09-14") == 0
        assert not (wl / "watch_series.json").exists()

    def test_points_accumulate_across_days(self, wl):
        watchlist.record([_obs("a/b", stars=10)], today="2026-09-14")
        watchlist.record([_obs("a/b", stars=25)], today="2026-09-15")
        series = json.loads((wl / "watch_series.json").read_text())["repos"]["a/b"]
        assert [p["stars"] for p in series] == [10, 25]


class TestPruneAndBackfill:

    def test_prune_forgets_the_watch_but_keeps_the_series(self, wl):
        watchlist.add_discoveries([{"full_name": "a/b"}], today="2026-09-01")
        watchlist.record([_obs("a/b")], today="2026-09-02")
        assert watchlist.prune_expired(today="2026-09-20") == 1
        assert json.loads((wl / "watchlist.json").read_text())["repos"] == {}
        assert "a/b" in json.loads((wl / "watch_series.json").read_text())["repos"]

    def test_backfill_adopts_only_discoveries_young_enough_to_be_observed(self, wl):
        for day, name in (("2026-09-13", "recent/one"), ("2026-08-01", "ancient/two")):
            (wl / f"discovery-{day}.json").write_text(json.dumps(
                {"date": day, "new": [{"full_name": name}], "repeat": []}))
        assert watchlist.backfill(days=7, today="2026-09-14") == 1
        stored = json.loads((wl / "watchlist.json").read_text())["repos"]
        assert list(stored) == ["recent/one"] and stored["recent/one"]["backfilled"] is True
        assert watchlist.backfill(days=7, today="2026-09-14") == 0  # idempotent


class TestCoverage:

    def _discovery(self, wl, day, name):
        (wl / f"discovery-{day}.json").write_text(json.dumps(
            {"date": day, "new": [{"full_name": name}], "repeat": []}))

    def test_a_reading_at_exactly_seven_days_counts(self, wl):
        self._discovery(wl, "2026-09-01", "a/b")
        watchlist.record([_obs("a/b", stars=50)], today="2026-09-08")
        cov = watchlist.coverage()
        assert cov["discoveries"] == 1 and cov["labelable"] == 1
        assert cov["labelable_watch_series"] == 1

    def test_a_reading_at_six_days_does_not(self, wl):
        self._discovery(wl, "2026-09-01", "a/b")
        watchlist.record([_obs("a/b", stars=50)], today="2026-09-07")
        cov = watchlist.coverage()
        assert cov["discoveries"] == 1 and cov["labelable"] == 0

    def test_the_old_snapshot_file_still_counts(self, wl):
        # 与历史基线可比：旧文件的点也算数，但要单独报出来
        self._discovery(wl, "2026-09-01", "a/b")
        (wl / "star_snapshots.json").write_text(json.dumps(
            {"repos": {"a/b": [["2026-09-01", 10], ["2026-09-09", 80]]}, "updated_at": ""}))
        cov = watchlist.coverage()
        assert cov["labelable"] == 1
        assert cov["labelable_star_snapshots"] == 1 and cov["labelable_watch_series"] == 0


class TestRefresh:

    def test_records_observations_and_reports_stats(self, wl):
        watchlist.add_discoveries([{"full_name": "a/b"}, {"full_name": "c/d"}], today="2026-09-14")
        calls = []

        def fake(name):
            calls.append(name)
            return _obs(name)

        stats = watchlist.refresh(today="2026-09-14", fetch=fake, verbose=False)
        assert sorted(calls) == ["a/b", "c/d"]
        assert stats["due"] == 2 and stats["observed"] == 2 and stats["failed"] == 0

    def test_one_broken_repo_does_not_stop_the_run(self, wl):
        watchlist.add_discoveries([{"full_name": "a/b"}, {"full_name": "c/d"}], today="2026-09-14")

        def fake(name):
            if name == "a/b":
                raise RuntimeError("boom")
            return _obs(name)

        stats = watchlist.refresh(today="2026-09-14", fetch=fake, verbose=False)
        assert stats["observed"] == 1 and stats["failed"] == 1

    def test_all_failures_exit_non_zero(self, wl):
        watchlist.add_discoveries([{"full_name": "a/b"}], today="2026-09-14")
        with patch.object(watchlist, "refresh", return_value={
                "due": 1, "observed": 0, "failed": 1, "pruned": 0, "labelable": 0,
                "discoveries": 1, "pct": 0.0, "watch_days": 7,
                "labelable_watch_series": 0, "labelable_star_snapshots": 0}):
            assert watchlist.main([]) == 1
