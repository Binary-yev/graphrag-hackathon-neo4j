# GraphRAG Hackathon — Neo4j

A GraphRAG project built for the **Neo4j GraphRAG Hackathon** (GraphSummit NY),
using **Neo4j AuraDB Free**, **hosted Aura MCP**, and an **AI coding agent** as
the agent runtime.

> **Status: scaffolding.** The domain and dataset are not locked yet. Candidate
> directions and the feasibility work behind them live in [IDEATION.md](IDEATION.md).
> This README documents the environment; it will document the chosen build once
> that decision is made.

---

## Architecture

```text
Developer
   |
   v
AI coding agent  (custom agent in .github/agents/)
   |
   | MCP
   v
Neo4j Aura MCP
   |
   | schema + read-only Cypher
   v
AuraDB Free  (200k nodes / 400k relationships)
   ^
   | loaders in scripts/
   |
Source data  (public dataset, TBD)
```

The coding agent runs the agent loop. This repository supplies the four things
that make it useful: **instructions**, **graph tools**, **domain rules**, and a
**source of truth**.

---

## What you need

1. A [Neo4j Aura](https://console.neo4j.io) account with a **Free** instance
2. Python 3.11+
3. An AI coding agent with MCP support (Claude Code, Copilot Chat, Cursor)

---

## Setup

### 1. Install dependencies

```bash
make install          # python -m pip install -r requirements.txt
```

### 2. Configure credentials

Aura gives you a credential file when you create the instance. Keep it in
`keys/` — that folder is **gitignored and must stay that way**.

```bash
cp .env.example .env
```

Fill in `.env` from the credential file:

```ini
NEO4J_URI="neo4j+s://xxxxxxxx.databases.neo4j.io"
NEO4J_USERNAME="neo4j"
NEO4J_PASSWORD="..."
NEO4J_DATABASE="neo4j"
```

### 3. Verify the connection

```bash
make check
```

Expected:

```text
OK: connected to database 'neo4j'
    nodes: 0
    relationships: 0
    Aura Free budget: 200,000 nodes / 400,000 relationships
```

### 4. Connect your agent to Aura MCP

In the Aura console, open the instance and copy its MCP endpoint, then put it in
`.vscode/mcp.json` (replace `<YOUR_INSTANCE_ID>`). Restart the agent so it picks
up the server.

---

## Repository layout

| Path | Purpose |
| --- | --- |
| [AGENTS.md](AGENTS.md) | Rules and conventions for AI agents working in this repo |
| [IDEATION.md](IDEATION.md) | Candidate directions, scored and ranked |
| [docs/PROPOSAL-RETRACTION-CONTAGION.md](docs/PROPOSAL-RETRACTION-CONTAGION.md) | Current front-runner: full proposal with worked example |
| [docs/CONCEPTS.md](docs/CONCEPTS.md) | Reusable design concepts extracted from prior art |
| [.github/agents/](.github/agents/) | Custom domain-agent definitions |
| [.github/skills/](.github/skills/) | Reusable agent workflows |
| [cypher/](cypher/) | Reference Cypher queries |
| [data/](data/) | Source and derived data — contents gitignored |
| [docs/CANDIDATE-MEDICARE.md](docs/CANDIDATE-MEDICARE.md) | Parked candidate — verified feasibility work |
| [docs/GRAPH_MODEL.md](docs/GRAPH_MODEL.md) | Graph schema for the parked Medicare candidate |
| [sql/](sql/) | BigQuery queries for the parked Medicare candidate |
| [scripts/](scripts/) | Python utilities (connection, schema, loaders) |
| `keys/` | Aura credentials — **gitignored, never committed** |

---

## Commands

```bash
make install    # install Python dependencies
make check      # verify Aura credentials and report graph size
make schema     # print live labels, relationship types, and counts
```

---

## Security

`keys/`, `llinks/`, and `.env` are excluded from Git by [.gitignore](.gitignore).
Credentials are read only through [scripts/common.py](scripts/common.py). If a
credential is ever committed, rotate the Aura password immediately — removing
the commit is not sufficient.

---

## Constraints worth remembering

- **Aura Free caps at 200,000 nodes and 400,000 relationships.** Every dataset
  decision has to be sized against that ceiling before loading.
- A GraphRAG submission needs both halves: **retrieval over unstructured text**
  *and* **graph traversal**. A project that only does graph analytics is not
  GraphRAG. See [IDEATION.md](IDEATION.md).
