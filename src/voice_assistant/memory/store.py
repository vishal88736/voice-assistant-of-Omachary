"""Persistent memory backed by SQLite."""

from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable

from ..config.settings import db_path


SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at REAL NOT NULL,
    ended_at REAL,
    summary TEXT
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(content, content='messages', content_rowid='id');
CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
  INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
END;
CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
  INSERT INTO messages_fts(messages_fts, rowid, content) VALUES('delete', old.id, old.content);
END;
"""


class MemoryStore:
    def __init__(self, path: Path | None = None):
        self.path = path or db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _init(self) -> None:
        with self._conn() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def start_session(self) -> int:
        with self._conn() as c:
            cur = c.execute("INSERT INTO sessions(started_at) VALUES (?)", (time.time(),))
            return int(cur.lastrowid)

    def end_session(self, session_id: int, summary: str | None = None) -> None:
        with self._conn() as c:
            c.execute("UPDATE sessions SET ended_at=?, summary=? WHERE id=?", (time.time(), summary, session_id))

    def add_message(self, session_id: int, role: str, content: str) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO messages(session_id, role, content, created_at) VALUES (?,?,?,?)",
                (session_id, role, content, time.time()),
            )

    def recent_messages(self, session_id: int, limit: int = 20) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT role, content, created_at FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def list_sessions(self, limit: int = 50) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT s.id, s.started_at, s.ended_at, s.summary, "
                "  (SELECT COUNT(*) FROM messages m WHERE m.session_id=s.id) AS message_count, "
                "  (SELECT content FROM messages m WHERE m.session_id=s.id ORDER BY m.id DESC LIMIT 1) AS preview "
                "FROM sessions s ORDER BY s.id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def session_messages(self, session_id: int) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT role, content, created_at FROM messages WHERE session_id=? ORDER BY id ASC",
                (session_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def delete_session(self, session_id: int) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
            c.execute("DELETE FROM sessions WHERE id=?", (session_id,))

    def purge_old_sessions(self, retention_days: int, max_sessions: int) -> int:
        cutoff = time.time() - max(0, retention_days) * 86400
        removed = 0
        with self._conn() as c:
            ids = [r["id"] for r in c.execute(
                "SELECT id FROM sessions WHERE started_at < ? ORDER BY id ASC", (cutoff,)
            ).fetchall()]
            keep = [r["id"] for r in c.execute(
                "SELECT id FROM sessions ORDER BY id DESC LIMIT ?", (max(1, max_sessions),)
            ).fetchall()]
            keep_set = set(keep)
            for sid in ids:
                if sid not in keep_set:
                    c.execute("DELETE FROM messages WHERE session_id=?", (sid,))
                    c.execute("DELETE FROM sessions WHERE id=?", (sid,))
                    removed += 1
            # also enforce max count
            all_ids = [r["id"] for r in c.execute("SELECT id FROM sessions ORDER BY id DESC").fetchall()]
            for sid in all_ids[max(1, max_sessions):]:
                c.execute("DELETE FROM messages WHERE session_id=?", (sid,))
                c.execute("DELETE FROM sessions WHERE id=?", (sid,))
                removed += 1
        return removed

    def purge_memories(self) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM memories")

    def search(self, query: str, limit: int = 10) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT m.id, m.session_id, m.role, m.content, m.created_at FROM messages m "
                "JOIN messages_fts f ON f.rowid=m.id WHERE messages_fts MATCH ? ORDER BY m.id DESC LIMIT ?",
                (query, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def add_memory(self, kind: str, content: str, source: str | None = None) -> int:
        now = time.time()
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO memories(kind, content, source, created_at, updated_at) VALUES (?,?,?,?,?)",
                (kind, content, source, now, now),
            )
            return int(cur.lastrowid)

    def list_memories(self, kind: str | None = None) -> list[dict]:
        with self._conn() as c:
            if kind:
                rows = c.execute("SELECT * FROM memories WHERE kind=? ORDER BY updated_at DESC", (kind,)).fetchall()
            else:
                rows = c.execute("SELECT * FROM memories ORDER BY updated_at DESC").fetchall()
        return [dict(r) for r in rows]

    def delete_memory(self, memory_id: int) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM memories WHERE id=?", (memory_id,))

    def last_session_summary(self) -> str | None:
        with self._conn() as c:
            row = c.execute("SELECT summary FROM sessions WHERE summary IS NOT NULL ORDER BY id DESC LIMIT 1").fetchone()
        return row["summary"] if row else None