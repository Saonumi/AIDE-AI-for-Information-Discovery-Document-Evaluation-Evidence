"""Step 12 — Approve & activate (temporal + index + graph sync).

Two activation paths, both gated on employee approval:

A) Base-document activation: a freshly-parsed, approved REGULATION/POLICY. Its
   provisions get their first APPROVED version [valid_from, None), are embedded and
   indexed, and Provision/ProvisionVersion nodes + HAS_VERSION edges are written.

B) ChangeEvent activation (the SME 500->700 case): on APPROVE of a CHANGE_EVENT_REVIEW
   we deterministically patch V1 -> V2, set half-open intervals
       V1 = [old.valid_from, change.valid_from)
       V2 = [change.valid_from, None)
   approve V2, re-index V1 (now closed) and index V2, and write graph edges:
       Provision HAS_VERSION v1, v2 ; ChangeEvent TARGETS/BEFORE/AFTER ; v2 SUPERSEDES v1.

INVARIANT: only APPROVED content is embedded/indexed into retrieval.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from infra import embeddings
from infra.db_models import (
    ChangeEventRow,
    DocumentRow,
    ProvisionRow,
    ProvisionVersionRow,
)
from infra.neo4j_client import get_graph
from infra.opensearch_client import get_store
from packages.common.ids import new_id, new_version_id
from packages.contracts.enums import (
    AmendmentOperation,
    ApprovalStatus,
    ProcessingStatus,
    ReviewStatus,
)
from ingestion import chunking
from ingestion import patch as patch_mod
from ingestion.change_event import get_change_event


# --------------------------------------------------------------------------- #
# Indexing helpers
# --------------------------------------------------------------------------- #
def _index_version(
    *,
    document_id: str,
    document_number: Optional[str],
    provision_id: str,
    version_id: str,
    heading_path: List[str],
    content: str,
    page: Optional[int],
    valid_from: date,
    valid_to_exclusive: Optional[date],
) -> List[str]:
    """Build, embed and index chunks for one APPROVED version. Returns chunk ids.

    Chunk ids are DETERMINISTIC (f"chk-{version_id}-{i}") so re-indexing a version
    whose temporal window changed (e.g. V1 closed by a ChangeEvent) upserts the same
    store entries instead of leaving a stale open-interval duplicate behind.
    """
    store = get_store()
    store.ensure_index()
    _counter = {"i": 0}

    def _next_chunk_id() -> str:
        cid = f"chk-{version_id}-{_counter['i']}"
        _counter["i"] += 1
        return cid

    chunk_dicts = chunking.build_chunks_for_version(
        provision_id=provision_id,
        version_id=version_id,
        document_id=document_id,
        document_number=document_number,
        heading_path=heading_path,
        content=content,
        page=page,
        valid_from=valid_from,
        valid_to_exclusive=valid_to_exclusive,
        new_chunk_id=_next_chunk_id,
        approval_status=ApprovalStatus.APPROVED.value,
    )
    ids: List[str] = []
    for cd in chunk_dicts:
        emb_text = chunking.embedding_text_for(cd["heading_path"], cd["content"])
        store.index_chunk(cd, embeddings.embed_one(emb_text))
        ids.append(cd["chunk_id"])
    return ids


def _reindex_version_window(store, version_id: str, valid_to_exclusive: Optional[date]) -> None:
    """Update the temporal window of already-indexed chunks for a version.

    The in-memory / OpenSearch stores index by chunk_id; re-indexing the same chunk
    with a new valid_to_exclusive is a no-op-safe upsert. Here we simply re-emit the
    stored chunks with the closed interval by scanning nothing — instead the caller
    re-indexes V1 from its DB row. This helper is kept for symmetry.
    """
    # Handled by _reindex_from_row in practice; kept intentionally minimal.
    return None


def _graph_write_version_nodes(graph, doc_id: str, prov: ProvisionRow, ver: ProvisionVersionRow) -> None:
    heading = " > ".join(prov.heading_path or []) if prov.heading_path else prov.provision_id
    locator = " ".join(filter(None, [
        f"Điều {prov.article}" if prov.article else None,
        f"Khoản {prov.clause}" if prov.clause else None,
        f"Điểm {prov.point}" if prov.point else None,
    ])) or heading
    graph.upsert_node(prov.provision_id, "Provision", title=heading, locator=locator,
                      document_id=doc_id, article=prov.article, clause=prov.clause,
                      point=prov.point)
    graph.upsert_node(
        ver.version_id, "ProvisionVersion",
        title=heading,
        valid_from=ver.valid_from.isoformat() if ver.valid_from else None,
        valid_to_exclusive=ver.valid_to_exclusive.isoformat() if ver.valid_to_exclusive else None,
        approval_status=ver.approval_status,
    )
    graph.upsert_edge(prov.provision_id, ver.version_id, "HAS_VERSION")


def _get_provision(session, provision_id: str) -> Optional[ProvisionRow]:
    return session.execute(
        select(ProvisionRow).where(ProvisionRow.provision_id == provision_id)
    ).scalars().first()


# --------------------------------------------------------------------------- #
# A) Base document activation
# --------------------------------------------------------------------------- #
def activate_base_document(session, document_id: str) -> Dict[str, Any]:
    """Approve + index every provision version of a base document.

    Marks each existing PENDING version APPROVED (open interval), indexes it, and
    writes Provision/HAS_VERSION graph nodes. The document is set APPROVED/INDEXED.
    """
    doc = session.execute(
        select(DocumentRow).where(DocumentRow.document_id == document_id)
    ).scalars().first()
    if doc is None:
        raise ValueError(f"Document {document_id} not found.")

    provisions = session.execute(
        select(ProvisionRow).where(ProvisionRow.document_id == document_id)
    ).scalars().all()

    graph = get_graph()
    indexed_versions: List[str] = []
    now = datetime.utcnow()

    for prov in provisions:
        versions = session.execute(
            select(ProvisionVersionRow)
            .where(ProvisionVersionRow.provision_id == prov.provision_id)
        ).scalars().all()
        for ver in versions:
            if ver.approval_status == ApprovalStatus.APPROVED.value:
                continue
            ver.approval_status = ApprovalStatus.APPROVED.value
            ver.approved_at = now
            _index_version(
                document_id=document_id,
                document_number=doc.document_number,
                provision_id=prov.provision_id,
                version_id=ver.version_id,
                heading_path=prov.heading_path or [],
                content=ver.content,
                page=ver.page,
                valid_from=ver.valid_from,
                valid_to_exclusive=ver.valid_to_exclusive,
            )
            _graph_write_version_nodes(graph, document_id, prov, ver)
            indexed_versions.append(ver.version_id)

    doc.approval_status = ApprovalStatus.APPROVED.value
    doc.processing_status = ProcessingStatus.INDEXED.value
    session.flush()
    return {"document_id": document_id, "indexed_versions": indexed_versions,
            "provision_count": len(provisions)}


# --------------------------------------------------------------------------- #
# B) ChangeEvent activation (partial supersession)
# --------------------------------------------------------------------------- #
def _reindex_from_row(session, doc_number_cache: Dict[str, Optional[str]],
                      prov: ProvisionRow, ver: ProvisionVersionRow) -> None:
    """Re-index an existing version row after its temporal window changed."""
    docno = doc_number_cache.get(ver.document_id)
    if docno is None and ver.document_id not in doc_number_cache:
        d = session.execute(
            select(DocumentRow).where(DocumentRow.document_id == ver.document_id)
        ).scalars().first()
        docno = d.document_number if d else None
        doc_number_cache[ver.document_id] = docno
    _index_version(
        document_id=ver.document_id,
        document_number=docno,
        provision_id=prov.provision_id,
        version_id=ver.version_id,
        heading_path=prov.heading_path or [],
        content=ver.content,
        page=ver.page,
        valid_from=ver.valid_from,
        valid_to_exclusive=ver.valid_to_exclusive,
    )


def activate_change_event(session, change_event_id: str,
                          edited_payload: Optional[dict] = None) -> Dict[str, Any]:
    """Apply an approved ChangeEvent: build V2, set half-open intervals, index, graph.

    edited_payload (from an EDIT decision) may override old_text/new_text/valid_from.
    Returns a summary dict incl. before/after version ids and the patch status.
    """
    ce = get_change_event(session, change_event_id)
    if ce is None:
        raise ValueError(f"ChangeEvent {change_event_id} not found.")
    if not ce.target_provision_id:
        raise ValueError("ChangeEvent has no resolved target provision.")

    # Apply any employee edits.
    old_text = ce.old_text
    new_text = ce.new_text
    valid_from = ce.valid_from
    operation = AmendmentOperation(ce.operation)
    if edited_payload:
        old_text = edited_payload.get("old_text", old_text)
        new_text = edited_payload.get("new_text", new_text)
        if edited_payload.get("valid_from"):
            from packages.common.vn_normalize import normalize_date
            vf = normalize_date(str(edited_payload["valid_from"]))
            if vf:
                valid_from = vf
        if edited_payload.get("operation"):
            try:
                operation = AmendmentOperation(edited_payload["operation"])
            except ValueError:
                pass

    prov = _get_provision(session, ce.target_provision_id)
    if prov is None:
        raise ValueError(f"Provision {ce.target_provision_id} not found.")

    # Latest APPROVED version becomes V1 (the one being superseded).
    v1 = session.execute(
        select(ProvisionVersionRow)
        .where(ProvisionVersionRow.provision_id == prov.provision_id)
        .where(ProvisionVersionRow.approval_status == ApprovalStatus.APPROVED.value)
        .order_by(ProvisionVersionRow.valid_from.desc())
    ).scalars().first()
    if v1 is None:
        raise ValueError("No approved V1 to supersede.")

    # Deterministic patch V1 -> V2 content.
    result = patch_mod.apply_patch(v1.content, operation, old_text=old_text, new_text=new_text)
    if result.needs_review or result.new_content is None:
        return {"status": ReviewStatus.PENDING.value, "patch_status": result.status,
                "reason": result.reason, "change_event_id": change_event_id}

    # Half-open intervals: close V1 at valid_from, open V2 from valid_from.
    v1.valid_to_exclusive = valid_from

    v2_id = new_version_id()
    now = datetime.utcnow()
    v2 = ProvisionVersionRow(
        version_id=v2_id,
        provision_id=prov.provision_id,
        document_id=v1.document_id,
        content=result.new_content,
        valid_from=valid_from,
        valid_to_exclusive=None,
        approval_status=ApprovalStatus.APPROVED.value,
        page=v1.page,
        obligation=None,
        scope=None,
        created_at=now,
        approved_at=now,
    )
    session.add(v2)

    # ChangeEvent now records before/after + is APPROVED.
    ce.before_version_id = v1.version_id
    ce.after_version_id = v2_id
    ce.review_status = ReviewStatus.APPROVED.value
    ce.valid_from = valid_from
    session.flush()

    # Re-index V1 (now closed) and index V2 (open). Only APPROVED content is indexed.
    doc_number_cache: Dict[str, Optional[str]] = {}
    _reindex_from_row(session, doc_number_cache, prov, v1)
    _reindex_from_row(session, doc_number_cache, prov, v2)

    # Graph: HAS_VERSION for both, ChangeEvent TARGETS/BEFORE/AFTER, v2 SUPERSEDES v1.
    graph = get_graph()
    _graph_write_version_nodes(graph, v1.document_id, prov, v1)
    _graph_write_version_nodes(graph, v2.document_id, prov, v2)
    graph.upsert_node(
        ce.change_event_id, "ChangeEvent",
        title=f"{operation.value} {prov.provision_id}",
        operation=operation.value,
        old_text=old_text, new_text=new_text,
        before_version_id=v1.version_id, after_version_id=v2_id,
        valid_from=valid_from.isoformat(),
    )
    graph.upsert_edge(ce.amending_document_id, ce.change_event_id, "DECLARES")
    graph.upsert_edge(ce.change_event_id, prov.provision_id, "TARGETS")
    graph.upsert_edge(ce.change_event_id, v1.version_id, "BEFORE")
    graph.upsert_edge(ce.change_event_id, v2_id, "AFTER")
    graph.upsert_edge(v2_id, v1.version_id, "SUPERSEDES")

    return {
        "status": ReviewStatus.APPROVED.value,
        "patch_status": result.status,
        "change_event_id": change_event_id,
        "before_version_id": v1.version_id,
        "after_version_id": v2_id,
        "v1_valid_from": v1.valid_from.isoformat(),
        "v1_valid_to_exclusive": valid_from.isoformat(),
        "v2_valid_from": valid_from.isoformat(),
        "v2_content": result.new_content,
    }
