"""测试 main.py 的编排与发信逻辑。"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock

import main


class TestSendEmailViaResend:
    """send_email_via_resend 的三态返回 (sent/skipped/failed)。"""

    def test_skipped_when_no_api_key(self):
        with patch.object(main, "RESEND_API_KEY", ""):
            assert main.send_email_via_resend(["a@b.com"], "s", "<p>x</p>") == "skipped"

    def test_skipped_when_no_recipients(self):
        with patch.object(main, "RESEND_API_KEY", "re_test"):
            assert main.send_email_via_resend([], "s", "<p>x</p>") == "skipped"

    def test_sent_when_resend_returns_id(self):
        with patch.object(main, "RESEND_API_KEY", "re_test"), \
             patch("main.subprocess.run") as mrun:
            mrun.return_value = MagicMock(returncode=0, stdout=json.dumps({"id": "abc123"}), stderr="")
            assert main.send_email_via_resend(["a@b.com"], "s", "<p>x</p>") == "sent"

    def test_failed_when_curl_nonzero(self):
        with patch.object(main, "RESEND_API_KEY", "re_test"), \
             patch("main.subprocess.run") as mrun:
            mrun.return_value = MagicMock(returncode=7, stdout="", stderr="connection refused")
            assert main.send_email_via_resend(["a@b.com"], "s", "<p>x</p>") == "failed"

    def test_failed_when_response_has_no_id(self):
        """curl 成功但 Resend 返回错误体(无 id)也应视为失败。"""
        with patch.object(main, "RESEND_API_KEY", "re_test"), \
             patch("main.subprocess.run") as mrun:
            mrun.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps({"statusCode": 401, "message": "invalid key"}),
                stderr="",
            )
            assert main.send_email_via_resend(["a@b.com"], "s", "<p>x</p>") == "failed"

    def test_failed_when_response_not_json(self):
        with patch.object(main, "RESEND_API_KEY", "re_test"), \
             patch("main.subprocess.run") as mrun:
            mrun.return_value = MagicMock(returncode=0, stdout="<html>502</html>", stderr="")
            assert main.send_email_via_resend(["a@b.com"], "s", "<p>x</p>") == "failed"


def _payload_of(call):
    """从 mock 的 curl argv 中取出 -d 后面的 JSON payload。"""
    argv = call.args[0]
    return json.loads(argv[argv.index("-d") + 1])


class TestPerRecipientIsolation:
    """#8:逐收件人单发,To 头只含一人,单个失败不阻断其他人。"""

    SUBSCRIBERS = ["a@b.com", "c@d.com", "e@f.com"]

    def test_one_api_call_per_subscriber_with_single_to(self):
        with patch.object(main, "RESEND_API_KEY", "re_test"), \
             patch("main.subprocess.run") as mrun:
            mrun.return_value = MagicMock(returncode=0, stdout=json.dumps({"id": "abc"}), stderr="")
            result = main.send_email_via_resend(self.SUBSCRIBERS, "s", "<p>x</p>")

        assert result == "sent"
        assert mrun.call_count == len(self.SUBSCRIBERS)
        payloads = [_payload_of(c) for c in mrun.call_args_list]
        # 每次调用 to 只含一个地址,且顺序覆盖全部订阅者
        assert [p["to"] for p in payloads] == [[s] for s in self.SUBSCRIBERS]

    def test_one_failure_does_not_block_other_recipients(self):
        """第二个收件人 curl 失败,其余两人仍然送达,整体结果为 sent。"""
        responses = [
            MagicMock(returncode=0, stdout=json.dumps({"id": "id1"}), stderr=""),
            MagicMock(returncode=7, stdout="", stderr="connection refused"),
            MagicMock(returncode=0, stdout=json.dumps({"id": "id3"}), stderr=""),
        ]
        with patch.object(main, "RESEND_API_KEY", "re_test"), \
             patch("main.subprocess.run", side_effect=responses) as mrun:
            result = main.send_email_via_resend(self.SUBSCRIBERS, "s", "<p>x</p>")

        assert result == "sent"
        assert mrun.call_count == 3  # 失败后没有提前退出

    def test_all_failures_return_failed(self):
        with patch.object(main, "RESEND_API_KEY", "re_test"), \
             patch("main.subprocess.run") as mrun:
            mrun.return_value = MagicMock(returncode=7, stdout="", stderr="boom")
            assert main.send_email_via_resend(self.SUBSCRIBERS, "s", "<p>x</p>") == "failed"
            assert mrun.call_count == 3


class TestSendDigestEmail:
    """send_digest_email 依赖订阅者列表。"""

    def test_skipped_when_no_subscribers(self):
        with patch("main.get_subscribers", return_value=[]):
            assert main.send_digest_email("2026-07-02", []) == "skipped"

    def test_passes_through_send_result(self):
        repo = {"full_name": "u/r", "url": "https://github.com/u/r",
                "stars": 100, "daily_stars": 10, "language": "Python",
                "description": "x", "source": "trending"}
        with patch("main.get_subscribers", return_value=["a@b.com"]), \
             patch("main.send_email_via_resend", return_value="sent") as msend:
            result = main.send_digest_email("2026-07-02", [(repo, {"total": 90})])
            assert result == "sent"
            assert msend.called

    def test_escapes_html_in_description(self):
        """描述含 HTML 特殊字符时应被转义,避免破坏邮件结构。"""
        repo = {"full_name": "u/r", "url": "https://github.com/u/r",
                "stars": 100, "daily_stars": 10, "language": "Python",
                "description": "<script>alert(1)</script>", "source": "hn"}
        captured = {}
        def fake_send(to, subject, html):
            captured["html"] = html
            return "sent"
        with patch("main.get_subscribers", return_value=["a@b.com"]), \
             patch("main.send_email_via_resend", side_effect=fake_send):
            main.send_digest_email("2026-07-02", [(repo, {"total": 90})])
        assert "<script>" not in captured["html"]
        assert "&lt;script&gt;" in captured["html"]


class TestGenerateMarkdown:
    """generate_markdown 的输出结构。"""

    def _repo(self, name="u/r", **kw):
        base = {"full_name": name, "url": f"https://github.com/{name}",
                "stars": 500, "age_days": 3, "daily_stars": 50.0,
                "description": "a tool", "language": "Go", "source": "trending"}
        base.update(kw)
        return base

    def test_includes_sections_and_source(self):
        new = [(self._repo("a/b"), {"total": 95, "acceleration": 40, "quality": 30, "antispam": 25})]
        md = main.generate_markdown(new, [])
        assert "First Timers" in md
        assert "[a/b]" in md
        assert "Source" in md
        assert "95/100" in md

    def test_repeat_section_only_when_present(self):
        new = [(self._repo("a/b"), {"total": 90, "acceleration": 30, "quality": 30, "antispam": 30})]
        md_no_repeat = main.generate_markdown(new, [])
        assert "Repeat Performers" not in md_no_repeat
        repeat = [(self._repo("c/d"), {"total": 80, "acceleration": 20, "quality": 30, "antispam": 30})]
        md_repeat = main.generate_markdown(new, repeat)
        assert "Repeat Performers" in md_repeat


class TestMainIdempotency:
    """main() 的同日幂等 guard。"""

    def test_skips_when_today_report_exists(self, tmp_path, capsys):
        today = main.datetime.now().strftime("%Y-%m-%d")
        report = tmp_path / f"discovery-{today}.md"
        report.write_text("# existing")
        # fetch_all 若被调用说明没跳过 —— 用它做哨兵
        with patch.object(main, "OUTPUT_DIR", str(tmp_path)), \
             patch("main.fetch_all") as mfetch:
            main.main()
            assert not mfetch.called
        out = capsys.readouterr().out
        assert "already exists" in out


class TestMainPipeline:
    """端到端流水线集成测试：mock 网络/邮件，验证 粗排→深查→落盘 全链路。"""

    def _mk_repo(self, name, stars, age, **kw):
        r = {
            "id": kw.pop("id", name.replace("/", "-")),
            "full_name": name,
            "url": f"https://github.com/{name}",
            "description": "A useful project with a reasonably long description",
            "language": "Python",
            "stars": stars,
            "forks": stars // 10,
            "fork": False,
            "license": "MIT",
            "age_days": age,
            "daily_stars": stars / age,
            "watchers": 10,
            "open_issues": 3,
            "source": kw.pop("source", "trending"),
            "sources": kw.pop("sources", None) or ["trending"],
        }
        r.update(kw)
        return r

    def test_full_pipeline_writes_reports_and_history(self, tmp_path, capsys):
        import dedup
        import snapshots as snap_mod

        out_dir = tmp_path / "output"
        data_dir = tmp_path / "data"
        repos = [
            self._mk_repo("hot/rocket", 900, 3),
            self._mk_repo("ok/steady", 300, 30, source="search", sources=["search"]),
            self._mk_repo("meh/slow", 50, 60, source="hn", sources=["hn"]),
        ]

        fake_quality = {
            "has_readme": True, "has_license": True, "has_ci": True,
            "recent_commits": 7, "open_issues": 3, "open_prs": 1,
            "quality_score": 15,
        }
        fake_auth = {"is_suspicious": False, "reason": "", "penalty": 0}

        with patch.object(main, "OUTPUT_DIR", str(out_dir)), \
             patch.object(main, "DATA_DIR", str(data_dir)), \
             patch.object(dedup, "HISTORY_FILE", tmp_path / "history.json"), \
             patch.object(snap_mod, "SNAPSHOT_FILE", data_dir / "star_snapshots.json"), \
             patch("main.fetch_all", return_value=repos), \
             patch("main.check_quality", return_value=fake_quality) as mq, \
             patch("main.check_star_authenticity", return_value=fake_auth), \
             patch("main.send_digest_email", return_value="sent"):
            main.main()

        today = main.datetime.now().strftime("%Y-%m-%d")

        # markdown + JSON 报告都已写出
        md = (out_dir / f"discovery-{today}.md").read_text()
        assert "hot/rocket" in md
        data = json.loads((data_dir / f"discovery-{today}.json").read_text())
        names = [e["full_name"] for e in data["new"]]
        assert set(names) == {"hot/rocket", "ok/steady", "meh/slow"}
        # 高增速仓库应排在低增速之前，且 JSON 按分数降序
        scores = [e["scores"]["total"] for e in data["new"]]
        assert scores == sorted(scores, reverse=True)
        assert names.index("hot/rocket") < names.index("meh/slow")

        # 深查按粗排顺序执行（第一个被深查的是分数最高的 hot/rocket）
        assert mq.call_args_list[0].args[0] == "hot/rocket"

        # 快照与推荐历史已落盘
        snap = json.loads((data_dir / "star_snapshots.json").read_text())
        assert snap["repos"]["hot/rocket"][-1][1] == 900
        hist = json.loads((tmp_path / "history.json").read_text())
        assert "hot/rocket" in hist["repos"]

    def test_repeat_classification_uses_history(self, tmp_path):
        """recommend_history 里已有的仓库应进 Repeat 区，而不是 First Timers。"""
        import dedup
        import snapshots as snap_mod
        from datetime import timedelta, timezone as tz

        out_dir = tmp_path / "output"
        data_dir = tmp_path / "data"
        history_file = tmp_path / "history.json"
        # 10 天前推荐过 → 已过 7 天去重窗口，但存在于历史 → repeat
        old_date = (main.datetime.now(tz.utc) - timedelta(days=10)).isoformat()
        history_file.write_text(json.dumps({
            "repos": {"seen/before": {"count": 1, "scores": [90], "last_recommended": old_date}},
            "updated_at": old_date,
        }))

        repos = [
            self._mk_repo("brand/new", 500, 5),
            self._mk_repo("seen/before", 800, 20),
        ]
        fake_quality = {"has_readme": True, "has_license": True, "has_ci": False,
                        "recent_commits": 5, "open_issues": 1, "open_prs": 0, "quality_score": 10}
        fake_auth = {"is_suspicious": False, "reason": "", "penalty": 0}

        with patch.object(main, "OUTPUT_DIR", str(out_dir)), \
             patch.object(main, "DATA_DIR", str(data_dir)), \
             patch.object(dedup, "HISTORY_FILE", history_file), \
             patch.object(snap_mod, "SNAPSHOT_FILE", data_dir / "star_snapshots.json"), \
             patch("main.fetch_all", return_value=repos), \
             patch("main.check_quality", return_value=fake_quality), \
             patch("main.check_star_authenticity", return_value=fake_auth), \
             patch("main.send_digest_email", return_value="sent"):
            main.main()

        today = main.datetime.now().strftime("%Y-%m-%d")
        data = json.loads((data_dir / f"discovery-{today}.json").read_text())
        assert [e["full_name"] for e in data["new"]] == ["brand/new"]
        assert [e["full_name"] for e in data["repeat"]] == ["seen/before"]


class TestDigestReasonLine:
    """#9:每张邮件卡片带「为什么推荐」理由行,裸分不再按分数高亮。"""

    def _send(self, repo, scores):
        captured = {}
        def fake_send(to, subject, html):
            captured["html"] = html
            return "sent"
        with patch("main.get_subscribers", return_value=["a@b.com"]), \
             patch("main.send_email_via_resend", side_effect=fake_send):
            main.send_digest_email("2026-08-21", [(repo, scores)])
        return captured["html"]

    def test_reason_line_in_email(self):
        repo = {"full_name": "u/r", "url": "https://github.com/u/r",
                "stars": 5000, "age_days": 5, "daily_stars": 1000.0,
                "real_daily_stars": 852.0, "language": "Python",
                "description": "x", "sources": ["trending", "hn"], "source": "trending"}
        html = self._send(repo, {"total": 100})
        assert "+852/day" in html
        assert "Trending+HN" in html

    def test_head_entries_distinguishable(self):
        """两个 100 分条目的渲染行必须不同(理由行提供区分度)。"""
        mk = lambda name, rd, srcs: {
            "full_name": name, "url": f"https://github.com/{name}",
            "stars": 1000, "age_days": 10, "daily_stars": 100.0,
            "real_daily_stars": rd, "language": "Go",
            "description": "same desc", "sources": srcs, "source": srcs[0]}
        captured = {}
        def fake_send(to, subject, html):
            captured["html"] = html
            return "sent"
        with patch("main.get_subscribers", return_value=["a@b.com"]), \
             patch("main.send_email_via_resend", side_effect=fake_send):
            main.send_digest_email("2026-08-21", [
                (mk("a/b", 500.0, ["trending"]), {"total": 100}),
                (mk("c/d", 120.0, ["hn", "rising"]), {"total": 100}),
            ])
        html = captured["html"]
        assert "+500/day" in html and "+120/day" in html
        assert "HN+Rising" in html
