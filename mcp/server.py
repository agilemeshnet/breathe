#!/usr/bin/env python3
"""Breathe MCP server.

Exposes three tools to any MCP-compatible client:
  - foveate: directed zoom into the knowledge store
  - ground: verify a claim against stored knowledge
  - remember: add a memory to the store

Requires: pip install mcp[server]

Run:
    python3 -m breathe.mcp.server
    # or
    python3 breathe/mcp/server.py

Wire into Claude Code settings as an MCP server:
    {
      "mcpServers": {
        "breathe": {
          "command": "python3",
          "args": ["/path/to/breathe/mcp/server.py"]
        }
      }
    }
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from mcp.server import Server
    from mcp.server.stdio import run_server
    from mcp.types import Tool, TextContent
    HAS_MCP = True
except ImportError:
    HAS_MCP = False

from adapters.sqlite import SQLiteStore
from core.identity import Identity, Memory

BREATHE_DIR = Path.home() / ".breathe"
DB_PATH = BREATHE_DIR / "memory.db"
IDENTITY_PATH = BREATHE_DIR / "identity.json"


def create_server() -> "Server":
    """Build the MCP server with breathe tools."""
    server = Server("breathe")
    store = SQLiteStore(str(DB_PATH))
    identity = Identity(store_path=str(IDENTITY_PATH))

    @server.tool()
    async def foveate(topic: str, k: int = 8) -> list[TextContent]:
        """Directed zoom into the knowledge store on a specific topic.

        Returns relevant memories, decisions, and diary entries.
        Use when you need depth on something specific.
        """
        memories = store.query(topic, k=k)
        decisions = store.query_decisions(topic, k=3)
        diary = store.recent_diary(limit=3)

        parts = []
        if memories:
            items = [f"- **{m['name']}**: {m['content']}" for m in memories]
            parts.append("## Memories\n" + "\n".join(items))
        if decisions:
            items = [f"- {d['problem']} -> {d['outcome']}" for d in decisions]
            parts.append("## Decisions\n" + "\n".join(items))
        if diary:
            items = [f"- [{d['agent']}] {d['action']}" for d in diary]
            parts.append("## Recent Activity\n" + "\n".join(items))

        text = "\n\n".join(parts) if parts else "Nothing found for that topic."
        return [TextContent(type="text", text=text)]

    @server.tool()
    async def ground(claim: str) -> list[TextContent]:
        """Verify a claim against stored knowledge.

        Searches memories for evidence that supports or contradicts the claim.
        Returns what the store knows, or says it has no evidence.
        """
        results = store.query(claim, k=5)
        if not results:
            return [TextContent(
                type="text",
                text=f"No stored evidence for or against: \"{claim}\""
            )]

        items = [f"- **{r['name']}**: {r['content']}" for r in results]
        text = f"Evidence found for \"{claim[:80]}\":\n\n" + "\n".join(items)
        return [TextContent(type="text", text=text)]

    @server.tool()
    async def remember(
        name: str,
        content: str,
        memory_type: str = "project",
        description: str = "",
    ) -> list[TextContent]:
        """Add a memory to the knowledge store.

        Types: user, feedback, project, reference.
        The memory persists across sessions and surfaces during breathing.
        """
        identity.remember(Memory(
            name=name,
            type=memory_type,
            description=description or content[:100],
            body=content,
        ))
        store.add(name, content, labels=[memory_type], description=description)
        return [TextContent(
            type="text",
            text=f"Remembered: {name} ({memory_type})"
        )]

    return server


def main():
    if not HAS_MCP:
        print("MCP server requires: pip install 'mcp[server]'", file=sys.stderr)
        sys.exit(1)

    BREATHE_DIR.mkdir(parents=True, exist_ok=True)
    import asyncio
    server = create_server()
    asyncio.run(run_server(server))


if __name__ == "__main__":
    main()
