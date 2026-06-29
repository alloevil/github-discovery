"""公共 fixtures，为所有测试模块提供统一的测试数据和工具。"""

import json
import os
import sys
import tempfile
import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

# 确保 scripts/ 目录在 import 路径中
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


# ── 临时数据目录 ──────────────────────────────────────────────────────

@pytest.fixture
def tmp_data_dir(tmp_path):
    """提供临时数据目录，避免污染真实数据文件。"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


# ── 标准仓库数据 ──────────────────────────────────────────────────────

@pytest.fixture
def sample_repo():
    """一个标准的、健康的仓库数据。"""
    return {
        "id": "123456",
        "full_name": "user/awesome-project",
        "url": "https://github.com/user/awesome-project",
        "description": "A really cool open source project for developers",
        "language": "Python",
        "stars": 500,
        "forks": 50,
        "fork": False,
        "license": "MIT",
        "has_readme": True,
        "created_at": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
        "age_days": 30,
        "daily_stars": 16.7,
        "watchers": 80,
        "source": "trending",
    }


@pytest.fixture
def viral_repo():
    """一个病毒式传播的新仓库。"""
    return {
        "id": "789012",
        "full_name": "dev/viral-tool",
        "url": "https://github.com/dev/viral-tool",
        "description": "Revolutionary AI tool that changes everything about how we code and build software",
        "language": "TypeScript",
        "stars": 3000,
        "forks": 200,
        "fork": False,
        "license": "Apache-2.0",
        "has_readme": True,
        "created_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
        "age_days": 2,
        "daily_stars": 1500.0,
        "watchers": 500,
        "source": "search",
    }


@pytest.fixture
def spam_repo():
    """一个疑似刷量的垃圾仓库。"""
    return {
        "id": "999999",
        "full_name": "xjkq83ab/spam-project",
        "url": "https://github.com/xjkq83ab/spam-project",
        "description": "Best revolutionary game-changing ultimate AI-powered tool guaranteed to 10x your productivity",
        "language": "",
        "stars": 6000,
        "forks": 5,
        "fork": False,
        "license": "",
        "has_readme": False,
        "created_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        "age_days": 1,
        "daily_stars": 6000.0,
        "watchers": 10,
        "source": "search",
    }


@pytest.fixture
def empty_repo():
    """一个几乎没有信息的最小仓库。"""
    return {
        "id": "000001",
        "full_name": "newbie/empty",
        "url": "https://github.com/newbie/empty",
        "description": "",
        "language": "",
        "stars": 0,
        "forks": 0,
        "fork": True,
        "license": "",
        "has_readme": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "age_days": 1,
        "daily_stars": 0.0,
        "watchers": 0,
        "source": "search",
    }


# ── GitHub API 模拟响应 ────────────────────────────────────────────────

@pytest.fixture
def gh_api_repo_response():
    """模拟 GitHub /repos/{owner}/{repo} API 返回的标准数据。"""
    return {
        "id": 123456,
        "full_name": "user/awesome-project",
        "html_url": "https://github.com/user/awesome-project",
        "description": "A really cool open source project",
        "language": "Python",
        "stargazers_count": 500,
        "forks_count": 50,
        "fork": False,
        "license": {"spdx_id": "MIT"},
        "subscribers_count": 80,
        "open_issues_count": 10,
        "created_at": (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


@pytest.fixture
def gh_search_response(gh_api_repo_response):
    """模拟 GitHub Search API 返回。"""
    return {
        "total_count": 1,
        "items": [gh_api_repo_response],
    }


@pytest.fixture
def hn_story_response():
    """模拟 Hacker News 单条 story 返回。"""
    return {
        "id": 40001,
        "type": "story",
        "title": "Show HN: My cool GitHub tool",
        "url": "https://github.com/user/awesome-project",
        "score": 150,
        "time": int(datetime.now(timezone.utc).timestamp()),
    }


# ── Mock 工具函数 ──────────────────────────────────────────────────────

@pytest.fixture
def mock_fetch_url():
    """Mock sources._fetch_url 以避免真实网络请求。"""
    with patch("sources._fetch_url") as mock:
        yield mock


@pytest.fixture
def mock_gh_api():
    """Mock sources._gh_api 以避免真实 GitHub API 请求。"""
    with patch("sources._gh_api") as mock:
        yield mock


@pytest.fixture
def mock_time_sleep():
    """Mock time.sleep 以加速测试执行。"""
    with patch("time.sleep"):
        yield
