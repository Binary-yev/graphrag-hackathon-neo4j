"""Draw the 100-edge pilot sample and a blind view for classification.

- all propofol edges with context (23)
- Wakefield edges to make up 100, split evenly before / after retraction

The blind view shows only the citing title and citation sentences. Year,
retraction status, and Semantic Scholar's own labels are withheld so the
classifier cannot shortcut ("cited after 2010, so it must be critical").

Usage: python pilot/make_sample.py
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "data" / "pilot"
TOTAL = 100
RNG_SEED = 20260918


def main() -> int:
    rows = [json.loads(line) for line in (PILOT / "contexts.jsonl").open(encoding="utf-8")]
    rng = random.Random(RNG_SEED)

    propofol = [r for r in rows if r["seed"] == "propofol"]
    wake_pre = [r for r in rows if r["seed"] == "wakefield" and not r["afterRetraction"]]
    wake_post = [r for r in rows if r["seed"] == "wakefield" and r["afterRetraction"]]

    need = TOTAL - len(propofol)
    n_pre = min(len(wake_pre), need // 2)
    n_post = need - n_pre
    sample = propofol + rng.sample(wake_pre, n_pre) + rng.sample(wake_post, n_post)
    rng.shuffle(sample)

    for i, r in enumerate(sample, 1):
        r["edgeId"] = f"e{i:03d}"

    with (PILOT / "sample.jsonl").open("w", encoding="utf-8") as fh:
        for r in sample:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    with (PILOT / "blind.txt").open("w", encoding="utf-8") as fh:
        for r in sample:
            fh.write(f"### {r['edgeId']} | {r['title']}\n")
            for ctx in r["contexts"][:3]:
                fh.write(f"  > {' '.join(ctx.split())[:400]}\n")
            fh.write("\n")

    print(f"sample: {len(sample)} edges  (propofol {len(propofol)}, "
          f"wakefield pre {n_pre}, wakefield post {n_post})")
    print(f"wrote {PILOT.relative_to(ROOT)}/sample.jsonl and blind.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
