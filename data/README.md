# Data

Source data is **not committed**. `data/raw/` and `data/processed/` are
gitignored; only this README and the `.gitkeep` files are tracked.

```text
data/raw/          Unmodified downloads, exactly as retrieved
data/processed/    Filtered/aggregated extracts ready for loading into Aura
data/manifest.json Provenance record (gitignored, written by the download script)
```

## Provenance rules

Every dataset that enters `data/raw/` must be recorded in `data/manifest.json`
with:

- source URL
- retrieval timestamp
- file size and SHA-256
- row count
- licence or terms-of-use reference

When a dataset is chosen, document its columns and its licence in this file and
in `DATA_LICENSE.md`.

## Sizing

Aura Free holds **200,000 nodes / 400,000 relationships**. Estimate node and
relationship counts from the extract before loading. Filtering belongs upstream
(in BigQuery or in the download script), not in Cypher.

## Current status

No dataset selected yet. See [../IDEATION.md](../IDEATION.md).
