# Ideation — not locked

Candidate directions, scored against the design concepts in
[docs/CONCEPTS.md](docs/CONCEPTS.md). Every data claim below was verified
against a live API on 2026-09-18.

## Where the previous round landed

Medicare provider anomaly triage, South Florida 2015 — feasible, verified, and
**parked**. Full writeup in [docs/CANDIDATE-MEDICARE.md](docs/CANDIDATE-MEDICARE.md).
It works, but it fails C10 (a Medicare peer-group argument takes three minutes
to explain) and its retrieval step was bolted on rather than load-bearing. Still
revivable; the feasibility work stands.

## The brief

Inherit C1–C11 from Jeremy's repo and fix C12, the thing his workshop has none
of: **semantic retrieval has to be the entry point into the graph**, not a
garnish. The target shape:

> text question → vector search finds the entry nodes → graph traversal does the
> reasoning → evidence path comes back

---

# Candidate 1 — Retraction contagion  ★ recommended

**The hook.** *"This paper was retracted. What is still standing on top of it?"*

That is C1 with the serial numbers filed off — a retraction is an outage, and
the citation descendants are the reachability loss. Except the stakes are
better than a cancelled flight: somewhere downstream is a clinical guideline or
a meta-analysis whose foundation quietly disappeared.

### The data (verified, free, no API keys)

| Source | What it gives | Verified |
| --- | --- | --- |
| [OpenAlex](https://api.openalex.org) | 135,642 works flagged `is_retracted`; `referenced_works` (outbound citations), `cites:` filter (inbound), authorships, topics | queried live |
| [Retraction Watch](https://api.labs.crossref.org/data/retractionwatch) via Crossref Labs | 72,602 records, 69,929 with `OriginalPaperDOI`, free CSV, 66 MB | downloaded and profiled |
| Crossref REST | 75,562 retraction notices with `update-to` links | queried live |

Retraction Watch columns: `Title, Subject, Institution, Journal, Publisher,
Country, Author, ArticleType, RetractionDate, RetractionDOI, OriginalPaperDate,
OriginalPaperDOI, RetractionNature, Reason, Notes`.

`RetractionNature` splits 67,050 retractions / 3,718 expressions of concern /
1,525 corrections / 160 reinstatements. `Reason` is a 112-token taxonomy; the
top values are a story in themselves:

```text
Investigation by Journal/Publisher                    32,181
Unreliable Results and/or Conclusions                 21,996
Concerns/Issues about Data                            15,925
Compromised Peer Review                               11,872
Paper Mill                                            11,798
Computer-Aided Content or Computer-Generated Content   9,280
Duplication of/in Image                                5,669
```

Nearly 12,000 paper-mill retractions and over 9,000 for machine-generated
content. That is a live, current problem, not a historical curiosity.

The seed set writes itself — the most-cited retracted papers are famous:

```text
 5,536 cites  STAP cells / pluripotency of mesenchymal stem cells
 4,965 cites  Hydroxychloroquine + azithromycin for COVID-19 (Surgisphere)
 4,297 cites  6-month consequences of COVID-19
 4,266 cites  PREDIMED Mediterranean diet primary prevention
 2,963 cites  Wakefield, ileal-lymphoid-nodular hyperplasia (MMR)
```

### The sizing result that reshapes the design

Measured fan-out from one seed (Wakefield, 2,963 direct citers): the median
direct citer has **622 citations of its own**. Generation 2 for that single seed
is ~1.8M works. Aura Free holds 200,000 nodes.

So full breadth-first contagion is impossible, and that is the good news,
because it forces the interesting move:

**Selective traversal.** Not every citation is load-bearing. A paper that cites
Wakefield *to refute it* is not standing on it. A paper that cites it as the
basis for its method is. The agent classifies each citation edge — load-bearing
/ background / critical — and **only load-bearing edges propagate contagion**.

That is an LLM making a traversal decision per edge, which is a genuinely
different thing from an LLM writing one Cypher query. It is the novelty of the
project, and the node budget is what forces it.

Budget with selective traversal:

```text
15 seeds, generation 1 complete      ~51,000 works    (measured)
generation 2, load-bearing only      ~10-20,000       (estimated, needs a pilot)
authors, journals, retraction notices ~20,000
total                                 ~90,000 nodes   — fits, with headroom
```

### Where retrieval is load-bearing (C12)

Embed: OpenAlex abstracts (54% coverage, measured) + retraction notice text +
the `Notes` field. The question is not keyword-shaped:

> *"Which downstream papers depend on the claim that this intervention reduces
> mortality?"*

You cannot grep that. The dependency is semantic — it lives in how the citing
paper describes what it took from the source. Vector search finds the entry
points, and the graph decides what is downstream of them.

### Concepts inherited

| | How it maps |
| --- | --- |
| C1 | Retraction = outage. Direct lift. |
| C2 | Never delete the retracted node — mark it and exclude it from support paths. |
| C3 | Baseline: what the field believed. Counterfactual: same graph, retracted claim excluded. |
| C4 | "Most damaged" ≠ most citations. Depth of dependency, citations *after* the retraction date, whether the citer is in a clinical guideline. |
| C5 | **Citing a retracted paper is not misconduct.** Many citers cite it to criticise it; many cited it before retraction. This is the exact analogue of the OpenFlights historical-data rule, and it has to be in the agent rules. |
| C6 | Named traps: citation count vs unique citing works; retraction date vs publication date; expression of concern is not a retraction. |
| C7 | Skills: `contagion-trace`, `classify-citation`, `compare-two-retractions`. |
| C8 | Scorecard maps cleanly — did it use the graph, did it respect the retraction date, did it distinguish criticism from dependence. |
| C9 | lookup → count citers → trace paths → contagion → *"find a still-active research line resting on retracted work that nobody has flagged."* |
| C10 | "This paper was retracted, what still depends on it" needs no glossary. |

### Risks

- Abstract coverage is 54%, not 100%. Retraction notice text partially fills the
  gap; the seed set should be chosen from works that have abstracts.
- Citation classification quality is the whole project. Needs a pilot on ~100
  edges before committing.
- OpenAlex is rate-limited for anonymous use; add a mailto for the polite pool.

---

# Candidate 2 — Dependency blast radius (pragmatic fallback)

**The hook.** *"This advisory just dropped. What in the stack breaks, and what is
the minimum upgrade that fixes it?"*

### Data (verified, free, no keys)

- **OSV.dev** — `POST /v1/query` returned 10 advisories for `npm:lodash`, each
  with a prose `details` field (763 chars on the sample) and structured
  `affected` version ranges. The prose is genuinely embeddable.
- **deps.dev** — `express@4.18.2` resolved to 71 transitive dependency nodes and
  128 edges. Roughly 70 nodes per package means a realistic 40-service estate
  fits comfortably.

### Why it scores well

C1 maps perfectly (a yanked package *is* an outage). C2 is natural — exclude the
vulnerable version from resolution rather than deleting it. C10 is excellent for
a developer audience. Retrieval is real: advisory prose says "prototype pollution
in deeply nested merge", which no lexical search over package names will find.

A stronger variant folds in **bus factor** — maintainer nodes, so the question
becomes *"if this one maintainer walks away, what is downstream?"* The xz-utils
angle. More novel than CVE propagation alone.

### Why it is second

Novelty. Judges have seen software composition analysis. The honest summary is
"Dependabot with semantic search and a graph," which is useful but not
surprising. Candidate 1 asks a question nobody has a tool for.

---

# Candidate 3 — Paper mill cluster detection

11,798 paper-mill retractions, and mills produce *clusters* — shared authors,
recycled images, templated phrasing, citation rings. Finding **unretracted**
papers sitting inside a known mill cluster is a graph problem and a genuinely
novel one.

Strong C4 (what defines cluster membership?) and a natural C9 discovery moment.
But it carries the same accusatory-framing risk that got the Medicare idea its
ethics caveat, and the labels are weaker.

**Recommendation: build this as a feature of Candidate 1, not a separate
project.** The data is already loaded and the `Reason` field already tags it.

---

# Candidate 4 — Sanctions and ownership blast radius

*"Sanction this entity — who else is captured three hops out through shell
ownership?"* [OpenSanctions](https://www.opensanctions.org) is free and rich, and
ICIJ Offshore Leaks is a real graph dataset.

Great hook, great demo. **Novelty discount:** ICIJ Offshore Leaks is one of
Neo4j's own long-standing demo datasets. These judges have seen it. Worth
knowing before choosing it, not a disqualifier.

---

# Candidate 5 — Statutory cross-reference

*"Repeal this section — what breaks?"* US Code has explicit cross-references and
the counterfactual is clean, but parsing the XML is a slog and the demo is hard
to make visual in 60 seconds. Not developed.

---

# Scorecard

| | C1 hook | C4 metric | C5 honesty | C10 legible | C12 retrieval | Novelty | Data risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **1. Retraction contagion** | ★★★ | ★★★ | ★★★ | ★★★ | ★★★ | ★★★ | low |
| 2. Dependency blast radius | ★★★ | ★★ | ★★ | ★★★ | ★★★ | ★★ | low |
| 3. Paper mill clusters | ★★ | ★★★ | ★★ | ★★ | ★★ | ★★★ | medium |
| 4. Sanctions ownership | ★★★ | ★★ | ★★★ | ★★★ | ★★ | ★ | low |
| 5. Statutory repeal | ★★★ | ★★ | ★★ | ★ | ★★ | ★★ | high |
| — Medicare (parked) | ★ | ★★★ | ★★★ | ★ | ★★ | ★★ | low |

---

# Recommendation

**Candidate 1, with Candidate 3 folded in as a feature.**

It inherits Jeremy's entire structure, fills the retrieval gap he leaves open,
and the node-budget constraint pushes it somewhere genuinely new: an LLM
deciding, edge by edge, whether a citation actually carries weight. The demo
lands in one sentence and the honesty caveat is sharp rather than defensive.

## Next step before committing

One pilot, roughly an hour: take a single seed (Wakefield or Surgisphere), pull
its direct citers from OpenAlex, and hand ~100 citation contexts to a model to
classify as load-bearing / background / critical. If that classification is
reliable, the project works. If it is not, the whole design collapses and
Candidate 2 is the fallback.

**Do not load anything into Aura until that pilot runs.**

## Decision log

| Date | Decision |
| --- | --- |
| 2026-09-18 | Repo scaffolded. |
| 2026-09-18 | Medicare direction verified feasible (see parked doc), then set aside — weak on C10 and C12. |
| 2026-09-18 | Extracted 11 reusable concepts from Jeremy's repo into docs/CONCEPTS.md; identified C12 (retrieval as graph entry point) as the gap his workshop leaves. |
| 2026-09-18 | Retraction contagion recommended. Gen-2 fan-out measured at ~1.8M works for one seed, which rules out breadth-first traversal and motivates LLM-classified selective traversal. Pilot required before load. |
