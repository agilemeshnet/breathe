#!/usr/bin/env python3
"""Generic hook for any AI coding tool that supports pre-prompt injection.

Usage:
    # From your tool's hook system, call with the user's message as argument:
    python3 -m breathe.hooks.generic "tell me about sheaf theory"

    # Or pipe the message:
    echo "tell me about sheaf theory" | python3 -m breathe.hooks.generic

Prints injection text to stdout if the breathing cycle has cached results.
Prints nothing if no injection is ready (the tool should treat empty stdout as no-op).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.breathing import Breathing, BreathingState
from adapters.sqlite import SQLiteStore

BREATHE_DIR = Path.home() / ".breathe"


def main():
    BREATHE_DIR.mkdir(parents=True, exist_ok=True)

    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
    else:
        message = sys.stdin.read().strip()

    if not message:
        return

    store = SQLiteStore(str(BREATHE_DIR / "memory.db"))
    state = BreathingState(
        cache_path=BREATHE_DIR / "cache.json",
        state_path=BREATHE_DIR / "state.json",
    )
    breathing = Breathing(store=store, cadence=3, background=False, state=state)
    injection = breathing.tick(message)
    store.close()

    if injection:
        print(injection)


if __name__ == "__main__":
    main()
