"""推荐期（picks）—— 聊天推荐和邮件共用的唯一来源。

每 PICKS_EVERY_DAYS 天出一期，每期 PICKS_MIN..PICKS_MAX 个仓库，至少 SEMI_MIN 个
半导体/工业 AI 仓库。和每日的 discovery 报告不同：
  - 永久去重：data/picks_history.json 里出现过的仓库永不再进 picks（不像
    recommend_history 那样 7 天后放行、30 天后清除）；
  - 只写事实字段：数字全部来自 GitHub API（verify_picks 当场重新读取）或本仓库
    提交的 star 快照，增长拿不到就写 null，不用终身平均值顶替；
  - 不接大模型：「做什么 / 为什么火」的文字由读取方根据这些字段来写。
"""

import json
import re
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
PICKS_HISTORY_FILE = DATA_DIR / "picks_history.json"

PICKS_EVERY_DAYS = 3
# 推荐日 = 与锚点相差 PICKS_EVERY_DAYS 整数倍的日期（UTC）。锚点是第一期聊天推荐的日期。
PICKS_ANCHOR = "2026-10-16"
PICKS_MIN = 8
PICKS_MAX = 10
SEMI_MIN = 2

AI_TERMS = [
    "llm", "large language model", "language model", "agent", "agentic", "ai",
    "machine learning", "deep learning", "transformer", "diffusion", "rag",
    "embedding", "fine-tuning", "lora", "inference", "mcp", "model context protocol",
    "reinforcement learning", "multimodal", "vlm", "world model", "neural",
    "gpt", "claude", "gemini", "qwen", "deepseek", "llama", "computer vision", "nlp",
]
SEMI_TERMS = [
    "semiconductor", "chip design", "asic", "fpga", "rtl", "verilog", "systemverilog",
    "vhdl", "eda", "hdl", "pdk", "wafer", "lithography", "tapeout", "risc-v", "riscv",
    "uvm", "formal verification", "timing closure", "place and route", "openroad",
    "yosys", "chisel", "industrial ai", "predictive maintenance", "plc", "scada",
    "manufacturing", "digital twin", "industrial iot", "iiot", "process control",
]


def is_picks_day(day: date | None = None) -> bool:
    day = day or datetime.now(timezone.utc).date()
    anchor = date.fromisoformat(PICKS_ANCHOR)
    return (day - anchor).days % PICKS_EVERY_DAYS == 0


def _has_term(text: str, term: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", text) is not None


def topic_of(repo: dict) -> str | None:
    """'semi' / 'ai' / None，依据仓库描述、topics 和名字。半导体优先。"""
    text = " ".join([
        repo.get("full_name", "").replace("-", " ").replace("_", " "),
        repo.get("description") or "",
        " ".join(t.replace("-", " ") for t in repo.get("topics") or []),
    ]).lower()
    if any(_has_term(text, t) for t in SEMI_TERMS):
        return "semi"
    if any(_has_term(text, t) for t in AI_TERMS):
        return "ai"
    return None


# ── 永久历史 ─────────────────────────────────────────────────────────

def load_history() -> dict:
    if PICKS_HISTORY_FILE.exists():
        return json.loads(PICKS_HISTORY_FILE.read_text())
    return {"repos": {}}


def was_ever_picked(full_name: str, history: dict | None = None) -> bool:
    history = history if history is not None else load_history()
    key = full_name.lower()
    return any(k.lower() == key for k in history.get("repos", {}))


def record_picks(picks: list[dict], day: str, source: str = "github-discovery"):
    history = load_history()
    repos = history.setdefault("repos", {})
    for p in picks:
        repos.setdefault(p["full_name"], {"first_picked": day, "source": source})
    history["updated_at"] = datetime.now(timezone.utc).isoformat()
    PICKS_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    PICKS_HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n")


# ── 选择 ─────────────────────────────────────────────────────────────

def select_candidates(scored: list[tuple[dict, dict]], history: dict | None = None) -> list[tuple[dict, dict]]:
    """按 (半导体配额, 有主题优先, 分数) 给出有序候选（多于 PICKS_MAX，留给核实失败时补位）。"""
    history = history if history is not None else load_history()
    pool = []
    for repo, scores in scored:
        if was_ever_picked(repo["full_name"], history):
            continue
        if repo.get("star_suspicious") or scores.get("fraud_penalty"):
            continue
        repo["topic"] = topic_of(repo)
        pool.append((repo, scores))
    pool.sort(key=lambda x: x[1].get("total", 0), reverse=True)
    semi = [x for x in pool if x[0]["topic"] == "semi"]
    rest = [x for x in pool if x[0]["topic"] != "semi"]
    rest.sort(key=lambda x: (x[0]["topic"] is None, -x[1].get("total", 0)))
    return semi[:SEMI_MIN] + rest + semi[SEMI_MIN:]


def finalize(verified: list[tuple[dict, dict]]) -> list[tuple[dict, dict]]:
    """核实后的有序候选 → 最多 PICKS_MAX 个，尽量满足 SEMI_MIN。"""
    semi = [x for x in verified if x[0].get("topic") == "semi"]
    chosen = semi[:SEMI_MIN]
    for x in verified:
        if len(chosen) >= PICKS_MAX:
            break
        if x not in chosen:
            chosen.append(x)
    return chosen


# ── 核实与增长 ───────────────────────────────────────────────────────

def verify_picks(ordered: list[tuple[dict, dict]], gh_api, need: int = PICKS_MAX) -> list[tuple[dict, dict]]:
    """逐个用 GET /repos/{full_name} 重新读取；404、归档、禁用的丢弃。

    凑够 need 个、且其中半导体达到 SEMI_MIN（或候选里已无半导体）就停，省 API 配额。
    """
    out = []
    semi_left = sum(1 for r, _ in ordered if r.get("topic") == "semi")
    for repo, scores in ordered:
        is_semi = repo.get("topic") == "semi"
        semi_have = sum(1 for r, _ in out if r.get("topic") == "semi")
        if len(out) >= need and (semi_have >= SEMI_MIN or semi_left == 0):
            break
        if is_semi:
            semi_left -= 1
        data = gh_api(f"/repos/{repo['full_name']}")
        if not data or data.get("archived") or data.get("disabled") or data.get("private"):
            print(f"  [Picks] drop {repo['full_name']}: not reachable/archived")
            continue
        repo.update({
            "full_name": data["full_name"],
            "url": data["html_url"],
            "description": data.get("description") or "",
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "language": data.get("language") or "",
            "topics": data.get("topics") or [],
            "created_at": data.get("created_at", ""),
            "pushed_at": data.get("pushed_at", ""),
            "license": (data.get("license") or {}).get("spdx_id") or "",
            "verified_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
        repo["topic"] = topic_of(repo) or repo.get("topic")
        out.append((repo, scores))
    return finalize(out)


def measured_growth(full_name: str, current_stars: int, snapshots: dict, today: str) -> dict | None:
    """只用提交过的快照算实测增长；优先取 7 天前（或更早、14 天内）的点，否则取最近的一个更早的点。"""
    hist = [p for p in snapshots.get("repos", {}).get(full_name, []) if p[0] < today]
    if not hist:
        return None
    t = date.fromisoformat(today)
    week = [p for p in hist if 7 <= (t - date.fromisoformat(p[0])).days <= 14]
    prev_date, prev_stars = (week[-1] if week else hist[-1])
    span = (t - date.fromisoformat(prev_date)).days
    return {
        "since": prev_date,
        "window_days": span,
        "stars_gained": current_stars - prev_stars,
        "source": "star_snapshots",
    }


def build_pick(rank: int, repo: dict, scores: dict, snapshots: dict, today: str) -> dict:
    return {
        "rank": rank,
        "full_name": repo["full_name"],
        "url": repo["url"],
        "description": repo.get("description") or "",
        "topic": repo.get("topic"),
        "language": repo.get("language") or "",
        "topics": repo.get("topics") or [],
        "license": repo.get("license") or "",
        "stars": repo.get("stars", 0),
        "forks": repo.get("forks", 0),
        "created_at": repo.get("created_at", ""),
        "pushed_at": repo.get("pushed_at", ""),
        "growth": measured_growth(repo["full_name"], repo.get("stars", 0), snapshots, today),
        "evidence": {
            "sources": repo.get("sources") or [repo.get("source", "unknown")],
            "hn_title": repo.get("hn_title"),
            "hn_score": repo.get("hn_score"),
            "hf_title": repo.get("hf_title"),
            "hf_upvotes": repo.get("hf_upvotes"),
        },
        "score": scores.get("total"),
        "verified_at": repo.get("verified_at"),
    }


def write_picks(day: str, chosen: list[tuple[dict, dict]], snapshots: dict) -> str:
    picks = [build_pick(i, r, s, snapshots, day) for i, (r, s) in enumerate(chosen, 1)]
    semi = sum(1 for p in picks if p["topic"] == "semi")
    doc = {
        "date": day,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "every_days": PICKS_EVERY_DAYS,
        "count": len(picks),
        "semi_count": semi,
        "semi_min_met": semi >= SEMI_MIN,
        "picks": picks,
    }
    path = DATA_DIR / f"picks-{day}.json"
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    return str(path)
