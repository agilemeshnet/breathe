"""Multi-arm retrieval - four independent paths to the same query.

Most retrieval systems ask one question: "what matches this?"
Multi-arm retrieval asks four:

1. Vector: "What sounds like what you're asking?"
2. Graph: "What connects to what was found?"
3. Episodic: "What did we decide about this before?"
4. Speculative: "What's unexpectedly close?"

Results from all arms are assembled and optionally compressed
through a token budget.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class RetrievalArm(Protocol):
    """A single retrieval pathway."""

    name: str

    def search(self, query: str, k: int = 10) -> list[dict]:
        """Return up to k results for the query.

        Each result should have at minimum:
            - "name": str
            - "score": float (0-1, higher = more relevant)

        Optional but useful:
            - "labels": list[str]
            - "description": str
            - "relationship": str (for graph arms)
            - "source": str
            - "target": str
        """
        ...


@dataclass
class RetrievalResult:
    """Combined results from all arms."""

    query: str
    vector: list[dict]
    graph: list[dict]
    episodic: list[dict]
    speculative: list[dict]

    def to_markdown(self, max_per_arm: int = 8) -> str:
        """Render all results as structured markdown."""
        sections = []

        if self.vector:
            items = []
            for h in self.vector[:max_per_arm]:
                name = h.get("name", "?")
                labels = ", ".join(h.get("labels", []))
                score = h.get("score", 0)
                desc = h.get("description", "")
                line = f"- **{name}**"
                if labels:
                    line += f" ({labels})"
                if score:
                    line += f" [{score:.3f}]"
                if desc:
                    line += f" - {desc[:120]}"
                items.append(line)
            sections.append("## Semantically Similar\n" + "\n".join(items))

        if self.graph:
            items = []
            for r in self.graph[:max_per_arm]:
                src = r.get("source", "?")
                rel = r.get("relationship", "?")
                tgt = r.get("target", "?")
                items.append(f"- {src} -[{rel}]-> {tgt}")
            sections.append("## Connected\n" + "\n".join(items))

        if self.episodic:
            items = []
            for e in self.episodic[:max_per_arm]:
                problem = e.get("problem", e.get("name", "?"))
                outcome = e.get("outcome", e.get("description", ""))
                items.append(f"- **{problem}**: {outcome[:120]}")
            sections.append("## Past Decisions\n" + "\n".join(items))

        if self.speculative:
            items = []
            for s in self.speculative[:max_per_arm]:
                a = s.get("source", s.get("name", "?"))
                b = s.get("target", "?")
                score = s.get("score", 0)
                items.append(f"- {a} <-> {b} [{score:.3f}]")
            sections.append("## Surprising Connections\n" + "\n".join(items))

        return "\n\n".join(sections) if sections else f"No results for: {self.query}"

    @property
    def total_count(self) -> int:
        return len(self.vector) + len(self.graph) + len(self.episodic) + len(self.speculative)


class MultiArmRetriever:
    """Orchestrates retrieval across multiple arms.

    Usage:
        retriever = MultiArmRetriever()
        retriever.add_arm(FaissArm(index_path="embeddings.npz"))
        retriever.add_arm(Neo4jArm(driver=driver))
        retriever.add_arm(EpisodicArm(driver=driver))
        retriever.add_arm(SpeculativeArm(findings_path="findings.jsonl"))

        result = retriever.search("claims processing pipeline", k=10)
        print(result.to_markdown())
    """

    def __init__(self):
        self._arms: dict[str, RetrievalArm] = {}

    def add_arm(self, arm: RetrievalArm, role: str | None = None):
        """Register a retrieval arm.

        role: one of "vector", "graph", "episodic", "speculative".
              If not specified, uses arm.name.
        """
        key = role or arm.name
        self._arms[key] = arm

    def search(self, query: str, k: int = 10) -> RetrievalResult:
        """Fire all arms and assemble results."""
        results = {}
        for role in ["vector", "graph", "episodic", "speculative"]:
            arm = self._arms.get(role)
            if arm:
                try:
                    results[role] = arm.search(query, k=k)
                except Exception:
                    results[role] = []
            else:
                results[role] = []

        return RetrievalResult(
            query=query,
            vector=results["vector"],
            graph=results["graph"],
            episodic=results["episodic"],
            speculative=results["speculative"],
        )
