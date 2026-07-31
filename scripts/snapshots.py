"""每日 Star 快照 — 为真实增速/加速度计算积累时间序列。

daily_stars = stars / age_days 只是终身平均速度，无法体现"最近突然加速"。
这里把每天抓到的候选仓库 star 数落盘（data/star_snapshots.json，随
workflow 提交），第二天起即可计算真实日增量，以及
「真实日增 / 终身平均」的加速比 —— 这是区别于 GitHub Trending 的核心信号。

文件格式:
{
  "repos": {
    "owner/name": [["2026-07-30", 1200], ["2026-07-31", 1450]]
  },
  "updated_at": "..."
}
每个仓库保留最近 SNAPSHOT_KEEP_DAYS 天的点；超过该天数没再出现的仓库整体清除。
"""

import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

SNAPSHOT_FILE = Path(__file__).parent.parent / "data" / "star_snapshots.json"
SNAPSHOT_KEEP_DAYS = 30


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load() -> dict:
    if SNAPSHOT_FILE.exists():
        try:
            return json.loads(SNAPSHOT_FILE.read_text())
        except (ValueError, OSError):
            pass
    return {"repos": {}, "updated_at": ""}


def _save(data: dict):
    SNAPSHOT_FILE.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    SNAPSHOT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=1))


def record_snapshots(repos: list[dict], today: str = None):
    """记录一批仓库今天的 star 数（同日重跑覆盖当日点）。

    应对**所有**抓到的候选仓库调用（包括被 7 天去重过滤掉的），
    这样已推荐仓库的时间序列不会中断。
    """
    today = today or _today()
    cutoff = (datetime.strptime(today, "%Y-%m-%d") - timedelta(days=SNAPSHOT_KEEP_DAYS)).strftime("%Y-%m-%d")
    data = _load()
    store = data.setdefault("repos", {})

    for repo in repos:
        name = repo.get("full_name")
        if not name:
            continue
        history = [p for p in store.get(name, []) if p[0] != today and p[0] >= cutoff]
        history.append([today, repo.get("stars", 0)])
        history.sort(key=lambda p: p[0])
        store[name] = history

    # 清除长期未出现的仓库（最新点已过期）
    stale = [name for name, hist in store.items() if not hist or hist[-1][0] < cutoff]
    for name in stale:
        del store[name]

    _save(data)
    print(f"[Snapshot] Recorded {len(repos)} repos ({len(stale)} stale pruned, {len(store)} tracked)")


def get_growth(full_name: str, current_stars: int, today: str = None) -> dict | None:
    """基于最近一个早于今天的快照点，计算真实日增速。

    Returns:
        {"real_daily": float, "span_days": int, "prev_stars": int}
        无历史数据（首次见到该仓库）时返回 None。
    只看早于今天的点，因此与 record_snapshots 的调用顺序无关，
    同日重跑也不会算出 delta=0。
    """
    today = today or _today()
    history = _load().get("repos", {}).get(full_name, [])
    prior = [p for p in history if p[0] < today]
    if not prior:
        return None

    prev_date, prev_stars = prior[-1]
    span = max(1, (datetime.strptime(today, "%Y-%m-%d") - datetime.strptime(prev_date, "%Y-%m-%d")).days)
    return {
        "real_daily": (current_stars - prev_stars) / span,
        "span_days": span,
        "prev_stars": prev_stars,
    }
