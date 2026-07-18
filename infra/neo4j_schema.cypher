// Constraints for the Temporal Regulatory Graph. Run once against Neo4j.
CREATE CONSTRAINT provision_id IF NOT EXISTS FOR (p:Provision) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT version_id IF NOT EXISTS FOR (v:ProvisionVersion) REQUIRE v.id IS UNIQUE;
CREATE CONSTRAINT change_event_id IF NOT EXISTS FOR (c:ChangeEvent) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT artifact_id IF NOT EXISTS FOR (a:InternalArtifact) REQUIRE a.id IS UNIQUE;

// Node labels:  Document, Provision, ProvisionVersion, ChangeEvent, InternalArtifact
// Relationships:
//   (Document)-[:CONTAINS]->(Provision)
//   (Provision)-[:HAS_VERSION]->(ProvisionVersion)
//   (Document)-[:DECLARES]->(ChangeEvent)                 // amending document
//   (ChangeEvent)-[:TARGETS]->(Provision)
//   (ChangeEvent)-[:BEFORE]->(ProvisionVersion)
//   (ChangeEvent)-[:AFTER]->(ProvisionVersion)
//   (ProvisionVersion)-[:SUPERSEDES]->(ProvisionVersion)  // created only after approval
//   (Provision)-[:REFERENCES]->(Provision)
//   (InternalArtifact)-[:ALIGNED_TO]->(ProvisionVersion)
//   (Provision)-[:POTENTIALLY_CONFLICTS_WITH]->(Provision)
