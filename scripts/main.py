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


def get_buttondown_subscribers() -> list[str]:
    """Fetch confirmed subscriber emails from Buttondown using curl."""
    if not BUTTONDOWN_API_KEY:
        return []
    emails = []
    url = "https://api.buttondown.com/v1/subscribers?status=active"
    while url:
        try:
            result = subprocess.run(
                ["curl", "-s", url, "-H", f"Authorization: Token {BUTTONDOWN_API_KEY}"],
                capture_output=True, text=True, timeout=15,
            )
            data = json.loads(result.stdout)
            for sub in data.get("results", data) if isinstance(data, dict) else data:
                email = sub.get("email", "") if isinstance(sub, dict) else ""
                if email:
                    emails.append(email)
            url = data.get("next") if isinstance(data, dict) else None
        except Exception as e:
            print(f"[WARN] Buttondown subscribers fetch failed: {e}")
            break
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
    # 1. Get subscribers from Buttondown
    subscribers = get_buttondown_subscribers()
    if not subscribers:
        print("[SKIP] No subscribers found.")
        return False
    print(f"[INFO] Found {len(subscribers)} subscribers.")

    # 2. Build email body
    top5_lines = []
    for i, (repo, scores) in enumerate(top_new[:5], 1):
        name = repo['full_name']
        url = repo['url']
        stars = repo.get('stars', 0)
        desc = (repo.get('description') or 'No description')[:80]
        top5_lines.append(f"{i}. <b><a href=\"{url}\">{name}</a></b> — ⭐{stars:,} — {desc}")

    top5_html = "<br>".join(top5_lines)
    total = len(top_new)

    html_body = f"""<div style="font-family:monospace;background:#0a0a0f;color:#c0c0d0;padding:24px;max-width:600px;margin:0 auto;">
<h2 style="color:#00ffff;">🔥 GitHub Discovery — {date_str}</h2>
<p><b>{total} new repos</b> discovered today. Top 5:</p>
<p>{top5_html}</p>
<hr style="border-color:#00ffff33;">
<p><a href="https://alloevil.github.io/github-discovery/" style="color:#00ffff;">View full report →</a></p>
<p style="color:#666;font-size:12px;">Sent by <a href="https://github.com/alloevil/github-discovery" style="color:#888;">GitHub Discovery</a></p>
</div>"""

    # 3. Send via Resend
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
    print("=" * 60)
    print("  GitHub Discovery Tool")
    print("  Finding repos before they go viral")
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
    for repo in all_repos:
        scores = calculate_score(repo)
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
    print("=" * 60)
    for i, (repo, scores) in enumerate(top_new[:5], 1):
        print(f"  {i}. {repo['full_name']:40s} ⭐{repo['stars']:>6,}  📊{scores['total']:>3}/100")
    if len(top_new) > 5:
        print(f"  ... and {len(top_new) - 5} more")


if __name__ == "__main__":
    main()
