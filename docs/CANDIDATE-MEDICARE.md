# Candidate A (PARKED) — Medicare provider anomaly triage

Parked on 2026-09-18 in favour of a more novel direction. See [../IDEATION.md](../IDEATION.md).
The data feasibility work below is verified and still valid if this is revived.


Every number below was measured against the live BigQuery public dataset and the
current OIG exclusion file on 2026-09-18, not estimated. The queries are in
[sql/](../sql/).

---

## Candidate A — Medicare provider anomaly triage (current front-runner)

**The pitch.** Load public Medicare billing data into Neo4j as a provider graph.
Let an agent take a plain-language description of a fraud scheme, find the
billing codes that scheme actually uses, traverse to the providers whose billing
structure matches it, and rank them against their peers with graph evidence.

---

## 1. The tables

### Available

`bigquery-public-data.cms_medicare` contains 23 tables. Verified inventory:

| Table | Grain | Rows | Size |
| --- | --- | --- | --- |
| `physicians_and_other_supplier_2012..2015` | NPI x HCPCS x place of service | 9.5M (2015) | 2.37 GB |
| `part_d_prescriber_2014` | NPI x drug | 24.1M | 3.78 GB |
| `referring_durable_medical_equip_2013/2014` | one row per referring NPI | 366k | 0.12 GB |
| `inpatient_charges_2011..2015` | hospital x DRG | — | — |
| `outpatient_charges_2011..2015` | hospital x APC | — | — |
| `home_health_agencies_2013/2014`, `hospice_providers_2014`, `nursing_facilities_2013/2014` | facility attributes + quality measures | — | — |
| `hospital_general_info` | hospital reference data | — | — |

### What I would actually use

**Primary — `physicians_and_other_supplier_2015`.** This is the backbone. Grain
is one row per (NPI, HCPCS code, place of service), which is already an edge
list. The columns that matter:

| Column | Role in the graph |
| --- | --- |
| `npi` | `:Provider` node key |
| `nppes_provider_last_org_name`, `..._first_name`, `nppes_entity_code` | provider identity, individual vs organisation |
| `provider_type` | `:Specialty` — one half of the peer group |
| `nppes_provider_state`, `nppes_provider_zip`, `nppes_provider_city` | geography — the other half of the peer group |
| `hcpcs_code` | `:Procedure` node key |
| **`hcpcs_description`** | **the text that gets embedded — this is what makes it GraphRAG** |
| `hcpcs_drug_indicator` | flags drug codes |
| `line_srvc_cnt`, `bene_unique_cnt`, `bene_day_srvc_cnt` | edge weights: volume, distinct patients, patient-days |
| `average_submitted_chrg_amt`, `average_medicare_payment_amt`, `average_medicare_allowed_amt` | edge weights: money, and the charge-to-paid ratio |

Two derived signals worth computing at load time, because they are classic
abuse indicators and cost nothing to add:

- `line_srvc_cnt / bene_unique_cnt` — services per patient. High values mean the
  same patient is billed for the same thing repeatedly.
- `average_submitted_chrg_amt / average_medicare_allowed_amt` — the markup
  ratio.

**Secondary — `referring_durable_medical_equip_2014`.** Small (366k rows, one
row per referring provider) and the richest single fraud signal in the dataset.
`number_of_suppliers` is the number of distinct DME suppliers a provider sent
business to. Measured distribution:

| State | Referring providers | Median suppliers | p99 | Max | DME paid |
| --- | --- | --- | --- | --- | --- |
| TX | 22,489 | 10 | 77 | 322 | $296.4M |
| CA | 28,655 | 10 | 72 | 138 | $289.3M |
| FL | 22,314 | 10 | 82 | **200** | $287.6M |
| NY | 23,728 | 9 | 66 | 204 | $178.8M |
| MI | 13,739 | 11 | 70 | 200 | $160.3M |

A 20x gap between the median and the maximum. A physician routing patients to
200 different DME suppliers in one year is not a normal practice pattern. These
become `:Provider` properties, not edges — the table is provider-level and does
not name the suppliers.

**Third — `part_d_prescriber_2014`** for `(:Provider)-[:PRESCRIBED]->(:Drug)`.
Optional. It adds controlled-substance angles but also 24M rows to filter, and
it is a different year from the billing backbone. Add it only if there is time.

### What is *not* there — the correction to the original idea

There is **no provider-to-provider referral edge anywhere in this dataset.**
`referring_durable_medical_equip_*` sounds like it has one, but its grain is one
row per referring provider with aggregate counts — it never names the supplier
on the other end. Every table here is provider-to-*service*, not
provider-to-*provider*.

Real referral edges live in a separate CMS release,
[Physician Shared Patient Patterns](https://www.nber.org/research/data/physician-shared-patient-patterns-data)
(NBER-hosted, 2009–2015), which links two providers who treated the same patient
within 30/60/90/180 days. It is a bulk download, roughly ten million edges per
year nationally.

**So the provider-to-provider edges have to be derived, not loaded:**

- `(:Provider)-[:PEER_OF]->(:Provider)` — same `provider_type`, same geography.
  Defines the comparison group.
- `(:Provider)-[:SIMILAR_BASKET_TO {jaccard}]->(:Provider)` — overlap in the set
  of HCPCS codes billed. This is the interesting one: providers running the same
  scheme bill the same unusual basket, and that shows up as a dense cluster.

Keying `:Provider` on NPI from day one means the real shared-patient edges can
be layered in later without a remodel, if the schedule allows.

### Labels — OIG LEIE

The [OIG List of Excluded Individuals and Entities](https://oig.hhs.gov/exclusions/exclusions_list.asp)
is a free 15 MB CSV, refreshed monthly, holding exclusions currently in effect.
Columns: `LASTNAME, FIRSTNAME, MIDNAME, BUSNAME, GENERAL, SPECIALTY, UPIN, NPI,
DOB, ADDRESS, CITY, STATE, ZIP, EXCLTYPE, EXCLDATE, REINDATE, WAIVERDATE,
WVRSTATE`.

**Caution, and the reason to check before building on it: only 10.6% of records
carry a usable NPI** — 8,700 of 84,001. The rest predate NPI collection or are
individuals without one. Join on name/state for the remainder is fuzzy and not
worth the time here.

Measured overlap against FL providers in the 2015 billing file:

```text
FL 2015 Medicare providers           59,326
LEIE records with usable NPI          8,700
FL providers found in LEIE              149   <-- the label set
2015 Medicare paid to those 149    $23.6M
```

Exclusion year of those 149: **3 in 2015, the other 146 in 2016–2026.** That is
the whole story — the labels land *after* the billing year, so this is a genuine
forward-looking test, not a lookup. Exclusion types: 55 `1128b4` (licence
revocation, often not fraud), 44 `1128a1` (program-related crime conviction), 20
`1128a4` (felony controlled substance), 19 `1128a3` (felony health-care fraud).
Roughly 87 of the 149 are fraud-relevant types.

---

## 2. Scope — what fits in Aura Free

Aura Free caps at **200,000 nodes / 400,000 relationships**. Measured options:

| Scope | Providers | Billed edges | Nodes | LEIE labels | Fits? |
| --- | --- | --- | --- | --- | --- |
| FL statewide | 59,326 | 695,541 | ~65k | 149 | **over cap** |
| South FL (zip3 330–334, 339, 341–342) | 23,678 | 269,223 | ~30k | 68 | yes |
| Tri-county + SW coast | 19,532 | 208,158 | ~26k | 63 | yes |
| Miami-Dade + Broward only | 11,970 | 105,296 | ~18k | 40 | yes |
| FL statewide, top-8 codes per provider | 59,326 | 332,614 | ~65k | 149 | yes, but tight |

**Recommended: South Florida, 2015.** Reasons:

1. 269k billed edges leaves ~110k relationship headroom for the derived
   `:PEER_OF` and `:SIMILAR_BASKET_TO` edges — and those derived edges *are* the
   analysis. The statewide top-8 option leaves only ~47k, which is not enough.
2. Truncating to top-K codes per provider throws away exactly the rare codes
   that carry the fraud signal. Geographic scoping does not distort the basket.
3. Geography is the correct peer-group boundary anyway — comparing a Miami
   podiatrist to a rural Montana one is not a comparison.
4. 68 labels is enough to report precision@50 honestly.
5. South Florida is the genuine Medicare fraud epicentre, so the narrative is
   real rather than arbitrary.

`:Procedure` nodes cost almost nothing: **5,983 distinct HCPCS codes nationally,
5,421 distinct descriptions.** The entire vector index is under 6,000 embeddings.

---

## 3. The GraphRAG use case

The honest problem with "find billing outliers" as a hackathon entry is that it
is graph analytics with an agent bolted on. There is no retrieval, so it is not
GraphRAG. Here is the version that is.

### The retrieval loop

**Question:** *"Show me providers who look like the orthotic brace scheme."*

1. **Vector retrieval over text.** Embed the 5,421 `hcpcs_description` strings
   as `:Procedure` nodes, plus chunked DOJ and HHS-OIG enforcement press
   releases as `:SchemeNarrative` nodes. The question hits the vector index and
   returns the scheme narrative *and* the specific codes it maps to — L0648,
   L0650, L1832 and friends. The billing file calls these "knee orthosis, rigid,
   custom fabricated"; nobody types that, and nobody knows the code. **Lexical
   search fails here and vector search succeeds** — that is the retrieval step
   doing real work, not decoration.

2. **Graph traversal from the retrieved entry points.** From those `:Procedure`
   nodes, walk to every `:Provider` that billed them, then out to
   `:PEER_OF` to build the comparison group, and compute deviation within it.

3. **Second-hop structural reasoning.** For the providers that stand out: what
   *else* do they bill? Do they cluster with each other via
   `:SIMILAR_BASKET_TO`? Is the cluster geographically tight? Is anyone in it
   within one or two hops of a provider already carrying an `:Exclusion`?

4. **Answer with an evidence path.** Ranked leads, each with the peer group used,
   the deviation, the cluster it sits in, and the Cypher that produced it.

### Why this needs a graph

Step 1 alone is plain RAG and returns a document. Step 2 alone is SQL. The parts
that are neither:

- **Basket similarity clustering.** "Which providers bill a near-identical
  unusual set of codes?" is a self-join over set overlap — expressible in SQL,
  miserable, and it does not compose with anything else.
- **Proximity to known-bad.** "Which still-active providers are two hops from an
  excluded provider through shared billing patterns?" is a variable-length path
  query. This is where a graph stops being a preference.
- **Structural position.** Betweenness and community detection ask *where a
  provider sits*, not *what they billed*. A high-volume provider in the middle of
  a dense lookalike cluster is a different object from an equally high-volume
  provider sitting alone, and only the graph can tell them apart.
- **Composability.** The agent chains retrieval into traversal into ranking in
  one pass, then follows up on its own findings. That is the demo.

### The validation claim

Because the labels land after the billing year, the headline is measurable:

> Using only 2015 billing structure, the top-50 structural anomalies contain
> N providers who were excluded from federal healthcare programs in 2016–2026.

If N is meaningfully above the base rate (68 labels in 23,678 providers, so
~0.29%; a random top-50 would expect 0.14 hits), that is a real result. If it is
not, that is *also* reportable and more interesting than a fraud score nobody
checked. Either way it beats an unvalidated number.

---

## 4. Framing

The data is public *aggregate* billing data. A statistical outlier is not fraud
and usually has a benign explanation: a regional referral centre, a sicker
patient panel, the only specialist in a county, a small denominator. Note that
55 of the 149 FL labels are licence revocations, which frequently have nothing
to do with billing at all.

Frame the output as **anomaly triage and lead generation for a human
investigator**, and build that into the agent rules: always state the peer group,
always offer a benign explanation, never assert wrongdoing about a named real
provider. This is already in [AGENTS.md](../AGENTS.md).

---

## 5. Open questions

- [ ] Confirm South Florida over statewide-truncated. Leaning South Florida.
- [ ] Where do the 5,421 embeddings get generated, and do `:Procedure` vector
      properties fit the Aura Free node budget alongside the graph? (They should
      — 6k nodes is nothing — but confirm the index builds.)
- [ ] How many DOJ/OIG enforcement press releases to chunk, and can provider
      names in them be resolved to NPIs, or do they stay as scheme-level text?
- [ ] `:SIMILAR_BASKET_TO` threshold — what Jaccard cutoff keeps the derived
      edge count under the ~110k headroom?
- [ ] Is `part_d_prescriber_2014` worth the year mismatch against 2015 billing?

---

## Candidate B — Open Payments influence graph (fallback)

`(:Company)-[:PAID]->(:Physician)-[:PRESCRIBED]->(:Drug)`, from CMS Open
Payments plus Part D. Joins on NPI exactly like Candidate A, so it reuses the
same `:Provider` model — a short pivot rather than a restart if A stalls. The
question, does industry payment correlate with prescribing, is well-trodden:
lower risk, lower ceiling.

---

## Candidate C — something non-healthcare

Not developed. Only worth opening if A and B both hit a wall.

---

## Sources checked

- `bigquery-public-data.cms_medicare` — queried directly, 2026-09-18
- [OIG LEIE downloadable files](https://oig.hhs.gov/exclusions/exclusions_list.asp) — downloaded and profiled, 2026-09-18
- [Medicare Physician & Other Practitioners](https://data.cms.gov/provider-summary-by-type-of-service/medicare-physician-other-practitioners)
- [Medicare DME by Referring Provider](https://data.cms.gov/provider-summary-by-type-of-service/medicare-durable-medical-equipment-devices-supplies/medicare-durable-medical-equipment-devices-supplies-by-referring-provider-and-service)
- [Physician Shared Patient Patterns (NBER)](https://www.nber.org/research/data/physician-shared-patient-patterns-data)
- [Reference structure: JeremyMorgan/neo4j-airport-resilience-agent](https://github.com/JeremyMorgan/neo4j-airport-resilience-agent)

---

## Decision log

| Date | Decision |
| --- | --- |
| 2026-09-18 | Repo scaffolded. Direction not locked; Candidate A front-runner. |
| 2026-09-18 | Verified BigQuery tables and LEIE overlap. No provider-to-provider edges exist in `cms_medicare`; they must be derived. LEIE NPI coverage is 10.6%, giving 149 FL labels. South Florida 2015 is the recommended scope at 269k billed edges. GraphRAG hinges on embedding `hcpcs_description` + enforcement narratives as the entry point into the graph. |
