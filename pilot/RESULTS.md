# Pilot results — citation classification

Run 2026-09-18. Reproduce with:

```bash
python pilot/fetch_contexts.py   # pull citation sentences from Semantic Scholar
python pilot/make_sample.py      # draw the 100-edge sample (fixed seed)
python pilot/score.py            # distributions, data quality, agreement
```

Raw contexts live in `data/pilot/` (gitignored). The rules were fixed in
[RUBRIC.md](RUBRIC.md) before any context was read, and the model labels are in
[labels_model.csv](labels_model.csv).

## Verdict

**Provisional pass on plausibility. The real gate is still open.** The model
labels behave exactly as the design needs, but they have only been checked
against expectations, not against independent human labels. Classifying and
then grading its own work is not a test. The gate closes when
`data/pilot/human_labels.csv` is filled in (`score.py` creates the blank
template) and reaches **kappa ≥ 0.6 and load-bearing precision and recall
≥ 80%**.

## Setup

| | |
| --- | --- |
| Seeds | Wakefield MMR (*Lancet* 1998, retracted 2010-02-06); Propofol / gastric cancer, paper mill (*IJBM* 2018, retracted 2022-02-25) |
| Source of citation sentences | Semantic Scholar Graph API, `contexts` field |
| Sample | 100 edges: all 23 propofol edges with context, 38 Wakefield cited before retraction, 39 after |
| Classifier | Claude, blind: saw only the citing title and citation sentences. Year, retraction status and Semantic Scholar's labels were withheld |
| Labels | load-bearing / background / critical / unclear, per [RUBRIC.md](RUBRIC.md) |

## Result 1 — the classification separates the two cases

| Group | load-bearing | background | critical | unclear | n |
| --- | --- | --- | --- | --- | --- |
| Propofol (paper mill), all | **23** | 0 | 0 | 0 | 23 |
| Wakefield, cited before retraction | 5 | 19 | 14 | 0 | 38 |
| Wakefield, cited after retraction | **1** | 6 | **30** | 2 | 39 |

This is the proposal's central claim, now measured instead of argued:

- **Every propofol citation with a readable context treats the fabricated result
  as established fact.** Sentences like *"Propofol inhibits proliferation,
  migration and invasion, and induces apoptosis in gastric cancer cells by
  upregulating mir-195 and mir-451"*,
  in review tables, as the rationale for new studies, and as corroboration
  ("quite in coincidence with our findings"). One citing paper is itself
  retracted.
- **Wakefield, after retraction, is overwhelmingly cited to refute it** (30 of
  39 critical). The 66% post-retraction citation figure is nearly all people
  studying the fraud.
- **The load-bearing Wakefield edges are the right ones.** Before retraction:
  the authors' own follow-up, *"Autism: A Unique Type of Mercury Poisoning"*, a
  multivitamin trial for autism, and a paper proposing an acetaminophen-MMR
  link. After retraction, exactly one: a 2015 paper on communication devices
  that states the 1998 finding as fact. That is the kind of edge the product
  exists to surface.

Confidence: 56 high, 33 medium, 11 low.

## Result 2 — Semantic Scholar's own labels cannot do this job

Semantic Scholar publishes a citation-intent label (background / methodology /
result). Against the model labels:

| Model label | S2 said background | S2 said methodology | S2 said result |
| --- | --- | --- | --- |
| load-bearing | **24** | 0 | 0 |
| critical | **30** | 2 | 2 |

Every load-bearing edge it labelled (24 of 29) it called "background", and it did the same for most critical ones. Its
taxonomy has no notion of *disputing* a source, so it cannot tell "builds on"
from "argues against". The classification step cannot be skipped by reusing an
existing label; this is new work.

## Result 3 — data problems found (these matter as much as the labels)

1. **Citation-context coverage is low.** Semantic Scholar has the citing sentence
   for only **21%** of Wakefield's 1,876 citations and **39%** of the propofol
   paper's 59. The rest cannot be classified from context. **This is now the
   largest risk to the project**, larger than classification quality.
2. **Duplicate records.** The 23 propofol edges contain at least 5 exact duplicates,
   and about 7 once truncated copies are counted, so roughly 16–18 distinct papers:
   the same paper under a real title and under PDF-junk titles such as
   `OTT_A_232601 361..370`. The Wakefield set has a Spanish and an English
   version of one article. Without deduplication, contagion counts inflate by
   roughly 20%.
3. **Misattributed citations.** At least 2 of 100 contexts have nothing to do with
   the seed (an HIV pharmacology sentence; a reference-list fragment).
4. **Source disagreement.** OpenAlex counts 2,961 Wakefield citers and 51 for
   propofol; Semantic Scholar counts 1,876 and 59. Counts must name their
   source.

## Result 4 — where the rubric is soft

- The 4-class labels are sensitive to one convention: citing Wakefield as the
  *origin of a scare* is labelled `critical`. Changing that convention moves
  7 edges between `background` and `critical`, but **none across the
  load-bearing line**, which is the only boundary that controls propagation.
- The genuinely hard cases are hedged citations inside a paper whose own
  hypothesis depends on the seed. The acetaminophen paper (e020) says "studies
  have suggested... but see", but its own hypothesis rests on the MMR link. The
  sentence alone undersells the dependency. Giving the classifier the citing
  paper's abstract would likely fix this class.

## What changes in the design

| Finding | Change |
| --- | --- |
| Context coverage 21–39% | Add a fallback path: classify context-less edges from the citing abstract, with a lower confidence and a separate label. Evaluate open-access full-text extraction (for example via OpenAlex OA locations) to raise coverage. Report coverage alongside every contagion count. |
| Duplicate S2 records | Deduplicate citing papers on DOI, then normalised title, before any counting. Make it a tested staging step. |
| Misattributed contexts | Keep `unclear` as a first-class label; never propagate through it. |
| S2 intents unusable | Do not use them as features or shortcuts. |
| Hedged-but-dependent citations | Pass the citing abstract to the classifier alongside the sentence. |

## Next step

Fill in `data/pilot/human_labels.csv` blind (do not open `labels_model.csv`
first), then run `python pilot/score.py`. About an hour for 100 edges. If
someone else can independently label the same 100, their agreement with you
gives a ceiling for what the model can be expected to reach.
