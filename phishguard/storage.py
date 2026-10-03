"""SQLite history of analysed messages and their results."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .engine import Assessment
from .message import Message

DEFAULT_DB = Path(__file__).resolve().parent.parent / "phishguard.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS analyses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL,
    channel     TEXT NOT NULL,
    sender      TEXT,
    subject     TEXT,
    body        TEXT,
    score       INTEGER NOT NULL,
    level       TEXT NOT NULL,
    result_json TEXT NOT NULL,
    feedback    TEXT  -- user's own verdict: 'phish' | 'legit' | NULL
);
CREATE INDEX IF NOT EXISTS idx_analyses_created ON analyses(created_at DESC);
"""


class History:
    def __init__(self, path: Path | str = DEFAULT_DB):
        self.path = str(path)
        with self._conn() as c:
            c.executescript(SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def save(self, msg: Message, a: Assessment) -> int:
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO analyses (created_at, channel, sender, subject, body, score, level, result_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (datetime.now(timezone.utc).isoformat(timespec="seconds"), msg.channel, msg.sender,
                 msg.subject, msg.body[:20000], a.score, a.level, json.dumps(a.to_dict())),
            )
            return int(cur.lastrowid)

    def get(self, analysis_id: int) -> dict | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
        return self._row(row) if row else None

    def recent(self, limit: int = 50, level: str | None = None) -> list[dict]:
        sql, args = "SELECT * FROM analyses", []
        if level:
            sql += " WHERE level = ?"
            args.append(level)
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        with self._conn() as c:
            return [self._row(r) for r in c.execute(sql, args).fetchall()]

    def set_feedback(self, analysis_id: int, verdict: str) -> None:
        if verdict not in ("phish", "legit"):
            raise ValueError("verdict must be 'phish' or 'legit'")
        with self._conn() as c:
            c.execute("UPDATE analyses SET feedback = ? WHERE id = ?", (verdict, analysis_id))

    def delete(self, analysis_id: int) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))

    def stats(self) -> dict:
        with self._conn() as c:
            rows = c.execute("SELECT level, COUNT(*) AS n FROM analyses GROUP BY level").fetchall()
            total = c.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
        return {"total": total, "by_level": {r["level"]: r["n"] for r in rows}}

    @staticmethod
    def _row(row: sqlite3.Row) -> dict:
        d = dict(row)
        d["result"] = json.loads(d.pop("result_json"))
        return d
