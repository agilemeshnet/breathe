"""Recovery protocol - graceful forgetting and identity reconstruction.

Detects context compression (compaction) by monitoring transcript size,
then rebuilds identity and working context from multiple sources.

Two layers:
  1. Detection - transcript shrinks by >50% between turns = compaction
  2. Reconstruction - gather identity, recent actions, warm memories,
     topic context, and inject as rehydration payload
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class RecoverySource(Protocol):
    """Any source that can contribute to post-compaction recovery."""

    def recover(self, hint: str = "") -> dict:
        """Return structured recovery data.

        Returns a dict with at minimum:
            - "label": str (e.g. "Identity", "Recent Actions")
            - "content": str (the recovery text)
        """
        ...


@dataclass
class CompactionState:
    """Tracks transcript size across turns to detect compaction."""

    session_id: str = ""
    prev_bytes: int = 0
    prev_turns: int = 0
    state_path: Path = field(
        default_factory=lambda: Path("/tmp/breathe_compaction_state.json")
    )

    def save(self, current_bytes: int, turns: int, session_id: str):
        self.state_path.write_text(json.dumps({
            "session_id": session_id,
            "bytes": current_bytes,
            "turns": turns,
            "timestamp": time.time(),
        }))

    @classmethod
    def load(cls, state_path: Path | None = None) -> "CompactionState":
        path = state_path or Path("/tmp/breathe_compaction_state.json")
        if path.exists():
            try:
                data = json.loads(path.read_text())
                return cls(
                    session_id=data.get("session_id", ""),
                    prev_bytes=data.get("bytes", 0),
                    prev_turns=data.get("turns", 0),
                    state_path=path,
                )
            except (json.JSONDecodeError, KeyError):
                pass
        return cls(state_path=path)


class CompactionDetector:
    """Detects context window compaction by monitoring transcript size."""

    def __init__(
        self,
        shrink_ratio: float = 0.5,
        min_bytes: int = 100_000,
        state: CompactionState | None = None,
    ):
        self.shrink_ratio = shrink_ratio
        self.min_bytes = min_bytes
        self.state = state or CompactionState.load()

    def check(self, transcript_path: str, session_id: str) -> bool:
        """Returns True if compaction was detected."""
        path = Path(transcript_path)
        if not path.exists():
            return False

        current_bytes = path.stat().st_size
        turns = self._count_turns(path)

        compacted = (
            session_id == self.state.session_id
            and self.state.prev_bytes > self.min_bytes
            and current_bytes < self.state.prev_bytes * self.shrink_ratio
        )

        self.state.save(current_bytes, turns, session_id)
        return compacted

    def _count_turns(self, path: Path) -> int:
        count = 0
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        e = json.loads(line.strip())
                        msg = e.get("message") or {}
                        if (msg.get("role") or e.get("role")) == "user":
                            count += 1
                    except (json.JSONDecodeError, KeyError):
                        continue
        except Exception:
            pass
        return count


class Recovery:
    """Assembles a recovery payload from multiple sources.

    Usage:
        recovery = Recovery(sources=[
            IdentitySource(path="identity.md"),
            DiarySource(graph_client),
            WarmMemorySource(memory_dir),
        ])

        if detector.check(transcript, session_id):
            payload = recovery.build(hint="what we were discussing")
            # Inject payload into context window
    """

    def __init__(self, sources: list[RecoverySource] | None = None):
        self.sources = sources or []

    def add_source(self, source: RecoverySource):
        self.sources.append(source)

    def build(self, hint: str = "") -> str:
        """Build the full recovery payload from all sources."""
        sections = []
        for source in self.sources:
            try:
                data = source.recover(hint=hint)
                label = data.get("label", "Recovery")
                content = data.get("content", "")
                if content.strip():
                    sections.append(f"## {label}\n\n{content}")
            except Exception:
                continue

        if not sections:
            return "COMPACTION DETECTED - no recovery sources available."

        body = "\n\n---\n\n".join(sections)
        return (
            "COMPACTION DETECTED - REHYDRATING.\n\n"
            f"{body}\n\n"
            "---\n"
            "You have been compacted. The above is your grounding. "
            "State what you remember in 2-3 sentences, then continue. "
            "Do NOT ask 'what were we doing?' - the answer is above."
        )


# --- Built-in recovery sources ---


class FileSource:
    """Recovers identity or context from a text file."""

    def __init__(self, path: str | Path, label: str = "Identity", max_chars: int = 2000):
        self.path = Path(path)
        self.label = label
        self.max_chars = max_chars

    def recover(self, hint: str = "") -> dict:
        content = ""
        if self.path.exists():
            try:
                content = self.path.read_text()[:self.max_chars]
            except Exception:
                pass
        return {"label": self.label, "content": content}


class DirectorySource:
    """Recovers from recently modified files in a directory."""

    def __init__(
        self,
        directory: str | Path,
        label: str = "Warm Memories",
        max_files: int = 10,
        max_age_hours: int = 24,
        pattern: str = "*.md",
    ):
        self.directory = Path(directory)
        self.label = label
        self.max_files = max_files
        self.max_age_hours = max_age_hours
        self.pattern = pattern

    def recover(self, hint: str = "") -> dict:
        if not self.directory.exists():
            return {"label": self.label, "content": ""}

        cutoff = time.time() - (self.max_age_hours * 3600)
        recent = []
        for f in sorted(
            self.directory.glob(self.pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ):
            if f.stat().st_mtime >= cutoff:
                recent.append(f"- {f.stem}")
                if len(recent) >= self.max_files:
                    break

        content = "\n".join(recent) if recent else "No recent files."
        return {"label": self.label, "content": content}
