"""测试各数据源的解析逻辑（mock 网络请求）。"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, call

import sources


class TestNormalizeRepo:
    """测试 _normalize_repo 对 GitHub API 原始数据的标准化处理。"""

    def test_normalizes_basic_fields(self, gh_api_repo_response):
        """应正确提取所有基础字段。"""
        result = sources._normalize_repo(gh_api_repo_response)

        assert result["id"] == "123456"
        assert result["full_name"] == "user/awesome-project"
        assert result["url"] == "https://github.com/user/awesome-project"
        assert result["stars"] == 500
        assert result["forks"] == 50
        assert result["language"] == "Python"
        assert result["license"] == "MIT"
        assert result["fork"] is False

    def test_calculates_age_days(self, gh_api_repo_response):
        """应正确计算仓库年龄（天数）。"""
        result = sources._normalize_repo(gh_api_repo_response)

        assert result["age_days"] >= 29  # 30 天前创建，允许 1 天误差
        assert result["age_days"] <= 31

    def test_calculates_daily_stars(self, gh_api_repo_response):
        """应正确计算每日 star 增速。"""
        result = sources._normalize_repo(gh_api_repo_response)

        expected = 500 / result["age_days"]
        assert abs(result["daily_stars"] - expected) < 0.1

    def test_handles_missing_license(self):
        """无 license 时应返回空字符串。"""
        data = {
            "id": 1, "full_name": "a/b", "html_url": "https://github.com/a/b",
            "description": "", "language": "Go", "stargazers_count": 10,
            "forks_count": 1, "fork": False, "license": None,
            "subscribers_count": 2, "created_at": "2026-06-20T00:00:00Z",
        }
        result = sources._normalize_repo(data)
        assert result["license"] == ""

    def test_handles_empty_description(self):
        """无描述时应返回空字符串，不报错。"""
        data = {
            "id": 2, "full_name": "a/b", "html_url": "https://github.com/a/b",
            "description": None, "language": "Rust", "stargazers_count": 0,
            "forks_count": 0, "fork": False, "license": None,
            "subscribers_count": 0, "created_at": "2026-06-24T00:00:00Z",
        }
        result = sources._normalize_repo(data)
        assert result["description"] == ""

    def test_handles_zero_age_days(self):
        """刚创建（age_days=0）的仓库不应除零报错。"""
        data = {
            "id": 3, "full_name": "a/b", "html_url": "https://github.com/a/b",
            "description": "", "language": "", "stargazers_count": 100,
            "forks_count": 0, "fork": False, "license": None,
            "subscribers_count": 5,
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        result = sources._normalize_repo(data)
        assert result["age_days"] >= 1  # 最小为 1
        assert result["daily_stars"] >= 0


class TestFetchTrending:
    """测试 GitHub Trending 页面抓取和解析。"""

    @patch("sources._parse_repo")
    @patch("sources._fetch_url")
    @patch("time.sleep")
    def test_parses_repo_paths_from_html(self, mock_sleep, mock_fetch, mock_parse):
        """应从 HTML 中正确提取仓库路径。"""
        mock_fetch.return_value = '''
            <h2><a href="/user/repo1">repo1</a></h2>
            <h2><a href="/org/repo2">repo2</a></h2>
        '''
        mock_parse.side_effect = lambda name: {"full_name": name, "id": name}

        results = sources.fetch_trending()

        assert len(results) == 2
        assert results[0]["full_name"] == "user/repo1"
        assert results[1]["full_name"] == "org/repo2"

    @patch("sources._parse_repo")
    @patch("sources._fetch_url")
    @patch("time.sleep")
    def test_skips_invalid_paths(self, mock_sleep, mock_fetch, mock_parse):
        """应跳过不含斜杠的无效路径。"""
        mock_fetch.return_value = '<h2><a href="/invalid-path">x</a></h2>'
        mock_parse.return_value = {"full_name": "a/b", "id": "1"}

        results = sources.fetch_trending()
        # "/invalid-path" 不含 "/" 分隔的 owner/repo 格式，应被跳过
        assert mock_parse.call_count == 0

    @patch("sources._fetch_url")
    @patch("time.sleep")
    def test_returns_empty_on_fetch_failure(self, mock_sleep, mock_fetch):
        """抓取失败时应返回空列表而不报错。"""
        mock_fetch.side_effect = Exception("network error")

        results = sources.fetch_trending()
        assert results == []

    @patch("sources._parse_repo")
    @patch("sources._fetch_url")
    @patch("time.sleep")
    def test_limits_to_25_repos(self, mock_sleep, mock_fetch, mock_parse):
        """最多处理 25 个仓库。"""
        paths = " ".join(f'<h2><a href="/u/r{i}">r{i}</a></h2>' for i in range(30))
        mock_fetch.return_value = paths
        mock_parse.side_effect = lambda name: {"full_name": name, "id": name}

        results = sources.fetch_trending()
        assert len(results) <= 25


class TestFetchSearch:
    """测试 GitHub Search API 数据源。"""

    @patch("sources._gh_api")
    @patch("time.sleep")
    def test_deduplicates_by_full_name(self, mock_sleep, mock_api, gh_api_repo_response):
        """同一仓库出现在多个查询结果中时应去重。"""
        mock_api.return_value = {"items": [gh_api_repo_response]}

        results = sources.fetch_search()

        # 4 个查询但同一仓库，最终只应有 1 个
        full_names = [r["full_name"] for r in results]
        assert len(full_names) == len(set(full_names))

    @patch("sources._gh_api")
    @patch("time.sleep")
    def test_handles_empty_search_results(self, mock_sleep, mock_api):
        """搜索无结果时应返回空列表。"""
        mock_api.return_value = {"items": []}

        results = sources.fetch_search()
        assert results == []

    @patch("sources._gh_api")
    @patch("time.sleep")
    def test_handles_api_error(self, mock_sleep, mock_api):
        """API 返回 None 时应跳过而不报错。"""
        mock_api.return_value = None

        results = sources.fetch_search()
        assert results == []


class TestFetchHN:
    """测试 Hacker News Show HN 数据源。"""

    @patch("sources._parse_repo")
    @patch("sources._fetch_url")
    @patch("time.sleep")
    def test_extracts_github_url_from_story(self, mock_sleep, mock_fetch, mock_parse):
        """应从 story URL 中提取 GitHub 仓库链接。"""
        mock_parse.return_value = {"full_name": "user/repo", "id": "1"}

        # 第一次调用获取 story ID 列表，后续调用获取各 story 详情
        story = json.dumps({"id": 1, "type": "story", "title": "Show HN: My project",
                            "url": "https://github.com/user/repo", "score": 100})
        mock_fetch.side_effect = [
            json.dumps([1]),  # story IDs
            story,  # story detail
        ]

        results = sources.fetch_hn()

        assert len(results) == 1
        assert results[0]["hn_title"] == "Show HN: My project"
        assert results[0]["hn_score"] == 100

    @patch("sources._fetch_url")
    @patch("time.sleep")
    def test_extracts_github_url_from_title(self, mock_sleep, mock_fetch):
        """当 story URL 不是 GitHub 链接时，应从标题中提取。"""
        story = json.dumps({"id": 2, "type": "story",
                            "title": "My tool github.com/user/repo is great",
                            "url": "https://example.com/article", "score": 50})
        mock_fetch.side_effect = [json.dumps([2]), story]

        with patch("sources._parse_repo", return_value={"full_name": "user/repo", "id": "1"}):
            results = sources.fetch_hn()
            assert len(results) == 1

    @patch("sources._fetch_url")
    @patch("time.sleep")
    def test_skips_non_story_items(self, mock_sleep, mock_fetch):
        """应跳过非 story 类型的 item。"""
        comment = json.dumps({"id": 3, "type": "comment", "text": "nice"})
        mock_fetch.side_effect = [json.dumps([3]), comment]

        results = sources.fetch_hn()
        assert results == []

    @patch("sources._fetch_url")
    @patch("time.sleep")
    def test_returns_empty_on_fetch_failure(self, mock_sleep, mock_fetch):
        """HN API 不可达时应返回空列表。"""
        mock_fetch.side_effect = Exception("timeout")

        results = sources.fetch_hn()
        assert results == []


class TestFetchReddit:
    """测试 Reddit 数据源。"""

    @patch("sources._parse_repo")
    @patch("sources.urllib.request.urlopen")
    @patch("time.sleep")
    def test_extracts_github_links(self, mock_sleep, mock_urlopen, mock_parse, reddit_response):
        """应从 Reddit 帖子中提取 GitHub 链接。"""
        mock_parse.return_value = {"full_name": "user/awesome-project", "id": "1"}

        resp = MagicMock()
        resp.read.return_value = json.dumps(reddit_response).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = resp

        results = sources.fetch_reddit()

        assert len(results) == 1
        assert results[0]["reddit_title"] == "Check out this new Python framework"
        assert results[0]["reddit_score"] == 350

    @patch("sources.urllib.request.urlopen")
    @patch("time.sleep")
    def test_skips_non_github_posts(self, mock_sleep, mock_urlopen, reddit_response):
        """应跳过不包含 GitHub 链接的帖子。"""
        # reddit_response 中第二个帖子不是 GitHub 链接
        resp = MagicMock()
        resp.read.return_value = json.dumps(reddit_response).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = resp

        with patch("sources._parse_repo", return_value={"full_name": "user/awesome-project", "id": "1"}):
            results = sources.fetch_reddit()
            # 只有第一个帖子匹配
            assert len(results) == 1


class TestFetchRising:
    """测试 Rising 仓库检测源。"""

    @patch("sources._gh_api")
    @patch("time.sleep")
    def test_filters_by_fork_ratio(self, mock_sleep, mock_api):
        """应只保留 fork_ratio > 0.3 或 watch_ratio > 0.1 的仓库。"""
        # 高 fork ratio 的仓库
        high_fork = {
            "id": 10, "full_name": "a/b", "html_url": "https://github.com/a/b",
            "description": "test", "language": "Go", "stargazers_count": 100,
            "forks_count": 50, "fork": False, "license": None,
            "subscribers_count": 5,
            "created_at": (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        # 低比率的仓库（应被过滤）
        low_ratio = {
            "id": 11, "full_name": "c/d", "html_url": "https://github.com/c/d",
            "description": "test", "language": "JS", "stargazers_count": 1000,
            "forks_count": 1, "fork": False, "license": None,
            "subscribers_count": 1,
            "created_at": (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        mock_api.return_value = {"items": [high_fork, low_ratio]}

        results = sources.fetch_rising()

        full_names = [r["full_name"] for r in results]
        assert "a/b" in full_names
        assert "c/d" not in full_names


class TestFetchAll:
    """测试 fetch_all 聚合逻辑。"""

    @patch("sources.fetch_rising", return_value=[])
    @patch("sources.fetch_reddit", return_value=[])
    @patch("sources.fetch_ai_trending", return_value=[])
    @patch("sources.fetch_rising", return_value=[])
    @patch("sources.fetch_reddit", return_value=[])
    @patch("sources.fetch_hn", return_value=[])
    @patch("sources.fetch_search", return_value=[])
    @patch("sources.fetch_trending", return_value=[])
    def test_deduplicates_by_full_name(self, *mocks):
        """各源返回同名仓库时应去重，保留第一个。"""
        repo = {"full_name": "user/repo", "id": "1"}
        sources.fetch_trending.return_value = [dict(repo)]
        sources.fetch_search.return_value = [dict(repo)]
        sources.fetch_hn.return_value = [dict(repo)]

        results = sources.fetch_all()

        assert len(results) == 1
        # 应保留 trending 的 source 标签
        assert results[0]["source"] == "trending"

    @patch("sources.fetch_ai_trending", return_value=[])
    @patch("sources.fetch_rising", return_value=[])
    @patch("sources.fetch_reddit", return_value=[])
    @patch("sources.fetch_hn", return_value=[])
    @patch("sources.fetch_search", return_value=[])
    @patch("sources.fetch_trending", return_value=[])
    def test_assigns_source_tags(self, *mocks):
        """每个仓库应被标记正确的 source。"""
        sources.fetch_trending.return_value = [{"full_name": "a/b", "id": "1"}]
        sources.fetch_search.return_value = [{"full_name": "c/d", "id": "2"}]
        sources.fetch_hn.return_value = [{"full_name": "e/f", "id": "3"}]
        sources.fetch_reddit.return_value = [{"full_name": "g/h", "id": "4"}]
        sources.fetch_rising.return_value = [{"full_name": "i/j", "id": "5"}]

        results = sources.fetch_all()
        sources_map = {r["full_name"]: r["source"] for r in results}

        assert sources_map["a/b"] == "trending"
        assert sources_map["c/d"] == "search"
        assert sources_map["e/f"] == "hn"
        assert sources_map["g/h"] == "reddit"
        assert sources_map["i/j"] == "rising"
