"""Print the live graph schema so the agent and the humans see the same model.

Usage: python scripts/show_schema.py
"""

from __future__ import annotations

import sys

from common import create_driver, neo4j_settings


def main() -> int:
    _, _, _, database = neo4j_settings()

    with create_driver() as driver, driver.session(database=database) as session:
        labels = session.run("CALL db.labels() YIELD label RETURN label ORDER BY label")
        print("Labels:")
        for record in labels:
            count = session.run(
                f"MATCH (n:`{record['label']}`) RETURN count(n) AS c"
            ).single()["c"]
            print(f"  :{record['label']}  ({count:,})")

        print("\nRelationship types:")
        types = session.run(
            "CALL db.relationshipTypes() YIELD relationshipType "
            "RETURN relationshipType ORDER BY relationshipType"
        )
        for record in types:
            rel = record["relationshipType"]
            count = session.run(
                f"MATCH ()-[r:`{rel}`]->() RETURN count(r) AS c"
            ).single()["c"]
            print(f"  [:{rel}]  ({count:,})")

        print("\nVisual schema:")
        for record in session.run("CALL db.schema.visualization()"):
            print(f"  {record}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
