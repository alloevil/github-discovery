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
