"""Neo4j adapter - graph-native memory store.

Memory has structure. Things connect to other things. Decisions
lead to outcomes. People relate to projects. A graph database
is the natural shape of that structure - not a feature, but the
correct default for anything demanding of memory.

Requires: pip install neo4j
"""

from __future__ import annotations

import time
from typing import Any

try:
    from neo4j import GraphDatabase
    HAS_NEO4J = True
except ImportError:
    HAS_NEO4J = False


class Neo4jStore:
    """Graph-backed knowledge store.

    Four retrieval arms map directly to graph operations:
    - Vector: index-backed semantic search (requires vector index)
    - Graph: neighbourhood walks from matched nodes
    - Episodic: decision/diary nodes ordered by time
    - Speculative: two-hop paths that cross domain boundaries

    Usage:
        store = Neo4jStore("neo4j+s://xxx.databases.neo4j.io", "neo4j", "password")
        store.add("sheaf theory", "Local-to-global consistency framework",
                  labels=["concept"], description="Topology")
        results = store.query("what connects to sheaf theory?")
    """

    name = "neo4j"

    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        if not HAS_NEO4J:
            raise ImportError("Neo4j adapter requires: pip install neo4j")
        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self._database = database
        self._init_schema()

    def _init_schema(self):
        with self._driver.session(database=self._database) as s:
            s.run("""
                CREATE CONSTRAINT memory_name IF NOT EXISTS
                FOR (m:Memory) REQUIRE m.name IS UNIQUE
            """)
            s.run("""
                CREATE INDEX memory_search IF NOT EXISTS
                FOR (m:Memory) ON (m.name, m.description)
            """)

    def _run(self, query: str, **params) -> list[dict]:
        with self._driver.session(database=self._database) as s:
            result = s.run(query, **params)
            return [dict(r) for r in result]

    def add(self, name: str, content: str, labels: list[str] | None = None,
            description: str = "", properties: dict | None = None):
        """Add or update a memory node."""
        props = {
            "name": name,
            "content": content,
            "description": description,
            "labels": labels or [],
            "updated_at": time.time(),
        }
        if properties:
            props.update(properties)

        self._run("""
            MERGE (m:Memory {name: $name})
            SET m += $props
            SET m.created_at = coalesce(m.created_at, $now)
        """, name=name, props=props, now=time.time())

        if labels:
            for label in labels:
                self._run("""
                    MERGE (t:Tag {name: $tag})
                    WITH t
                    MATCH (m:Memory {name: $name})
                    MERGE (m)-[:TAGGED]->(t)
                """, tag=label, name=name)

    def connect(self, from_name: str, to_name: str, relationship: str = "RELATES_TO",
                properties: dict | None = None):
        """Create a relationship between two memories."""
        props = properties or {}
        self._run(f"""
            MATCH (a:Memory {{name: $from_name}})
            MATCH (b:Memory {{name: $to_name}})
            MERGE (a)-[r:{relationship}]->(b)
            SET r += $props
        """, from_name=from_name, to_name=to_name, props=props)

    def add_decision(self, problem: str, outcome: str, significance: int = 5):
        """Record a decision as a node."""
        self._run("""
            CREATE (d:Decision {
                problem: $problem,
                outcome: $outcome,
                significance: $significance,
                created_at: $now
            })
        """, problem=problem, outcome=outcome, significance=significance, now=time.time())

    def add_diary(self, action: str, notes: str = "", agent: str = "default"):
        """Record activity."""
        self._run("""
            CREATE (d:DiaryEntry {
                agent: $agent,
                action: $action,
                notes: $notes,
                created_at: $now
            })
        """, agent=agent, action=action, notes=notes, now=time.time())

    def query(self, text: str, k: int = 10) -> list[dict]:
        """Full-text search across memories. Store protocol."""
        words = [w.lower() for w in text.split() if len(w) > 2]
        if not words:
            return []

        where_clauses = []
        for i, w in enumerate(words[:8]):
            param = f"w{i}"
            where_clauses.append(
                f"(toLower(m.name) CONTAINS ${param} OR "
                f"toLower(m.content) CONTAINS ${param} OR "
                f"toLower(m.description) CONTAINS ${param})"
            )

        params = {f"w{i}": w for i, w in enumerate(words[:8])}
        params["k"] = k

        where = " OR ".join(where_clauses)
        rows = self._run(f"""
            MATCH (m:Memory)
            WHERE {where}
            RETURN m.name AS name, m.content AS content,
                   m.labels AS labels, m.description AS description
            LIMIT $k
        """, **params)

        return [
            {
                "name": r["name"],
                "content": (r.get("content") or "")[:200],
                "labels": r.get("labels") or [],
                "description": r.get("description") or "",
            }
            for r in rows
        ]

    def search(self, query: str, k: int = 10) -> list[dict]:
        """RetrievalArm protocol."""
        return self.query(query, k)

    def neighbourhood(self, name: str, depth: int = 2, limit: int = 20) -> list[dict]:
        """Graph walk - what connects to this memory?"""
        return self._run("""
            MATCH (m:Memory {name: $name})-[r*1..$depth]-(connected)
            WHERE connected:Memory OR connected:Decision OR connected:Tag
            RETURN DISTINCT
                labels(connected)[0] AS type,
                coalesce(connected.name, connected.problem, '') AS name,
                coalesce(connected.description, connected.outcome, '') AS description,
                type(last(r)) AS relationship
            LIMIT $limit
        """, name=name, depth=depth, limit=limit)

    def query_decisions(self, text: str, k: int = 5) -> list[dict]:
        """Search past decisions."""
        words = [w.lower() for w in text.split() if len(w) > 3]
        if not words:
            return []

        where_clauses = []
        for i, w in enumerate(words[:4]):
            param = f"w{i}"
            where_clauses.append(
                f"(toLower(d.problem) CONTAINS ${param} OR "
                f"toLower(d.outcome) CONTAINS ${param})"
            )

        params = {f"w{i}": w for i, w in enumerate(words[:4])}
        params["k"] = k

        rows = self._run(f"""
            MATCH (d:Decision)
            WHERE {" OR ".join(where_clauses)}
            RETURN d.problem AS problem, d.outcome AS outcome,
                   d.significance AS significance
            ORDER BY d.significance DESC
            LIMIT $k
        """, **params)

        return [dict(r) for r in rows]

    def recent_diary(self, limit: int = 5) -> list[dict]:
        """Recent activity."""
        return self._run("""
            MATCH (d:DiaryEntry)
            RETURN d.agent AS agent, d.action AS action,
                   d.notes AS notes, d.created_at AS created_at
            ORDER BY d.created_at DESC
            LIMIT $limit
        """, limit=limit)

    def recover(self, hint: str = "") -> dict:
        """RecoverySource interface."""
        diary = self.recent_diary(limit=5)
        items = [f"- [{d['agent']}] {d['action']}" for d in diary]

        decisions = self._run("""
            MATCH (d:Decision)
            RETURN d.problem AS problem, d.outcome AS outcome
            ORDER BY d.created_at DESC
            LIMIT 3
        """)
        for d in decisions:
            items.append(f"- Decided: {d['problem']} -> {d['outcome']}")

        content = "\n".join(items) if items else "No recent activity."
        return {"label": "Recent Activity & Decisions", "content": content}

    def close(self):
        self._driver.close()
