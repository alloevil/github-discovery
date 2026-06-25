"""GitHub Discovery - Main entry point.

Discovers trending GitHub repos before they go mainstream.
Outputs top repos as markdown to stdout and file.
"""

import os
import sys
import json
import subprocess
import urllib.request
import urllib.error
from datetime import datetime

# Ensure we can import sibling modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import TOP_N, OUTPUT_DIR, BUTTONDOWN_API_KEY, RESEND_API_KEY
from db import init_db, repo_exists, save_repo, save_run
from sources import fetch_all
from scorer import calculate_score
from feedback import get_all_feedback
from dedup import is_recently_recommended, record_recommendation, cleanup_old_records
from quality import check_quality, check_star_authenticity


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


def send_email_via_resend(to: list[str], subject: str, html_body: str) -> bool:
    """Send email via Resend API using curl (urllib blocked by Cloudflare)."""
    if not RESEND_API_KEY:
        print("[SKIP] No Resend API key configured.")
        return False
    if not to:
        print("[SKIP] No subscribers to send to.")
        return False

    payload = json.dumps({
        "from": "onboarding@resend.dev",
        "to": to,
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
        if result.returncode == 0:
            resp = json.loads(result.stdout)
            print(f"[OK] Resend email sent: {resp.get('id', 'ok')}")
            return True
        else:
            print(f"[ERROR] Resend curl failed: {result.stderr[:200]}")
            return False
    except Exception as e:
        print(f"[ERROR] Resend send failed: {e}")
        return False


def send_buttondown_email(date_str: str, top_new: list) -> bool:
    """Send discovery report email to all subscribers."""
    subscribers = get_subscribers()
    if not subscribers:
        print("[SKIP] No subscribers found.")
        return False
    print(f"[INFO] Found {len(subscribers)} subscribers.")

    repo_lines = []
    for i, (repo, scores) in enumerate(top_new, 1):
        name = repo['full_name']
        url = repo['url']
        stars = repo.get('stars', 0)
        daily = repo.get('daily_stars', 0)
        lang = repo.get('language', '')
        desc = (repo.get('description') or 'No description')[:120]
        score = scores.get('total', 0)
        repo_lines.append(
            f'<tr style="border-bottom:1px solid #1a1a2e;">'
            f'<td style="padding:8px;color:#00ffff;font-weight:600;">{i}</td>'
            f'<td style="padding:8px;">'
            f'<a href="{url}" style="color:#00ffff;text-decoration:none;">{name}</a>'
            f'<br><span style="color:#666;font-size:12px;">{desc}</span>'
            f'</td>'
            f'<td style="padding:8px;color:#888;text-align:right;">⭐{stars:,}<br><span style="font-size:11px;">{daily:.0f}/day</span></td>'
            f'<td style="padding:8px;color:#888;">{lang}</td>'
            f'<td style="padding:8px;text-align:center;">'
            f'<span style="color:{'#ffaa00' if score>=98 else '#00ff88' if score>=95 else '#00ffff' if score>=90 else '#444'};">{score}</span>'
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
<body style="margin:0;padding:0;background:#0a0a0f;color-scheme:dark;">
<div style="font-family:'Courier New',monospace;background:#0a0a0f;color:#c0c0d0;padding:24px;max-width:700px;margin:0 auto;">
<h2 style="color:#00ffff;font-size:18px;">🔥 GitHub Discovery — {date_str}</h2>
<p style="color:#888;">{total} new repos discovered today:</p>
<table style="width:100%;border-collapse:collapse;margin:16px 0;">
<tr style="border-bottom:2px solid #00ffff33;color:#666;font-size:11px;text-transform:uppercase;">
<th style="padding:8px;text-align:left;">#</th>
<th style="padding:8px;text-align:left;">Repo</th>
<th style="padding:8px;text-align:right;">Stars</th>
<th style="padding:8px;">Lang</th>
<th style="padding:8px;">Score</th>
</tr>
{repo_rows}
</table>
<hr style="border-color:#00ffff33;margin:24px 0;">
<p><a href="https://alloevil.github.io/github-discovery/" style="color:#00ffff;">View on GitHub Discovery →</a></p>
<p style="color:#333;font-size:11px;">Sent by <a href="https://github.com/alloevil/github-discovery" style="color:#555;">GitHub Discovery</a></p>
</div>
</body>
</html>"""

    return send_email_via_resend(subscribers, f"🔥 GitHub Discovery — {date_str}", html_body)


def format_repo_markdown(repo: dict, scores: dict, rank: int) -> str:
    """Format a single repo as markdown."""
    name = repo["full_name"]
    url = repo["url"]
    stars = repo.get("stars", 0)
    age = repo.get("age_days", 1)
    daily = repo.get("daily_stars", 0)
    desc = repo.get("description", "No description")
    lang = repo.get("language", "Unknown")
    source = repo.get("source", "unknown")
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
        f"| 🚀 Daily Growth | {daily:.1f} stars/day |",
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
    # Cleanup old dedup records
    cleanup_old_records()

    print("=" * 60)
    print("  GitHub Discovery Tool")
    print("  Finding repos before they go viral")
    # Cleanup old dedup records
    cleanup_old_records()

    print("=" * 60)
    print()

    # Init database
    init_db()

    # Fetch from all sources
    all_repos = fetch_all()

    if not all_repos:
        print("[ERROR] No repos found from any source. Check network/API.")
        sys.exit(1)

    # Score and filter
    new_scored = []
    repeat_scored = []
    # Load user feedback
    all_feedback = get_all_feedback()

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

    # 代码质量检测 + Star 真实性检测（仅对高潜力仓库）
    quality_checked = set()
    for repo in all_repos[:30]:  # 只检测前 30 个，避免 API 限流
        full_name = repo["full_name"]
        stars = repo.get("stars", 0)
        age_days = repo.get("age_days", 1)

        # 代码质量
        try:
            quality = check_quality(full_name)
            repo["quality_score"] = quality["quality_score"]
            repo["has_readme"] = quality.get("has_readme", False)
            repo["has_license"] = quality.get("has_license", False)
            repo["has_ci"] = quality.get("has_ci", False)
        except Exception as e:
            repo["quality_score"] = 0

        # Star 真实性检测
        try:
            auth = check_star_authenticity(full_name, stars, age_days)
            repo["star_suspicious"] = auth["is_suspicious"]
            repo["star_penalty"] = auth.get("penalty", 0)
            if auth["is_suspicious"]:
                print(f"  ⚠️ Suspicious stars: {full_name} ({auth['reason']})")
        except Exception:
            repo["star_suspicious"] = False
            repo["star_penalty"] = 0

        quality_checked.add(full_name)

    for repo in all_repos:
        scores = calculate_score(repo)
        
        # 代码质量加分
        quality_bonus = repo.get("quality_score", 0)
        if quality_bonus:
            scores["total"] = min(100, scores["total"] + quality_bonus)
            scores["quality_bonus"] = quality_bonus
        
        # Star 可疑扣分
        star_penalty = repo.get("star_penalty", 0)
        if star_penalty:
            scores["total"] = max(0, scores["total"] + star_penalty)
            scores["star_penalty"] = star_penalty
        
        # 用户反馈调整
        fb = all_feedback.get(repo["full_name"], {})
        fb_score = fb.get("score", 0)
        if fb_score > 0:
            scores["total"] = min(100, scores["total"] + min(10, fb_score * 2))
            scores["feedback_boost"] = fb_score
        elif fb_score < 0:
            scores["total"] = max(0, scores["total"] + max(-10, fb_score * 2))
            scores["feedback_penalty"] = fb_score

        if repo_exists(repo["id"]):
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

    # Save to database
    for repo, scores in top_new:
        save_repo(repo, scores["total"], repo.get("source", "unknown"))
        record_recommendation(repo["full_name"], scores["total"])
    save_run(len(new_scored), top_new[0][1]["total"] if top_new else 0)

    # Generate and output markdown
    md = generate_markdown(top_new, top_repeat)
    print(md)

    # Save to file
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    out_path = os.path.join(OUTPUT_DIR, f"discovery-{date_str}.md")
    with open(out_path, "w") as f:
        f.write(md)
    print(f"\n[Saved] Report written to {out_path}")

    # Send email via Buttondown
    date_str = datetime.now().strftime("%Y-%m-%d")
    send_buttondown_email(date_str, top_new)

    # Print compact summary
    print("\n" + "=" * 60)
    print("  TOP PICKS SUMMARY")
    # Cleanup old dedup records
    cleanup_old_records()

    print("=" * 60)
    for i, (repo, scores) in enumerate(top_new[:5], 1):
        print(f"  {i}. {repo['full_name']:40s} ⭐{repo['stars']:>6,}  📊{scores['total']:>3}/100")
    if len(top_new) > 5:
        print(f"  ... and {len(top_new) - 5} more")


if __name__ == "__main__":
    main()
