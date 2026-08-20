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
