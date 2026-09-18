# Ideation — not locked

Working notes on the candidate direction. Nothing here is a commitment. The
README stays domain-neutral until a direction is chosen.

---

## Candidate A — Medicare provider anomaly triage (current front-runner)

**The pitch.** Load public Medicare billing data into Neo4j as a provider graph,
find providers whose behaviour is structurally unusual relative to their peers,
and let an agent explain *why* a provider stands out, with graph evidence.

**Why this suits a graph.** The interesting questions are relational and are
genuinely awkward in SQL:

- Which providers sit in a tight cluster that bills a near-identical, unusual
  basket of codes?
- Which providers are reachable in one or two hops from a provider who was
  later excluded from federal healthcare programs?
- Are there cycles or rings in referral patterns rather than the usual tree?
- Which node's removal disconnects a local patient-sharing community — i.e.
  which provider is a structural bottleneck?
- Who is an outlier on *position* in the network, not just on dollar amount?

Degree, betweenness, community detection, and path queries are the analysis.
That is a real graph argument, not a graph-flavoured table scan.

### Verdict

**The idea is sound and worth pursuing**, with four caveats. Three are
data-shaped and one is framing. None of them kills it; all of them change what
gets built, so they are worth settling before any loader is written.

### Caveat 1 — BigQuery does not contain provider-to-provider referrals

This is the big correction to the original framing.
`bigquery-public-data.cms_medicare` has provider-to-*service* data, not
provider-to-*provider* data:

| Table family | Edge it actually gives you |
| --- | --- |
| `physicians_and_other_supplier_*` | NPI → HCPCS procedure code (volume, charges, payments) |
| `part_d_prescriber_*` | NPI → drug |
| `referring_durable_medical_equip_*` | referring NPI → DME HCPCS code |
| `inpatient_charges_*`, `outpatient_charges_*` | hospital → DRG / APC |
| `home_health_agencies`, `hospice_providers`, `nursing_facilities` | facility attributes + quality measures |

Note that `referring_durable_medical_equip_*` is a *referring provider → item*
edge, despite the name. It is not a referral to another provider.

Real provider-to-provider edges come from a **separate** CMS release:
[Physician Shared Patient Patterns](https://www.nber.org/research/data/physician-shared-patient-patterns-data),
hosted by NBER. It defines an edge when two providers treat the same patient
within 30/60/90/180 days, and covers 2009 through 2015.

**Two ways forward:**

- **(A1) Bipartite projection, BigQuery only.** Build
  `(:Provider)-[:BILLED]->(:Procedure)` from BigQuery, then project a
  `(:Provider)-[:PEER_OF]->(:Provider)` edge between providers in the same
  specialty and geography. This is a *peer-comparison* graph, not a referral
  graph — but it directly supports "this provider bills code X at 9x the county
  median for their specialty." One query, no extra download.
- **(A2) Real shared-patient edges.** Download one year and one state of the
  shared patient patterns file for actual
  `(:Provider)-[:SHARED_PATIENTS]->(:Provider)` edges. Richer, and the only way
  to get true ring and cycle analysis, but it is a bulk file download that needs
  hard filtering.

**Recommendation:** start with A1 because it is reachable in an afternoon, and
add A2 only if the schedule allows. Model the graph so A2 can be layered in
without a rewrite — that means `:Provider` nodes keyed on NPI from day one.

### Caveat 2 — Aura Free will not hold the national graph

Aura Free caps at **200,000 nodes / 400,000 relationships**. For scale: the
shared-patient files run to roughly ten million edges per year across hundreds
of thousands of providers. A naive load fails.

Scope down *before* loading, and do the aggregation in BigQuery (the free tier
covers 1 TB of query per month) so that only a pre-filtered extract lands
locally:

- one state,
- one year,
- a handful of specialties, or the top-N providers by volume,
- procedure nodes collapsed to the codes that actually matter.

A defensible target: roughly 20k provider nodes, 5k procedure nodes, 150k edges.
That leaves headroom and still looks substantial in a demo.

### Caveat 3 — outlier detection alone is not GraphRAG

This is the caveat most likely to cost points. The hackathon is a **GraphRAG**
hackathon: retrieval over unstructured text, combined with graph traversal. A
pure anomaly-detection pipeline has no retrieval in it. It is graph analytics
with an agent on top.

To make it genuinely GraphRAG, attach a text corpus to the same `:Provider`
nodes and give the agent something to retrieve:

| Text source | What it adds |
| --- | --- |
| **OIG LEIE** (List of Excluded Individuals and Entities) | Exclusion reason text, plus a ground-truth label for "known bad actor". Free CSV, small. |
| **DOJ / HHS-OIG enforcement press releases** | Narrative descriptions of actual schemes — chunk, embed, link named providers to NPI nodes. |
| **CMS Open Payments** | Industry payments to physicians; nature-of-payment and product text. |
| **NUCC provider taxonomy** | Specialty definitions, so the agent can reason about whether a service is plausible for a specialty. |

That produces the full GraphRAG loop, and it is a much better demo:

> Vector-search the enforcement narratives for "unnecessary DME braces" → land
> on the scheme and the codes it uses → traverse the graph to providers
> exhibiting that billing pattern → return them with peer-group evidence.

Text in, graph traversal in the middle, evidence out. **This caveat is the one
that should most shape the build.** The LEIE corpus is also the cheapest of the
four to add and the highest value, because it doubles as labels.

### Caveat 4 — framing

The data is public *aggregate* billing data. A statistical outlier is not fraud
and frequently has a benign explanation: a regional referral centre, a sicker
patient panel, the only specialist in a rural county, a small denominator.

Claiming to "detect fraud" invites an easy objection from judges and is simply
not what the data supports. Frame it as **anomaly triage and lead generation for
a human investigator**, and build that into the agent rules: always state the
peer group, always offer a benign explanation, never assert wrongdoing about a
named real provider.

The LEIE labels give a genuinely strong and honest claim to make instead: "N of
our top-50 structural anomalies were providers later excluded from federal
healthcare programs." That is measurable, defensible, and more impressive than
an unvalidated fraud score.

### Open questions before locking A

- [ ] A1 (BigQuery peer projection) or A2 (real shared-patient edges) first?
- [ ] Which state and year? High enforcement volume helps the LEIE overlap.
- [ ] Does the chosen LEIE slice actually intersect the chosen state and
      specialty slice? **Check this before loading anything** — an empty overlap
      removes the strongest part of the story.
- [ ] Where do embeddings get generated, and do they fit under the Aura Free
      node budget alongside the graph?

---

## Candidate B — Open Payments influence graph (fallback)

`(:Company)-[:PAID]->(:Physician)-[:PRESCRIBED]->(:Drug)`, built from CMS Open
Payments plus Part D. Smaller, cleaner, and joins on NPI exactly like Candidate
A. The question — does industry payment correlate with prescribing — is
well-trodden, which makes it lower risk and lower ceiling.

Worth keeping as a fallback because it reuses the identical `:Provider` / NPI
model. If the Candidate A data pull stalls, this is a short pivot rather than a
restart.

---

## Candidate C — something non-healthcare

Not developed. Only worth opening if both A and B hit a wall on data volume or
time.

---

## Sources checked

- [CMS Medicare public dataset on BigQuery](https://console.cloud.google.com/marketplace/details/hhs/cms-medicare)
- [Medicare Physician & Other Practitioners](https://data.cms.gov/provider-summary-by-type-of-service/medicare-physician-other-practitioners)
- [Medicare DME by Referring Provider and Service](https://data.cms.gov/provider-summary-by-type-of-service/medicare-durable-medical-equipment-devices-supplies/medicare-durable-medical-equipment-devices-supplies-by-referring-provider-and-service)
- [Physician Shared Patient Patterns (NBER)](https://www.nber.org/research/data/physician-shared-patient-patterns-data)
- [Neo4j healthcare and life sciences use cases](https://neo4j.com/developer/industry-use-cases/life-sciences/)
- [Reference structure: JeremyMorgan/neo4j-airport-resilience-agent](https://github.com/JeremyMorgan/neo4j-airport-resilience-agent)

---

## Decision log

| Date | Decision |
| --- | --- |
| 2026-09-18 | Repo scaffolded. Direction not locked; Candidate A is the front-runner, pending the four caveats above. |
