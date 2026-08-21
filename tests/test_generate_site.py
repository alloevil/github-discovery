"""测试静态站 HTML 生成的转义（存储型 XSS 防护）。

仓库描述 / owner / repo 名都是攻击者可控字段（让自己的仓库被推荐即可注入），
repo_card 必须转义后再拼进 index.html。
"""

import generate_site


def _card(**overrides):
    card = {
        "name": "user/repo",
        "url": "https://github.com/user/repo",
        "owner": "user",
        "repo": "repo",
        "stars": "500",
        "daily": "16.7",
        "score": "95",
        "language": "Python",
        "description": "A normal description",
        "source": "trending",
    }
    card.update(overrides)
    return card


class TestRepoCardEscaping:

    def test_script_in_description_is_escaped(self):
        html_out = generate_site.repo_card(
            _card(description='<script>alert(1)</script>'))
        assert "<script>" not in html_out
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html_out

    def test_img_onerror_in_description_is_escaped(self):
        html_out = generate_site.repo_card(
            _card(description='<img src=x onerror=alert(document.domain)>'))
        assert "<img src=x" not in html_out
        assert "&lt;img" in html_out

    def test_owner_and_repo_name_are_escaped(self):
        html_out = generate_site.repo_card(
            _card(owner='<b>evil</b>', repo='"><script>x()</script>'))
        assert "<b>evil</b>" not in html_out
        assert "<script>x()</script>" not in html_out

    def test_normal_card_still_renders_fields(self):
        html_out = generate_site.repo_card(_card())
        assert "user /" in html_out
        assert "A normal description" in html_out
        assert 'href="https://github.com/user/repo"' in html_out


class TestRepoCardReason:
    """#9:站点卡片渲染理由行,且裸分不再分级高亮。"""

    def test_reason_line_rendered_and_escaped(self):
        html_out = generate_site.repo_card(
            _card(reason='+852/day · Trending+HN · <b>3x</b>'))
        assert 'class="repo-reason"' in html_out
        assert '+852/day · Trending+HN' in html_out
        assert '<b>3x</b>' not in html_out  # 理由行同样必须转义

    def test_fallback_reason_for_legacy_markdown_reports(self):
        """旧 markdown 报告没有 reason 字段 → 退化为 日增+来源。"""
        html_out = generate_site.repo_card(_card())
        assert 'class="repo-reason"' in html_out
        assert '+16.7/day' in html_out
        assert 'Trending' in html_out

    def test_score_tag_is_neutral(self):
        html_out = generate_site.repo_card(_card(score='100'))
        assert 'score-tag high' not in html_out
        assert 'Score 100' in html_out

    def test_json_entry_carries_reason(self):
        entry = {"full_name": "u/r", "url": "https://github.com/u/r",
                 "stars": 5000, "age_days": 5, "real_daily_stars": 852.0,
                 "sources": ["trending", "hn"], "language": "Python",
                 "description": "x", "scores": {"total": 100}}
        card = generate_site._json_entry_to_card(entry)
        assert card["reason"].startswith("+852/day")
        assert "Trending+HN" in card["reason"]
