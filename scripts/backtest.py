"""Backtest — does the score predict anything?

The question this answers is not "is the arithmetic right" (that is `verify_scoring.py`) but "did the
repos we scored highest actually break out?". It needs a label, and a label needs two readings of the
same repo: where it stood when we recommended it, and where it stood seven days later. The second
reading is what `watchlist.py` collects, because the older snapshot store only covered repos that kept
re-appearing in the candidate pool (measured 2026-09-14: 29 of 463 recommendations, 6.3%).

Everything here is computed from committed files — the daily JSON reports, `data/watch_series.json`,
`data/star_snapshots.json` and the trending snapshots — so anyone can re-derive the tables:

    reports/backtest-YYYY-MM-DD.csv   one row per labelled recommendation
    reports/backtest-YYYY-MM-DD.md    the summary, with the sample size next to every rate

Three deliberate choices:

* **A 200% seven-day rise is the primary label.** The roadmap's alternative — "top 5% of growth" —
  needs a cohort of at least 20 to mean anything, and a day's recommendation list is about eleven
  repos, so a 5% cut would select half a repo. The pooled quartile is reported alongside it instead.
* **Rates carry their N, and thin buckets say so.** A 100% breakout rate over two repos is noise, and
  printing it without the sample size is how a backtest becomes marketing.
* **Lead time is measured forward only.** Trending history cannot be reconstructed, so the comparison
  starts when the snapshots start and the report states how many days of it exist.
"""

import csv
import json
import statistics
import sys
from datetime import datetime, timedelta
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
REPORTS = Path(__file__).parent.parent / "reports"

LABEL_DAYS = 7
BREAKOUT_PCT = 200.0        # ≥ 200% growth in LABEL_DAYS is the primary label
MIN_BUCKET_N = 20           # below this, a rate is printed but marked as insufficient
BUCKETS = [(90, 101, "90–100"), (80, 90, "80–89"), (70, 80, "70–79"),
           (60, 70, "60–69"), (0, 60, "<60")]


def _load(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    return default


def recommendations() -> list[dict]:
    """Every recommendation, once per repo, with the score it had the first time we showed it."""
    out: dict[str, dict] = {}
    for path in sorted(DATA.glob("discovery-*.json")):
        doc = _load(path, {})
        day = doc.get("date") or path.stem.replace("discovery-", "")
        for bucket in ("new", "repeat"):
            for item in doc.get(bucket) or []:
                name = item.get("full_name")
                if not name or name in out:
                    continue  # first recommendation is the one a label is measured from
                out[name] = {
                    "repo": name,
                    "first_seen": day,
                    "score": (item.get("scores") or {}).get("total"),
                    "acceleration": (item.get("scores") or {}).get("acceleration"),
                    "quality": (item.get("scores") or {}).get("quality"),
                    "antispam": (item.get("scores") or {}).get("antispam"),
                    "sources": "+".join(item.get("sources") or []),
                    "stars_at_discovery": item.get("stars"),
                    "age_days": item.get("age_days"),
                }
    return sorted(out.values(), key=lambda r: r["first_seen"])


def _readings(name: str, series: dict, snaps: dict) -> list[tuple[str, int]]:
    """All (date, stars) readings for a repo, from the watch series and the older snapshot store."""
    points = [(p["date"], p["stars"]) for p in series.get(name, []) if "date" in p and "stars" in p]
    points += [(p[0], p[1]) for p in snaps.get(name, []) if isinstance(p, list) and len(p) == 2]
    return sorted(set(points))


def latest_observation(name: str, series: dict) -> dict:
    points = series.get(name) or []
    return points[-1] if points else {}


def label(rows: list[dict], series: dict, snaps: dict) -> list[dict]:
    """Attach the seven-day label where the data can support it."""
    for row in rows:
        target = (datetime.strptime(row["first_seen"], "%Y-%m-%d")
                  + timedelta(days=LABEL_DAYS)).strftime("%Y-%m-%d")
        readings = _readings(row["repo"], series, snaps)
        later = [(d, s) for d, s in readings if d >= target]
        start = row["stars_at_discovery"]
        obs = latest_observation(row["repo"], series)
        row["label_date"] = later[0][0] if later else ""
        row["stars_at_label"] = later[0][1] if later else ""
        row["commits_7d_at_label"] = obs.get("commits_7d", "")
        row["open_issues_at_label"] = obs.get("open_issues", "")
        if later and start:
            growth = 100.0 * (later[0][1] - start) / start if start else 0.0
            row["growth_pct"] = round(growth, 1)
            row["breakout"] = int(growth >= BREAKOUT_PCT)
        else:
            row["growth_pct"] = ""
            row["breakout"] = ""
    return rows


def _bucket(score) -> str:
    for lo, hi, name in BUCKETS:
        if score is not None and lo <= score < hi:
            return name
    return "unknown"


def summarise(rows: list[dict]) -> dict:
    labelled = [r for r in rows if r["breakout"] != ""]
    growths = [r["growth_pct"] for r in labelled]
    # 池化四分位：绝对阈值之外的第二个标签，用全样本而不是当日小队
    quartile_cut = (statistics.quantiles([r["growth_pct"] for r in labelled], n=4)[2]
                    if len(labelled) >= 8 else None)
    if quartile_cut is not None:
        for r in labelled:
            r["breakout_top_quartile"] = int(r["growth_pct"] >= quartile_cut)

    table = []
    for _lo, _hi, name in BUCKETS:
        bucket = [r for r in labelled if _bucket(r["score"]) == name]
        table.append({
            "bucket": name,
            "n": len(bucket),
            "breakout_rate": round(100 * sum(r["breakout"] for r in bucket) / len(bucket), 1)
            if bucket else None,
            "median_growth": round(statistics.median(r["growth_pct"] for r in bucket), 1)
            if bucket else None,
            "insufficient": len(bucket) < MIN_BUCKET_N,
        })
    unlabelled = [r for r in rows if r["breakout"] == ""]
    return {
        "recommendations": len(rows),
        "labelled": len(labelled),
        "coverage_pct": round(100 * len(labelled) / len(rows), 1) if rows else 0.0,
        "median_growth": round(statistics.median(growths), 1) if growths else None,
        "quartile_cut_pct": round(quartile_cut, 1) if quartile_cut is not None else None,
        "table": table,
        "unlabelled": len(unlabelled),
        "min_bucket_n": MIN_BUCKET_N,
    }


def lead_time(rows: list[dict]) -> dict:
    """How many days before the trending snapshots did we recommend these repos?

    Forward-only: trending history cannot be reconstructed, so the answer is limited to repos we
    recommended after the snapshots began, and the report says how much history exists.
    """
    snapshots = sorted(DATA.glob("trending-*.json"))
    first_seen: dict[str, str] = {}
    for path in snapshots:
        doc = _load(path, {})
        day = doc.get("date") or path.stem.replace("trending-", "")
        for item in doc.get("repos") or []:
            name = item.get("full_name")
            if name and name not in first_seen:
                first_seen[name] = day
    leads = []
    for row in rows:
        t = first_seen.get(row["repo"])
        if t and t > row["first_seen"]:
            leads.append((datetime.strptime(t, "%Y-%m-%d")
                          - datetime.strptime(row["first_seen"], "%Y-%m-%d")).days)
    return {
        "trending_days": len(snapshots),
        "matched": len(leads),
        "median_lead_days": statistics.median(leads) if leads else None,
        "max_lead_days": max(leads) if leads else None,
    }


def render(rows: list[dict], stats: dict, leads: dict, today: str) -> str:
    lines = [
        f"# Backtest — {today}",
        "",
        f"Every recommendation across {stats['recommendations']} repos, each labelled with the star "
        f"reading {LABEL_DAYS} days after we first showed it. **{stats['labelled']} are labelled "
        f"({stats['coverage_pct']}%)** — a rate computed on the rest would be a guess, so the "
        f"unlabelled {stats['unlabelled']} are excluded rather than defaulted to “no breakout”.",
        "",
        f"Label: a repo *broke out* if it gained ≥ {BREAKOUT_PCT:.0f}% in {LABEL_DAYS} days "
        f"(median growth across labelled repos: {stats['median_growth']}%).",
        "",
        "| score at discovery | repos | breakout rate | median growth | sample |",
        "|---|---:|---:|---:|---|",
    ]
    for row in stats["table"]:
        rate = "—" if row["breakout_rate"] is None else f"{row['breakout_rate']}%"
        med = "—" if row["median_growth"] is None else f"{row['median_growth']}%"
        note = f"thin (n<{stats['min_bucket_n']})" if row["insufficient"] and row["n"] else ""
        lines.append(f"| {row['bucket']} | {row['n']} | {rate} | {med} | {note} |")
    lines += [
        "",
        "A rate over fewer than "
        f"{stats['min_bucket_n']} repos is printed but marked thin: at this sample size it moves by "
        "tens of points when one repo moves.",
        "",
        "### Lead time vs GitHub Trending",
        "",
        f"- trending snapshots so far: **{leads['trending_days']} day(s)** (the comparison is "
        "forward-only — trending history cannot be reconstructed)",
        f"- repos we recommended *before* they appeared in a snapshot: **{leads['matched']}**",
    ]
    if leads["median_lead_days"] is not None:
        lines.append(f"- median lead: **{leads['median_lead_days']} day(s)**, max "
                     f"{leads['max_lead_days']}")
    else:
        lines.append("- median lead: not yet measurable — no recommended repo has appeared in a "
                     "snapshot yet")
    lines += ["", "### Maintenance signals for labelled repos", ""]
    obs = [r for r in rows if r.get("commits_7d_at_label") != "" and r["commits_7d_at_label"] is not None]
    if obs:
        idle = sum(1 for r in obs if r["commits_7d_at_label"] == 0)
        issues = [r["open_issues_at_label"] for r in obs if r.get("open_issues_at_label") is not None]
        lines += [
            f"- repos with observations: **{len(obs)}**",
            f"- commits_7d == 0 at the latest observation: **{idle}** "
            f"({round(100 * idle / len(obs), 1)}%) — high stars with no commits is attention "
            "without adoption",
            f"- median open issues at the latest observation: "
            f"**{statistics.median(issues) if issues else '—'}**",
        ]
    else:
        lines.append("- no follow-up observations yet")
    lines += ["", "### Raw data", "",
              f"- `reports/backtest-{today}.csv` — one row per recommendation with score, label and "
              "observation fields", ""]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    if "--date" in argv:
        today = argv[argv.index("--date") + 1]
    series = _load(DATA / "watch_series.json", {"repos": {}}).get("repos", {})
    snaps = _load(DATA / "star_snapshots.json", {"repos": {}}).get("repos", {})
    rows = label(recommendations(), series, snaps)
    stats = summarise(rows)
    leads = lead_time(rows)

    REPORTS.mkdir(parents=True, exist_ok=True)
    fields = ["repo", "first_seen", "score", "acceleration", "quality", "antispam", "sources",
              "stars_at_discovery", "age_days", "label_date", "stars_at_label", "growth_pct",
              "breakout", "commits_7d_at_label", "open_issues_at_label"]
    csv_path = REPORTS / f"backtest-{today}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    md_path = REPORTS / f"backtest-{today}.md"
    md_path.write_text(render(rows, stats, leads, today), encoding="utf-8")

    print(f"[Backtest] {stats['labelled']}/{stats['recommendations']} recommendations labelled "
          f"({stats['coverage_pct']}%) · median growth {stats['median_growth']}%")
    for row in stats["table"]:
        if row["n"]:
            print(f"[Backtest]   score {row['bucket']:<7} n={row['n']:<4} "
                  f"breakout {row['breakout_rate']}%{' (thin)' if row['insufficient'] else ''}")
    print(f"[Backtest] trending snapshots {leads['trending_days']} day(s) · matched {leads['matched']} "
          f"· median lead {leads['median_lead_days']}")
    print(f"[Backtest] wrote {csv_path.name} and {md_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
