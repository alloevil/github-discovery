#!/usr/bin/env python3
"""Scoring Verification & Backtest Module for GitHub Discovery.

Reads historical recommendations from the database, queries current GitHub
star counts, calculates growth rates, and evaluates whether high-scored
repos actually became popular.

Usage:
    python3 scripts/verify_scoring.py                  # full backtest
    python3 scripts/verify_scoring.py --days 30        # last 30 days only
    python3 scripts/verify_scoring.py --output report.json  # save JSON report
"""

import argparse
import json
import os
import sqlite3
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

# Ensure sibling imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import GITHUB_API, DB_PATH, GITHUB_TOKEN


# ── Constants ────────────────────────────────────────────────────────────────

GROWTH_THRESHOLD = 0.10  # 10% star growth = "took off"
SCORE_HIGH = 90          # score >= this is considered "high confidence"

# Mutable module-level — updated via CLI args
_threshold_override = None
_score_high_override = None


# ── GitHub API ───────────────────────────────────────────────────────────────

def _gh_headers() -> dict:
    h = {"Accept": "application/vnd.github+json", "User-Agent": "github-discovery-verify"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


def fetch_current_stars(full_name: str) -> dict | None:
    """Fetch current star count and metadata for a repo via GitHub API.

    Returns dict with keys: stars, forks, open_issues, pushed_at, watchers
    or None on failure.
    """
    url = f"{GITHUB_API}/repos/{full_name}"
    req = urllib.request.Request(url, headers=_gh_headers())
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return {
                "stars": data.get("stargazers_count", 0),
                "forks": data.get("forks_count", 0),
                "open_issues": data.get("open_issues_count", 0),
                "pushed_at": data.get("pushed_at", ""),
                "archived": data.get("archived", False),
                "description": data.get("description", ""),
            }
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"  ⚠️  {full_name}: repo deleted or renamed (404)")
        elif e.code == 403:
            print(f"  ⚠️  {full_name}: rate limited (403)")
        else:
            print(f"  ⚠️  {full_name}: HTTP {e.code}")
        return None
    except Exception as e:
        print(f"  ⚠️  {full_name}: {e}")
        return None


# ── Data Loading ─────────────────────────────────────────────────────────────

def load_repos_from_db(days: int | None = None) -> list[dict]:
    """Load historical recommendations from the SQLite database.

    Args:
        days: If set, only return repos discovered within the last N days.

    Returns:
        List of dicts with keys: full_name, url, stars_at_discovery,
        score, discovered_at, created_at, language, source
    """
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found: {DB_PATH}")
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    query = "SELECT * FROM repos"
    params = []
    if days:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        query += " WHERE discovered_at >= ?"
        params.append(cutoff)
    query += " ORDER BY discovered_at DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    repos = []
    for r in rows:
        repos.append({
            "full_name": r["full_name"],
            "url": r["url"],
            "stars_at_discovery": r["stars"],
            "score": r["score"],
            "discovered_at": r["discovered_at"],
            "created_at": r["created_at"],
            "language": r["language"],
            "source": r["source"],
        })
    return repos


# ── Analysis ─────────────────────────────────────────────────────────────────

def analyze_repo(entry: dict, current: dict) -> dict:
    """Compare discovered state vs current state for one repo."""
    stars_before = entry["stars_at_discovery"]
    stars_now = current["stars"]
    delta = stars_now - stars_before
    growth_rate = delta / stars_before if stars_before > 0 else 0.0

    days_since = (datetime.now(timezone.utc) - datetime.fromisoformat(
        entry["discovered_at"].replace(" ", "T") + "+00:00"
        if "+" not in entry["discovered_at"] and "Z" not in entry["discovered_at"]
        else entry["discovered_at"].replace(" ", "T").replace("Z", "+00:00")
    )).days
    if days_since < 1:
        days_since = 1

    daily_growth = delta / days_since

    return {
        "full_name": entry["full_name"],
        "url": entry["url"],
        "language": entry["language"],
        "source": entry["source"],
        "score": entry["score"],
        "discovered_at": entry["discovered_at"],
        "created_at": entry["created_at"],
        "days_since_discovery": days_since,
        "stars_at_discovery": stars_before,
        "stars_now": stars_now,
        "star_delta": delta,
        "growth_rate": round(growth_rate, 4),
        "daily_growth": round(daily_growth, 2),
        "took_off": growth_rate >= (_threshold_override or GROWTH_THRESHOLD),
        "archived": current.get("archived", False),
        "current_description": current.get("description", ""),
        "pushed_at": current.get("pushed_at", ""),
    }


def compute_metrics(results: list[dict]) -> dict:
    """Compute aggregate accuracy metrics for the scoring system."""
    score_high = _score_high_override or SCORE_HIGH
    growth_thr = _threshold_override or GROWTH_THRESHOLD

    if not results:
        return {"total": 0, "error": "no data"}

    total = len(results)
    high_score = [r for r in results if r["score"] >= score_high]
    low_score = [r for r in results if r["score"] < score_high]

    took_off = [r for r in results if r["took_off"]]
    high_took_off = [r for r in high_score if r["took_off"]]
    low_took_off = [r for r in low_score if r["took_off"]]

    avg_growth_all = sum(r["growth_rate"] for r in results) / total if total else 0
    avg_growth_high = (sum(r["growth_rate"] for r in high_score) / len(high_score)
                       if high_score else 0)
    avg_growth_low = (sum(r["growth_rate"] for r in low_score) / len(low_score)
                      if low_score else 0)

    avg_daily_all = sum(r["daily_growth"] for r in results) / total if total else 0

    # Precision: of all high-score repos, how many actually took off
    precision = len(high_took_off) / len(high_score) if high_score else 0

    # Recall: of all repos that took off, how many were high-scored
    recall = len(high_took_off) / len(took_off) if took_off else 0

    # F1
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    # Lift: how much better is high-score vs low-score
    lift = avg_growth_high / avg_growth_low if avg_growth_low > 0 else float("inf")

    return {
        "total_repos": total,
        "high_score_count": len(high_score),
        "low_score_count": len(low_score),
        "took_off_count": len(took_off),
        "took_off_rate": round(len(took_off) / total, 4) if total else 0,
        "high_score_took_off_count": len(high_took_off),
        "high_score_precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "lift": round(lift, 2) if lift != float("inf") else "inf",
        "avg_growth_rate_all": round(avg_growth_all, 4),
        "avg_growth_rate_high_score": round(avg_growth_high, 4),
        "avg_growth_rate_low_score": round(avg_growth_low, 4),
        "avg_daily_growth": round(avg_daily_all, 2),
        "best_performer": _best(results),
        "worst_performer": _worst(results),
        "score_threshold": score_high,
        "growth_threshold": growth_thr,
    }


def _best(results: list[dict]) -> dict | None:
    if not results:
        return None
    r = max(results, key=lambda x: x["growth_rate"])
    return {"full_name": r["full_name"], "growth_rate": r["growth_rate"],
            "stars_at_discovery": r["stars_at_discovery"], "stars_now": r["stars_now"],
            "score": r["score"]}


def _worst(results: list[dict]) -> dict | None:
    if not results:
        return None
    r = min(results, key=lambda x: x["growth_rate"])
    return {"full_name": r["full_name"], "growth_rate": r["growth_rate"],
            "stars_at_discovery": r["stars_at_discovery"], "stars_now": r["stars_now"],
            "score": r["score"]}


# ── Console Output ───────────────────────────────────────────────────────────

def print_summary(results: list[dict], metrics: dict, days: int | None):
    """Print a human-readable summary to the console."""
    border = "═" * 72
    print(f"\n{border}")
    print("  📊  GitHub Discovery — Scoring Verification Report")
    if days:
        print(f"  Period: last {days} days")
    else:
        print("  Period: all time")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(border)

    # Metrics table
    print(f"\n  {'Metric':<40} {'Value':>12}")
    print(f"  {'─' * 40} {'─' * 12}")
    print(f"  {'Total repos analyzed':<40} {metrics['total_repos']:>12}")
    print(f"  {'High-score repos (≥{})'.format(metrics['score_threshold']):<40} {metrics['high_score_count']:>12}")
    print(f"  {'Repos that took off (≥{})'.format(int(metrics['growth_threshold']*100))+'% growth':<40} {metrics['took_off_count']:>12}")
    print(f"  {'Overall took-off rate':<40} {metrics['took_off_rate']:>11.1%}")
    print(f"  {'High-score precision':<40} {metrics['high_score_precision']:>11.1%}")
    print(f"  {'Recall':<40} {metrics['recall']:>11.1%}")
    print(f"  {'F1 Score':<40} {metrics['f1_score']:>12.3f}")
    lift = metrics['lift']
    lift_str = f"{lift:.2f}x" if isinstance(lift, float) else str(lift)
    print(f"  {'Lift (high vs low)':<40} {lift_str:>12}")
    print(f"  {'Avg growth (all)':<40} {metrics['avg_growth_rate_all']:>11.1%}")
    print(f"  {'Avg growth (high-score)':<40} {metrics['avg_growth_rate_high_score']:>11.1%}")
    print(f"  {'Avg growth (low-score)':<40} {metrics['avg_growth_rate_low_score']:>11.1%}")
    print(f"  {'Avg daily star gain':<40} {metrics['avg_daily_growth']:>12.1f}")

    # Best / Worst
    bp = metrics.get("best_performer")
    wp = metrics.get("worst_performer")
    if bp:
        print(f"\n  🏆 Best:  {bp['full_name']}")
        print(f"     {bp['stars_at_discovery']} → {bp['stars_now']} stars "
              f"(+{bp['growth_rate']:.0%}), score={bp['score']}")
    if wp:
        print(f"  📉 Worst: {wp['full_name']}")
        print(f"     {wp['stars_at_discovery']} → {wp['stars_now']} stars "
              f"({wp['growth_rate']:+.0%}), score={wp['score']}")

    # Detailed table
    print(f"\n  {'#':<3} {'Repo':<42} {'Score':>5} {'Before':>7} {'Now':>7} {'Δ':>6} {'Growth':>7} {'OK?':>4}")
    print(f"  {'─'*3} {'─'*42} {'─'*5} {'─'*7} {'─'*7} {'─'*6} {'─'*7} {'─'*4}")
    for i, r in enumerate(sorted(results, key=lambda x: x["score"], reverse=True), 1):
        flag = "✅" if r["took_off"] else "❌"
        name = r["full_name"][:40]
        print(f"  {i:<3} {name:<42} {r['score']:>5.0f} {r['stars_at_discovery']:>7,} "
              f"{r['stars_now']:>7,} {r['star_delta']:>+6,} {r['growth_rate']:>+6.0%} {flag:>4}")

    print(f"\n{border}\n")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Verify GitHub Discovery scoring accuracy")
    parser.add_argument("--days", type=int, default=None,
                        help="Only backtest repos discovered in the last N days")
    parser.add_argument("--output", type=str, default=None,
                        help="Save JSON report to this path")
    parser.add_argument("--json", action="store_true",
                        help="Print JSON report to stdout instead of console summary")
    parser.add_argument("--threshold", type=float, default=GROWTH_THRESHOLD,
                        help=f"Growth rate threshold to count as 'took off' (default: {GROWTH_THRESHOLD})")
    parser.add_argument("--score-high", type=float, default=SCORE_HIGH,
                        help=f"Score threshold for 'high confidence' (default: {SCORE_HIGH})")
    args = parser.parse_args()

    global _threshold_override, _score_high_override
    _threshold_override = args.threshold
    _score_high_override = args.score_high

    # Load historical data
    repos = load_repos_from_db(days=args.days)
    if not repos:
        print("[ERROR] No repos found in database. Run main.py first.")
        sys.exit(1)

    print(f"[INFO] Loaded {len(repos)} repos from database")
    if args.days:
        print(f"[INFO] Filtering: last {args.days} days")

    # Fetch current state from GitHub
    results = []
    for i, entry in enumerate(repos, 1):
        name = entry["full_name"]
        print(f"  [{i}/{len(repos)}] Querying {name}...", end=" ", flush=True)
        current = fetch_current_stars(name)
        if current is None:
            print("skipped")
            continue
        result = analyze_repo(entry, current)
        results.append(result)
        print(f"⭐{current['stars']:,} (was {entry['stars_at_discovery']:,}, "
              f"Δ{result['star_delta']:+,}, {result['growth_rate']:+.0%})")

    if not results:
        print("[ERROR] No repos could be verified (all API calls failed).")
        sys.exit(1)

    # Compute metrics
    metrics = compute_metrics(results)

    # Build report
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period_days": args.days,
        "parameters": {
            "growth_threshold": args.threshold,
            "score_high_threshold": args.score_high,
        },
        "metrics": metrics,
        "repos": sorted(results, key=lambda x: x["score"], reverse=True),
    }

    # Output
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_summary(results, metrics, args.days)

    # Save JSON report
    out_path = args.output
    if not out_path:
        # Default: save to project root's reports/ directory
        out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
        os.makedirs(out_dir, exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        out_path = os.path.join(out_dir, f"verify-{date_str}.json")

    with open(out_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"[Saved] JSON report: {out_path}")


if __name__ == "__main__":
    main()
