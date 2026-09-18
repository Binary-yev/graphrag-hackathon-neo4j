"""Score the pilot: label distributions, data quality, and (once available)
agreement between the model labels and independent human labels.

Human labels go in data/pilot/human_labels.csv. If the file does not exist it is
created as a blank template: fill the `human_label` column with one of
load-bearing / background / critical / unclear, using pilot/RUBRIC.md, WITHOUT
looking at pilot/labels_model.csv first.

Usage: python pilot/score.py
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT_DATA = ROOT / "data" / "pilot"
MODEL_LABELS = ROOT / "pilot" / "labels_model.csv"
HUMAN_LABELS = PILOT_DATA / "human_labels.csv"
LABELS = ["load-bearing", "background", "critical", "unclear"]


def norm(text: str) -> str:
    return " ".join(text.lower().split())[:160]


def load() -> list[dict]:
    sample = {r["edgeId"]: r for r in map(json.loads, (PILOT_DATA / "sample.jsonl").open(encoding="utf-8"))}
    for row in csv.DictReader(MODEL_LABELS.open(encoding="utf-8")):
        sample[row["edgeId"]].update(model=row["label"], confidence=row["confidence"])
    missing = [k for k, v in sample.items() if "model" not in v]
    if missing:
        raise SystemExit(f"model labels missing for: {missing}")
    return list(sample.values())


def distributions(rows: list[dict]) -> None:
    groups = {
        "propofol (paper mill), all": [r for r in rows if r["seed"] == "propofol"],
        "wakefield, cited before retraction": [r for r in rows if r["seed"] == "wakefield" and not r["afterRetraction"]],
        "wakefield, cited after retraction": [r for r in rows if r["seed"] == "wakefield" and r["afterRetraction"]],
    }
    print("MODEL LABEL DISTRIBUTION")
    print(f"  {'group':<38}" + "".join(f"{l:>14}" for l in LABELS) + f"{'n':>6}")
    for name, g in groups.items():
        c = Counter(r["model"] for r in g)
        print(f"  {name:<38}" + "".join(f"{c[l]:>14}" for l in LABELS) + f"{len(g):>6}")
    conf = Counter(r["confidence"] for r in rows)
    print(f"\n  confidence: high {conf['high']}, medium {conf['medium']}, low {conf['low']}")


def data_quality(rows: list[dict]) -> None:
    print("\nDATA QUALITY (Semantic Scholar)")
    for seed in ("propofol", "wakefield"):
        g = [r for r in rows if r["seed"] == seed]
        uniq_ctx = {norm(r["contexts"][0]) for r in g}
        print(f"  {seed:<10} edges {len(g):>3}   distinct first-context texts {len(uniq_ctx):>3}"
              f"   -> {len(g) - len(uniq_ctx)} probable duplicate records")
    intents = Counter(i for r in rows for i in (r["s2Intents"] or ["(none)"]))
    print(f"  S2 intent labels present: {dict(intents)}")


def agreement(rows: list[dict]) -> None:
    if not HUMAN_LABELS.exists():
        with HUMAN_LABELS.open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["edgeId", "human_label", "title", "contexts"])
            for r in sorted(rows, key=lambda r: r["edgeId"]):
                w.writerow([r["edgeId"], "", r["title"], " || ".join(r["contexts"][:3])])
        print(f"\nHUMAN AGREEMENT: not yet available. Blank template written to {HUMAN_LABELS.relative_to(ROOT)}")
        return

    human = {r["edgeId"]: r["human_label"].strip() for r in csv.DictReader(HUMAN_LABELS.open(encoding="utf-8"))}
    pairs = [(human[r["edgeId"]], r["model"]) for r in rows if human.get(r["edgeId"]) in LABELS]
    if not pairs:
        print(f"\nHUMAN AGREEMENT: template exists but no labels filled in yet ({HUMAN_LABELS.relative_to(ROOT)})")
        return

    n = len(pairs)
    acc = sum(h == m for h, m in pairs) / n
    ph, pm = Counter(h for h, _ in pairs), Counter(m for _, m in pairs)
    pe = sum(ph[l] * pm[l] for l in LABELS) / (n * n)
    kappa = (acc - pe) / (1 - pe) if pe < 1 else 1.0
    print(f"\nHUMAN AGREEMENT on {n} edges: accuracy {acc:.0%}, Cohen's kappa {kappa:.2f}")

    print("  confusion (rows = human, cols = model)")
    print(f"  {'':<14}" + "".join(f"{l:>14}" for l in LABELS))
    for h in LABELS:
        print(f"  {h:<14}" + "".join(f"{sum(1 for a, b in pairs if a == h and b == m):>14}" for m in LABELS))

    # The decision that matters: does this edge propagate contagion?
    tp = sum(1 for h, m in pairs if h == m == "load-bearing")
    fp = sum(1 for h, m in pairs if m == "load-bearing" and h != "load-bearing")
    fn = sum(1 for h, m in pairs if h == "load-bearing" and m != "load-bearing")
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    print(f"\n  PROPAGATION DECISION (load-bearing vs not): precision {prec:.0%}, recall {rec:.0%}")
    print("  Gate: kappa >= 0.6 and load-bearing precision and recall >= 80% -> build")


def main() -> int:
    rows = load()
    distributions(rows)
    data_quality(rows)
    agreement(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
