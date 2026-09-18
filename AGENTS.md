# AGENTS.md

Operating guide for AI coding agents working in this repository (Claude Code,
GitHub Copilot, Cursor, or any agent that reads `AGENTS.md`).

## Project

A GraphRAG project built for the **Neo4j GraphRAG Hackathon** (GraphSummit NY).
The stack is Neo4j AuraDB Free + hosted Aura MCP + an AI coding agent. The
domain is still being chosen — see `IDEATION.md`. Do not hard-code assumptions
about the domain model until that document says the direction is locked.

## Repository layout

```text
.github/agents/    Custom domain-agent definitions (*.agent.md)
.github/skills/    Reusable agent workflows (SKILL.md per skill)
cypher/            Reference Cypher, one file per theme. Read-only unless named *-load.cypher
data/raw/          Source downloads. Gitignored. Never commit.
data/processed/    Derived extracts ready for loading. Gitignored. Never commit.
docs/              Working notes, data dictionaries, modelling decisions
keys/              Aura credential files. GITIGNORED. Never read out, never commit.
scripts/           Python utilities; all connection logic goes through scripts/common.py
```

## Setup

```bash
python -m pip install -r requirements.txt   # or: make install
cp .env.example .env                        # then fill from the file in keys/
make check                                  # verifies Aura connectivity + shows graph size
make schema                                 # prints live labels/relationship types
```

There is no test suite yet. `make check` is the smoke test: if it prints `OK`,
the environment is working.

## Hard rules

1. **Never commit secrets.** `keys/`, `llinks/`, and `.env` are gitignored and
   must stay that way. Do not copy credential values into code, Cypher,
   commit messages, README examples, or chat output. If you need a connection,
   read it through `scripts/common.py`.
2. **Never `git add -f`** a gitignored path.
3. **Aura Free is capped at 200,000 nodes and 400,000 relationships.** Before
   proposing a load, state the expected node and relationship counts. If an
   import would exceed the cap, narrow the scope (one state, one year, top-N
   entities) *before* writing the loader, not after the import fails.
4. **Read-only by default.** Investigation queries — and anything the domain
   agent runs via MCP — must not `CREATE`, `MERGE`, `SET`, `DELETE`, or
   `REMOVE`. Data loading happens only in explicit, clearly named loader
   scripts under `scripts/`.
5. **Inspect the schema, do not assume it.** Run `make schema` or the MCP
   schema tool before writing Cypher against labels you have not verified.

## Working style

- Prefer small, reviewable steps. This repo is being built incrementally by a
  human who reads each change before moving on; do not scaffold several
  subsystems at once.
- Put connection handling in `scripts/common.py` and import it. Do not
  re-implement `load_dotenv` / driver setup per script.
- Every loader script must be idempotent — safe to re-run — using `MERGE` on a
  natural key plus uniqueness constraints created up front.
- When a query result surprises you, verify it with a second query before
  reporting a conclusion. Never report a difference produced by changing two
  conditions at once.
- Keep raw data out of Git. Record source URL, retrieval date, row count, and
  SHA-256 in `data/manifest.json` (gitignored) and describe the source in
  `data/README.md` (committed).

## Cypher conventions

- Labels: `PascalCase` singular (`:Provider`, `:Procedure`).
- Relationship types: `UPPER_SNAKE_CASE` verbs (`:REFERRED_TO`, `:BILLED`).
- Properties: `camelCase` (`npi`, `hcpcsCode`, `totalServices`).
- Always create a uniqueness constraint on the natural key of a node label
  before bulk loading it.
- Parameterise with `$param`; never string-interpolate user input into Cypher.

## Python conventions

- Python 3.11+, standard library plus the pinned deps in `requirements.txt`.
- `from __future__ import annotations` at the top; type-hint function
  signatures.
- Scripts are runnable as `python scripts/<name>.py`, expose `main() -> int`,
  and exit via `sys.exit(main())`.
- Print human-readable progress; no logging framework unless it earns its keep.

## Analytical honesty

This project may touch public healthcare billing data. Statistical outliers are
not evidence of wrongdoing. Any agent or document produced here must:

- state the peer group and metric used for a comparison,
- offer plausible benign explanations alongside any flagged anomaly,
- describe outputs as **leads for human review**, never as findings of fraud,
- never name a real provider as fraudulent based on billing statistics alone.

## Commits

- Imperative subject line, ~72 chars (`Add provider peer-group loader`).
- One logical change per commit.
- Do not commit generated data, notebooks with output, or credential files.
