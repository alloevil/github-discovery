"""picks：推荐期的选择、永久去重、核实与增长字段。"""

import json
from datetime import date

import pytest

import picks


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(picks, "DATA_DIR", tmp_path)
    monkeypatch.setattr(picks, "PICKS_HISTORY_FILE", tmp_path / "picks_history.json")


def R(name, desc="", topics=None, **kw):
    return {"full_name": name, "url": f"https://github.com/{name}", "description": desc,
            "topics": topics or [], **kw}


def api_ok(path):
    name = path.split("/repos/", 1)[1]
    return {"full_name": name, "html_url": f"https://github.com/{name}", "description": "d",
            "stargazers_count": 100, "forks_count": 5, "topics": []}


def test_picks_day_every_three_days():
    assert picks.is_picks_day(date(2026, 10, 16))
    assert not picks.is_picks_day(date(2026, 10, 17))
    assert not picks.is_picks_day(date(2026, 10, 18))
    assert picks.is_picks_day(date(2026, 10, 19))


def test_topic_tagging():
    assert picks.topic_of(R("a/b", "An RTL to GDS flow")) == "semi"
    assert picks.topic_of(R("a/b", "LLM agent framework")) == "ai"
    assert picks.topic_of(R("a/b", "a retro game port")) is None
    # 子串不算：'paint' 里有 'ai'，'credit' 里没有 'eda' 边界
    assert picks.topic_of(R("a/b", "paint program for credit cards")) is None


def test_never_repeats_even_after_months():
    picks.record_picks([R("old/one")], "2026-01-01", source="chat")
    scored = [(R("old/one", "llm"), {"total": 99}), (R("new/two", "llm"), {"total": 50})]
    names = [r["full_name"] for r, _ in picks.select_candidates(scored)]
    assert names == ["new/two"]
    assert picks.was_ever_picked("OLD/ONE")


def test_semi_quota_comes_first_and_suspicious_dropped():
    scored = [(R(f"ai/{i}", "llm agent"), {"total": 100 - i}) for i in range(12)]
    scored += [(R("chip/a", "verilog linter"), {"total": 10}), (R("chip/b", "fpga toolkit"), {"total": 9}),
               (R("bad/x", "llm", star_suspicious=True), {"total": 100})]
    ordered = picks.select_candidates(scored)
    chosen = picks.verify_picks(ordered, api_ok)
    names = [r["full_name"] for r, _ in chosen]
    assert len(names) == picks.PICKS_MAX
    assert {"chip/a", "chip/b"} <= set(names)
    assert "bad/x" not in names


def test_verify_drops_missing_and_archived():
    def api(path):
        if path.endswith("gone/x"):
            return None
        if path.endswith("arch/x"):
            return {**api_ok(path), "archived": True}
        return api_ok(path)
    ordered = [(R("gone/x", topic="ai"), {}), (R("arch/x", topic="ai"), {}), (R("ok/x", topic="ai"), {})]
    assert [r["full_name"] for r, _ in picks.verify_picks(ordered, api)] == ["ok/x"]


def test_growth_measured_or_null():
    snaps = {"repos": {"a/b": [["2026-10-08", 100], ["2026-10-15", 180]]}}
    g = picks.measured_growth("a/b", 200, snaps, "2026-10-16")
    assert g == {"since": "2026-10-08", "window_days": 8, "stars_gained": 100, "source": "star_snapshots"}
    assert picks.measured_growth("c/d", 50, snaps, "2026-10-16") is None


def test_write_picks_shape(tmp_path):
    chosen = [(R("a/b", "llm", topic="ai", stars=10), {"total": 90})]
    path = picks.write_picks("2026-10-19", chosen, {"repos": {}})
    doc = json.loads(open(path).read())
    assert doc["count"] == 1 and doc["picks"][0]["growth"] is None
    assert doc["picks"][0]["url"] == "https://github.com/a/b"
    assert doc["semi_min_met"] is False


def test_committed_history_seeds_chat_picks():
    import pathlib
    real = json.loads((pathlib.Path(__file__).parent.parent / "data" / "picks_history.json").read_text())
    chat = [k for k, v in real["repos"].items() if v.get("source") == "chat"]
    assert len(chat) >= 10
