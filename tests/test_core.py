"""Core module tests - breathing, recovery, identity, retrieval."""

import json
import os
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.breathing import Breathing, BreathingState
from core.recovery import CompactionDetector, Recovery, FileSource
from core.identity import Identity, Memory
from core.retrieval import RetrievalResult, MultiArmRetriever
from adapters.sqlite import SQLiteStore


def test_breathing_one_turn_delay():
    """Query fires on cadence turn, injection surfaces on the next."""
    with tempfile.TemporaryDirectory() as tmp:
        store = SQLiteStore(f"{tmp}/test.db")
        store.add("topic-a", "Content about topic A", description="Test topic")

        state = BreathingState(
            cache_path=Path(f"{tmp}/cache.json"),
            state_path=Path(f"{tmp}/state.json"),
        )
        b = Breathing(store=store, cadence=3, background=False, state=state)

        r1 = b.tick("hello")
        r2 = b.tick("how are you")
        r3 = b.tick("tell me about topic-a")
        assert r1 is None, "Turn 1 should have no injection"
        assert r2 is None, "Turn 2 should have no injection"
        assert r3 is None, "Turn 3 fires query but injection is next turn"

        r4 = b.tick("follow up question")
        assert r4 is not None, "Turn 4 should inject cached results from turn 3"
        assert "topic-a" in r4

        store.close()


def test_breathing_cache_updates():
    """New query on turn 6 should update the cache for turn 7."""
    with tempfile.TemporaryDirectory() as tmp:
        store = SQLiteStore(f"{tmp}/test.db")
        store.add("alpha", "Alpha content", description="First")
        store.add("beta", "Beta content", description="Second")

        state = BreathingState(
            cache_path=Path(f"{tmp}/cache.json"),
            state_path=Path(f"{tmp}/state.json"),
        )
        b = Breathing(store=store, cadence=3, background=False, state=state)

        for _ in range(3):
            b.tick("tell me about alpha")
        r4 = b.tick("still alpha")
        assert r4 is not None and "alpha" in r4

        b.tick("something else")
        b.tick("tell me about beta")
        r7 = b.tick("follow up on beta")
        assert r7 is not None and "beta" in r7

        store.close()


def test_identity_remember_recall():
    """Identity stores and retrieves memories."""
    with tempfile.TemporaryDirectory() as tmp:
        identity = Identity(store_path=f"{tmp}/id.json")
        identity.remember(Memory(
            name="test-pref",
            type="feedback",
            description="User prefers direct answers",
        ))

        recalled = identity.recall("feedback")
        assert len(recalled) == 1
        assert recalled[0].name == "test-pref"

        identity.forget("test-pref")
        assert len(identity.recall("feedback")) == 0


def test_identity_recovery_source():
    """Identity implements RecoverySource protocol."""
    with tempfile.TemporaryDirectory() as tmp:
        identity = Identity(store_path=f"{tmp}/id.json")
        identity.remember(Memory(name="researcher", type="user", description="Researcher"))

        result = identity.recover()
        assert "label" in result
        assert "researcher" in result["content"].lower()


def test_sqlite_fts5_sanitisation():
    """FTS5 handles punctuation and hyphens without crashing."""
    with tempfile.TemporaryDirectory() as tmp:
        store = SQLiteStore(f"{tmp}/test.db")
        store.add("real-world example", "Something practical", description="Test")

        results = store.query("What about real-world examples?")
        assert len(results) > 0, "FTS5 should handle hyphens and question marks"

        results2 = store.query("!@#$%")
        assert results2 == [], "Garbage input should return empty, not crash"

        store.close()


def test_sqlite_decisions_and_diary():
    """SQLite stores and retrieves decisions and diary entries."""
    with tempfile.TemporaryDirectory() as tmp:
        store = SQLiteStore(f"{tmp}/test.db")
        store.add_decision("context window filling", "built breathing system", significance=9)
        store.add_diary(action="tested breathing", agent="test")

        decisions = store.query_decisions("context window")
        assert len(decisions) > 0

        diary = store.recent_diary(limit=1)
        assert len(diary) == 1
        assert diary[0]["action"] == "tested breathing"

        store.close()


def test_recovery_builds_payload():
    """Recovery assembles a rehydration payload from multiple sources."""
    with tempfile.TemporaryDirectory() as tmp:
        store = SQLiteStore(f"{tmp}/test.db")
        store.add_diary(action="seeded test data", agent="test")

        identity = Identity(store_path=f"{tmp}/id.json")
        identity.remember(Memory(name="dev", type="user", description="Developer"))

        recovery = Recovery(sources=[identity, store])
        payload = recovery.build(hint="test recovery")

        assert "COMPACTION DETECTED" in payload
        assert "Developer" in payload or "dev" in payload

        store.close()


def test_multi_arm_retriever():
    """MultiArmRetriever combines results from multiple arms."""
    with tempfile.TemporaryDirectory() as tmp:
        store = SQLiteStore(f"{tmp}/test.db")
        store.add("concept-x", "Important concept", description="Test")

        retriever = MultiArmRetriever()
        retriever.add_arm(store, role="graph")

        result = retriever.search("concept-x")
        assert result.total_count > 0, f"Expected results, got {result.total_count}"
        assert len(result.graph) == 1, "Should have one graph result"

        store.close()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS  {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {test.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed out of {passed + failed}")
