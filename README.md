# breathe

**Memory frameworks retrieve. Breathe remembers.**

You know what it feels like to forget someone's name mid-sentence. The face is right there, the context is right there, you were just talking about them - but the word is gone. Now imagine that happening to every conversation you have ever had, every few hours, permanently.

That is what happens to an AI in a long conversation. The context window fills. Older material compresses. The model does not know it has forgotten. It continues speaking with the same confidence, but the thread that connected Tuesday's decision to Thursday's question has silently snapped.

Most memory frameworks solve this by building a better filing cabinet. Store more. Index better. Retrieve faster. And that works - for the moment someone thinks to ask. But human memory does not work that way. You do not query your past. Your past queries you. A smell pulls up a room you have not thought about in years. A phrase someone uses reminds you of a decision you made last week. Associations surface uninvited.

Breathe works that way.

## Why a graph

Memory has structure. A decision connects to the problem it solved. A person connects to the projects they work on. A concept connects to the concepts it depends on. These connections are not metadata - they are the memory. When you remember a conversation, you do not retrieve a row from a table. You walk a web of associations until the right one lights up.

A graph database is the natural shape of that web. Flat storage gives you retrieval. Graph gives you neighbourhood - the ability to ask not just "what do I know about this?" but "what connects to this, and what connects to that?"

Four retrieval arms, each walking the graph differently:

- **Vector** - what sounds like this? (semantic similarity across embedded nodes)
- **Graph** - what connects to this? (neighbourhood walks, two hops out)
- **Episodic** - have we been here before? (past decisions, ordered by time)
- **Speculative** - what else might matter? (cross-domain paths the user did not ask for)

All four arms fire on the same query. Results are merged and injected. The model gets multidimensional evidence, not a ranked list.

## What it does

### Breathing

Every few conversational turns, breathe queries the graph with whatever the person is currently talking about. Not because anyone asked - because that is what tethered memory does. The results arrive one turn later, as peripheral context. The model does not have to stop and search. The relevant past is already in the room.

This is the difference between a notebook you carry and a notebook that reads itself back to you while you work.

### Recovery

Forgetting will happen. Context windows are finite. The useful goal is not preventing forgetting - it is waking up oriented rather than blank.

When compression happens, breathe detects it and rebuilds from the graph: who the agent is, what it was working on, what decisions were made, what the person cares about. The model opens its eyes knowing where it is.

You have experienced this if you have ever woken up in a hotel room. For a moment you do not know where you are. Then the pieces arrive: the city, the reason for the trip, what you need to do today. Recovery is engineering that moment to be fast and reliable instead of slow and partial.

### Identity

Two people asking the same question should get different answers from memory. A researcher asking "what about sheaf theory" needs the mathematical structure. A product manager asking the same question needs the business implication. What surfaces should be shaped by who is asking - their preferences, their history, their rejected approaches, their arc.

This is not personalisation. It is how memory works. Your memory of a conversation is shaped by your relationship to the person you were talking to. The same words carry different weight depending on who said them.

## How it works

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
                    |    Graph    |
                    |   Database  |  <-- Neo4j, AuraDB, Memgraph...
                    +-------------+
```

## Get started

### With Neo4j (recommended)

```bash
pip install neo4j
```

```python
from adapters.neo4j import Neo4jStore

store = Neo4jStore(
    uri="neo4j+s://your-instance.databases.neo4j.io",
    user="neo4j",
    password="your-password",
)

store.add("project-alpha", "Rewriting the claims pipeline",
          labels=["project"], description="Q3 initiative")
store.add("decision-batch-size", "Chose 500 over 1000 after load testing",
          labels=["decision"])
store.connect("decision-batch-size", "project-alpha", "DECIDED_FOR")

results = store.query("claims pipeline")
neighbours = store.neighbourhood("project-alpha", depth=2)
```

Memories are nodes. Relationships are first-class. Neighbourhood walks give you what flat search cannot - the context around the answer, not just the answer.

[Neo4j AuraDB Free](https://neo4j.com/cloud/aura-free/) gives you a graph database in two minutes, no credit card.

### Quick demo (no database needed)

```bash
git clone https://github.com/agilemeshnet/breathe.git
cd breathe
python3 examples/quickstart.py
```

The quickstart uses SQLite to demonstrate the breathing cycle without any setup. For real use, point it at a graph.

## Use it

Claude Code hook:

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

MCP server (exposes `foveate`, `ground`, and `remember` tools):

```json
{
  "mcpServers": {
    "breathe": {
      "command": "python3",
      "args": ["/path/to/breathe/mcp/server.py"]
    }
  }
}
```

## Adapters

| Adapter | Status | Why |
|---------|--------|-----|
| Neo4j | Working | Graph-native. Neighbourhood walks, relationship queries, multidimensional retrieval |
| SQLite (FTS5) | Working | Zero-dependency demo and lightweight use |
| FAISS | Planned | Vector similarity arm |
| Cognee | Planned | Semantic memory with ontology |
| Mem0 | Planned | Fact extraction |
| ChromaDB | Planned | Vector store alternative |

## Contributing

Contributions welcome - especially adapters for additional knowledge stores.

## License

MIT
