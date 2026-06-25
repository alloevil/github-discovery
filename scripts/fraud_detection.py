"""批量刷量检测模块

检测同一 owner 下的可疑批量操作模式：
1. 多个仓库同时出现在 trending 中（>=3 个）
2. 多个仓库短时间内 Star 暴涨
3. 仓库描述高度相似（模板批量创建）

输出格式：{"is_fraud": bool, "reason": str, "penalty": int}
"""

import re
from collections import defaultdict
from difflib import SequenceMatcher


def _extract_owner(full_name: str) -> str:
    """从 full_name 中提取 owner（org 或 user）。"""
    return full_name.split("/")[0] if "/" in full_name else ""


def _normalize_text(text: str) -> str:
    """归一化文本用于相似度比较：小写、去标点、去多余空格。"""
    text = (text or "").lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _description_similarity(desc_a: str, desc_b: str) -> float:
    """计算两个描述的相似度（0.0 ~ 1.0）。"""
    a = _normalize_text(desc_a)
    b = _normalize_text(desc_b)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _has_template_pattern(descriptions: list[str]) -> bool:
    """检测一组描述是否有模板化痕迹。

    策略：提取每条描述的前 N 个词作为"模板前缀"，
    如果超过半数共享同一前缀，则判定为模板化。
    """
    if len(descriptions) < 2:
        return False

    prefixes = []
    for desc in descriptions:
        words = _normalize_text(desc).split()
        # 取前 5 个词作为前缀签名
        prefix = " ".join(words[:5]) if words else ""
        prefixes.append(prefix)

    # 统计前缀出现频率
    from collections import Counter
    counts = Counter(prefixes)
    most_common_count = counts.most_common(1)[0][1] if counts else 0

    # 超过半数共享同一前缀 → 模板化
    if most_common_count >= len(descriptions) * 0.5 and most_common_count >= 2:
        return True

    # 两两相似度 > 0.7 的对数超过半数 → 模板化
    n = len(descriptions)
    similar_pairs = 0
    total_pairs = n * (n - 1) // 2
    for i in range(n):
        for j in range(i + 1, n):
            if _description_similarity(descriptions[i], descriptions[j]) > 0.7:
                similar_pairs += 1

    if total_pairs > 0 and similar_pairs / total_pairs > 0.5:
        return True

    return False


def detect_batch_fraud(repos: list[dict]) -> list[dict]:
    """对一批仓库执行批量刷量检测。

    Args:
        repos: 仓库列表，每个仓库需包含 full_name, stars, age_days, description 等字段。

    Returns:
        可疑 owner 列表，每项格式：
        {
            "owner": str,
            "is_fraud": True,
            "reason": str,          # 可疑原因
            "penalty": int,         # 建议扣分（负数）
            "repo_count": int,      # 该 owner 下的仓库数
            "repos": list[str],     # 涉及的仓库 full_name
        }
    """
    if not repos:
        return []

    # 按 owner 分组
    owner_repos: dict[str, list[dict]] = defaultdict(list)
    for repo in repos:
        owner = _extract_owner(repo["full_name"])
        if owner:
            owner_repos[owner].append(repo)

    fraud_results = []

    for owner, orepos in owner_repos.items():
        reasons = []
        penalty = 0

        # ── 检测 1：同一 owner 下多个仓库同时出现在 trending ──
        if len(orepos) >= 3:
            reasons.append(
                f"owner_has_{len(orepos)}_repos_in_batch"
            )
            penalty -= 15

        # ── 检测 2：多个仓库短时间内 Star 暴涨 ──
        #     定义：age_days <= 7 且 stars >= 200 的仓库 >= 2 个
        rapid_growth = [
            r for r in orepos
            if r.get("age_days", 999) <= 7 and r.get("stars", 0) >= 200
        ]
        if len(rapid_growth) >= 2:
            reasons.append(
                f"owner_has_{len(rapid_growth)}_repos_rapid_star_growth"
            )
            penalty -= 15

        # ── 检测 3：描述高度相似（模板批量创建）──
        descriptions = [r.get("description", "") for r in orepos]
        # 只在有 >=2 条非空描述时检测
        non_empty_descs = [d for d in descriptions if len(d.strip()) > 10]
        if len(non_empty_descs) >= 2 and _has_template_pattern(non_empty_descs):
            reasons.append("template_similar_descriptions")
            penalty -= 10

        # 只要有任何一项触发就标记为可疑
        if reasons:
            fraud_results.append({
                "owner": owner,
                "is_fraud": True,
                "reason": "; ".join(reasons),
                "penalty": penalty,
                "repo_count": len(orepos),
                "repos": [r["full_name"] for r in orepos],
            })

    return fraud_results


def apply_fraud_penalty(repo: dict, fraud_map: dict[str, dict]) -> dict:
    """将批量刷量扣分应用到单个仓库。

    Args:
        repo: 单个仓库字典
        fraud_map: detect_batch_fraud 返回结果按 owner 索引的映射

    Returns:
        {"is_fraud": bool, "reason": str, "penalty": int}
    """
    owner = _extract_owner(repo["full_name"])
    if owner and owner in fraud_map:
        entry = fraud_map[owner]
        return {
            "is_fraud": True,
            "reason": entry["reason"],
            "penalty": entry["penalty"],
        }
    return {"is_fraud": False, "reason": "", "penalty": 0}
