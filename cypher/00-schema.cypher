// Constraints and indexes. Run this before any bulk load.
// Placeholder: the node keys depend on the dataset chosen in IDEATION.md.
//
// Pattern to follow once the model is fixed:
//
//   CREATE CONSTRAINT provider_npi IF NOT EXISTS
//   FOR (p:Provider) REQUIRE p.npi IS UNIQUE;
//
//   CREATE INDEX provider_state IF NOT EXISTS
//   FOR (p:Provider) ON (p.state);

// Inspect what is actually in the database:
CALL db.schema.visualization();
