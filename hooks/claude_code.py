#!/usr/bin/env python3
"""Claude Code UserPromptSubmit hook.

Wire into .claude/settings.json:

    {
      "hooks": {
        "UserPromptSubmit": [{
          "type": "command",
          "command": "python3 /path/to/breathe/hooks/claude_code.py"
        }]
      }
    }

On each user message the hook:
  1. Reads the transcript to find what the user said
  2. Ticks the breathing system (fires a query if cadence hit)
  3. Prints any cached injection to stdout (Claude Code injects it)

The first run creates a SQLite store at ~/.breathe/memory.db.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.breathing import Breathing, BreathingState
from core.recovery import CompactionDetector, Recovery
from core.identity import Identity
from adapters.sqlite import SQLiteStore

BREATHE_DIR = Path.home() / ".breathe"
DB_PATH = BREATHE_DIR / "memory.db"
STATE_PATH = BREATHE_DIR / "state.json"
CACHE_PATH = BREATHE_DIR / "cache.json"
IDENTITY_PATH = BREATHE_DIR / "identity.json"


def _read_payload() -> dict:
    """Read the hook payload from stdin."""
    try:
        return json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        return {}


def _extract_last_user_message(transcript_path: str) -> str:
    """Pull the most recent user message from the JSONL transcript."""
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


def _detect_compaction(transcript_path: str) -> str | None:
    """Check for compaction and return recovery payload if detected."""
    detector = CompactionDetector(transcript_path=transcript_path)
    if not detector.detect():
        return None

    store = SQLiteStore(str(DB_PATH))
    identity = Identity(store_path=str(IDENTITY_PATH))
    recovery = Recovery(sources=[identity, store])
    payload = recovery.build()
    store.close()
    return payload


def main():
    BREATHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = _read_payload()
    transcript_path = payload.get("transcript_path", "")

    if not transcript_path:
        return

    compaction_payload = _detect_compaction(transcript_path)
    if compaction_payload:
        print(compaction_payload)
        return

    user_message = _extract_last_user_message(transcript_path)
    if not user_message:
        return

    store = SQLiteStore(str(DB_PATH))
    state = BreathingState(
        cache_path=CACHE_PATH,
        state_path=STATE_PATH,
    )
    breathing = Breathing(
        store=store,
        cadence=3,
        background=False,
        state=state,
    )

    injection = breathing.tick(user_message)
    store.close()

    if injection:
        print(injection)


if __name__ == "__main__":
    main()
