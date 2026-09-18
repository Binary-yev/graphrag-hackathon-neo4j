// Read-only exploration. Safe to run at any time.

// Label and relationship-type counts, plus property keys (APOC Core, available on Aura).
CALL apoc.meta.stats()
YIELD labels, relTypesCount, nodeCount, relCount
RETURN nodeCount, relCount, labels, relTypesCount;

// Graph size against the Aura Free budget (200k nodes / 400k relationships).
MATCH (n) WITH count(n) AS nodes
MATCH ()-[r]->() WITH nodes, count(r) AS rels
RETURN nodes, rels,
       round(100.0 * nodes / 200000, 1) AS pctNodeBudget,
       round(100.0 * rels / 400000, 1) AS pctRelBudget;

// Fallback if APOC is unavailable: list labels and relationship types only.
CALL db.labels() YIELD label RETURN label ORDER BY label;
CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType ORDER BY relationshipType;
