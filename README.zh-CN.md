# GitHub Discovery

**GitHub Discovery** 是一个每天运行的 GitHub 仓库发现流水线，在项目还处于加速上升期时就把它挖出来，服务于想要早期信号、而不是昨天热度的开发者。

<p align="center">
  <img src="./assets/hero.svg" width="100%" alt="GitHub Discovery — spot trending repos before they go mainstream. 6 data sources, smart scoring, anti-spam, daily email digest.">
</p>

<p align="center">
  <img src="https://img.shields.io/github/actions/workflow/status/alloevil/github-discovery/daily.yml?branch=main&label=CI&logo=github&logoColor=white&color=00ccff" alt="CI" />
  <img src="https://img.shields.io/badge/license-MIT-00ccff?style=flat" alt="License" />
  <img src="https://img.shields.io/github/stars/alloevil/github-discovery?style=flat&logo=github&color=00ccff" alt="Stars" />
  <a href="https://alloevil.github.io/github-discovery/"><img src="https://img.shields.io/badge/website-live-00ccff?style=flat" alt="Website" /></a>
</p>

<p align="center">
  <a href="https://alloevil.github.io/github-discovery/">网站</a> · 
  <a href="#快速开始">快速开始</a> · 
  <a href="#功能特性">功能特性</a> · 
  <a href="#开发">开发</a>
</p>

<p align="center">
  <a href="README.md">English</a> | 简体中文
</p>

---

## 这是什么

GitHub Trending 告诉你**今天**什么最火。

GitHub Discovery 告诉你什么**即将火起来**——增长曲线异常的仓库、Hacker News 上的社区精选，以及正在积攒势头的早期项目。

它每天从 6 个数据源采集信号，经过一套智能评分系统（满分 100 分）筛选，最终通过邮件和网页把精选结果送到你面前。工作流每天调度两次（04:43 和 08:43 UTC）；当天已生成报告时，第二次运行会被同日保护直接跳过。

---

## 工作原理

```
  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
  │   GitHub    │  │   GitHub    │  │   Hacker    │
  │  Trending   │  │   Search    │  │    News     │
  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
         │                │                │
  ┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴──────┐
  │   Rising    │  │   AI/ML     │  │  HF Daily   │
  │  Detection  │  │  Keywords   │  │   Papers    │
  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
         │                │                │
         └────────────────┼────────────────┘
                          ▼
              ┌───────────────────────┐
              │    Smart Scorer       │
              │    (100 points)       │
              │  ─────────────────    │
              │  acceleration : 40    │
              │  quality      : 30    │
              │  anti-spam    : 30    │
              └───────────┬───────────┘
                          ▼
              ┌───────────────────────┐
              │  Cross-day Dedup      │
              │  (7-day window)       │
              └───────────┬───────────┘
                          ▼
         ┌────────────────┴────────────────┐
         ▼                                 ▼
  ┌─────────────┐                  ┌─────────────┐
  │ 📧 Email    │                  │ 🌐 GitHub   │
  │   Digest    │                  │    Pages    │
  └─────────────┘                  └─────────────┘
```

---

## 功能特性

### 6 个数据源

| 数据源 | 信号 | 能发现什么 |
|--------|--------|-----------------|
| [GitHub Trending](https://github.com/trending) | 热度 | 每日趋势仓库 |
| GitHub Search | 新晋上升 | 最近 7 天创建、星标增长迅猛的仓库 |
| [Hacker News](https://news.ycombinator.com/) | 社区精选 | Show HN 帖子中出现的 GitHub 仓库 |
| Rising Detection | 早期信号 | 最近 3 天创建、fork/star 比大于 0.3 且不超过 0.5 的仓库——fork 作为真实使用的早期信号；比率更高的按 fork farm 直接排除 |
| AI/ML 关键词轮扫 | AI 方向 | 用一组 AI/ML 关键词扫 GitHub Search，每天轮换 5 个词（思路来自 [OSSInsight trending/ai](https://ossinsight.io/trending/ai)，实现走的是 GitHub Search API） |
| [HF Daily Papers](https://huggingface.co/papers) | 研究信号 | Hugging Face 热门论文关联的 GitHub 仓库——我们假设论文点赞领先 GitHub 星标几天，但仓库里还没有可提交的测量来支撑这个领先时间 |

### 智能评分（满分 100 分）

| 维度 | 分值 | 衡量什么 |
|-----------|--------|------------------|
| **加速度** | 40 | 真实的日环比星标增长（基于每日快照）+ 相对生命周期均值的加速度 |
| **质量** | 30 | 项目年龄、语言、许可证、内容完整度 |
| **反垃圾** | 30 | 从 30 分起扣：star/fork 比 > 50、年龄 < 3 天且 5000+ 星、营销买词、外挂/随机用户名特征 |
| **代码质量** | +20 | README、CI 配置、提交频率——按比例并入 quality 维度，而不是额外叠加 |
| **可疑星标** | -20 / -15 | 年龄 ≤ 1 天且 1000+ 星（-20）；年龄 ≤ 2 天且 2000+ 星（-15）；日增 1000+ 星且描述为空（-15） |
| **批量刷量** | 最多 -40 | 同一作者一批里出现 ≥ 3 个仓库（-15）、≥ 2 个仓库上线不足 7 天已过 200 星（-15）、描述高度模板化（-10） |

### 反垃圾

- **刷星检测**：年龄 ≤ 1 天且 1000+ 星、年龄 ≤ 2 天且 2000+ 星，或日增 1000+ 星且描述为空 → 标记
- **批量刷量检测**：同一作者一批里出现 ≥ 3 个仓库，或 ≥ 2 个上线不足 7 天的仓库已过 200 星 → 标记
- **内容质量**：没有描述或没有 README → 扣分
- **跨日去重**：7 天窗口内跨天不重复推荐（同日重跑可能重复选到同一个仓库）

### 邮件订阅

- 每日精选仓库直达你的收件箱
- 只渲染深色版本，并声明 `color-scheme` 供支持深色的客户端使用（Apple Mail / iOS）
- 基于 Resend API 发送

### RSS / Atom 订阅

- 不想留邮箱？用阅读器订阅 Atom feed：
  `https://alloevil.github.io/github-discovery/feed.xml`
- 保留最近约 14 天的推荐，随每日任务自动更新

### GitHub Pages

- 现代、专业的网页界面
- 按日期和语言筛选
- 展示最近一次发布运行的评分（页面是由每日工作流重建的静态文件）

---

## 安装

不需要装任何依赖：流水线只用 Python 标准库（无需 pip 安装），仓库里没有 `requirements.txt`，CI 跑的是 Python 3.11。Resend 和 Firecrawl 的 HTTP 请求会调用系统的 `curl`。

```bash
git clone https://github.com/alloevil/github-discovery.git
cd github-discovery
python scripts/main.py   # 跑一次完整流程：采集 → 评分 → 去重 → 写 output/ 和 data/
```

发邮件日报需要 `RESEND_API_KEY`；采集、评分、站点和 Atom feed 完全不需要任何 key，`GITHUB_TOKEN` 只是可选，用来把 GitHub API 限额从每小时 60 次提高到 5000 次。想让它每天自动跑而不是本地手动跑，看下面的「快速开始」。

---

## 什么时候适合用

- 你想在一个库、工具或模型冲到 1 万星**之前**就看到它，而不是之后。
- 你希望推荐结论可以复查：每条推荐都带着自己的分数，每次运行的输入数据都提交在 `data/` 里。
- 你不想维护任何基础设施——GitHub Actions 加一个发信用的 API key，没有服务器，没有数据库。
- 你在意刷出来的热度：星标真实性检查、跨仓库的批量刷量检测、描述/README 质量检查都会扣分。

## 什么时候不要用

- 你想要的是有编辑判断的人工精选。这里只是一个评分函数，偶尔会让一个仅靠加速度的仓库排到前面。
- 你想按主题或按人订阅。6 个数据源及其查询阈值都写在 `scripts/sources.py`，评分权重在 `scripts/config.py`；网页只提供事后的日期和语言筛选。
- 你想要「高分必然长期成功」的证据。仓库里提交的回测用 7 天报告筛选出 20 个仓库，但实际观察到的增长窗口只有约 1 天（20 条记录全部是 `days_since_discovery: 1`），而且只是一个时间点——够用来体检评分，不足以证明预测能力。
- 你需要「一个都不漏」。只有出现在这 6 个数据源里的仓库才会被打分，跨日去重会在推荐后压制该仓库 7 天，而昂贵的逐仓库质量与星标真实性检查只跑粗排后的前 `DEEP_CHECK_TOP_K`（20）个候选。
- 你希望 AI/ML 轮扫每天都覆盖全部关键词：它每天只用轮换列表里的 5 个词，单日只覆盖其中一部分。

---

## 快速开始

### 1. Fork 本仓库

点击右上角的 **Fork** 按钮。

### 2. 配置 Secrets

进入 **Settings → Secrets and variables → Actions**，添加：

| Secret | 必填 | 说明 |
|--------|----------|-------------|
| `RESEND_API_KEY` | ✅ | [Resend](https://resend.com/) API Key，用于发送邮件 |
| `GITHUB_TOKEN` | ❌ | GitHub Personal Access Token（可选，默认使用 GITHUB_TOKEN） |
| `FIRECRAWL_API_KEY` | ❌ | [Firecrawl](https://firecrawl.dev) 的 key。让 GitHub Trending 的解析更健壮（抓取页面而不是正则匹配原始 HTML）。不配置时 Trending 回退为直接抓取 HTML。 |

### 3. 启用 GitHub Actions

进入 **Actions**，点击 **I understand my workflows, go ahead and enable them**。

### 4. 手动测试

进入 **Actions → Daily Discovery → Run workflow** 触发一次测试运行。

### 5. 查看结果

- **GitHub Pages**：访问 `https://<your-username>.github.io/github-discovery/`
- **邮件**：订阅者每天收到日报

---

## 项目结构

```
github-discovery/
├── scripts/
│   ├── sources.py           # 6 data source collectors
│   ├── scorer.py            # Scoring algorithm
│   ├── quality.py           # Code quality detection
│   ├── anti_spam.py         # Anti-spam scoring dimension
│   ├── dedup.py             # Cross-day deduplication (7-day window)
│   ├── fraud_detection.py   # Batch fraud detection
│   ├── snapshots.py         # Daily star snapshots (real growth)
│   ├── verify_scoring.py    # Scoring verification / backtesting
│   ├── generate_site.py     # GitHub Pages site + Atom feed
│   ├── subscribe_handler.gs # Google Apps Script subscribe endpoint
│   ├── main.py              # Entry point
│   └── config.py            # Configuration
├── tests/                   # Unit tests (pytest)
├── docs/                    # GitHub Pages (index.html, feed.xml)
├── .github/workflows/       # Daily automation
└── subscribers.txt          # Email subscriber list
```

---

## 开发

### 本地运行

```bash
git clone https://github.com/alloevil/github-discovery.git
cd github-discovery
python scripts/main.py
```

### 运行测试

```bash
pip install pytest
python -m pytest tests/ -v
```

### 添加新数据源

1. 在 `scripts/sources.py` 中添加新的 `fetch_xxx()` 函数
2. 在 `fetch_all()` 中调用它
3. 在 `tests/test_sources.py` 中补充测试
4. 提交 PR

### 评分算法

评分逻辑位于 `scripts/scorer.py`，各维度上限是 `scripts/config.py` 里的常量：

```python
ACCELERATION_MAX = 40
QUALITY_MAX = 30
ANTISPAM_MAX = 30
QUALITY_BONUS_MAX = 20   # 深查代码质量加分，按比例并入 quality 维度
DEEP_CHECK_TOP_K = 20    # 粗排后有多少候选进入昂贵的深度检查
```

---

## 评分验证

运行回测，验证高分仓库后来是否真的火了。回测直接读取随仓库提交的每日
JSON 报告（`data/discovery-*.json`），全新 clone 无需先前运行过也能跑；
但它仍需要联网，因为当前星标数来自 GitHub API（未设 `GITHUB_TOKEN` 时按
匿名每小时 60 次限额）：

```bash
python scripts/verify_scoring.py --days 30
```

`--days N` 是按「相对今天」的日期筛选报告，所以每次运行度量的都是当前窗口、
并用今天的星标数重算增长。它无法复现已提交的 `reports/verify-2026-06-25.json`：
那份快照的输入报告已不在 `data/` 里，相关仓库的星标数也早已变化。

---

## 常见问题

**100 分是怎么分配的？** 加速度最多 40 分，衡量基于自己提交的每日快照算出的真实日环比星标增长，加上相对该仓库生命周期均值的加速度；质量最多 30 分（年龄、语言、许可证、内容完整度）；反垃圾从 30 分起扣：star/fork 比超过 50、年龄不足 3 天却已过 5000 星、描述里的营销买词、外挂类或随机数字用户名特征。此外深查代码质量（README、CI 配置、提交频率）提供最多 20 分的加分，按比例并入 quality 维度而不是额外叠加；星标真实性检查扣 15 或 20 分；批量刷量最多扣 40 分。

**需要付费服务吗？** 只有邮件需要。`RESEND_API_KEY` 用于通过 Resend 发送日报；`FIRECRAWL_API_KEY` 是可选的，只是让 GitHub Trending 的解析比正则匹配原始 HTML 更健壮。其余部分都跑在 GitHub Actions 免费额度上，用默认的 `GITHUB_TOKEN` 即可。

**一个仓库火着的时候会天天被推荐吗？** 不会。跨日去重会拦掉过去 7 天内推荐过的仓库，依据是提交在 `data/recommend_history.json` 里的推荐历史，超过 30 天的记录会被清理。这份历史必须是提交进仓库的文件，因为每次 CI 都是全新 checkout，没有任何本地状态。

**网页上的数字可信吗？** 网页是构建产物：`scripts/generate_site.py` 用 `docs/template.html` 加上已提交的报告渲染出 `docs/index.html`，工作流再把整个 `docs/` 发布到 `gh-pages` 分支。真正权威的是提交在 `data/` 下的 JSON，`verify_scoring.py` 读的就是它；`output/` 下的 Markdown 日报是给人看的副本，站点优先读 JSON、读不到才回退到日报。所以网页上的任何结论都能在全新 clone 上重算一遍。

**怎么加一个数据源？** 在 `scripts/sources.py` 里加一个 `fetch_xxx()` 函数，在 `fetch_all()` 里调用它，然后在 `tests/test_sources.py` 补测试。各数据源返回同一种仓库字典结构，所以评分、去重和渲染都不需要改。

---

## 参与贡献

欢迎贡献！请按以下步骤操作：

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/your-feature`
3. 提交改动：`git commit -m 'feat: add your feature'`
4. 推送分支：`git push origin feature/your-feature`
5. 提交 Pull Request

### 贡献方向

- 📡 添加新数据源
- 🎯 优化评分算法
- 🐛 修复 bug
- 📖 完善文档
- ✅ 补充测试

---

## 许可证

本项目基于 [MIT License](LICENSE) 开源。

---

## 致谢

- [GitHub API](https://docs.github.com/en/rest)
- [Hacker News API](https://github.com/HackerNews/API)
- [OSSInsight](https://ossinsight.io/) —— AI/ML 仓库趋势与分析
- [Resend](https://resend.com/)
- [Firecrawl](https://firecrawl.dev/) —— 为 GitHub Trending 提供健壮的网页抓取

---

<p align="center">
  <strong>⭐ 如果这个项目对你有用，欢迎点个 star！</strong>
</p>
