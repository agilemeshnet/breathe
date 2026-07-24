# breathe

**Memory frameworks retrieve. Breathe remembers.**

You know what it feels like to forget someone's name mid-sentence. The face is right there, the context is right there, you were just talking about them - but the word is gone. Now imagine that happening to every conversation you have ever had, every few hours, permanently.

That is what happens to an AI in a long conversation. The context window fills. Older material compresses. The model does not know it has forgotten. It continues speaking with the same confidence, but the thread that connected Tuesday's decision to Thursday's question has silently snapped.

Most memory frameworks solve this by building a better filing cabinet. Store more. Index better. Retrieve faster. And that works - for the moment someone thinks to ask. But human memory does not work that way. You do not query your past. Your past queries you. A smell pulls up a room you have not thought about in years. A phrase someone uses reminds you of a decision you made last week. Associations surface uninvited.

Breathe works that way.

## What it does

### Breathing

Every few conversational turns, breathe queries the knowledge store with whatever the person is currently talking about. Not because anyone asked - because that is what tethered memory does. The results arrive one turn later, as peripheral context. The model does not have to stop and search. The relevant past is already in the room.

This is the difference between a notebook you carry and a notebook that reads itself back to you while you work.

### Recovery

Forgetting will happen. Context windows are finite. The useful goal is not preventing forgetting - it is waking up oriented rather than blank.

When compression happens, breathe detects it and rebuilds: who the agent is, what it was working on, what decisions were made, what the person cares about. The model opens its eyes knowing where it is.

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
                    |  Knowledge  |
                    |    Store    |
                    +-------------+
```

Retrieval has four arms, each returning different evidence for the same query:

- **Vector** - what sounds like this?
- **Graph** - what connects to this?
- **Episodic** - have we been here before?
- **Speculative** - what else might matter?

Breathe sits on top of existing knowledge stores, not instead of them. SQLite works out of the box. Neo4j, FAISS, Cognee, Mem0, and ChromaDB adapters are planned.

## Try it

```bash
git clone https://github.com/agilemeshnet/breathe.git
cd breathe
python3 examples/quickstart.py
```

No dependencies beyond Python. No API keys. No cloud services.

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

MCP server:

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

## Contributing

Contributions welcome - especially adapters for additional knowledge stores.

## License

MIT
