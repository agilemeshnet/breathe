"""SQLite adapter - zero-dependency starter store.

No graph database, no vector index, no external services needed.
Uses SQLite FTS5 for full-text search. Good enough to demonstrate
the breathing pattern with nothing installed.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path


class SQLiteStore:
    """A simple knowledge store backed by SQLite with FTS5.

    Implements both the Store protocol (for breathing) and
    RetrievalArm protocol (for multi-arm retrieval).

    Usage:
        store = SQLiteStore("~/.breathe/memory.db")
        store.add("sheaf theory", {"labels": ["concept"], "description": "..."})
        results = store.query("topology", k=5)
    """

    name = "sqlite"

    def __init__(self, db_path: str | Path = "~/.breathe/memory.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                content TEXT NOT NULL,
                labels TEXT DEFAULT '[]',
                description TEXT DEFAULT '',
                created_at REAL,
                updated_at REAL
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
            USING fts5(name, content, description, content=memories, content_rowid=id);

            CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                INSERT INTO memories_fts(rowid, name, content, description)
                VALUES (new.id, new.name, new.content, new.description);
            END;

            CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, name, content, description)
                VALUES ('delete', old.id, old.name, old.content, old.description);
                INSERT INTO memories_fts(rowid, name, content, description)
                VALUES (new.id, new.name, new.content, new.description);
            END;

            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                problem TEXT NOT NULL,
                outcome TEXT NOT NULL,
                significance INTEGER DEFAULT 5,
                created_at REAL
            );

            CREATE TABLE IF NOT EXISTS diary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent TEXT DEFAULT 'default',
                action TEXT NOT NULL,
                notes TEXT DEFAULT '',
                created_at REAL
            );
        """)
        self.conn.commit()

    def add(self, name: str, content: str, labels: list[str] | None = None, description: str = ""):
        """Add a memory to the store."""
        now = time.time()
        self.conn.execute(
            "INSERT INTO memories (name, content, labels, description, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, content, json.dumps(labels or []), description, now, now),
        )
        self.conn.commit()

    def add_decision(self, problem: str, outcome: str, significance: int = 5):
        """Record a decision for episodic retrieval."""
        self.conn.execute(
            "INSERT INTO decisions (problem, outcome, significance, created_at) VALUES (?, ?, ?, ?)",
            (problem, outcome, significance, time.time()),
        )
        self.conn.commit()

    def add_diary(self, action: str, notes: str = "", agent: str = "default"):
        """Record an activity for temporal awareness."""
        self.conn.execute(
            "INSERT INTO diary (agent, action, notes, created_at) VALUES (?, ?, ?, ?)",
            (agent, action, notes, time.time()),
        )
        self.conn.commit()

    @staticmethod
    def _sanitise_fts(text: str) -> str:
        """Build a safe FTS5 query from free text."""
        import re
        words = re.findall(r"[a-zA-Z0-9]+", text.lower())
        unique = list(dict.fromkeys(w for w in words if len(w) > 2))
        return " OR ".join(f'"{w}"' for w in unique[:12])

    def query(self, text: str, k: int = 10) -> list[dict]:
        """Full-text search across memories. Store protocol."""
        terms = self._sanitise_fts(text)
        if not terms:
            return []
        try:
            rows = self.conn.execute(
                "SELECT m.name, m.content, m.labels, m.description, "
                "rank * -1 as score "
                "FROM memories_fts f "
                "JOIN memories m ON f.rowid = m.id "
                "WHERE memories_fts MATCH ? "
                "ORDER BY rank "
                "LIMIT ?",
                (terms, k),
            ).fetchall()
        except sqlite3.OperationalError:
            return []

        return [
            {
                "name": r[0],
                "content": r[1][:200],
                "labels": json.loads(r[2]) if r[2] else [],
                "description": r[3],
                "score": round(r[4], 4) if r[4] else 0,
            }
            for r in rows
        ]

    def search(self, query: str, k: int = 10) -> list[dict]:
        """RetrievalArm protocol (alias for query)."""
        return self.query(query, k)

    def query_decisions(self, text: str, k: int = 5) -> list[dict]:
        """Search past decisions."""
        terms = [w for w in text.lower().split() if len(w) > 3]
        if not terms:
            return []
        results = []
        seen = set()
        for term in terms[:4]:
            rows = self.conn.execute(
                "SELECT problem, outcome, significance FROM decisions "
                "WHERE problem LIKE ? OR outcome LIKE ? "
                "ORDER BY significance DESC LIMIT ?",
                (f"%{term}%", f"%{term}%", k),
            ).fetchall()
            for r in rows:
                if r[0] not in seen:
                    seen.add(r[0])
                    results.append({
                        "problem": r[0],
                        "outcome": r[1],
                        "significance": r[2],
                    })
        return results[:k]

    def recent_diary(self, limit: int = 5) -> list[dict]:
        """Get recent diary entries."""
        rows = self.conn.execute(
            "SELECT agent, action, notes, created_at FROM diary "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {"agent": r[0], "action": r[1], "notes": r[2], "created_at": r[3]}
            for r in rows
        ]

    def close(self):
        self.conn.close()

    def recover(self, hint: str = "") -> dict:
        """RecoverySource interface."""
        diary = self.recent_diary(limit=5)
        items = [f"- [{d['agent']}] {d['action']}" for d in diary]
        content = "\n".join(items) if items else "No recent activity."
        return {"label": "Recent Activity", "content": content}
