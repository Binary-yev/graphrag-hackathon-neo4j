# Custom agents

One `*.agent.md` file per domain agent. Each defines the agent name, the MCP
tools it may use, and the domain rules it must follow.

Format:

```markdown
---
name: Agent Name
description: One line describing what this agent investigates.
tools:
  - neo4j-aura/*
---

Role, graph model, operating rules, investigation behaviour, response style.
```

Nothing here yet — the domain agent is written once the direction in
[IDEATION.md](../../IDEATION.md) is locked. See
[AGENTS.md](../../AGENTS.md) for the repo-wide rules every agent inherits.
