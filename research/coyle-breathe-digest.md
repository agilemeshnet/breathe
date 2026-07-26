# Coyle Digest - What It Means for Breathe

Frank Coyle teaches at Berkeley, 35 years in CS, early career in neuroscience. Came back to cognitive science through Agent AI. That arc matters - he is not a graph vendor or an ontology academic. He is watching agents break and asking why.

## His argument in one line

Most agent failures - brittle tools, fragile handoffs, hallucinated states - are symptoms of one missing layer: a formal ontology sitting outside the model as logical guardrails.

## The shape he draws

Two lineages converging. Agents (probabilistic, neural, LLM-based) and ontologies (formal, symbolic, graph-based). Neither is complete alone. Together they make neuro-symbolic AI - which he defines simply as "a way to keep the LLM on its guardrails."

He is explicit that hallucination is a feature, not a bug. "We hallucinate. We imagine things that may not exist, then turn them into reality." The ontology is not there to suppress imagination. It is there to catch the output before it does damage.

## Where he puts the ontology

Not inside the prompt. Not in the training data. In the loop, AFTER the tool runs, BEFORE the result goes back to the model:

```
LLM decides tool call -> tool executes -> ONTOLOGY VALIDATES -> result returns to LLM
```

"Pydantic at the door, ontology at the ledger." Pydantic checks types. Ontology checks meaning. Pure agents with no side effects until the ontology approves.

## What breathe already does

Coyle's architecture puts the ontology as a validation gate in the agent loop. Breathe puts the graph as a continuous awareness layer around the context window. These are complementary positions on the same circle:

| Coyle | Breathe |
|-------|---------|
| Ontology validates AFTER tool use | Graph informs BEFORE the model speaks |
| Gate (binary pass/fail) | Peripheral vision (continuous context) |
| Catches errors | Prevents errors by keeping the model tethered |
| Static constraints (OWL/RDFS) | Dynamic graph (grows with every conversation) |
| Agent loop | Breathing cycle |

Coyle's ontology catches "a second refund on the same order" after it happens. Breathe's graph would have surfaced "this order was already refunded" before the model even considered it - because the breathing cycle would have pulled that neighbourhood into context.

## What breathe should learn from Coyle

1. **Constraint language matters.** OWL's functional properties, disjoint classes, and enumerated values are precise tools for catching specific errors. The graph in breathe stores relationships but does not yet express constraints. A node can say "project-alpha DECIDED_FOR batch-size-500" but cannot say "a project can have only one active batch size" (functional property) or "a refund recipient must be the original buyer, not a support agent" (disjoint classes).

2. **The ledger position.** Coyle puts validation after tool execution. Breathe could add a validation arm to the breathing cycle - when a tool result arrives, check it against graph constraints before injecting it into context. This is the fifth arm: not vector, graph, episodic, or speculative, but **normative** - what SHOULD be true given what we know.

3. **Bottom-up ontology building.** Coyle describes two approaches: top-down (experts define the domain) and bottom-up (events shape the graph). Breathe is already bottom-up - memories accumulate from conversations. But the constraint layer (OWL-style rules) could be top-down: the domain owner defines what relationships are allowed, what properties are functional, what values are enumerated. Graph grows bottom-up, constraints applied top-down.

## What Coyle is missing

He does not address memory. His ontology is static - defined by experts or accumulated from events, but not breathing. It validates, but it does not orient. There is no Vista (panoramic awareness), no breathing cycle (continuous tethering), no recovery (surviving compression). His agents check the ontology like a bouncer checks IDs. Breathe's agents live inside the graph like fish in water.

The two approaches need each other. An ontology without breathing is a filing cabinet with rules. Breathing without ontological constraints is peripheral vision with no depth perception.

## The Gruber definition

Coyle quotes Gruber 1993: "A formal specification of a shared conceptualization."

Every word matters for breathe:
- **Formal** - structured, machine-readable, not prose
- **Specification** - explicit, not implicit
- **Shared** - multiple agents, one graph (this is already in breathe's README)
- **Conceptualization** - the domain owner's understanding, not the model's guess

The graph in breathe IS the shared conceptualization. What it does not yet have is the formal specification layer - the constraints that say what relationships are valid, what properties are unique, what classes are disjoint.

## Connection to the paper

Coyle's convergence of neural and symbolic maps directly onto the Shape of Thought thesis. The probabilistic model (LLM) is one projection. The formal ontology (graph) is another. Neither is the territory. Both are measurements. The graph is not a database - it is an observation of structure. The LLM is not intelligence - it is an observation of language. Layer them and you get something neither provides alone.

His neuroscience background and the "engage your senses, draw pictures, write in notebooks" philosophy rhymes with Peter's substrate-and-shape framework. The graph is not metadata about the world. It IS the world model. Coyle gets halfway there by calling it "a formal specification of a shared conceptualization." The paper goes further - the specification and the conceptualization are the same thing observed at different scales.
