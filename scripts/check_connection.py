"""Confirm the .env credentials reach the Aura instance.

Usage: python scripts/check_connection.py
"""

from __future__ import annotations

import sys

from common import create_driver, neo4j_settings


def main() -> int:
    try:
        _, _, _, database = neo4j_settings()
    except RuntimeError as exc:
        print(f"FAIL: {exc}")
        return 1

    try:
        with create_driver() as driver:
            driver.verify_connectivity()
            with driver.session(database=database) as session:
                counts = session.run(
                    "MATCH (n) RETURN count(n) AS nodes"
                ).single()["nodes"]
                rels = session.run(
                    "MATCH ()-[r]->() RETURN count(r) AS rels"
                ).single()["rels"]
    except Exception as exc:  # noqa: BLE001 - surface whatever the driver says
        print(f"FAIL: could not query Aura: {exc}")
        return 1

    print(f"OK: connected to database '{database}'")
    print(f"    nodes: {counts:,}")
    print(f"    relationships: {rels:,}")
    print("    Aura Free budget: 200,000 nodes / 400,000 relationships")
    return 0


if __name__ == "__main__":
    sys.exit(main())
