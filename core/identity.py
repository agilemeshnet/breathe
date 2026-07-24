"""Identity layer - accumulated model of who the agent serves.

This is the piece every other memory framework misses: retrieval
shaped by the person's trajectory, not just semantic similarity.

The identity accumulates across sessions. Feedback, preferences,
intellectual arc, emotional register, rejected approaches - all
of it informs what surfaces and how it's framed.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Memory:
    """A single memory entry in the identity model."""

    name: str
    type: str  # user, feedback, project, reference
    description: str
    body: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "body": self.body,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Memory":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class Identity:
    """Persistent identity model that accumulates across sessions.

    Usage:
        identity = Identity(store_path="~/.breathe/identity.json")

        # Record what you learn about the person
        identity.remember(Memory(
            name="prefers-direct-answers",
            type="feedback",
            description="User wants headline first, no preamble",
            body="Corrected twice for long introductions before answers."
        ))

        # Get relevant memories for a context
        relevant = identity.recall(types=["feedback", "user"], limit=10)

        # Get the full identity summary for recovery
        summary = identity.summarise()
    """

    def __init__(self, store_path: str | Path = "~/.breathe/identity.json"):
        self.store_path = Path(store_path).expanduser()
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.memories: dict[str, Memory] = {}
        self._load()

    def _load(self):
        if self.store_path.exists():
            try:
                data = json.loads(self.store_path.read_text())
                for name, entry in data.items():
                    self.memories[name] = Memory.from_dict(entry)
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        data = {name: mem.to_dict() for name, mem in self.memories.items()}
        self.store_path.write_text(json.dumps(data, indent=2))

    def remember(self, memory: Memory):
        """Add or update a memory."""
        if memory.name in self.memories:
            memory.created_at = self.memories[memory.name].created_at
        memory.updated_at = time.time()
        self.memories[memory.name] = memory
        self._save()

    def forget(self, name: str) -> bool:
        """Remove a memory by name."""
        if name in self.memories:
            del self.memories[name]
            self._save()
            return True
        return False

    def recall(
        self,
        types: list[str] | None = None,
        limit: int = 20,
    ) -> list[Memory]:
        """Get memories, optionally filtered by type, sorted by recency."""
        memories = list(self.memories.values())
        if types:
            memories = [m for m in memories if m.type in types]
        memories.sort(key=lambda m: m.updated_at, reverse=True)
        return memories[:limit]

    def summarise(self, max_per_type: int = 5) -> str:
        """Build a summary string suitable for context injection."""
        by_type: dict[str, list[Memory]] = {}
        for mem in self.memories.values():
            by_type.setdefault(mem.type, []).append(mem)

        type_labels = {
            "user": "Who They Are",
            "feedback": "How They Want To Work",
            "project": "What's Active",
            "reference": "Where To Look",
        }

        sections = []
        for mem_type in ["user", "feedback", "project", "reference"]:
            mems = by_type.get(mem_type, [])
            if not mems:
                continue
            mems.sort(key=lambda m: m.updated_at, reverse=True)
            label = type_labels.get(mem_type, mem_type.title())
            items = [f"- **{m.name}**: {m.description}" for m in mems[:max_per_type]]
            sections.append(f"### {label}\n" + "\n".join(items))

        return "\n\n".join(sections) if sections else "No identity memories stored."

    def recover(self, hint: str = "") -> dict:
        """RecoverySource interface - returns identity for post-compaction."""
        return {
            "label": "Identity",
            "content": self.summarise(),
        }
