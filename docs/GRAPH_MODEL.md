# Graph model — proposed

Status: **parked.** This models the Medicare candidate, which was set aside on
2026-09-18 — see [../IDEATION.md](../IDEATION.md) for the current direction and
[CANDIDATE-MEDICARE.md](CANDIDATE-MEDICARE.md) for the feasibility work it rests
on. Kept because the sizing method transfers. Scope was South Florida, 2015.

## Shape

```text
                    ┌──────────────────┐
                    │ :SchemeNarrative │  DOJ / HHS-OIG enforcement text
                    │   embedding      │  (chunked, embedded)
                    └────────┬─────────┘
                             │ :MENTIONS_CODE
                             ▼
  ┌────────────┐      ┌──────────────┐
  │ :Specialty │      │  :Procedure  │  hcpcs_description, embedded
  └─────▲──────┘      │   embedding  │  ~5,400 nodes
        │             └──────▲───────┘
        │ :HAS_SPECIALTY     │ :BILLED  {services, beneficiaries,
        │                    │           avgSubmittedCharge, avgMedicarePayment,
        │                    │           servicesPerBene, markupRatio, placeOfService}
        │             ┌──────┴───────┐
        └─────────────┤  :Provider   ├──────────────┐
                      │  npi (key)   │              │ :EXCLUDED_AS
                      │  ~23,700     │              ▼
                      └──┬────────┬──┘      ┌──────────────┐
           :LOCATED_IN   │        │         │ :Exclusion   │  LEIE
                         ▼        │         │ exclType,    │  68 in scope
                  ┌───────────┐   │         │ exclDate     │
                  │ :ZipArea  │   │         └──────────────┘
                  └───────────┘   │
                                  │ :PEER_OF            (derived)
                                  │ :SIMILAR_BASKET_TO  (derived, {jaccard})
                                  ▼
                            ┌──────────────┐
                            │  :Provider   │
                            └──────────────┘
```

## Nodes

| Label | Key | Count | Source |
| --- | --- | --- | --- |
| `:Provider` | `npi` | ~23,700 | `physicians_and_other_supplier_2015` + DME table |
| `:Procedure` | `hcpcsCode` | ~5,400 | same, `hcpcs_description` embedded |
| `:Specialty` | `name` | ~90 | `provider_type` |
| `:ZipArea` | `zip` | ~250 | `nppes_provider_zip` |
| `:Exclusion` | `npi` + `exclDate` | 68 | OIG LEIE |
| `:SchemeNarrative` | `chunkId` | TBD | DOJ / HHS-OIG press releases, chunked |

## Relationships

| Type | From → To | Count | Origin |
| --- | --- | --- | --- |
| `:BILLED` | Provider → Procedure | ~269,000 | loaded |
| `:HAS_SPECIALTY` | Provider → Specialty | ~23,700 | loaded |
| `:LOCATED_IN` | Provider → ZipArea | ~23,700 | loaded |
| `:EXCLUDED_AS` | Provider → Exclusion | 68 | loaded |
| `:PEER_OF` | Provider → Provider | derived | same specialty + same ZipArea |
| `:SIMILAR_BASKET_TO` | Provider → Provider | derived | HCPCS-set Jaccard above a threshold |
| `:MENTIONS_CODE` | SchemeNarrative → Procedure | derived | code extraction from narrative text |

## Budget

Aura Free allows 200,000 nodes / 400,000 relationships.

```text
nodes          ~29,500     15% of budget
loaded edges  ~293,000     73% of budget
headroom      ~107,000     for :PEER_OF + :SIMILAR_BASKET_TO
```

`:PEER_OF` is the risk. Materialising it for every same-specialty, same-ZIP pair
is quadratic within each group and will blow the budget. Options, in order of
preference:

1. Do not materialise it. Compute the peer group at query time from
   `:HAS_SPECIALTY` + `:LOCATED_IN` — both are cheap index lookups.
2. Materialise only at the specialty + county level, capped per group.
3. Materialise only for the providers that survive a first-pass deviation
   filter.

**Start with option 1.** `:SIMILAR_BASKET_TO` is the derived edge worth spending
relationships on, since it is what makes the cluster analysis possible, and its
count is controlled by the Jaccard threshold.

## Vector indexes

| Index | On | Dimension |
| --- | --- | --- |
| `procedure_description` | `:Procedure(embedding)` | per model |
| `scheme_narrative` | `:SchemeNarrative(embedding)` | per model |

~5,400 procedure embeddings is small enough that the index builds in seconds and
costs almost nothing to generate.

## Constraints

```cypher
CREATE CONSTRAINT provider_npi IF NOT EXISTS
FOR (p:Provider) REQUIRE p.npi IS UNIQUE;

CREATE CONSTRAINT procedure_code IF NOT EXISTS
FOR (c:Procedure) REQUIRE c.hcpcsCode IS UNIQUE;

CREATE CONSTRAINT specialty_name IF NOT EXISTS
FOR (s:Specialty) REQUIRE s.name IS UNIQUE;

CREATE CONSTRAINT ziparea_zip IF NOT EXISTS
FOR (z:ZipArea) REQUIRE z.zip IS UNIQUE;
```

## Open modelling questions

- Should `place_of_service` be an edge property (as above) or a separate node?
  Edge property unless a question needs to traverse by it.
- `:ZipArea` at 5-digit or 3-digit granularity? 5-digit peer groups may be too
  small to compare against; county would be better but needs a ZIP-to-county
  crosswalk.
- Do provider names in enforcement narratives resolve to NPIs, or does
  `:SchemeNarrative` stay linked only to `:Procedure` via extracted codes?
