# 🔥 GitHub Discovery

> 发现正在爆发的 GitHub 仓库，在它们变成热门之前。

## ✨ 特性

- 🔍 **5 大数据源**：GitHub Trending + Hacker News + Reddit + Fork/Watch 增速异常 + GitHub Search
- 📊 **智能评分**：加速度(40) + 质量(30) + 反垃圾(30) + 代码质量(+20) - Star 可疑(-15) + 用户反馈(±10)
- 🔄 **跨天去重**：7 天窗口，不重复推荐
- 🛡️ **反垃圾**：Star 刷量检测、单人高星检测
- 👍👎 **用户反馈**：每条推荐可投票，反馈融入评分
- 📬 **邮件订阅**：每日推送精选仓库（支持暗模式）
- 🎨 **GitHub Pages**：赛博朋克风格在线展示

## 📡 数据源

| 数据源 | 信号类型 | 说明 |
|--------|----------|------|
| GitHub Trending | 热度 | 每日热门仓库 |
| GitHub Search | 新高星 | 最近 7 天高 Star 仓库 |
| Hacker News | 社区推荐 | Show HN 中的 GitHub 项目 |
| Reddit | 讨论热度 | /r/programming 热帖中的 GitHub 链接 |
| Rising | 早期信号 | Fork/Watch 增速异常检测 |

## 📊 评分体系

| 维度 | 分值 | 说明 |
|------|------|------|
| 加速度 | 40 | Star 增速、加速趋势 |
| 质量 | 30 | 年龄、语言、许可证 |
| 反垃圾 | 30 | Fork 比率、内容完整性 |
| 代码质量 | +20 | README、CI、commit 频率 |
| Star 可疑 | -15 | 单人高星、暴涨检测 |
| 用户反馈 | ±10 | 👍👎 投票 |

## 🚀 快速开始

1. Fork 本仓库
2. 配置 Secrets（`RESEND_API_KEY` 用于邮件推送）
3. 启用 GitHub Actions
4. 访问 GitHub Pages 查看每日报告

## 📁 项目结构

```
github-discovery/
├── scripts/
│   ├── sources.py        # 5 个数据源
│   ├── scorer.py         # 评分算法
│   ├── quality.py        # 代码质量检测
│   ├── dedup.py          # 跨天去重
│   ├── feedback.py       # 用户反馈系统
│   ├── main.py           # 入口
│   └── ...
├── data/
│   ├── feedback.json     # 用户投票数据
│   └── recommend_history.json  # 推荐历史（去重用）
├── docs/
│   └── index.html        # GitHub Pages
└── .github/workflows/    # CI/CD
```

## 🤝 Contributing

欢迎提交 PR 添加新的数据源！

## 📄 License

MIT
