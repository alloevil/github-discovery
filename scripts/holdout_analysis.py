"""Time-split evaluation of the fixed recommendation policy.

This never tunes weights. It evaluates recommended candidates against eligible, non-selected
candidates after a date cutoff, once both sides have enough seven-day observations.
"""
from __future__ import annotations

import argparse
import glob
import json
from datetime import datetime, timedelta
from pathlib import Path

import backtest

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
REPORTS = ROOT / "reports"
LABEL_DAYS = backtest.LABEL_DAYS
HORIZONS = (1, 3, 7, 14)
FORMAL_HORIZON = 7


def load_candidate_rows(data_dir: Path = DATA) -> list[dict]:
    rows = []
    for path in sorted(data_dir.glob("candidate-pool-*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        date = doc.get("date") or path.stem.removeprefix("candidate-pool-")
        for candidate in doc.get("candidates") or []:
            row = dict(candidate)
            row["first_seen"] = date
            score = row.get("pool_score") or {}
            row["score"] = score.get("total")
            row["sources"] = "+".join(row.get("sources") or ([row.get("source")] if row.get("source") else []))
            row["stars_at_discovery"] = row.get("stars")
            rows.append(row)
    return rows


def label_candidates(rows: list[dict], series: dict, snapshots: dict, horizon: int) -> list[dict]:
    labelled = []
    for row in rows:
        name = row.get("full_name")
        start = row.get("stars_at_discovery")
        target = (datetime.strptime(row["first_seen"], "%Y-%m-%d") + timedelta(days=horizon)).strftime("%Y-%m-%d")
        readings = backtest._readings(name, series, snapshots)
        later = [(date, stars) for date, stars in readings if date >= target]
        row = dict(row)
        row["label_date"] = later[0][0] if later else ""
        row["growth_pct"] = round(100 * (later[0][1] - start) / start, 1) if later and start else ""
        row["breakout"] = int(row["growth_pct"] >= backtest.BREAKOUT_PCT) if row["growth_pct"] != "" else ""
        labelled.append(row)
    return labelled


def summarize(rows: list[dict]) -> dict:
    mature = [r for r in rows if r["breakout"] != ""]
    recommended = [r for r in mature if r.get("pool_status") == "recommended"]
    eligible = [r for r in mature if r.get("pool_status") == "eligible"]
    rec_rate = 100 * sum(r["breakout"] for r in recommended) / len(recommended) if recommended else None
    eligible_rate = 100 * sum(r["breakout"] for r in eligible) / len(eligible) if eligible else None
    return {
        "rows": len(rows), "mature": len(mature), "coverage_pct": round(100 * len(mature) / len(rows), 1) if rows else 0,
        "recommended_mature": len(recommended), "eligible_mature": len(eligible),
        "recommended_breakout_rate": round(rec_rate, 1) if rec_rate is not None else None,
        "eligible_breakout_rate": round(eligible_rate, 1) if eligible_rate is not None else None,
        "lift": round(rec_rate / eligible_rate, 2) if rec_rate is not None and eligible_rate else None,
    }


def evaluate(cutoff: str, data_dir: Path = DATA) -> dict:
    rows = load_candidate_rows(data_dir)
    series = json.loads((data_dir / "watch_series.json").read_text())["repos"] if (data_dir / "watch_series.json").exists() else {}
    snapshots = json.loads((data_dir / "star_snapshots.json").read_text())["repos"] if (data_dir / "star_snapshots.json").exists() else {}
    horizons = {}
    for horizon in HORIZONS:
        labelled = label_candidates(rows, series, snapshots, horizon)
        horizons[str(horizon)] = {
            "train": summarize([r for r in labelled if r["first_seen"] <= cutoff]),
            "holdout": summarize([r for r in labelled if r["first_seen"] > cutoff]),
            "interpretation": "formal" if horizon == FORMAL_HORIZON else "exploratory",
        }
    result = {"cutoff": cutoff, "horizons": horizons}
    result["train"] = horizons[str(FORMAL_HORIZON)]["train"]
    result["holdout"] = horizons[str(FORMAL_HORIZON)]["holdout"]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cutoff", required=True, help="Last training date; later pools are the holdout")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(args.cutoff)
    ready = result["horizons"][str(FORMAL_HORIZON)]["holdout"]["recommended_mature"] >= 20 and result["horizons"][str(FORMAL_HORIZON)]["holdout"]["eligible_mature"] >= 20
    result["status"] = "ready" if ready else "not-ready"
    output = args.output or REPORTS / f"holdout-{args.cutoff}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = ", ".join(f"{h}d={result['horizons'][str(h)]['holdout']['mature']}" for h in HORIZONS)
    print(f"holdout: {result['status']} ({summary}); 7d is formal, 1/3/14d exploratory; wrote {output}")
    return 0
    raise SystemExit(main())
