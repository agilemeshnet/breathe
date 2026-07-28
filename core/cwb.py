"""Salience scorer for breathe.

Scores memory entries against a query with a six-signal formula, applied
in order:

  1. Type weight        (feedback 5, project 4, user 3, reference 2, dream 1)
  2. Recency bump       (up to +5 within RECENCY_HOURS window, linear decay)
  3. Standing pin       (+8 if fm.description or fm.name matches
                         STANDING / HARD RULE / FOUNDATIONAL)
  4. Query-term match   (+3 per whole-word hit against fm_name + fm_desc + name)
  5. Dream penalty      (-10 unless query mentions dream or bookend)
  6. Citation blend     (up to +CITATION_CAP, additive from a
                         slug -> in-degree dict, when available)

Adapters lift concrete records to a stable `Entry` shape so the same
score function can consume:

  - A row from a directory of `.md` files (see `md_corpus`)
  - A breathe `Identity` memory (see `identity_corpus`)
  - Any custom object satisfying the `MemoryLike` Protocol
"""
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Optional, Sequence

# ---- Constants ------------------------------------------------------------

RECENCY_HOURS = 24
ALWAYS_PATTERNS = ("STANDING", "HARD RULE", "FOUNDATIONAL")
TYPE_WEIGHTS = {"feedback": 5, "project": 4, "user": 3, "reference": 2, "dream": 1}
CITATION_PER_LINK = 0.4
CITATION_CAP = 4.0


# ---- Adapter surface ------------------------------------------------------

class MemoryLike(Protocol):
    """The minimum shape `score_entry` needs. Adapters lift real records to this."""
    type: str
    mtime: float
    name: str
    fm_name: str
    fm_desc: str


@dataclass
class Entry:
    """Concrete `MemoryLike` record used by the adapters below."""
    type: str
    mtime: float
    name: str
    fm_name: str = ""
    fm_desc: str = ""

    def as_score_input(self) -> dict:
        return {
            "type": self.type,
            "mtime": self.mtime,
            "name": self.name,
            "fm_name": self.fm_name,
            "fm_desc": self.fm_desc,
        }


# ---- Score function -------------------------------------------------------

def score_entry(
    e: dict,
    query: str,
    now_ts: float,
    citations: Optional[dict[str, int]] = None,
) -> float:
    """Return the salience score for `e` against `query` at `now_ts`.

    `e` must be a dict shaped like `Entry.as_score_input()`. `citations`
    is an optional slug -> in-degree map; when present, adds up to
    `CITATION_CAP` to reward heavily-cited entries.
    """
    score = float(TYPE_WEIGHTS.get(e["type"], 0))
    age_h = (now_ts - e["mtime"]) / 3600
    if age_h < RECENCY_HOURS:
        score += 5 * (1 - age_h / RECENCY_HOURS)
    upper = (e["fm_desc"] + " " + e["fm_name"]).upper()
    if any(pat in upper for pat in ALWAYS_PATTERNS):
        score += 8
    if query:
        terms = [t.lower() for t in query.split() if len(t) > 2]
        haystack = (e["fm_name"] + " " + e["fm_desc"] + " " + e["name"]).lower()
        for t in terms:
            if t in haystack:
                score += 3
    if e["type"] == "dream":
        if not any(w in query.lower() for w in ("dream", "bookend")):
            score -= 10
    if citations:
        slug = e.get("fm_name") or ""
        in_degree = citations.get(slug, 0)
        if in_degree:
            score += min(CITATION_CAP, CITATION_PER_LINK * in_degree)
    return score


# ---- Adapters -------------------------------------------------------------

def parse_frontmatter(text: str) -> dict:
    """Parse a leading `---` YAML-ish frontmatter block; empty dict if none."""
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    fm = {}
    for line in parts[1].strip().split("\n"):
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm


def _kind_for_filename(name: str) -> str:
    for prefix in TYPE_WEIGHTS:
        if name.startswith(prefix + "_") or name.startswith(prefix + "-"):
            return prefix
    return "other"


def md_corpus(memory_dir: Path, skip_index_name: Optional[str] = None) -> list[Entry]:
    """Walk a directory of `.md` files and return `Entry` rows.

    `skip_index_name`, when set, excludes a top-level index file (e.g. an
    index that catalogues the rest of the corpus). Type is inferred from
    the filename prefix using the same weights as `TYPE_WEIGHTS`; anything
    else falls through as `"other"`.
    """
    out: list[Entry] = []
    if not memory_dir.exists():
        return out
    for f in memory_dir.glob("*.md"):
        if skip_index_name and f.name == skip_index_name:
            continue
        try:
            text = f.read_text()
        except Exception:
            continue
        fm = parse_frontmatter(text)
        kind = _kind_for_filename(f.name)
        out.append(Entry(
            type=kind,
            mtime=f.stat().st_mtime,
            name=f.name,
            fm_name=fm.get("name", ""),
            fm_desc=fm.get("description", ""),
        ))
    return out


def identity_corpus(identity) -> list[Entry]:
    """Adapter for breathe's `Identity` store.

    Lifts each `Memory` to an `Entry`: name -> `fm_name`,
    description -> `fm_desc`, `updated_at` -> `mtime`. Type flows straight
    through.
    """
    out: list[Entry] = []
    for mem in identity.memories.values():
        out.append(Entry(
            type=mem.type,
            mtime=float(mem.updated_at),
            name=mem.name,
            fm_name=mem.name,
            fm_desc=mem.description,
        ))
    return out


# ---- Citation blend -------------------------------------------------------

def load_citation_counts(citation_db: Optional[Path]) -> dict[str, int]:
    """Read slug -> in-degree from a sibling sqlite index.

    Expects two tables: `memory_node(id, name)` and `memory_link(dst_id)`.
    Empty dict if the DB is missing or unreadable, so the caller falls
    back to recency + type + query scoring without special-casing.
    """
    if not citation_db or not citation_db.exists():
        return {}
    try:
        c = sqlite3.connect(f"file:{citation_db}?mode=ro", uri=True)
        rows = c.execute(
            """SELECT memory_node.name AS name, COUNT(*) AS n
               FROM memory_link
               JOIN memory_node ON memory_node.id = memory_link.dst_id
               WHERE memory_link.dst_id IS NOT NULL
               GROUP BY memory_node.id"""
        ).fetchall()
        c.close()
        return {row[0]: row[1] for row in rows}
    except Exception:
        return {}


# ---- Convenience: rank a corpus -------------------------------------------

def rank(
    entries: Sequence[Entry],
    query: str = "",
    now_ts: Optional[float] = None,
    citations: Optional[dict[str, int]] = None,
    limit: Optional[int] = None,
) -> list[tuple[Entry, float]]:
    """Score every entry and return them sorted highest-first.

    Suitable for direct wiring into breathe's arm-Protocol retrieval.
    """
    if now_ts is None:
        now_ts = time.time()
    scored = [
        (e, score_entry(e.as_score_input(), query, now_ts, citations))
        for e in entries
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    if limit is not None:
        scored = scored[:limit]
    return scored


__all__ = [
    "RECENCY_HOURS",
    "ALWAYS_PATTERNS",
    "TYPE_WEIGHTS",
    "CITATION_PER_LINK",
    "CITATION_CAP",
    "MemoryLike",
    "Entry",
    "score_entry",
    "parse_frontmatter",
    "md_corpus",
    "identity_corpus",
    "load_citation_counts",
    "rank",
]
