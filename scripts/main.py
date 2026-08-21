"""GitHub Discovery - Main entry point.

Discovers trending GitHub repos before they go mainstream.
Outputs top repos as markdown to stdout and file.
"""

import os
import sys
import json
import html
import subprocess
import urllib.request
import urllib.error
from datetime import datetime

# Ensure we can import sibling modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import TOP_N, DEEP_CHECK_TOP_K, OUTPUT_DIR, DATA_DIR, RESEND_API_KEY
from sources import fetch_all
from scorer import calculate_score, merge_quality_bonus, build_reason
from dedup import (
    is_recently_recommended, was_recommended_before,
    record_recommendation, cleanup_old_records,
)
from quality import check_quality, check_star_authenticity, is_blocked_content
from fraud_detection import detect_batch_fraud, apply_fraud_penalty
from snapshots import record_snapshots, get_growth


def get_subscribers() -> list[str]:
    """Fetch subscriber emails from subscribers.txt file."""
    sub_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'subscribers.txt')
    emails = []
    try:
        with open(sub_file, 'r') as f:
            for line in f:
                email = line.strip()
                if email and not email.startswith('#') and '@' in email:
                    emails.append(email)
    except FileNotFoundError:
        print("[WARN] subscribers.txt not found")
    return emails


def _send_single_email(recipient: str, subject: str, html_body: str) -> bool:
    """Send one email to one recipient via the Resend API. Returns True on success."""
    payload = json.dumps({
        "from": "onboarding@resend.dev",
        "to": [recipient],
        "subject": subject,
        "html": html_body,
    })

    try:
        result = subprocess.run(
            [
                "curl", "-s", "-X", "POST",
                "https://api.resend.com/emails",
                "-H", f"Authorization: Bearer {RESEND_API_KEY}",
                "-H", "Content-Type: application/json",
                "-d", payload,
            ],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            print(f"[ERROR] Resend curl failed for {recipient}: {result.stderr[:200]}")
            return False
        # curl exit 0 only means the request was sent; Resend signals
        # success by returning an "id". An error body (bad key, etc.) has
        # no id, so treat that as a failure too.
        try:
            resp = json.loads(result.stdout)
        except (ValueError, TypeError):
            print(f"[ERROR] Resend returned non-JSON for {recipient}: {result.stdout[:200]}")
            return False
        if resp.get("id"):
            print(f"[OK] Resend email sent to {recipient}: {resp['id']}")
            return True
        print(f"[ERROR] Resend rejected the request for {recipient}: {str(resp)[:200]}")
        return False
    except Exception as e:
        print(f"[ERROR] Resend send failed for {recipient}: {e}")
        return False


def send_email_via_resend(to: list[str], subject: str, html_body: str) -> str:
    """Send email via Resend API using curl (urllib blocked by Cloudflare).

    Each recipient gets an individual API call so no subscriber ever sees
    another subscriber's address in the To header, and one bad address
    doesn't block delivery to the rest.

    Returns: "sent" when at least one recipient was delivered, "skipped"
    when there is nothing to do (no key / no subscribers), or "failed"
    when every send errored. Partial failure still counts as "sent"
    (failures are logged per recipient) because a whole-run retry would
    double-deliver to the recipients that already succeeded.
    """
    if not RESEND_API_KEY:
        print("[SKIP] No Resend API key configured.")
        return "skipped"
    if not to:
        print("[SKIP] No subscribers to send to.")
        return "skipped"

    sent = sum(1 for recipient in to if _send_single_email(recipient, subject, html_body))
    failed = len(to) - sent
    if failed:
        print(f"[WARN] Resend delivery: {sent} sent, {failed} failed of {len(to)}.")
    return "sent" if sent else "failed"


EMAIL_SOURCE_LABELS = {
    "trending": "🔥 Trending",
    "search": "🔍 Search",
    "hn": "🟠 HN",
    "rising": "📈 Rising",
    "ai-trending": "🤖 AI/ML",
    "hf-papers": "🤗 HF Papers",
}


def send_digest_email(date_str: str, top_new: list) -> str:
    """Send the daily discovery digest email to all subscribers (via Resend).

    Returns "sent" / "skipped" / "failed" (see send_email_via_resend).
    """
    subscribers = get_subscribers()
    if not subscribers:
        print("[SKIP] No subscribers found.")
        return "skipped"
    print(f"[INFO] Found {len(subscribers)} subscribers.")

    repo_lines = []
    for i, (repo, scores) in enumerate(top_new, 1):
        name = repo['full_name']
        url = html.escape(repo['url'], quote=True)
        stars = repo.get('stars', 0)
        real_daily = repo.get('real_daily_stars')
        daily = real_daily if real_daily is not None else repo.get('daily_stars', 0)
        lang = repo.get('language', '')
        desc = html.escape((repo.get('description') or 'No description')[:120])
        score = scores.get('total', 0)
        owner = html.escape(name.split('/')[0] if '/' in name else '')
        repo_short = html.escape(name.split('/')[1] if '/' in name else name)
        avatar = html.escape(f"https://github.com/{owner}.png" if owner else "", quote=True)
        # 裸分降权（#9）：头部分数饱和成一排 100，按分数变色只会放大
        # 无意义的数字 —— 统一中性灰，让理由行承担区分度。
        lang_color = '#3572A5' if lang.lower() == 'python' else '#3178c6' if lang.lower() == 'typescript' else '#f1e05a' if lang.lower() == 'javascript' else '#dea584' if lang.lower() == 'rust' else '#00ADD8' if lang.lower() == 'go' else '#8a8f98'
        src_label = html.escape(EMAIL_SOURCE_LABELS.get((repo.get('source') or '').lower(), repo.get('source') or ''))
        reason = html.escape(build_reason(repo))

        repo_lines.append(
            f'<tr style="border-bottom:1px solid #23252a;">'
            f'<td style="padding:12px 8px;color:#8a8f98;font-size:13px;">{i}</td>'
            f'<td style="padding:12px 8px;">'
            f'<div style="display:flex;align-items:center;gap:8px;">'
            f'<img src="{avatar}" width="20" height="20" style="border-radius:4px;" alt="">'
            f'<div>'
            f'<a href="{url}" style="color:#5e6ad2;text-decoration:none;font-weight:500;font-size:14px;">{repo_short}</a>'
            f'<span style="color:#62666d;font-size:12px;margin-left:4px;">{owner}</span>'
            f'<br><span style="color:#8a8f98;font-size:12px;line-height:1.4;">{desc}</span>'
            f'<br><span style="color:#5e6ad2;font-size:12px;font-weight:500;">{reason}</span>'
            f'</div></div></td>'
            f'<td style="padding:12px 8px;text-align:right;">'
            f'<span style="color:#d0d6e0;font-size:13px;">{stars:,}</span>'
            f'<br><span style="color:#62666d;font-size:11px;">+{daily:.0f}/d</span></td>'
            f'<td style="padding:12px 8px;">'
            f'<span style="display:inline-flex;align-items:center;gap:4px;color:#8a8f98;font-size:12px;">'
            f'<span style="width:8px;height:8px;border-radius:2px;background:{lang_color};display:inline-block;"></span>'
            f'{lang}</span></td>'
            f'<td style="padding:12px 8px;text-align:center;">'
            f'<span style="background:#ffffff08;color:#8a8f98;padding:2px 8px;border-radius:4px;font-size:12px;">{score}</span>'
            f'</td>'
            f'<td style="padding:12px 8px;text-align:center;">'
            f'<span style="color:#8a8f98;font-size:12px;white-space:nowrap;">{src_label}</span>'
            f'</td></tr>'
        )

    repo_rows = "\n".join(repo_lines)
    total = len(top_new)

    html_body = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
</head>
<body style="margin:0;padding:0;background:#010102;color-scheme:dark;">
<div style="font-family:'Inter',-apple-system,BlinkMacSystemFont,'SF Pro Display',sans-serif;background:#010102;color:#f7f8f8;padding:32px 24px;max-width:700px;margin:0 auto;">

<div style="padding:24px 0 20px;border-bottom:1px solid #23252a;margin-bottom:24px;">
<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
<span style="font-size:24px;">🔥</span>
<span style="font-size:18px;font-weight:600;color:#f7f8f8;letter-spacing:-0.3px;">GitHub Discovery</span>
</div>
<p style="color:#8a8f98;font-size:13px;margin:0;">{date_str} · {total} new repos discovered</p>
</div>

<table style="width:100%;border-collapse:collapse;margin:0 0 24px;">
<tr style="border-bottom:1px solid #23252a;color:#62666d;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;">
<th style="padding:8px 8px 12px;text-align:left;font-weight:500;">#</th>
<th style="padding:8px 8px 12px;text-align:left;font-weight:500;">Repository</th>
<th style="padding:8px 8px 12px;text-align:right;font-weight:500;">Stars</th>
<th style="padding:8px 8px 12px;font-weight:500;">Lang</th>
<th style="padding:8px 8px 12px;font-weight:500;">Score</th>
<th style="padding:8px 8px 12px;font-weight:500;">Source</th>
</tr>
{repo_rows}
</table>

<div style="border-top:1px solid #23252a;padding-top:20px;">
<a href="https://alloevil.github.io/github-discovery/" style="display:inline-block;padding:8px 20px;background:#5e6ad218;color:#5e6ad2;text-decoration:none;font-size:13px;font-weight:500;border:1px solid #5e6ad244;border-radius:6px;">View Full Report →</a>
</div>

<div style="margin-top:24px;padding-top:16px;border-top:1px solid #23252a;">
<p style="color:#62666d;font-size:11px;margin:0;">Sent by <a href="https://github.com/alloevil/github-discovery" style="color:#8a8f98;">GitHub Discovery</a></p>
</div>

</div>
</body>
</html>"""

    return send_email_via_resend(subscribers, f"🔥 GitHub Discovery — {date_str}", html_body)


JSON_REPO_FIELDS = [
    "full_name", "url", "description", "language", "stars", "forks",
    "age_days", "daily_stars", "real_daily_stars", "watchers",
    "source", "sources", "license",
    "hn_title", "hn_score", "hf_title", "hf_upvotes", "rising_signal",
    "has_readme", "has_license", "has_ci",
]


def repo_to_json(repo: dict, scores: dict, rank: int) -> dict:
    """Whitelist repo fields + scores for the structured JSON report."""
    entry = {k: repo[k] for k in JSON_REPO_FIELDS if k in repo}
    entry["rank"] = rank
    entry["scores"] = scores
    return entry


def write_json_report(date_str: str, top_new: list, top_repeat: list) -> str:
    """写结构化 JSON 报告（data/discovery-YYYY-MM-DD.json）。

    网站/RSS 从这里读取数据，markdown 报告只服务于人类阅读 ——
    避免 generate_site.py 用正则反解析自己生成的 markdown。
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, f"discovery-{date_str}.json")
    payload = {
        "date": date_str,
        "generated_at": datetime.now().isoformat(),
        "new": [repo_to_json(r, s, i) for i, (r, s) in enumerate(top_new, 1)],
        "repeat": [repo_to_json(r, s, i) for i, (r, s) in enumerate(top_repeat, 1)],
    }
    with open(path, "w") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    return path


def format_repo_markdown(repo: dict, scores: dict, rank: int) -> str:
    """Format a single repo as markdown."""
    name = repo["full_name"]
    url = repo["url"]
    stars = repo.get("stars", 0)
    age = repo.get("age_days", 1)
    real_daily = repo.get("real_daily_stars")
    daily = real_daily if real_daily is not None else repo.get("daily_stars", 0)
    growth_label = "stars/day (measured)" if real_daily is not None else "stars/day (lifetime avg)"
    desc = repo.get("description", "No description")
    lang = repo.get("language", "Unknown")
    source = " + ".join(repo.get("sources") or [repo.get("source", "unknown")])
    total = scores["total"]

    # Score bar
    bar_len = int(total / 5)
    bar = "█" * bar_len + "░" * (20 - bar_len)

    lines = [
        f"### {rank}. [{name}]({url})",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| ⭐ Stars | {stars:,} |",
        f"| 📅 Age | {age} days |",
        f"| 🚀 Daily Growth | {daily:.1f} {growth_label} |",
        f"| 🔤 Language | {lang} |",
        f"| 📡 Source | {source} |",
        f"",
        f"> {desc}",
        f"",
        f"**Score: {total}/100** `{bar}`",
        f"- Acceleration: {scores['acceleration']}/40",
        f"- Quality: {scores['quality']}/30",
        f"- Anti-spam: {scores['antispam']}/30",
        f"",
        f"---",
        f"",
    ]

    # HN bonus info
    if repo.get("hn_title"):
        lines.insert(-2, f"- 🔶 HN: [{repo['hn_title']}](https://news.ycombinator.com) (score: {repo.get('hn_score', 0)})")
        lines.insert(-2, "")

    # HF paper info
    if repo.get("hf_title"):
        lines.insert(-2, f"- 🤗 HF Paper: {repo['hf_title']} (upvotes: {repo.get('hf_upvotes', 0)})")
        lines.insert(-2, "")

    return "\n".join(lines)


def generate_markdown(top_new: list[tuple[dict, dict]], top_repeat: list[tuple[dict, dict]]) -> str:
    """Generate full markdown report."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = f"""# 🔥 GitHub Discovery Report

> **Generated:** {now}
> **{len(top_new)} new repos + {len(top_repeat)} repeat performers**

---

"""

    # First Timers
    body = "## ⭐ Top Starred Repositories — First Timers\n\n"
    body += "*These repos were first featured in GitHub Discovery*\n\n"
    for i, (repo, scores) in enumerate(top_new, 1):
        body += format_repo_markdown(repo, scores, i)

    # Repeat Performers
    if top_repeat:
        body += "\n## 🔄 Top Starred Repositories — Repeat Performers\n\n"
        body += "*These repos were previously featured in GitHub Discovery*\n\n"
        for i, (repo, scores) in enumerate(top_repeat, 1):
            body += format_repo_markdown(repo, scores, i)

    summary = f"""
## 📊 Summary

- **New discoveries:** {len(top_new)} repos
- **Repeat performers:** {len(top_repeat)} repos
- **Score range:** {top_new[-1][1]['total'] if top_new else '?'} - {top_new[0][1]['total'] if top_new else '?'}
- **Top pick:** {f'[{top_new[0][0]["full_name"]}]({top_new[0][0]["url"]})' if top_new else 'N/A'}

---
*Generated by GitHub Discovery Tool*
"""
    return header + body + summary


def main():
    # Idempotency guard: GitHub cron is unreliable, so we schedule the
    # workflow twice a day. If today's report was already produced by an
    # earlier run, skip entirely — no duplicate email, no duplicate commit.
    today = datetime.now().strftime("%Y-%m-%d")
    today_report = os.path.join(OUTPUT_DIR, f"discovery-{today}.md")
    if os.path.exists(today_report):
        print(f"[SKIP] Today's report already exists ({today_report}). Nothing to do.")
        return

    # Cleanup old dedup records
    cleanup_old_records()

    print("=" * 60)
    print("  GitHub Discovery Tool")
    print("  Finding repos before they go viral")
    print("=" * 60)
    print()

    # Fetch from all sources
    all_repos = fetch_all()

    if not all_repos:
        print("[ERROR] No repos found from any source. Check network/API.")
        sys.exit(1)

    # Star 快照：对**所有**抓到的仓库记录（含即将被去重过滤的），
    # 保证已推荐仓库的时间序列不中断 —— 快照是次日计算真实增速的基础。
    record_snapshots(all_repos)

    # 跨天去重：过滤掉最近 7 天已推荐的仓库
    filtered_repos = []
    dedup_count = 0
    for repo in all_repos:
        if is_recently_recommended(repo["full_name"]):
            dedup_count += 1
            continue
        filtered_repos.append(repo)
    if dedup_count:
        print(f"[Dedup] Skipped {dedup_count} recently recommended repos")
    all_repos = filtered_repos

    # 内容过滤：赌博/色情/恶意利用
    content_blocked = 0
    clean_repos = []
    for repo in all_repos:
        blocked, reason = is_blocked_content(repo)
        if blocked:
            content_blocked += 1
            print(f"  🚫 Blocked: {repo['full_name']} ({reason})")
        else:
            clean_repos.append(repo)
    if content_blocked:
        print(f"[ContentFilter] Blocked {content_blocked} repos (gambling/malicious/NSFW)")
    all_repos = clean_repos

    # 注入真实日增（昨天的快照存在时）：scorer 优先使用它而非终身平均
    growth_known = 0
    for repo in all_repos:
        growth = get_growth(repo["full_name"], repo.get("stars", 0))
        if growth:
            repo["real_daily_stars"] = growth["real_daily"]
            growth_known += 1
    print(f"[Snapshot] Real growth known for {growth_known}/{len(all_repos)} repos")

    # ── 粗排：全量评分 + 排序 ──────────────────────────────────────
    # 深度检查（每个仓库约 3 次 API 调用）必须发生在粗排**之后**，
    # 让配额花在分数最高的候选上。旧版按抓取顺序取前 15 个深查，
    # 导致只有 trending 源能拿到 quality 加分，其他源结构性进不了 top。
    scored = [(repo, calculate_score(repo)) for repo in all_repos]
    scored.sort(key=lambda x: x[1]["total"], reverse=True)

    # ── 深查：代码质量 + Star 真实性，仅对粗排 top-K ──────────────
    deep_checked = []
    for repo, _ in scored[:DEEP_CHECK_TOP_K]:
        full_name = repo["full_name"]
        try:
            quality = check_quality(full_name, repo)
            repo["quality_score"] = quality["quality_score"]
            repo["has_readme"] = quality.get("has_readme", False)
            repo["has_license"] = quality.get("has_license", False)
            repo["has_ci"] = quality.get("has_ci", False)
        except Exception:
            repo["quality_score"] = 0

        try:
            auth = check_star_authenticity(
                full_name, repo.get("stars", 0), repo.get("age_days", 1),
                description=repo.get("description") or "",
            )
            repo["star_suspicious"] = auth["is_suspicious"]
            repo["star_penalty"] = auth.get("penalty", 0)
            if auth["is_suspicious"]:
                print(f"  ⚠️ Suspicious stars: {full_name} ({auth['reason']})")
        except Exception:
            repo["star_suspicious"] = False
            repo["star_penalty"] = 0
        deep_checked.append(repo)
    if deep_checked:
        print(f"[Quality] Deep-checked top {len(deep_checked)} candidates")

    # 批量刷量检测（跨仓库维度）
    fraud_list = detect_batch_fraud(all_repos)
    fraud_map = {f["owner"]: f for f in fraud_list}
    if fraud_list:
        print(f"[Fraud] Detected {len(fraud_list)} suspicious owner(s)")
        for f in fraud_list:
            print(f"  ⚠️ {f['owner']}: {f['reason']} (penalty: {f['penalty']})")

    # ── 终评：重算深查过的仓库（has_readme 影响 quality 分），应用加减分 ──
    new_scored = []
    repeat_scored = []
    for repo, scores in scored:
        if repo.get("quality_score") is not None:
            scores = calculate_score(repo)

        # 代码质量加分：并入 quality 维度取 max（叠加会重复计分并
        # 在 clamp 处饱和 —— 曾导致 94% 上榜条目总分恒为 100）
        scores = merge_quality_bonus(scores, repo.get("quality_score", 0))

        # Star 可疑扣分
        star_penalty = repo.get("star_penalty", 0)
        if star_penalty:
            scores["total"] = max(0, scores["total"] + star_penalty)
            scores["star_penalty"] = star_penalty

        # 批量刷量扣分
        fraud = apply_fraud_penalty(repo, fraud_map)
        if fraud["is_fraud"]:
            scores["total"] = max(0, scores["total"] + fraud["penalty"])
            scores["fraud_penalty"] = fraud["penalty"]
            scores["fraud_reason"] = fraud["reason"]

        # First Timer / Repeat Performer：以随仓库提交的 recommend_history
        # 为准（CI 每次全新环境，只有提交进仓库的文件跨 run 持久）
        if was_recommended_before(repo["full_name"]):
            repeat_scored.append((repo, scores))
        else:
            new_scored.append((repo, scores))

    # Sort by total score descending
    new_scored.sort(key=lambda x: x[1]["total"], reverse=True)
    repeat_scored.sort(key=lambda x: x[1]["total"], reverse=True)

    # Take top N new repos
    top_new = new_scored[:TOP_N]
    # Take top 5 repeat performers
    top_repeat = repeat_scored[:5]

    if not top_new and not top_repeat:
        print("[WARN] No repos to recommend.")
        sys.exit(0)

    # Record recommendation history。repeat 也要记录 ——
    # 否则其 last_recommended 一直是 8~30 天前，明天还会再进 repeat 区。
    for repo, scores in top_new:
        record_recommendation(repo["full_name"], scores["total"])
    for repo, scores in top_repeat:
        record_recommendation(repo["full_name"], scores["total"])

    # Generate and output markdown
    md = generate_markdown(top_new, top_repeat)
    print(md)

    # Send digest email FIRST. The report file doubles as the idempotency
    # marker (see main() top), so we must not write it until the email has
    # been sent (or benignly skipped). If the email fails, we exit non-zero
    # without writing the marker, so the next scheduled run retries.
    date_str = datetime.now().strftime("%Y-%m-%d")
    email_result = send_digest_email(date_str, top_new)
    if email_result == "failed":
        print("[ERROR] Email send failed — not writing today's report so the "
              "next run retries. Exiting non-zero to flag the failure.")
        sys.exit(1)

    # Save to file (also the idempotency marker for same-day reruns)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, f"discovery-{date_str}.md")
    with open(out_path, "w") as f:
        f.write(md)
    print(f"\n[Saved] Report written to {out_path}")

    # 结构化 JSON（网站/RSS 的数据来源）
    json_path = write_json_report(date_str, top_new, top_repeat)
    print(f"[Saved] JSON report written to {json_path}")

    # Print compact summary
    print("\n" + "=" * 60)
    print("  TOP PICKS SUMMARY")
    print("=" * 60)
    for i, (repo, scores) in enumerate(top_new[:5], 1):
        print(f"  {i}. {repo['full_name']:40s} ⭐{repo['stars']:>6,}  📊{scores['total']:>3}/100")
    if len(top_new) > 5:
        print(f"  ... and {len(top_new) - 5} more")


if __name__ == "__main__":
    main()
