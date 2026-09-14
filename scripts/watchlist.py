"""Watch list — keep observing the repos we recommended, after the day we recommended them.

Why this exists. `star_snapshots.json` only gains a point for a repo on a day it *re-appears in the
candidate pool*, so its series stops the moment the repo stops being re-discovered. Measured on
2026-09-14 over the 44 committed discovery files: of 497 recommendations, **5 (1.0%)** had both the
discovery-day reading and a reading exactly seven days later, and **31 (6.2%)** had any later
reading at all. The one label that would make the score measurable — "did this repo break out?" —
cannot be computed from that, so the first thing this project needs is not a model. It is follow-up
observations.

Two committed files, both plain JSON, both reproducible:

    data/watchlist.json      who is being watched, and until when
    data/watch_series.json   what was observed, one record per repo per day

The watch list is *not* a re-ranking input. It only collects: stars, forks, open issues, commits in
the last 7 days, contributors, and the last push. Nothing here changes what is recommended — if it
did, the follow-up observations would be conditioned on the signal being measured.

Cost: three API calls per watched repo per run. The daily workflow already runs twice a day with a
token (5000 requests/hour), so the default cap of 300 repos is roughly a fifth of one hour's budget.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import API_DELAY, WATCH_DAYS, WATCH_LIMIT
from snapshots import record_snapshots, _today

DATA = Path(__file__).parent.parent / "data"
WATCHLIST_FILE = DATA / "watchlist.json"
SERIES_FILE = DATA / "watch_series.json"
DISCOVERY_GLOB = "discovery-*.json"

# A record must carry these; the series is what a backtest reads, so a half-written point is worse
# than a missing one.
FIELDS = ("date", "stars", "forks", "open_issues", "commits_7d", "contributors_7d", "pushed_at")


def _load(path: Path, default: dict) -> dict:
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (ValueError, OSError):
            pass
    return dict(default)


def _save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def _window_end(today: str, days: int = None) -> str:
    return (datetime.strptime(today, "%Y-%m-%d")
            + timedelta(days=days if days is not None else WATCH_DAYS)).strftime("%Y-%m-%d")


def add_discoveries(repos: list[dict], today: str = None) -> int:
    """Put today's recommendations on the watch list. Returns how many were added.

    A repo that was already watched keeps its original `first_seen`: the label is "did it break out
    after we found it", and moving the start date forward would quietly reset that clock.
    """
    today = today or _today()
    data = _load(WATCHLIST_FILE, {"repos": {}})
    store = data.setdefault("repos", {})
    added = 0
    for repo in repos:
        name = repo.get("full_name")
        if not name or name in store:
            continue
        store[name] = {
            "first_seen": today,
            "until": _window_end(today),
            "stars_at_discovery": repo.get("stars", 0),
            "score_at_discovery": (repo.get("scores") or {}).get("total"),
            "source_at_discovery": repo.get("source", ""),
        }
        added += 1
    if added:
        _save(WATCHLIST_FILE, data)
    return added


def backfill(days: int = None, today: str = None) -> int:
    """Adopt discoveries from the last N days into the watch list.

    Only worthwhile for discoveries still young enough to gain a 7-day reading inside their window,
    which is why the default is the window length and not "everything we ever found": an older repo
    cannot be observed retroactively, and pretending otherwise would inflate the coverage number
    this whole module exists to report honestly.
    """
    today = today or _today()
    days = WATCH_DAYS if days is None else days
    floor = _window_end(today, -days)
    found = {n: d for n, d in discoveries().items() if d >= floor}
    data = _load(WATCHLIST_FILE, {"repos": {}})
    store = data.setdefault("repos", {})
    added = 0
    for name, first in sorted(found.items(), key=lambda kv: kv[1]):
        if name in store:
            continue
        store[name] = {"first_seen": first, "until": _window_end(first),
                       "stars_at_discovery": None, "score_at_discovery": None,
                       "source_at_discovery": "", "backfilled": True}
        added += 1
    if added:
        _save(WATCHLIST_FILE, data)
    return added


def due(today: str = None, limit: int = None) -> list[str]:
    """Repos still inside their window whose day has not been recorded yet.

    Same-day reruns are free: a repo with today's record is not returned again.
    """
    today = today or _today()
    data = _load(WATCHLIST_FILE, {"repos": {}})
    series = _load(SERIES_FILE, {"repos": {}})
    out = []
    for name, meta in sorted(data.get("repos", {}).items()):
        if meta.get("until", "") < today:
            continue  # window over; pruned by prune_expired on the same run
        if any(p.get("date") == today for p in series.get("repos", {}).get(name, [])):
            continue
        out.append(name)
    cap = WATCH_LIMIT if limit is None else limit
    if cap and len(out) > cap:
        # Oldest window first: it is the one about to expire, and every extra day is label data.
        out.sort(key=lambda n: (data["repos"][n].get("until", ""), n))
        out = out[:cap]
    return out


def record(observations: list[dict], today: str = None) -> int:
    """Append today's observations. Rerunning the same day replaces that day's records."""
    today = today or _today()
    data = _load(SERIES_FILE, {"repos": {}})
    store = data.setdefault("repos", {})
    kept, rejected = 0, []
    for obs in observations:
        name = obs.get("full_name")
        missing = [k for k in FIELDS if k != "date" and k not in obs]
        if not name or missing:
            # 静默丢弃过一个本该进序列的点，代价是整轮观察变成"observed 0" —— 说出来
            rejected.append(f"{name or '?'}:{','.join(missing) or 'no-name'}")
            continue
        point = {"date": today, **{k: obs[k] for k in FIELDS if k != "date"}}
        history = [p for p in store.get(name, []) if p.get("date") != today]
        history.append(point)
        history.sort(key=lambda p: p["date"])
        store[name] = history
        kept += 1
    if kept:
        _save(SERIES_FILE, data)
    if rejected:
        print(f"[Watchlist]   rejected {len(rejected)} record(s): {rejected[:3]}")
    return kept


def prune_expired(today: str = None) -> int:
    """Drop repos whose window has closed. The series keeps their observations — that is the data."""
    today = today or _today()
    data = _load(WATCHLIST_FILE, {"repos": {}})
    store = data.setdefault("repos", {})
    expired = [n for n, m in store.items() if m.get("until", "") < today]
    for name in expired:
        del store[name]
    if expired:
        _save(WATCHLIST_FILE, data)
    return len(expired)


def discoveries(watch_days: int = 7) -> dict[str, str]:
    """{full_name: first discovery date} from the committed daily files."""
    seen: dict[str, str] = {}
    for path in sorted(DATA.glob(DISCOVERY_GLOB)):
        day = path.stem.replace("discovery-", "")
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        for key in ("new", "repeat"):
            for item in doc.get(key) or []:
                name = item.get("full_name")
                if name:
                    seen.setdefault(name, day)
    return seen


def _labelable(names, dates, series, watch_days: int) -> int:
    n = 0
    for name in names:
        target = _window_end(dates[name], watch_days)
        if any(p.get("date", "") >= target for p in series.get(name, [])):
            n += 1
    return n


def coverage(watch_days: int = 7) -> dict:
    """How many discoveries have the follow-up a 7-day label needs.

    This is the number that says whether a backtest is possible yet, and it is deliberately computed
    from committed files only, so anyone can re-derive it. Two sources are reported separately: the
    long-standing `star_snapshots.json` (a repo appears there only on days it re-entered the
    candidate pool, which is why coverage is low) and `watch_series.json`, the follow-up this module
    adds. A repo counts as labelable if either one has a reading at least `watch_days` after it was
    first recommended.
    """
    found = discoveries()
    watch = _load(SERIES_FILE, {"repos": {}}).get("repos", {})
    snaps = _load(DATA / "star_snapshots.json", {"repos": {}}).get("repos", {})
    snap_series = {k: [{"date": p[0]} for p in v] for k, v in snaps.items() if isinstance(v, list)}
    total = len(found)
    by_watch = _labelable(found, found, watch, watch_days)
    by_snapshot = _labelable(found, found, snap_series, watch_days)
    combined = _labelable(found, found, {**snap_series, **{k: v for k, v in watch.items()}}, watch_days)
    pct = lambda n: round(100 * n / total, 1) if total else 0.0  # noqa: E731
    return {
        "discoveries": total,
        "labelable": combined,
        "pct": pct(combined),
        "labelable_watch_series": by_watch,
        "labelable_star_snapshots": by_snapshot,
        "watch_days": watch_days,
    }


def fetch_observation(full_name: str) -> dict | None:
    """One observation for one repo: three API calls, no writes to the recommendation path."""
    from sources import _gh_api, _normalize_repo

    repo = _gh_api(f"/repos/{full_name}")
    if not isinstance(repo, dict):
        return None
    since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    commits = _gh_api(f"/repos/{full_name}/commits", {"since": since, "per_page": 100})
    contributors = _gh_api(f"/repos/{full_name}/contributors", {"per_page": 100})
    obs = _normalize_repo(repo)
    obs["pushed_at"] = repo.get("pushed_at", "")
    obs["commits_7d"] = len(commits) if isinstance(commits, list) else 0
    obs["contributors_7d"] = len(contributors) if isinstance(contributors, list) else 0
    obs["commits_7d_capped"] = obs["commits_7d"] >= 100
    obs["contributors_7d_capped"] = obs["contributors_7d"] >= 100
    return obs


def refresh(today: str = None, limit: int = None, fetch=fetch_observation, verbose: bool = True) -> dict:
    """Observe everything due, record it, and report the coverage."""
    import time

    today = today or _today()
    names = due(today, limit)
    observations, failed = [], []
    for i, name in enumerate(names):
        try:
            obs = fetch(name)
        except Exception as exc:  # a single repo must not take the run down
            failed.append((name, type(exc).__name__))
        else:
            if obs:
                observations.append(obs)
            else:
                failed.append((name, "no data"))
        if i + 1 < len(names):
            time.sleep(API_DELAY)
    kept = record(observations, today)
    pruned = prune_expired(today)
    # The scorer reads star_snapshots.json; give it the same points so a watched repo keeps a
    # continuous series there too. Harmless if a repo never reaches the scorer.
    record_snapshots(observations, today)
    stats = coverage()
    stats.update({"due": len(names), "observed": kept, "failed": len(failed), "pruned": pruned})
    if verbose:
        print(f"[Watchlist] due {len(names)} · observed {kept} · failed {len(failed)} · pruned {pruned}")
        print(f"[Watchlist] label coverage: {stats['labelable']}/{stats['discoveries']} "
              f"discoveries have a {stats['watch_days']}-day follow-up ({stats['pct']}%) "
              f"[watch_series {stats['labelable_watch_series']}, "
              f"star_snapshots {stats['labelable_star_snapshots']}]")
        for name, why in failed[:5]:
            print(f"[Watchlist]   miss {name}: {why}")
    return stats


def main(argv: list[str]) -> int:
    limit = None
    dry = "--dry-run" in argv
    if "--limit" in argv:
        limit = int(argv[argv.index("--limit") + 1])
    if "--backfill" in argv:
        days = int(argv[argv.index("--backfill") + 1])
        print(f"[Watchlist] backfilled {backfill(days)} repo(s) from the last {days} days")
        if not dry:
            # Adopting the existing discoveries is a one-off bookkeeping step; do not also spend
            # API budget observing unless the caller asks for both.
            return 0
    if dry:
        today = _today()
        names = due(today, limit)
        print(f"[Watchlist] dry run: {len(names)} due, first five: {names[:5]}")
        print(f"[Watchlist] coverage: {coverage()}")
        return 0
    stats = refresh(limit=limit)
    # Every fetch failing means the token or the API changed shape — that must not look like a
    # quiet day. Individual misses are normal (renamed or deleted repos).
    if stats["due"] and stats["observed"] == 0:
        print("[Watchlist] nothing could be observed — treating as a failure", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
