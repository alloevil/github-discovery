# 🔥 GitHub Discovery

> 发现正在爆发的 GitHub 仓库，在它们变成热门之前。

## ✨ 特性

- 🔍 **多源采集**：GitHub Trending + Hacker News + Reddit + Fork/Watch 增速异常检测
- 📊 **智能评分**：加速度 + 质量 + 反垃圾 + 用户反馈，100 分制
- 👍👎 **用户反馈**：每条推荐可投票，反馈融入评分算法
- 📬 **邮件订阅**：每日推送精选仓库到邮箱（支持暗模式）
- 🎨 **GitHub Pages**：赛博朋克风格在线展示
- 🆓 **完全免费**：基于 GitHub Actions 运行，无需服务器

## 📡 数据源

| 数据源 | 说明 |
|--------|------|
| GitHub Trending | 每日热门仓库 |
| GitHub Search | 新创建的高星仓库 |
| Hacker News | Show HN 中的 GitHub 项目 |
| Reddit | /r/programming 热门帖子中的 GitHub 链接 |
| Rising Detection | Fork/Watch 增速异常检测（早期信号） |

## 🚀 快速开始

1. Fork 本仓库
2. 配置 Secrets（`RESEND_API_KEY` 用于邮件推送）
3. 启用 GitHub Actions
4. 访问 GitHub Pages 查看每日报告

## 📁 项目结构

```
github-discovery/
├── scripts/
│   ├── sources.py        # 数据源（5 个）
│   ├── scorer.py         # 评分算法
│   ├── feedback.py       # 用户反馈系统
│   ├── main.py           # 入口
│   └── ...
├── data/
│   └── feedback.json     # 反馈数据
├── docs/
│   └── index.html        # GitHub Pages
└── .github/workflows/    # CI/CD
```

## 🤝 Contributing

欢迎提交 PR 添加新的数据源！

## 📄 License

MIT
