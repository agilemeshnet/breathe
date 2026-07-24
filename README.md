# breathe

**Memory frameworks retrieve. Breathe remembers.**

We ran a single AI conversation for five days - across symbology theory, regulatory research, architecture documentation, and product design - without the model losing its thread. This library is how.

## The problem

AI conversations have a ceiling. The context window fills, older messages compress, and the model forgets why it made a decision even if it remembers the decision itself. For short tasks this doesn't matter. For long-running work - research spanning days, projects with history, relationships that accumulate - forgetting is expensive.

## What breathe does differently

Existing memory frameworks (Mem0, Zep, LangMem, Cognee) solve **retrieval**: given a query, find relevant memories. Breathe adds three things they don't have:

### 1. Continuous tethering (breathing)

Every few conversational turns, breathe queries your knowledge store in the background with whatever the user is currently discussing. Results are cached and injected into the *next* turn as peripheral context - one turn delayed, like real memory catching up. Zero latency cost.

```
Turn 15: user asks about sheaf theory
Turn 15: (background) breathe queries the store for "sheaf theory"
Turn 16: user asks a follow-up
Turn 16: breathe injects: "Memory sees [Sheaf Laplacian, FlyWire, Poincare]
          near 'sheaf theory'. Query for depth if needed."
```

The model stays connected to everything it has learned without anyone asking it to look things up.

### 2. Graceful forgetting (recovery)

When context compression happens, breathe detects it (transcript size shrinks >50%) and automatically rebuilds identity and context from multiple sources: who the agent is, what it was doing, what it has learned, what changed recently.

The model wakes up oriented instead of blank.

### 3. Identity-driven retrieval

What surfaces is shaped by who the person is - their preferences, their intellectual arc, their rejected approaches - not just semantic similarity. The identity layer accumulates across sessions.

## Quickstart (30 seconds, zero dependencies)

```bash
git clone https://github.com/agilemeshnet/breathe.git
cd breathe
python3 examples/quickstart.py
```

Uses SQLite only. No graph database, no vector index, no API keys.

## Core components

| Module | Purpose |
|--------|---------|
| `core/breathing.py` | Proactive background queries, cached injection |
| `core/recovery.py` | Compaction detection, multi-source identity reconstruction |
| `core/identity.py` | Persistent person model that accumulates across sessions |
| `core/retrieval.py` | Four-arm retrieval (vector + graph + episodic + speculative) |

## The methodology

**Panorama + Continuous Tethering + Directed Zoom, driven by an accumulated model of the person and their trajectory.**

Three capabilities:
- **Vista** - panoramic overview before zoom
- **Tethering** - background queries every N turns, associations surface uninvited
- **Foveation** - attention directed by salience for this person, not statistical nearest

Plus the foundation:
- **Identity** - persistent model of who the agent serves, built across sessions

## Adapters

Breathe sits on top of existing knowledge stores, not instead of them.

| Adapter | Status | Notes |
|---------|--------|-------|
| SQLite (FTS5) | Working | Zero-dependency starter |
| Neo4j/AuraDB | Planned | Full graph-backed retrieval |
| FAISS | Planned | Vector similarity arm |
| Cognee | Planned | Semantic memory integration |
| Mem0 | Planned | Fact extraction integration |
| ChromaDB | Planned | Vector store alternative |

## Claude Code integration

Breathe includes hooks for Claude Code's `UserPromptSubmit` event:

```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "type": "command",
      "command": "python3 /path/to/breathe/hooks/claude_code.py"
    }]
  }
}
```

The hook fires on every user message, runs the breathing cycle, and prints any injection text to stdout (which Claude Code injects as context).

## Theoretical grounding

The architecture is grounded in Andy Clark and David Chalmers' [Extended Mind thesis](https://en.wikipedia.org/wiki/Extended_mind_thesis) (1998): if an external process performs the same functional role as an internal cognitive process, it is part of cognition. The parity principle.

Real-world precedent: Patrick Jones, a Catholic deacon in Colorado Springs with a memory condition, uses Evernote trails to maintain continuity across social and professional interactions. Clark argues that Jones reaching for his Evernote is not "looking something up" - it is remembering.

Breathe takes this one step further: the system queries the knowledge store *before being asked*, surfacing relevant context proactively - closer to how biological memory actually works, where associations rise unbidden.

## Architecture

```
                    +-----------+
                    |  Context  |
                    |  Window   |
                    +-----+-----+
                          |
                    +-----+-----+
                    | Breathing |  <-- fires every N turns
                    |  System   |  <-- one-turn delayed injection
                    +-----+-----+
                          |
            +-------------+-------------+
            |             |             |
      +-----+-----+ +----+----+ +------+------+
      |  Identity  | | Recovery| |  Multi-Arm  |
      |   Layer    | | Protocol| |  Retrieval  |
      +-----+------+ +----+----+ +------+------+
            |              |             |
            +--------------+-------------+
                           |
                    +------+------+
                    |  Knowledge  |
                    |    Store    |  <-- SQLite, Neo4j, FAISS, Cognee...
                    +-------------+
```

## Contributing

This project grew from a real system running 300+ sessions. Contributions welcome - especially adapters for additional knowledge stores.

## License

MIT

---

*Built by [AgileMesh](https://agilemesh.net). The breathing dot pulses for as long as the conversation runs.*
