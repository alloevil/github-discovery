"""SQLite database for tracking discovered repos."""

import sqlite3
import os
from config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS repos (
            repo_id TEXT PRIMARY KEY,
            full_name TEXT,
            url TEXT,
            description TEXT,
            language TEXT,
            stars INTEGER,
            forks INTEGER,
            created_at TEXT,
            discovered_at TEXT,
            score REAL,
            source TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at TEXT,
            repos_found INTEGER,
            top_score REAL
        )
    """)
    conn.commit()
    conn.close()


def repo_exists(repo_id: str) -> bool:
    conn = get_conn()
    row = conn.execute("SELECT 1 FROM repos WHERE repo_id = ?", (repo_id,)).fetchone()
    conn.close()
    return row is not None


def save_repo(repo: dict, score: float, source: str):
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO repos
        (repo_id, full_name, url, description, language, stars, forks, created_at, discovered_at, score, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, ?)
    """, (
        repo["id"], repo["full_name"], repo["url"], repo.get("description", ""),
        repo.get("language", ""), repo.get("stars", 0), repo.get("forks", 0),
        repo.get("created_at", ""), score, source
    ))
    conn.commit()
    conn.close()


def save_run(repos_found: int, top_score: float):
    conn = get_conn()
    conn.execute(
        "INSERT INTO runs (run_at, repos_found, top_score) VALUES (datetime('now'), ?, ?)",
        (repos_found, top_score)
    )
    conn.commit()
    conn.close()
