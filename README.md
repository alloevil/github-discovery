# 🔥 GitHub Discovery

[![GitHub Actions](https://github.com/alloevil/github-discovery/actions/workflows/daily.yml/badge.svg)](https://github.com/alloevil/github-discovery/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Stars](https://img.shields.io/github/stars/alloevil/github-discovery?style=social)](https://github.com/alloevil/github-discovery/stargazers)

> **发现正在爆发的 GitHub 仓库，在它们变成热门之前。**

GitHub Discovery 是一个自动化工具，每天从多个数据源收集 GitHub 仓库信号，通过智能评分系统筛选出最有潜力的项目，并通过邮件和网页推送给你。

---

## ✨ 核心特性

### 📡 5 大数据源
| 数据源 | 信号类型 | 说明 |
|--------|----------|------|
| [GitHub Trending](https://github.com/trending) | 热度 | 每日热门仓库榜单 |
| GitHub Search | 新高星 | 最近 7 天快速获得 Star 的新仓库 |
| [Hacker News](https://news.ycombinator.com/) | 社区推荐 | Show HN 中的 GitHub 项目 |
| [Reddit](https://reddit.com/r/programming) | 讨论热度 | /r/programming 热帖中的 GitHub 链接 |
| Rising Detection | 早期信号 | Fork/Watch 增速异常检测 |

### 📊 智能评分系统（满分 100）

| 维度 | 分值 | 说明 |
|------|------|------|
| **加速度** | 40 | Star 增速、加速趋势 |
| **质量** | 30 | 年龄、语言、许可证、内容完整性 |
| **反垃圾** | 30 | Fork 比率、描述质量 |
| **代码质量** | +20 | README、CI 配置、commit 频率 |
| **Star 可疑** | -15 | 1天内1000+ Star、无描述暴涨 |
| **用户反馈** | ±10 | 👍👎 投票融入评分 |
| **批量刷量** | -20 | 同一 owner 多仓库同时暴涨 |

### 🛡️ 反垃圾机制
- **Star 刷量检测**：1天内1000+ Star 且年龄<1天 → 标记可疑
- **批量刷量检测**：同一 owner 下多个仓库同时暴涨 → 标记可疑
- **内容质量检测**：无描述、无 README 的高 Star 仓库 → 扣分
- **跨天去重**：7 天窗口，不重复推荐同一仓库

### 👍👎 用户反馈系统
- 每条推荐可投票（👍/👎）
- 反馈数据融入评分算法
- 支持 localStorage 本地存储

### 📬 邮件订阅
- 每日推送精选仓库到邮箱
- 支持 Apple Mail / iOS 暗模式
- 使用 Resend API 发送

### 🎨 GitHub Pages
- 赛博朋克风格在线展示
- 按日期/语言筛选
- 实时评分显示

---

## 🚀 快速开始

### 1. Fork 本仓库

点击右上角的 **Fork** 按钮，将仓库复制到你的账号下。

### 2. 配置 Secrets

进入仓库的 **Settings → Secrets and variables → Actions**，添加以下 Secrets：

| Secret | 必需 | 说明 |
|--------|------|------|
| `RESEND_API_KEY` | ✅ | [Resend](https://resend.com/) API Key，用于发送邮件 |
| `GITHUB_TOKEN` | ❌ | GitHub Personal Access Token，用于 API 调用（可选，默认使用 GITHUB_TOKEN） |

### 3. 启用 GitHub Actions

进入 **Actions** 页面，点击 **I understand my workflows, go ahead and enable them**。

### 4. 手动触发测试

进入 **Actions → Daily Paper Discovery → Run workflow**，手动运行一次测试。

### 5. 查看结果

- **GitHub Pages**：访问 `https://<你的用户名>.github.io/github-discovery/`
- **邮件**：订阅者会收到每日推送

---

## 📁 项目结构

```
github-discovery/
├── scripts/
│   ├── sources.py           # 5 个数据源采集器
│   ├── scorer.py            # 评分算法
│   ├── quality.py           # 代码质量检测
│   ├── dedup.py             # 跨天去重（7天窗口）
│   ├── feedback.py          # 用户反馈系统
│   ├── fraud_detection.py   # 批量刷量检测
│   ├── verify_scoring.py    # 评分回测验证
│   ├── main.py              # 入口脚本
│   └── config.py            # 配置文件
├── tests/
│   ├── test_sources.py      # 数据源测试
│   ├── test_scorer.py       # 评分算法测试
│   ├── test_dedup.py        # 去重逻辑测试
│   ├── test_feedback.py     # 反馈系统测试
│   ├── test_quality.py      # 质量检测测试
│   └── test_fraud_detection.py  # 刷量检测测试
├── data/
│   ├── feedback.json        # 用户投票数据
│   └── recommend_history.json  # 推荐历史（去重用）
├── docs/
│   └── index.html           # GitHub Pages
├── .github/
│   └── workflows/
│       └── daily.yml        # 每日自动运行
├── subscribers.txt          # 邮件订阅者列表
├── config.yaml              # 运行时配置
└── README.md                # 本文件
```

---

## 🔧 开发指南

### 本地运行

```bash
# 克隆仓库
git clone https://github.com/alloevil/github-discovery.git
cd github-discovery

# 安装依赖（仅需标准库，无需额外安装）
python scripts/main.py
```

### 运行测试

```bash
# 安装 pytest
pip install pytest

# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试
python -m pytest tests/test_scorer.py -v

# 查看测试覆盖率
python -m pytest tests/ --cov=scripts --cov-report=html
```

### 添加新数据源

1. 在 `scripts/sources.py` 中添加新的 `fetch_xxx()` 函数
2. 在 `fetch_all()` 中调用新函数
3. 在 `tests/test_sources.py` 中添加测试
4. 提交 PR

### 评分算法调整

评分逻辑在 `scripts/scorer.py` 中，权重可通过 `config.py` 调整：

```python
# config.py
SCORING_WEIGHTS = {
    "acceleration": 40,  # 加速度权重
    "quality": 30,       # 质量权重
    "antispam": 30,      # 反垃圾权重
}
```

---

## 📊 评分验证

运行评分回测，验证高分项目是否真的火了：

```bash
python scripts/verify_scoring.py --days 30
```

输出示例：
```
=== 评分验证报告 ===
回测时间范围: 最近 30 天
总推荐项目数: 150

评分区间    | 项目数 | 平均增长 | 准确率
------------|--------|----------|--------
90-100      | 45     | +320%    | 89%
80-89       | 38     | +180%    | 76%
70-79       | 32     | +95%     | 62%
60-69       | 20     | +45%     | 45%
<60         | 15     | +12%     | 20%

结论: 评分体系有效，高分项目确实更有可能爆发
```

---

## 🤝 Contributing

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m 'feat: add your feature'`
4. 推送分支：`git push origin feature/your-feature`
5. 提交 Pull Request

### 贡献方向

- 📡 添加新的数据源
- 🎯 优化评分算法
- 🐛 修复 bug
- 📖 完善文档
- ✅ 添加测试

---

## 📄 License

本项目采用 [MIT License](LICENSE) 开源。

---

## 🙏 致谢

- [GitHub API](https://docs.github.com/en/rest) - 数据来源
- [Hacker News API](https://github.com/HackerNews/API) - 数据来源
- [Reddit API](https://www.reddit.com/dev/api/) - 数据来源
- [Resend](https://resend.com/) - 邮件发送服务

---

## 📞 联系方式

- Issues: [GitHub Issues](https://github.com/alloevil/github-discovery/issues)
- Discussions: [GitHub Discussions](https://github.com/alloevil/github-discovery/discussions)

---

**⭐ 如果觉得有用，请给个 Star 支持一下！**
