"""Historical cohort analysis for mature GitHub Discovery recommendations.

This is intentionally separate from scripts/backtest.py: the backtest remains the canonical
row-level label generator, while this report adds source-cohort summaries without changing labels.
"""

from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime
from pathlib import Path

import backtest


REPORTS = Path(__file__).resolve().parent.parent / "reports"


def source_summary(rows: list[dict]) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for row in rows:
        if row.get("breakout") == "":
            continue
        groups.setdefault(row.get("sources") or "unknown", []).append(row)
    result = []
    for source, group in sorted(groups.items()):
        result.append({
            "source": source,
            "n": len(group),
            "breakout_rate": round(100 * sum(r["breakout"] for r in group) / len(group), 1),
            "median_growth": round(statistics.median(r["growth_pct"] for r in group), 1),
            "insufficient": len(group) < backtest.MIN_BUCKET_N,
        })
    return result

AGE_BUCKETS = ((0, 3, "0–2d"), (3, 14, "3–13d"), (14, 60, "14–59d"), (60, 10**9, "60d+"))
STAR_BUCKETS = ((0, 100, "0–99"), (100, 1000, "100–999"), (1000, 10000, "1k–9.9k"), (10000, 10**18, "10k+"))


def _bucket(value, buckets: tuple[tuple[int, int, str], ...]) -> str:
    if value is None:
        return "unknown"
    for low, high, name in buckets:
        if low <= value < high:
            return name
    return "unknown"


def controlled_summary(rows: list[dict], field: str, buckets: tuple[tuple[int, int, str], ...]) -> list[dict]:
    """Summarise mature labels by one confounder; thin groups stay visibly thin."""
    groups: dict[str, list[dict]] = {}
    for row in rows:
        if row.get("breakout") == "":
            continue
        value = row.get(field)
        if value is not None:
            value = float(value)
        groups.setdefault(_bucket(value, buckets), []).append(row)
    result = []
    for bucket, group in groups.items():
        result.append({
            "bucket": bucket,
            "n": len(group),
            "breakout_rate": round(100 * sum(r["breakout"] for r in group) / len(group), 1),
            "median_growth": round(statistics.median(r["growth_pct"] for r in group), 1),
            "insufficient": len(group) < backtest.MIN_BUCKET_N,
        })
    order = {name: i for i, (_low, _high, name) in enumerate(buckets)}
    return sorted(result, key=lambda row: order.get(row["bucket"], len(order)))


def render(today: str, stats: dict, source_groups: list[dict], age_groups: list[dict], star_groups: list[dict]) -> str:
    lines = [
        f"# Mature recommendation analysis — {today}",
        "",
        f"This report covers **{stats['labelled']} of {stats['recommendations']} recommendations** "
        f"({stats['coverage_pct']}%) with a {backtest.LABEL_DAYS}-day reading. Unlabelled rows are "
        "excluded, not treated as failures.",
        "",
        "## Score cohorts",
        "",
        "| Score | Mature repos | Breakout rate | Median growth | Note |",
        "|---|---:|---:|---:|---|",
    ]
    for row in stats["table"]:
        rate = "—" if row["breakout_rate"] is None else f"{row['breakout_rate']}%"
        growth = "—" if row["median_growth"] is None else f"{row['median_growth']}%"
        note = f"thin (n<{stats['min_bucket_n']})" if row["insufficient"] and row["n"] else ""
        lines.append(f"| {row['bucket']} | {row['n']} | {rate} | {growth} | {note} |")

    def add_groups(title: str, groups: list[dict], label_key: str) -> None:
        lines.extend(["", f"## {title}", "", "| Cohort | Mature repos | Breakout rate | Median growth | Note |", "|---|---:|---:|---:|---|"])
        for row in groups:
            note = f"thin (n<{backtest.MIN_BUCKET_N})" if row["insufficient"] else ""
            lines.append(f"| {row[label_key]} | {row['n']} | {row['breakout_rate']}% | {row['median_growth']}% | {note} |")

    add_groups("Source cohorts", source_groups, "source")
    add_groups("Recommendation-time age cohorts", age_groups, "bucket")
    add_groups("Recommendation-time star cohorts", star_groups, "bucket")
    lines += [
        "",
        "## Interpretation guardrails",
        "",
        f"- Mature coverage is **{stats['coverage_pct']}%**; the remaining {stats['unlabelled']} recommendations are unknown, not negative labels.",
        f"- A cohort below {stats['min_bucket_n']} mature repos is marked thin and is not a basis for changing weights or adding a source.",
        "- Source cohorts are descriptive associations. Age and starting-star tables reduce obvious confounding but do not establish incremental or causal source value.",
        "",
    ]
    return "\n".join(lines)
def build_report(today: str) -> tuple[str, dict]:
    series = backtest._load(backtest.DATA / "watch_series.json", {"repos": {}}).get("repos", {})
    snapshots = backtest._load(backtest.DATA / "star_snapshots.json", {"repos": {}}).get("repos", {})
    rows = backtest.label(backtest.recommendations(), series, snapshots)
    stats = backtest.summarise(rows)
    groups = source_summary(rows)
    age_groups = controlled_summary(rows, "age_days", AGE_BUCKETS)
    star_groups = controlled_summary(rows, "stars_at_discovery", STAR_BUCKETS)
    return render(today, stats, groups, age_groups, star_groups), {
        "date": today,
        "stats": stats,
        "source_groups": groups,
        "age_groups": age_groups,
        "star_groups": star_groups,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    markdown, payload = build_report(args.date)
    REPORTS.mkdir(parents=True, exist_ok=True)
    output = args.output or REPORTS / f"mature-analysis-{args.date}.md"
    output.write_text(markdown, encoding="utf-8")
    (output.with_suffix(".json")).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"mature analysis: {payload['stats']['labelled']}/{payload['stats']['recommendations']} labelled; wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
