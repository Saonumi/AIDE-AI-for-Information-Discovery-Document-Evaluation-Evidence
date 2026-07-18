"""Temporal Regulatory Graph store.

Interface used by:
  - Track A (ingestion): write nodes/edges when a version is approved & activated.
  - Track B (query): expand() for cross-reference/amendment traversal, version_chain()
    for the timeline, subgraph() for the KG visualisation.

Two backends behind get_graph(): Neo4jGraph (deploy) and InMemoryGraph (networkx,
demo_mode / no service). Traversal is bounded to <=2 hops over an allow-list of
relations — the LLM never emits Cypher (security invariant).

Nodes:  Document, Provision, ProvisionVersion, ChangeEvent, InternalArtifact
Edges:  CONTAINS, HAS_VERSION, DECLARES, TARGETS, BEFORE, AFTER, SUPERSEDES,
        REFERENCES, ALIGNED_TO, POTENTIALLY_CONFLICTS_WITH
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from packages.common.config import get_settings

ALLOWED_RELS = [
    "CONTAINS", "HAS_VERSION", "DECLARES", "TARGETS", "BEFORE", "AFTER",
    "SUPERSEDES", "REFERENCES", "ALIGNED_TO", "POTENTIALLY_CONFLICTS_WITH",
]

_graph = None


class InMemoryGraph:
    """networkx MultiDiGraph backend with the same method surface as Neo4jGraph."""

    def __init__(self):
        import networkx as nx
        self._nx = nx
        self.g = nx.MultiDiGraph()

    # ---- writes ----
    def upsert_node(self, node_id: str, label: str, **props) -> None:
        self.g.add_node(node_id, label=label, **props)

    def upsert_edge(self, src: str, dst: str, rel: str, **props) -> None:
        assert rel in ALLOWED_RELS, rel
        # avoid duplicate parallel edges of same rel
        if self.g.has_edge(src, dst):
            for _, data in self.g.get_edge_data(src, dst).items():
                if data.get("rel") == rel:
                    return
        self.g.add_edge(src, dst, key=rel, rel=rel, **props)

    def set_prop(self, node_id: str, **props) -> None:
        if node_id in self.g:
            self.g.nodes[node_id].update(props)

    # ---- reads ----
    def _out(self, node_id: str, rel: str) -> List[str]:
        if node_id not in self.g:
            return []
        return [d for _, d, k in self.g.out_edges(node_id, keys=True) if k == rel]

    def _in(self, node_id: str, rel: str) -> List[str]:
        if node_id not in self.g:
            return []
        return [s for s, _, k in self.g.in_edges(node_id, keys=True) if k == rel]

    def expand(self, provision_ids: List[str], max_hops: int = 2) -> Dict[str, Any]:
        seen = set(provision_ids)
        reference_paths: List[dict] = []
        frontier = list(provision_ids)
        for _ in range(max_hops):
            nxt = []
            for pid in frontier:
                for tgt in self._out(pid, "REFERENCES"):
                    loc = self.g.nodes.get(tgt, {}).get("locator", "")
                    reference_paths.append({"from_provision": pid, "to_provision": tgt,
                                            "to_locator": loc, "hops": 1})
                    if tgt not in seen:
                        seen.add(tgt)
                        nxt.append(tgt)
            frontier = nxt
        return {
            "provision_ids": list(seen),
            "reference_paths": reference_paths,
            "change_paths": self._change_paths(provision_ids),
        }

    def _change_paths(self, provision_ids: List[str]) -> List[dict]:
        out = []
        for pid in provision_ids:
            for ce in self._in(pid, "TARGETS"):
                node = self.g.nodes.get(ce, {})
                out.append({
                    "provision_id": pid,
                    "change_event_id": ce,
                    "before_version_id": node.get("before_version_id"),
                    "after_version_id": node.get("after_version_id"),
                    "operation": node.get("operation"),
                })
        return out

    def version_chain(self, provision_id: str) -> List[dict]:
        versions = self._out(provision_id, "HAS_VERSION")
        items = []
        for vid in versions:
            v = self.g.nodes.get(vid, {})
            items.append({"version_id": vid, "valid_from": v.get("valid_from"),
                          "valid_to_exclusive": v.get("valid_to_exclusive"),
                          "approval_status": v.get("approval_status")})
        items.sort(key=lambda x: str(x.get("valid_from")))
        return items

    def subgraph(self, provision_id: str, depth: int = 2) -> Dict[str, Any]:
        nodes: Dict[str, dict] = {}
        edges: List[dict] = []
        frontier = {provision_id}
        visited = set()
        for _ in range(depth + 1):
            nextf = set()
            for nid in frontier:
                if nid in visited or nid not in self.g:
                    continue
                visited.add(nid)
                nd = self.g.nodes[nid]
                nodes[nid] = {"id": nid, "label": nd.get("label", "Node"),
                              "title": nd.get("title", nid), "props": dict(nd)}
                for s, d, k in list(self.g.out_edges(nid, keys=True)) + list(self.g.in_edges(nid, keys=True)):
                    edges.append({"source": s, "target": d, "label": k})
                    nextf.add(s)
                    nextf.add(d)
            frontier = nextf - visited
        # de-dup edges
        uniq = {(e["source"], e["target"], e["label"]): e for e in edges}
        return {"nodes": list(nodes.values()), "edges": list(uniq.values())}

    def close(self):
        pass


class Neo4jGraph:
    """Real Neo4j backend. Cypher is parameterised and template-only."""

    def __init__(self):
        from neo4j import GraphDatabase
        s = get_settings()
        self.driver = GraphDatabase.driver(s.neo4j_uri, auth=(s.neo4j_user, s.neo4j_password))
        self.driver.verify_connectivity()

    def upsert_node(self, node_id: str, label: str, **props) -> None:
        assert label in {"Document", "Provision", "ProvisionVersion", "ChangeEvent", "InternalArtifact"}
        with self.driver.session() as ses:
            ses.run(f"MERGE (n:{label} {{id:$id}}) SET n += $props", id=node_id, props=props)

    def upsert_edge(self, src: str, dst: str, rel: str, **props) -> None:
        assert rel in ALLOWED_RELS, rel
        with self.driver.session() as ses:
            ses.run(
                f"MATCH (a {{id:$src}}),(b {{id:$dst}}) MERGE (a)-[r:{rel}]->(b) SET r += $props",
                src=src, dst=dst, props=props,
            )

    def set_prop(self, node_id: str, **props) -> None:
        with self.driver.session() as ses:
            ses.run("MATCH (n {id:$id}) SET n += $props", id=node_id, props=props)

    def expand(self, provision_ids: List[str], max_hops: int = 2) -> Dict[str, Any]:
        with self.driver.session() as ses:
            refs = ses.run(
                "MATCH (a:Provision)-[:REFERENCES]->(b:Provision) "
                "WHERE a.id IN $ids RETURN a.id AS f, b.id AS t, b.locator AS loc",
                ids=provision_ids,
            ).data()
            reference_paths = [{"from_provision": r["f"], "to_provision": r["t"],
                                "to_locator": r.get("loc") or "", "hops": 1} for r in refs]
            reached = set(provision_ids) | {r["t"] for r in refs}
            changes = ses.run(
                "MATCH (ce:ChangeEvent)-[:TARGETS]->(p:Provision) WHERE p.id IN $ids "
                "RETURN p.id AS pid, ce.id AS ceid, ce.before_version_id AS bv, "
                "ce.after_version_id AS av, ce.operation AS op",
                ids=provision_ids,
            ).data()
            change_paths = [{"provision_id": c["pid"], "change_event_id": c["ceid"],
                             "before_version_id": c["bv"], "after_version_id": c["av"],
                             "operation": c["op"]} for c in changes]
        return {"provision_ids": list(reached), "reference_paths": reference_paths,
                "change_paths": change_paths}

    def version_chain(self, provision_id: str) -> List[dict]:
        with self.driver.session() as ses:
            rows = ses.run(
                "MATCH (p:Provision {id:$id})-[:HAS_VERSION]->(v:ProvisionVersion) "
                "RETURN v.id AS version_id, v.valid_from AS valid_from, "
                "v.valid_to_exclusive AS valid_to_exclusive, v.approval_status AS approval_status "
                "ORDER BY v.valid_from",
                id=provision_id,
            ).data()
        return rows

    def subgraph(self, provision_id: str, depth: int = 2) -> Dict[str, Any]:
        with self.driver.session() as ses:
            rows = ses.run(
                f"MATCH path=(p {{id:$id}})-[*0..{depth}]-(n) "
                "UNWIND nodes(path) AS nd UNWIND relationships(path) AS rel "
                "RETURN collect(DISTINCT {id:nd.id, label:head(labels(nd)), title:coalesce(nd.title,nd.id)}) AS nodes, "
                "collect(DISTINCT {source:startNode(rel).id, target:endNode(rel).id, label:type(rel)}) AS edges",
                id=provision_id,
            ).single()
        if not rows:
            return {"nodes": [], "edges": []}
        return {"nodes": rows["nodes"], "edges": rows["edges"]}

    def close(self):
        self.driver.close()


def get_graph():
    global _graph
    if _graph is not None:
        return _graph
    s = get_settings()
    if not s.demo_mode:
        try:
            _graph = Neo4jGraph()
            return _graph
        except Exception:
            pass
    _graph = InMemoryGraph()
    return _graph


def reset_graph_for_tests(graph=None):
    global _graph
    _graph = graph or InMemoryGraph()
    return _graph
