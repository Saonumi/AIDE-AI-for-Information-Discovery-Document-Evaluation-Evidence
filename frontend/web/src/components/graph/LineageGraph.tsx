/**
 * lineage_graph (spec §10.6) — evidence lineage for an impact report (§10.3/§10.4).
 *
 * Renders the provenance chain as an explicit node/edge list rather than a
 * force-directed canvas: the reviewer needs to read "which source document, via
 * which change event, touched which policy clause, backed by which evidence",
 * and a text lineage is auditable while a canvas is not.
 */
export interface LineageNode {
  id: string
  kind: 'Document' | 'Provision' | 'ProvisionVersion' | 'ChangeEvent' | 'PolicyClause' | 'EvidenceSpan'
  label: string
}

export interface LineageEdge {
  from: string
  to: string
  relation: string
}

export function LineageGraph({ nodes, edges }: { nodes: LineageNode[]; edges: LineageEdge[] }) {
  const nodeById = new Map(nodes.map((n) => [n.id, n]))

  // A node with no edge would vanish if we only rendered edges — and a policy
  // clause silently disappearing from an impact report is worse than showing it
  // unlinked, because the reviewer cannot tell it was ever considered.
  const connected = new Set(edges.flatMap((e) => [e.from, e.to]))
  const orphans = nodes.filter((n) => !connected.has(n.id))

  return (
    <section className="lineage" data-testid="lineage-graph" aria-label="Evidence lineage">
      <ol className="lineage__chain">
        {edges.map((edge, i) => {
          const from = nodeById.get(edge.from)
          const to = nodeById.get(edge.to)
          return (
            <li key={`${edge.from}-${edge.to}-${i}`} className="lineage__edge" data-relation={edge.relation}>
              <span className="lineage__node" data-kind={from?.kind}>
                <small>{from?.kind}</small>
                {from?.label ?? edge.from}
              </span>
              <span className="lineage__relation">—{edge.relation}→</span>
              <span className="lineage__node" data-kind={to?.kind}>
                <small>{to?.kind}</small>
                {to?.label ?? edge.to}
              </span>
            </li>
          )
        })}
      </ol>

      {edges.length === 0 && <p className="lineage__empty">Chưa có lineage nào được dựng.</p>}

      {orphans.length > 0 && (
        <div className="lineage__orphans" data-testid="lineage-orphans">
          <p className="lineage__orphans-label">
            Chưa nối được vào lineage (thiếu evidence span chung) — cần người rà soát xác nhận:
          </p>
          <ul>
            {orphans.map((n) => (
              <li key={n.id} className="lineage__node" data-kind={n.kind}>
                <small>{n.kind}</small>
                {n.label}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}
