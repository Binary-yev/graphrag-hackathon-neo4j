# Proposal — Retraction Contagion

*Written for: hackathon teammates and judges. Assumes no background in
bibliometrics.*

Every figure in this document was measured against a live API on 2026-09-18.
Nothing here is estimated unless it says so.

---

## The one-liner

> A paper gets retracted. What is still standing on top of it?

## The problem, in plain terms

When a scientific paper is retracted, it is withdrawn from the record — the
findings were wrong, fabricated, or manufactured. But the paper does not exist
alone. Other papers cited it. Some of those *built on it*: they took its result
as an established fact and went one step further.

When the foundation is withdrawn, nobody goes back and checks the building.
There is no system that does this. Retraction notices propagate to the retracted
paper and stop there.

That is a dependency problem, and dependency problems are graph problems.

---

## Worked example

### Step 1 — the obvious case, and why it is a trap

The most famous retraction in medicine is Wakefield's 1998 *Lancet* paper
linking the MMR vaccine to autism. Real numbers from OpenAlex:

```text
Ileal-lymphoid-nodular hyperplasia... (Lancet, 1998)
  partial retraction  2004-03-06
  full retraction     2010-02-06
  total citing works  2,961
  cited AFTER the 2010 retraction  1,940  (66%)

  citations per year:  2010: 119   2012: 147   2014: 149   2018: 155
```

Two thirds of its citations came *after* it was retracted, and the rate went
**up**. A naive tool stops here and reports a catastrophe.

Now look at what those papers actually are — real titles, pulled live:

```text
[2019] Systematic Literature Review on the Spread of Health-related Misinformation
[2018] The Anti-vaccination Movement: A Regression in Modern Medicine
[2018] Conspiracy Theories and the People Who Believe Them
[2020] Vaccine Safety: Myths and Misinformation
[2021] Vaccine Hesitancy, Acceptance, and Anti-Vaccination
```

**None of these are standing on Wakefield. They are studying it.** They cite the
paper as an object of study — the thing misinformation researchers point at. The
contagion here is close to zero.

The naive metric gives exactly the wrong answer. That is the point of the
project.

### Step 2 — the case nobody is looking at

Now a paper you have never heard of. Retraction Watch flags it as a **paper
mill** product — a fake paper sold to authors who need a publication:

```text
"Propofol inhibits proliferation, migration and invasion of gastric cancer"
  International Journal of Biological Macromolecules
  published 2018, retracted 2022, reason: Paper Mill

  total citing works  51
  before retraction   47
  after retraction     4
```

Only 51 citations. It will never make the news. But those **47 papers were
published between 2018 and 2022, while everyone still believed it.** They are
mechanistic cancer-biology papers that cited it as supporting evidence for a
result that was manufactured. Not one of their authors has been told.

Nobody has gone back to check those 47. There is no mechanism that would.

And this is not a rare case: Retraction Watch lists **883 paper-mill retractions
in cancer biology retracted in 2021–2022 alone**.

### Step 3 — what the system actually does

The inversion between Steps 1 and 2 is the whole product:

| | Wakefield | Propofol paper mill |
| --- | --- | --- |
| Citations | 2,961 | 51 |
| Post-retraction citations | 1,940 (66%) | 4 (8%) |
| Famous | extremely | not at all |
| **Actual contagion risk** | **near zero** | **potentially high** |

Ranking by citation count is wrong. Ranking by post-retraction citations is
wrong. The thing you want to rank by is **structural dependency**, and you only
get that by looking at each citation edge and asking what it is doing.

### Step 4 — a session with the agent

```
> A 2018 gastric cancer paper was retracted as a paper mill product.
  What research is still resting on it?

  [vector search over abstracts + retraction notices → seed paper]
  [graph: 51 citing works, 47 published before the retraction]
  [classify each citation edge]

  Of 51 citing papers, 47 predate the retraction.
  Classified: 31 load-bearing, 12 background, 8 unclear.

  The 31 load-bearing citers have themselves been cited 890 times.
  Three are systematic reviews, which means the claim has been
  aggregated into the secondary literature.

  Highest-risk descendant: [title], cited 112 times, cites the
  retracted work as the sole support for its central mechanism.

  Cypher used: ...
```

The agent does not just count. It decides what each edge *means*, and only the
load-bearing ones carry contagion forward.

---

## Why this needs a graph, and why it needs RAG

**Why a graph.** The question is about paths, not rows. "What rests on this" is a
reachability query. "Which surviving paper is most exposed" is a centrality
question over a filtered subgraph. "Has this claim reached a systematic review"
is a path-to-node-type query. All of these compose; none is a lookup.

**Why retrieval.** The user does not know the paper, the DOI, or the field. They
ask *"which papers depend on the claim that propofol suppresses tumour
migration?"* That is a semantic question about what a paper claims, answerable
only by searching the text. Vector search finds the entry point; the graph
decides what is downstream of it.

**The constraint that forces the interesting design.** Measured fan-out: the
median paper citing Wakefield has **622 citations of its own**. Generation 2 for
that one seed is roughly **1.8 million works**. Aura Free holds 200,000 nodes.

Breadth-first contagion is therefore impossible — which is good, because it
forces the right design. Only load-bearing edges propagate. The LLM makes a
classification decision *per edge*, and the traversal follows only the edges
that survive. That is a different thing from an LLM writing one Cypher query,
and it is the novel part of this project.

---

## How this is GraphRAG

Neo4j defines GraphRAG as retrieval that uses "the rich context in graph data
structures," running the usual three RAG phases — **retrieval, augmentation,
generation** — but with a graph in the retrieval step. Their documented retrieval
patterns are: vector/index search as an *entry point*, neighbourhood traversal,
path traversal, dynamic Cypher generation, and agentic traversal.

Mapped onto this project:

| GraphRAG element | How this project does it |
| --- | --- |
| **Unstructured text corpus** | OpenAlex abstracts, Crossref retraction-notice text, Retraction Watch `Notes` |
| **Embedding / vector index** | `:Paper(embedding)` and `:Retraction(embedding)` in Aura |
| **Vector search as entry point** | "papers depending on the claim that propofol suppresses tumour migration" → lands on seed `:Paper` nodes |
| **Neighbourhood traversal** | reverse `:CITES` from the seed — who cited this |
| **Path traversal** | multi-hop descent, restricted to `classification = 'load-bearing'` |
| **Structured graph context** | authors, journals, topics, retraction dates and reasons attached to every node |
| **Dynamic Cypher** | agent writes read-only Cypher per question via Aura MCP |
| **Agentic traversal** | agent chains retrieve → classify → traverse → rank, and follows up on its own findings |
| **Augmentation** | context handed to the LLM is structured evidence — counts, classified edge lists, paths — not raw chunks |
| **Generation** | answer cites titles, counts, classification breakdown, and the Cypher used |

In `neo4j-graphrag-python` terms the core is a **`VectorCypherRetriever`** —
vector search for the entry node, Cypher for the surrounding structure — wrapped
in agentic tool selection.

### Why vector-only RAG fails here, demonstrably

This project has an unusually clean proof that plain RAG is insufficient, and it
is the Wakefield case.

Ask a vector-only system "what depends on the Wakefield MMR paper?" and its
nearest neighbours in embedding space are the misinformation and vaccine-
hesitancy literature — papers about Wakefield, densely similar in topic.

Those are **exactly the wrong answer.** They are the papers that depend on it
*least*: they cite it to refute it.

Semantic similarity is not dependency. Nothing in the text of a citing paper
reliably says "I am standing on this" — that lives in the edge, and in what the
edge means. Vector search cannot see edges. The graph is not an optimisation
here; it is the only thing that can answer the question.

### What this project does not do

Being honest about the boundary: some people use "GraphRAG" to mean
Microsoft's variant — LLM extraction of entities and relationships from raw text
to *construct* a knowledge graph, then community detection and summarisation for
global queries.

This project does not do that, because it does not need to: OpenAlex already
publishes the citation graph, so extraction would be re-deriving worse data.

What it does instead is **LLM-driven edge enrichment** — a model reads each
citation and writes a `classification` property onto the `:CITES` relationship.
That is the same idea as entity extraction, applied to edge semantics rather
than node discovery, and it is what makes traversal selective.

Community detection is not in scope for the first build, but it is the obvious
extension for the paper-mill cluster feature.

---

## Where the data lives

All three sources are free, public, and need no API key or registration.

### 1. OpenAlex — the citation graph

| | |
| --- | --- |
| Endpoint | `https://api.openalex.org` |
| Docs | https://docs.openalex.org |
| Licence | CC0 (public domain) |
| Scale | 327,345,085 works total; **135,642 flagged `is_retracted`** |
| Auth | none; add `?mailto=you@example.com` for the faster "polite pool" |
| Bulk | full snapshot on AWS S3 (`s3://openalex`), requester-pays-free |

What it gives:

- `is_retracted` — boolean flag on every work
- `referenced_works` — outbound citations (what this paper cites)
- `filter=cites:W123...` — inbound citations (what cites this paper)
- `abstract_inverted_index` — abstract text (**54% coverage, measured on a
  50-work sample of retracted works** — this is a real limitation)
- `authorships`, `topics`, `primary_location` — authors, fields, journals

Example calls that work right now:

```bash
# all retracted works
curl "https://api.openalex.org/works?filter=is_retracted:true&per-page=25"

# what cites the Wakefield paper, grouped by year
curl "https://api.openalex.org/works?filter=cites:W2117847125&group_by=publication_year"
```

**Operational note:** responses carry `x-ratelimit-limit: 1000` and a per-call
cost header. Fine for a scoped hackathon pull; use the S3 snapshot for anything
bulk.

### 2. Retraction Watch — why it was retracted

| | |
| --- | --- |
| Endpoint | `https://api.labs.crossref.org/data/retractionwatch?your@email.com` |
| Docs | https://www.crossref.org/documentation/retrieve-metadata/retraction-watch/ |
| Licence | **CC0.** Crossref acquired the database in September 2023 and released it publicly |
| Format | single CSV, 66 MB, one GET |
| Scale | **72,602 records; 69,929 carry an `OriginalPaperDOI`** (joins straight to OpenAlex) |

Columns: `Record ID, Title, Subject, Institution, Journal, Publisher, Country,
Author, URLS, ArticleType, RetractionDate, RetractionDOI, RetractionPubMedID,
OriginalPaperDate, OriginalPaperDOI, OriginalPaperPubMedID, RetractionNature,
Reason, Paywalled, Notes`.

`RetractionNature` splits:

```text
Retraction              67,050
Expression of concern    3,718
Correction               1,525
Reinstatement              160
```

`Reason` is a 112-token taxonomy. The top values:

```text
Investigation by Journal/Publisher                    32,181
Unreliable Results and/or Conclusions                 21,996
Concerns/Issues about Data                            15,925
Compromised Peer Review                               11,872
Paper Mill                                            11,798
Computer-Aided or Computer-Generated Content           9,280
Duplication of/in Image                                5,669
```

Nearly 12,000 paper-mill retractions and over 9,000 for machine-generated
content. This is a current problem, not a historical one.

**Useful detail found in the data:** a paper can appear multiple times, tracking
its *escalation*. The Surgisphere hydroxychloroquine paper has three rows —
Correction (2020-05-30), Expression of Concern (2020-06-03), Retraction
(2020-06-05). Wakefield has two: partial retraction 2004, full retraction 2010.
That timeline is itself a modellable feature.

### 3. Crossref REST — retraction notices

| | |
| --- | --- |
| Endpoint | `https://api.crossref.org/works?filter=update-type:retraction` |
| Licence | open |
| Scale | **75,562 retraction notices**, linked to the retracted paper via `update-to` |

Supplies notice text where the OpenAlex abstract is missing.

---

## Graph model

```text
(:Paper {openalexId, doi, title, year, isRetracted, embedding})
(:Retraction {reason[], nature, date, noticeText, embedding})
(:Author {openalexId, name})
(:Journal {issn, name})
(:Topic {name})

(:Paper)-[:CITES {classification, confidence, citedBeforeRetraction}]->(:Paper)
(:Paper)-[:RETRACTED_BY]->(:Retraction)
(:Paper)-[:AUTHORED_BY]->(:Author)
(:Paper)-[:PUBLISHED_IN]->(:Journal)
(:Paper)-[:ABOUT]->(:Topic)
```

The `classification` property on `:CITES` is the heart of it, set by the LLM:

| Value | Meaning | Propagates? |
| --- | --- | --- |
| `load-bearing` | cites it as support for its own claim or method | **yes** |
| `background` | passing mention, intro citation | no |
| `critical` | cites it to dispute, correct, or study it | no |
| `unclear` | insufficient context | flagged for review |

### Budget

Aura Free: 200,000 nodes / 400,000 relationships.

```text
15 seed retracted papers, generation 1 complete    ~51,000 papers  (measured)
generation 2, load-bearing edges only              ~10-20,000      (estimated)
authors, journals, topics, retraction notices      ~20,000
                                                   ---------------
                                                   ~90,000 nodes — fits
```

---

## Evaluation

Adapted from the scorecard pattern in [CONCEPTS.md](CONCEPTS.md) (C8).

**Ground truth for classification.** Hand-label 100 citation contexts, compare
against the model's labels, report precision and recall per class. The Wakefield
case is a natural test: a correct system classifies nearly all its
post-retraction citations as `critical`, not `load-bearing`.

**Per-answer checklist:**

- [ ] Used the graph rather than model knowledge
- [ ] Distinguished retraction date from publication date
- [ ] Distinguished expression of concern from retraction
- [ ] Did not treat citation count as contagion
- [ ] Classified edges before propagating
- [ ] Returned evidence (titles, counts, paths)
- [ ] Stated its uncertainty on `unclear` edges

---

## Honesty constraints

These go into the agent rules, not just this document.

1. **Citing a retracted paper is not misconduct.** Most post-retraction
   citations are legitimate — criticism, meta-research, or papers written before
   the retraction was issued.
2. **A paper downstream of a retraction is not wrong.** It is *unverified*. The
   output is a list of things worth rechecking, not a list of bad science.
3. **Never name an author as fraudulent.** The retraction record describes the
   paper; the agent describes dependencies.
4. **An expression of concern is not a retraction.** 3,718 records are
   expressions of concern and 160 are reinstatements — papers that were cleared.
5. **Classification is probabilistic.** Report confidence; surface `unclear`
   rather than guessing.

---

## Risks

| Risk | Severity | Mitigation |
| --- | --- | --- |
| Citation classification is unreliable | **fatal** | Pilot on 100 edges before building anything |
| Abstract coverage is 54%, not 100% | medium | Fill from Crossref notice text; choose seeds that have abstracts |
| Full citation context is not in OpenAlex | medium | Classify from abstract + title + topic overlap; note the limitation |
| OpenAlex rate limits during bulk pull | low | Polite pool, cache locally, or use the S3 snapshot |
| Generation 2 explodes | handled | Selective traversal is the design, not a workaround |

**The classification risk is the whole project.** If a model cannot reliably tell
"builds on" from "argues against", there is no product.

---

## Build order

1. **Pilot (gate).** One seed, pull direct citers, hand-label 100 citation
   contexts, measure classification accuracy. **Do not load Aura until this
   passes.**
2. Load seeds + generation 1 + retraction metadata.
3. Embed abstracts and notice text; build the vector index.
4. Classify generation-1 edges; expand generation 2 along load-bearing edges.
5. Write the agent definition and the `contagion-trace` skill.
6. Build the scorecard; run the Wakefield inversion as the headline test.

## Fallback

If the pilot fails, switch to dependency blast radius (OSV.dev + deps.dev) —
same counterfactual shape, mechanical rather than semantic edge classification.
See [../IDEATION.md](../IDEATION.md).

---

## Sources

- [OpenAlex API](https://docs.openalex.org) — queried live 2026-09-18
- [Retraction Watch via Crossref](https://www.crossref.org/documentation/retrieve-metadata/retraction-watch/) — downloaded and profiled 2026-09-18
- [Crossref acquires Retraction Watch, CC0](https://www.crossref.org/blog/news-crossref-and-retraction-watch) — September 2023
- [Crossref REST API](https://api.crossref.org)
- Design concepts: [CONCEPTS.md](CONCEPTS.md), from [JeremyMorgan/neo4j-airport-resilience-agent](https://github.com/JeremyMorgan/neo4j-airport-resilience-agent)
