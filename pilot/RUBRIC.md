# Citation classification rubric

Fixed **before** any context was read. The unit is one citation edge: a citing
paper plus every sentence in which it cites the seed paper. When the sentences
disagree, the most dependent use wins (one load-bearing sentence makes the edge
load-bearing).

| Label | Rule | Propagates contagion? |
| --- | --- | --- |
| `load-bearing` | The citing paper **asserts or relies on the seed's finding as valid**: as evidence for its own claim, the rationale for its hypothesis, or the source of a method or dataset. Counts even when the seed is one reference in a list, if the sentence states the finding as true. | yes |
| `background` | Mentions the seed **without asserting its finding is true**: history, "has been reported/proposed", a list of prior work on a topic, or a neutral pointer. | no |
| `critical` | Disputes, refutes, or corrects the seed; notes its retraction or fraud; or cites it as an example of misinformation, misconduct, or a public-health scare. | no |
| `unclear` | The context is too short, garbled, or ambiguous to decide. | flagged |

Borderline conventions, decided in advance:

- "X was **suggested / hypothesised** to cause Y [seed]" with no endorsement and
  no dispute → `background`.
- "X causes / is associated with / promotes Y [seed, others]" stated as fact →
  `load-bearing`.
- Describing the seed only as the *origin* of a controversy or scare →
  `critical`, since it is cited as the thing that was wrong.
- Using the seed's *methods* (an assay, a cell line, a protocol) while making no
  claim about its findings → `load-bearing`. A method taken from a fabricated
  paper is still a dependency.

The classifier sees only the citing title and the citation sentences. Year,
retraction status, and Semantic Scholar's intent labels are withheld.
