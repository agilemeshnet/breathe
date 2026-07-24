#!/usr/bin/env python3
"""Breathe quickstart - runs in 30 seconds with zero dependencies beyond Python 3.10+.

Demonstrates the breathing system with a SQLite store.
No graph database, no vector index, no API keys needed.

Usage:
    python3 quickstart.py
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.breathing import Breathing, BreathingState
from core.recovery import CompactionDetector, Recovery, FileSource
from core.identity import Identity, Memory
from adapters.sqlite import SQLiteStore


def main():
    print("=== Breathe Quickstart ===\n")

    # 1. Create a SQLite store (zero dependencies)
    store = SQLiteStore("/tmp/breathe_quickstart.db")
    print("1. SQLite store created at /tmp/breathe_quickstart.db")

    # 2. Seed it with some knowledge
    store.add("sheaf theory", "Mathematical framework for local-to-global consistency",
              labels=["mathematics"], description="Topology concept")
    store.add("context window", "The amount of text an LLM can process at once",
              labels=["ai"], description="Typically 128K-200K tokens")
    store.add("Andy Clark", "Philosopher who proposed the Extended Mind thesis with Chalmers",
              labels=["philosophy", "person"], description="Extended cognition")
    store.add("Patrick Jones", "Catholic deacon who uses Evernote as extended memory due to memory condition",
              labels=["case-study", "person"], description="Real-world extended mind")
    store.add("breathing system", "Proactive background queries every N turns",
              labels=["architecture"], description="CWB innovation")

    store.add_decision(
        problem="How to handle context window compaction",
        outcome="Built breathing system: background queries + cached injection",
        significance=9,
    )
    store.add_diary(action="Seeded quickstart knowledge base", agent="quickstart")
    print("2. Seeded 5 memories, 1 decision, 1 diary entry\n")

    # 3. Set up the identity layer
    identity = Identity(store_path="/tmp/breathe_quickstart_identity.json")
    identity.remember(Memory(
        name="prefers-direct-answers",
        type="feedback",
        description="User wants headline first, details after",
    ))
    identity.remember(Memory(
        name="researcher",
        type="user",
        description="User is a researcher interested in cognitive architectures",
    ))
    print("3. Identity layer initialised with 2 memories")
    print(f"   Identity summary:\n{identity.summarise()}\n")

    # 4. Set up the breathing system
    state = BreathingState(
        cache_path=Path("/tmp/breathe_qs_cache.json"),
        state_path=Path("/tmp/breathe_qs_state.json"),
    )
    breathing = Breathing(
        store=store,
        cadence=3,
        background=False,  # synchronous for demo clarity
        state=state,
    )
    print("4. Breathing system ready (cadence: every 3 turns)\n")

    # 5. Simulate a conversation
    messages = [
        "Tell me about the extended mind thesis",
        "How does Clark's parity principle work?",
        "What about real-world examples like Patrick Jones?",
        "How does the breathing system connect to this?",
        "Can you explain sheaf theory?",
        "What decisions have we made about context windows?",
        "How does all of this connect back to Andy Clark?",
    ]

    print("5. Simulating 7-turn conversation:\n")
    for i, msg in enumerate(messages, 1):
        injection = breathing.tick(msg)
        print(f"   Turn {i}: \"{msg[:50]}...\"")
        if injection:
            print(f"   >>> INJECTION: {injection}")
        else:
            print(f"   >>> (no injection this turn)")
        print()

    # 6. Show recovery
    print("6. Recovery payload (what would be injected after compaction):\n")
    recovery = Recovery(sources=[
        identity,  # Identity implements RecoverySource
        store,     # SQLiteStore implements RecoverySource
    ])
    payload = recovery.build(hint="extended mind thesis")
    print(payload[:500])
    print("   ...")

    # Clean up
    store.close()
    print("\n=== Done. The breathing system works. ===")


if __name__ == "__main__":
    main()
