# Design concepts worth stealing

Extracted from [JeremyMorgan/neo4j-airport-resilience-agent](https://github.com/JeremyMorgan/neo4j-airport-resilience-agent)
by reading its README, `CHALLENGES.md`, `INSTRUCTOR.md`, the agent definition,
and all three skills. Use this as a scorecard for any candidate direction.

The repo is a teaching workshop, not a hackathon entry, so not everything
transfers. But the structural moves are good and most of them are reusable.

## C1 — The counterfactual hook

The project is framed by a failure question, not a lookup:

> Chicago O'Hare has gone offline. What happens to the network?

This is the single biggest design decision in the repo. A lookup question makes
a graph look like a slow table. A question about *consequences propagating
through structure* makes the graph the only sensible tool. Any candidate
direction should have a one-sentence "what if X breaks" framing.

## C2 — Simulate failure by exclusion, never by mutation

Rule 8 of the agent: *do not simulate an outage by deleting the airport.* The
offline node is excluded from candidate paths instead. Read-only, repeatable,
and multiple scenarios can run against the same graph without teardown.

## C3 — Baseline vs counterfactual, one condition at a time

> Never report a difference produced by changing two conditions at once.

The agent must compute the unrestricted baseline and the restricted comparison
with identical hop limits and metrics. Obvious, routinely violated.

## C4 — Contest the headline metric

> Do not automatically equate "most important" with highest degree.

The agent is told to consider unique outbound destinations, unique inbound
origins, relationship counts, two-hop reachability, alternative paths, and
reachability lost on exclusion — then **state which metric it used**. Challenge
9 goes further and asks the agent to argue with the premise of the question.

## C5 — A domain honesty constraint, encoded as a rule

The OpenFlights route feed stopped updating in June 2014, so the agent is
forbidden from implying a historical route is currently bookable. Every domain
has an equivalent: the one claim the data cannot support but an LLM will happily
make. Find it and write it into the rules.

## C6 — Name the specific trap

> Distinguish between the number of route relationships and the number of unique
> destination airports.

Not generic caution — a named failure mode that an unconstrained model actually
hits. Worth one rule each for the two or three traps in the domain.

## C7 — Agent and skill are different things

- **Agent** (`.github/agents/*.agent.md`): role, domain model, operating rules,
  tool access, response style.
- **Skill** (`.github/skills/*/SKILL.md`): one named, repeatable workflow with an
  `argument-hint` and numbered steps.

`outage-analysis`, `route-around-outage`, and `inspect-network` are workflows,
not personalities. Keeping them separate makes both reusable.

## C8 — Ship an evaluation scorecard

`CHALLENGES.md` gives ten questions in four levels with explicit success criteria
per question, plus an 8-point checklist applied to every answer:

> Used Neo4j instead of model knowledge · correct schema · read-only · direction
> applied · relationships vs unique nodes · outage semantics · evidence returned
> · no unsupported currency claims

Most hackathon entries have no eval at all. This is cheap to copy and it is the
difference between "it answered" and "it answered correctly, and here is how we
know."

## C9 — Question progression

lookup → aggregation → path → failure → open-ended discovery.

Challenge 10 is *"find one surprising structural property I did not ask about."*
That is the demo moment: the agent forming and testing its own hypothesis.

## C10 — Legible domain, small graph

Everyone knows what an airport is. No glossary, no setup, the failure question
lands in one sentence. A domain needing three minutes of explanation has already
lost the room.

## C11 — Explicit separation of concerns

```text
LLM    -> interprets the question, decides what to investigate
MCP    -> exposes graph capabilities as tools
AuraDB -> stores the evidence
Cypher -> expresses the investigation
Agent  -> orchestrates the loop and explains the result
```

## What is missing from Jeremy's repo

**There is no vector search and no retrieval anywhere in it.** It is a pure
graph-agent workshop — the agent goes straight from question to Cypher. Nothing
is embedded, and no unstructured text is involved at all.

That is the gap a GraphRAG entry has to fill: a text corpus whose *semantic*
retrieval is the entry point into the graph. Inheriting C1–C11 and adding a
genuine retrieval step is the whole design brief.

## Scorecard

| | Concept |
| --- | --- |
| C1 | Counterfactual hook |
| C2 | Failure by exclusion, not mutation |
| C3 | Baseline vs counterfactual, one variable |
| C4 | Contested metric |
| C5 | Domain honesty constraint |
| C6 | Named traps |
| C7 | Agent / skill separation |
| C8 | Evaluation scorecard |
| C9 | Question progression to self-directed discovery |
| C10 | Legible domain |
| C11 | Separation of concerns |
| **C12** | **Retrieval is the entry point into the graph** (not in Jeremy's repo; required here) |
