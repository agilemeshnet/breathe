"""Breathing system - proactive background context retrieval.

Fires every N conversational turns, queries a knowledge store with the
current topic, caches results, and injects them into the next turn as
peripheral context. One-turn delayed, like memory catching up.

Zero added latency: the query runs in background on turn T,
results surface on turn T+1.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class Store(Protocol):
    """Any knowledge store that can answer a text query."""

    def query(self, text: str, k: int = 10) -> list[dict]:
        """Return up to k relevant items for the given text."""
        ...


@dataclass
class BreathingState:
    """Tracks the breathing cycle across turns."""

    turn_count: int = 0
    last_query: str = ""
    last_results: list[dict] = field(default_factory=list)
    last_query_time: float = 0.0
    cache_path: Path = field(default_factory=lambda: Path("/tmp/breathe_cache.json"))
    state_path: Path = field(default_factory=lambda: Path("/tmp/breathe_state.json"))

    def save(self):
        self.state_path.write_text(json.dumps({
            "turn_count": self.turn_count,
            "last_query": self.last_query,
            "last_query_time": self.last_query_time,
        }))

    @classmethod
    def load(cls, state_path: Path | None = None) -> "BreathingState":
        path = state_path or Path("/tmp/breathe_state.json")
        if path.exists():
            try:
                data = json.loads(path.read_text())
                return cls(
                    turn_count=data.get("turn_count", 0),
                    last_query=data.get("last_query", ""),
                    last_query_time=data.get("last_query_time", 0.0),
                    state_path=path,
                )
            except (json.JSONDecodeError, KeyError):
                pass
        return cls(state_path=path)


class Breathing:
    """The breathing system.

    Usage:
        breathing = Breathing(store=my_store, cadence=3)

        # On each conversational turn:
        injection = breathing.tick(user_message="tell me about sheaf theory")
        if injection:
            # Add to context window as peripheral note
            context += injection
    """

    def __init__(
        self,
        store: Store,
        cadence: int = 3,
        max_results: int = 8,
        background: bool = True,
        state: BreathingState | None = None,
    ):
        self.store = store
        self.cadence = cadence
        self.max_results = max_results
        self.background = background
        self.state = state or BreathingState.load()

    def tick(self, user_message: str) -> str | None:
        """Called on each conversational turn.

        Returns an injection string if cached results are available,
        and fires a background query if the cadence says it's time.

        The one-turn delay is the key design:
        - Turn N (cadence hit): fire query in background
        - Turn N+1: inject cached results from that query

        In sync mode, the query completes immediately but injection
        still waits for the next tick - matching the async behaviour.
        """
        self.state.turn_count += 1
        injection = None

        if self.state.turn_count > self.cadence:
            injection = self._read_cache()

        if self.state.turn_count % self.cadence == 0 and user_message.strip():
            self._fire_query(user_message)

        self.state.save()
        return injection

    def _read_cache(self) -> str | None:
        """Read cached results from the last background query."""
        if not self.state.cache_path.exists():
            return None
        try:
            cache = json.loads(self.state.cache_path.read_text())
            names = cache.get("top_names", [])
            query = cache.get("query", "")
            if not names:
                return None
            names_str = ", ".join(names[:6])
            return (
                f"GROUNDING (turn {self.state.turn_count}): "
                f"Memory sees [{names_str}] near \"{query[:60]}\". "
                f"Query for depth if needed."
            )
        except (json.JSONDecodeError, KeyError):
            return None

    def _fire_query(self, query: str):
        """Fire a background query to the store."""
        self.state.last_query = query[:500]
        self.state.last_query_time = time.time()

        if self.background:
            self._fire_background(query)
        else:
            self._fire_sync(query)

    def _fire_sync(self, query: str):
        """Synchronous query - blocks but simpler."""
        try:
            results = self.store.query(query, k=self.max_results)
            names = [r.get("name", "") for r in results if r.get("name")]
            cache = {"query": query[:500], "top_names": names[:8]}
            self.state.cache_path.write_text(json.dumps(cache))
        except Exception:
            pass

    def _fire_background(self, query: str):
        """Fire query in a subprocess so it doesn't block the turn."""
        script = self._build_query_script(query)
        try:
            subprocess.Popen(
                [sys.executable, "-c", script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except Exception:
            self._fire_sync(query)

    def _build_query_script(self, query: str) -> str:
        """Build a self-contained Python script for background execution.

        Subclasses or adapters override this to call their specific store.
        The default writes an empty cache (override in adapters).
        """
        cache_path = str(self.state.cache_path)
        return f"""
import json
cache = {{"query": {json.dumps(query[:500])}, "top_names": []}}
with open({json.dumps(cache_path)}, "w") as f:
    json.dump(cache, f)
"""


class BreathingHook:
    """Claude Code hook integration.

    Wire this into a UserPromptSubmit hook to get automatic breathing.
    Reads the hook payload from stdin, fires breathing, prints injection.
    """

    def __init__(self, breathing: Breathing):
        self.breathing = breathing

    def run(self, payload: dict) -> str | None:
        """Process a hook payload and return any injection text."""
        transcript_path = payload.get("transcript_path", "")
        if not transcript_path:
            return None

        last_message = self._extract_last_user_message(transcript_path)
        if not last_message:
            return None

        return self.breathing.tick(last_message)

    def _extract_last_user_message(self, transcript_path: str) -> str:
        """Extract the most recent user message from a JSONL transcript."""
        last = ""
        path = Path(transcript_path)
        if not path.exists():
            return last
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        e = json.loads(line)
                        msg = e.get("message") or {}
                        role = msg.get("role") or e.get("role")
                        if role == "user":
                            content = msg.get("content") if msg else e.get("content")
                            if isinstance(content, str):
                                last = content
                            elif isinstance(content, list):
                                texts = [
                                    c.get("text", "")
                                    for c in content
                                    if isinstance(c, dict) and c.get("type") == "text"
                                ]
                                if texts:
                                    last = " ".join(texts)
                    except (json.JSONDecodeError, KeyError):
                        continue
        except Exception:
            pass
        return last[:500]
