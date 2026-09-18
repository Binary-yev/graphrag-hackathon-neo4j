"""Pull citation contexts for the pilot seed papers from Semantic Scholar.

OpenAlex has the citation edges but not the sentence in which a paper is cited.
Semantic Scholar's Graph API does (`contexts`), plus its own citation-intent
labels (`intents`) and an `isInfluential` flag, which we keep as an independent
baseline to compare against.

Writes data/pilot/contexts.jsonl (gitignored): one row per citation edge that
has at least one context sentence, and prints coverage statistics.

Usage: python pilot/fetch_contexts.py
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "pilot" / "contexts.jsonl"

API = "https://api.semanticscholar.org/graph/v1/paper/{pid}/citations"
FIELDS = "title,year,externalIds,contexts,intents,isInfluential"
PAGE = 1000

SEEDS = {
    "wakefield": {
        "doi": "10.1016/S0140-6736(97)11096-0",
        "label": "Wakefield MMR (Lancet 1998)",
        "retracted": "2010-02-06",
    },
    "propofol": {
        "doi": "10.1016/j.ijbiomac.2018.08.173",
        "label": "Propofol / gastric cancer, paper mill (IJBM 2018)",
        "retracted": "2022-02-25",
    },
}


def get(url: str, attempts: int = 6) -> dict:
    """GET with exponential backoff; the keyless S2 pool rate-limits hard."""
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "graphrag-hackathon-pilot"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and i < attempts - 1:
                wait = 2 ** (i + 1)
                print(f"    rate limited, retrying in {wait}s")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("unreachable")


def fetch_all(doi: str) -> list[dict]:
    pid = urllib.parse.quote(f"DOI:{doi}", safe=":")
    rows, offset = [], 0
    while True:
        url = f"{API.format(pid=pid)}?fields={FIELDS}&limit={PAGE}&offset={offset}"
        page = get(url)
        rows.extend(page.get("data", []))
        if "next" not in page:
            return rows
        offset = page["next"]
        time.sleep(1.2)


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    kept = 0
    with OUT.open("w", encoding="utf-8") as fh:
        for key, seed in SEEDS.items():
            print(f"{seed['label']}")
            citations = fetch_all(seed["doi"])
            retracted_year = int(seed["retracted"][:4])
            with_ctx = 0
            for c in citations:
                paper = c.get("citingPaper") or {}
                contexts = [x for x in (c.get("contexts") or []) if x and x.strip()]
                if not contexts:
                    continue
                with_ctx += 1
                year = paper.get("year")
                fh.write(json.dumps({
                    "seed": key,
                    "seedRetracted": seed["retracted"],
                    "citingPaperId": paper.get("paperId"),
                    "citingDoi": (paper.get("externalIds") or {}).get("DOI"),
                    "title": paper.get("title"),
                    "year": year,
                    "afterRetraction": year is not None and year > retracted_year,
                    "contexts": contexts,
                    "s2Intents": c.get("intents") or [],
                    "s2Influential": c.get("isInfluential"),
                }, ensure_ascii=False) + "\n")
            kept += with_ctx
            pct = 100 * with_ctx / len(citations) if citations else 0
            print(f"    citations: {len(citations):,}   with context: {with_ctx:,} ({pct:.0f}%)")
            time.sleep(1.2)

    print(f"\nwrote {kept:,} citation edges with context -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
