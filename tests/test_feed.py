"""测试 Atom feed 生成（issue #5）。"""

import xml.etree.ElementTree as ET

import pytest

import generate_site

ATOM = "{http://www.w3.org/2005/Atom}"


def _card(name, **overrides):
    card = {
        "name": name,
        "url": f"https://github.com/{name}",
        "owner": name.split("/")[0],
        "repo": name.split("/")[1],
        "stars": "500",
        "daily": "16.7",
        "score": "95",
        "language": "Python",
        "description": "A really cool open source project for developers",
        "source": "trending",
    }
    card.update(overrides)
    return card


@pytest.fixture
def reports():
    """两天的报告，最新在前（generate_site.main 的排序约定）。"""
    return [
        ("2026-08-20", [_card("user/awesome-project"), _card("dev/viral-tool", language="TypeScript")], [_card("old/steady")]),
        ("2026-08-19", [_card("user/awesome-project")], []),
    ]


class TestGenerateFeed:

    def test_feed_is_well_formed_atom(self, reports):
        root = ET.fromstring(generate_site.generate_feed(reports))
        assert root.tag == f"{ATOM}feed"
        # feed 自描述：id / updated / author 必须存在（RFC 4287 必填项）
        assert root.find(f"{ATOM}id").text == f"{generate_site.SITE_URL}/"
        assert root.find(f"{ATOM}updated").text == "2026-08-20T18:00:00Z"
        assert root.find(f"{ATOM}author/{ATOM}name").text
        assert root.find(f"{ATOM}title").text == generate_site.SITE_TITLE

    def test_entry_fields(self, reports):
        root = ET.fromstring(generate_site.generate_feed(reports))
        entry = root.find(f"{ATOM}entry")
        assert entry.find(f"{ATOM}title").text.startswith("user/awesome-project — ")
        assert entry.find(f"{ATOM}link").get("href") == "https://github.com/user/awesome-project"
        assert entry.find(f"{ATOM}updated").text == "2026-08-20T18:00:00Z"
        summary = entry.find(f"{ATOM}summary").text
        assert "Score: 95/100" in summary
        assert "Language: Python" in summary

    def test_entry_ids_stable_per_repo_and_date(self, reports):
        """同一 repo 不同天有不同 id；重跑同一天 id 不变（阅读器才不会重复显示）。"""
        xml1 = generate_site.generate_feed(reports)
        xml2 = generate_site.generate_feed(reports)
        assert xml1 == xml2
        ids = [e.find(f"{ATOM}id").text for e in ET.fromstring(xml1).findall(f"{ATOM}entry")]
        assert len(ids) == len(set(ids))
        assert "https://github.com/user/awesome-project#2026-08-20" in ids
        assert "https://github.com/user/awesome-project#2026-08-19" in ids

    def test_keeps_only_recent_days(self):
        many = [(f"2026-07-{d:02d}", [_card("user/awesome-project")], []) for d in range(31, 0, -1)]
        root = ET.fromstring(generate_site.generate_feed(many))
        entries = root.findall(f"{ATOM}entry")
        assert len(entries) == generate_site.FEED_DAYS

    def test_escapes_special_characters(self):
        reports = [("2026-08-20", [_card("user/xml-tool", description='CLI for <xml> & "quotes"')], [])]
        root = ET.fromstring(generate_site.generate_feed(reports))
        entry = root.find(f"{ATOM}entry")
        assert 'CLI for <xml> & "quotes"' in entry.find(f"{ATOM}title").text
