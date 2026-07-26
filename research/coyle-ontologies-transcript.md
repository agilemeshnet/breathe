# Frank Coyle - Why Agentic Systems Need Ontologies
## AI Engineer, 23 Jul 2026
## https://www.youtube.com/watch?v=Sir59K8ZDPU

### [00:12] Introduction
Frank Coyle. Educator, teaching at Berkeley. 30-35 years in CS. Notes it's a critical time for CS students - degree no longer a guaranteed job thanks to AI.

### [01:09] Philosophy - Sister Corita Kent / John Cage
"Nothing is a mistake. There is no win. There's no fail. There's only make."
Get down and make stuff. Big fan of writing - early career was neuroscience, now coming back via cognitive science in Agent AI. Engage your senses - notebooks, pen, pencil, draw pictures. "When you type, your brain thinks about the letters. When you write in a book, all your sensory systems are engaged."

### [02:18] Two Lineages - Agents and Ontologies

**Agents**: Goes back to early AI. McCarthy, Selfridge, Minsky (Society of Mind). 1956 - the term "artificial intelligence" coined. Concept of agent: perceive, decide, act.

**Ontologies**: Not new. Aristotle - philosophy of being. Categories of being. Relates to graph databases and knowledge representation.
- Von Quine (philosopher)
- Gruber, 1993: "A formal specification of a shared conceptualization"
  "That's what we want to give to our agents. Our conceptualization of the universe, our domains."

### [04:06] Neuro-Symbolic AI
Convergence of probabilistic (agents, LLMs) with formal representations (ontologies).
"Neuro-symbolic AI represents a way to keep the LLM on its guardrails."
"People worry about hallucinations, but that's the feature. We hallucinate in a way. We imagine things that may not exist, then turn them into reality."

### [05:23] What Ontologies Are
Entities, relationships, properties. Graph databases arose when people realised relational databases (tables) were too restrictive. "You wanted to add something new - you have to add a new column, redo the whole structure. With a graph database, you can just attach another item."

**Two approaches to building:**
- Top-down: experts analyse domain, define entities/relationships/properties. Models the 1980s expert systems era. "Companies rose, millions spent. Japanese future world project. But they couldn't scale. AI winter."
- Bottom-up: customer reactions, real-world events shape what gets added to the graph.

**Existing taxonomies**: schema.org, FOAF (social networks), Dublin Core (research papers). "Wikipedia is based on an ontology called DBpedia. When you search Wikipedia, it's looking things up in its giant graph database."

### [09:12] Augmenting Technologies - RDFS and OWL
Sit "on the side" of your graph. Enable inference and constraints.

**RDFS Domain/Range inference:**
- "teaches has domain of teacher" -> if Bob teaches Scooter, Bob is a teacher
- "teaches has range of student" -> Scooter is a student
- "all teachers are persons" -> Bob is a person
Extra information derived, not stored.

**OWL properties:**
- Transitive: ancestor(Sue, Mary) + ancestor(Mary, Ann) -> ancestor(Sue, Ann)
- Functional: has_father is functional (only one). Bob = Jim's father AND BB = Jim's father -> Bob and BB are same individual.
These are constraints and derivations that don't sit IN the graph, they sit beside it.

### [12:18] Agents and Loops
"Everybody's talking about loops." Bohm and Jacopini 1966: sequence + conditional + loop = Turing complete.
"Agents now have loops. Loops give us the last piece - a technology capable of doing anything computational devices can do."

**The danger of loops:**
- Can break (infinite loops)
- Can drift (agents talking to each other go off the rails)
- Can cost money (token counts crank up)

"In a way we are revisiting the early stuff with symbolic AI. I would argue we're going back to the world of expert systems."

### [14:23] Claude Agent Loop Example
Shows a while-true loop with Claude API: model + prompt + tool. "LLMs can't do anything. All they can do is give us the next word with high probability."

The loop:
1. LLM receives prompt + tool definition
2. LLM sets up parameters, says "here's the call you need to make"
3. Stop reason = tool_use -> execute the tool
4. **After the tool runs**: THIS IS WHERE ONTOLOGIES COME IN
5. Validate the result against ontological constraints
6. If reasonable, proceed. If not, go back to LLM or get human in the loop.

### [17:44] Pydantic at the Door, Ontology at the Ledger
"Check your types with Pydantic, then check your results with the ontology."
"Agents should try to have no side effects. They're not changing things in the database yet. Run them through the ontology first."

### [18:44] What Ontological Constraints Catch

| OWL Feature | Error It Catches |
|-------------|-----------------|
| Functional property | A second refund on the same order |
| Disjoint classes | Payout sent to support desk instead of buyer |
| Enumerated values | Made-up status like "probably shipped" (must be paid/shipped/refunded) |

"In the pure text world, this can get funky because LLMs are probabilistic."

### [20:03] Conclusion
"Use a reasoner built on ontology to check, keep the LLM on track, have guardrails to keep it honest."
RDFS + OWL = the guardrails.
"Nothing is a mistake. There's no win, no fail, only a make."

codesupreme.ai | Named after John Coltrane's A Love Supreme.
