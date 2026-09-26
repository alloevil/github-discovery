"""回测：标签、分档、lead time。

守的是一条边界：**没有 7 天后读数就不能算标签**。把未标注的仓库默认成「没爆发」会让
整张表看起来比实际有信息量，这正是这个仓库反对的那种数字。
"""

import json
from datetime import datetime, timedelta

import backtest


def _row(name, first_seen, stars, score=95):
    return {"repo": name, "first_seen": first_seen, "score": score, "stars_at_discovery": stars,
            "acceleration": 30, "quality": 30, "antispam": 30, "sources": "trending", "age_days": 10}


def _day(offset):
    return (datetime(2026, 9, 1) + timedelta(days=offset)).strftime("%Y-%m-%d")


class TestLabel:

    def test_six_day_reading_is_not_a_label(self):
        rows = backtest.label([_row("a/b", _day(0), 100)],
                              {"a/b": [{"date": _day(6), "stars": 900}]}, {})
        assert rows[0]["breakout"] == "" and rows[0]["growth_pct"] == ""

    def test_seven_day_reading_labels_and_breaks_out(self):
        rows = backtest.label([_row("a/b", _day(0), 100)],
                              {"a/b": [{"date": _day(7), "stars": 350}]}, {})
        assert rows[0]["growth_pct"] == 250.0 and rows[0]["breakout"] == 1

    def test_below_threshold_does_not_break_out(self):
        rows = backtest.label([_row("a/b", _day(0), 100)],
                              {"a/b": [{"date": _day(7), "stars": 250}]}, {})
        assert rows[0]["growth_pct"] == 150.0 and rows[0]["breakout"] == 0

    def test_the_older_snapshot_store_still_labels(self):
        rows = backtest.label([_row("a/b", _day(0), 100)], {},
                              {"a/b": [[_day(9), 500]]})
        assert rows[0]["breakout"] == 1

    def test_no_starting_star_count_is_not_labelled(self):
        rows = backtest.label([_row("a/b", _day(0), None)],
                              {"a/b": [{"date": _day(7), "stars": 900}]}, {})
        assert rows[0]["breakout"] == ""


class TestSummarise:

    def test_unknown_scores_are_not_silently_bucketed(self):
        stats = backtest.summarise([{"score": None, "breakout": ""}])
        assert sum(r["n"] for r in stats["table"]) == 0

    def test_thin_buckets_are_flagged(self):
        rows = [{"score": 95, "breakout": 1, "growth_pct": 300.0}]
        stats = backtest.summarise(rows)
        bucket = next(r for r in stats["table"] if r["bucket"] == "90–100")
        assert bucket["n"] == 1 and bucket["breakout_rate"] == 100.0 and bucket["insufficient"]

    def test_empty_input(self):
        stats = backtest.summarise([])
        assert stats["recommendations"] == 0 and stats["coverage_pct"] == 0.0


class TestLeadTime:

    def test_counts_only_repos_we_recommended_first(self, tmp_path, monkeypatch):
        (tmp_path / "trending-2026-09-05.json").write_text(json.dumps(
            {"date": "2026-09-05", "repos": [{"full_name": "early/one"}, {"full_name": "late/two"}]}))
        monkeypatch.setattr(backtest, "DATA", tmp_path)
        rows = [{"repo": "early/one", "first_seen": "2026-09-02"},
                {"repo": "late/two", "first_seen": "2026-09-08"}]
        leads = backtest.lead_time(rows)
        assert leads["trending_days"] == 1 and leads["matched"] == 1
        assert leads["median_lead_days"] == 3


class TestMatureSourceSummary:
    def test_groups_only_mature_rows_and_marks_thin_groups(self):
        rows = [
            {"sources": "trending", "breakout": 1, "growth_pct": 250.0},
            {"sources": "trending", "breakout": 0, "growth_pct": 50.0},
            {"sources": "search+hn", "breakout": "", "growth_pct": ""},
        ]
        import mature_analysis
        groups = mature_analysis.source_summary(rows)
        assert groups == [
            {"source": "trending", "n": 2, "breakout_rate": 50.0, "median_growth": 150.0, "insufficient": True}
        ]
