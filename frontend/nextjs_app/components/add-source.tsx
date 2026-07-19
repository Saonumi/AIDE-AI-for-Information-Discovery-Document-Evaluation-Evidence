"use client"

// Tab Add Source (spec §2) — xây kho quy định đã xác minh, một màn duy nhất:
//   Upload → AI trích xuất → Người dùng kiểm tra → Approve/Edit/Reject → Activate
// Trust rule: file upload = AUTHORITY_SOURCE_CANDIDATE; chỉ APPROVED + ACTIVE
// mới được dùng trong RAG. Không có tab Review Queue riêng.

import * as React from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  api, ApiError, type DocumentRow, type Provision,
} from "@/lib/api"

const TYPE_LABEL: Record<string, string> = {
  REGULATION: "Quy định",
  AMENDMENT: "Văn bản sửa đổi",
  INTERNAL_POLICY: "Quy trình nội bộ",
  DECISION: "Quyết định",
  CIRCULAR: "Thông tư",
}

const TASK_LABEL: Record<string, string> = {
  PARSING_REVIEW: "Kiểm tra kết quả bóc tách",
  CHANGE_EVENT_REVIEW: "Duyệt điểm sửa đổi",
  REFERENCE_REVIEW: "Kiểm tra tham chiếu",
  CONFLICT_REVIEW: "Kiểm tra xung đột",
  IMPACT_REVIEW: "Kiểm tra tác động",
  INJECTION_REVIEW: "Cảnh báo chèn lệnh độc hại",
}

const APPROVAL_LABEL: Record<string, string> = {
  PENDING: "Chờ duyệt",
  APPROVED: "Đã duyệt",
  REJECTED: "Từ chối",
  ARCHIVED: "Đã lưu trữ",
}

const PROCESSING_LABEL: Record<string, string> = {
  QUARANTINED: "Chờ xử lý",
  PROCESSING: "Đang xử lý",
  PARSED: "Đã bóc tách",
  INDEXED: "Đã lập chỉ mục",
  FAILED: "Lỗi xử lý",
}

function extractReasons(e: unknown): string[] {
  // 409 activation_blocked → body {"detail": {"error": ..., "reasons": [...]}}
  if (e instanceof ApiError && typeof e.detail === "object" && e.detail !== null) {
    const d = (e.detail as { detail?: { reasons?: unknown } }).detail
    if (d && Array.isArray(d.reasons)) return d.reasons.map(String)
  }
  return [e instanceof Error ? e.message : String(e)]
}

export function AddSourceTab() {
  const [docs, setDocs] = React.useState<DocumentRow[] | null>(null)
  const [loadErr, setLoadErr] = React.useState<string | null>(null)

  const refresh = React.useCallback(() => {
    api.documents()
      .then((d) => { setDocs(d); setLoadErr(null) })
      .catch((e) => setLoadErr(e instanceof Error ? e.message : String(e)))
  }, [])
  React.useEffect(refresh, [refresh])

  const pendingDocs = docs?.filter((d) => d.approval_status !== "APPROVED") ?? []
  const activeDocs = docs?.filter((d) => d.approval_status === "APPROVED") ?? []

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6">
      <div className="max-w-4xl mx-auto space-y-8">
        <div className="border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-600 dark:text-amber-300 leading-relaxed">
          Nguồn upload ở đây là <strong>tài liệu chờ xác minh</strong> — chưa được dùng
          làm căn cứ pháp lý. Chỉ nguồn <strong>đã duyệt &amp; đang hoạt động</strong> (đã qua kiểm tra
          của cán bộ) mới xuất hiện trong kết quả tra cứu và nhận xét tài liệu bên tab RAG.
        </div>

        {loadErr && (
          <div className="border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-500">
            Không tải được dữ liệu: {loadErr}
          </div>
        )}

        <UploadCard onUploaded={refresh} />
        <PendingActivationSection docs={pendingDocs} loaded={docs !== null} onActivated={refresh} />
        <ActiveSourcesSection docs={activeDocs} loaded={docs !== null} />
      </div>
    </div>
  )
}

// ─── Upload ───────────────────────────────────────────────────────────────────

function UploadCard({ onUploaded }: { onUploaded: () => void }) {
  const [file, setFile] = React.useState<File | null>(null)
  const [docType, setDocType] = React.useState("CIRCULAR")
  const [busy, setBusy] = React.useState(false)
  const [notice, setNotice] = React.useState<{ tone: "ok" | "warn" | "err"; text: string } | null>(null)

  const upload = async () => {
    if (!file || busy) return
    setBusy(true); setNotice(null)
    try {
      const r = await api.uploadDocument(file, docType)
      setNotice(r.injection_suspected
        ? { tone: "warn", text: `Đã nhận ${r.filename} — phát hiện dấu hiệu prompt injection, cần cán bộ kiểm tra trước khi duyệt.` }
        : { tone: "ok", text: `Đã nhận ${r.filename} — AI đang trích xuất; kết quả sẽ hiện ở mục "Chờ kiểm tra" bên dưới.` })
      setFile(null)
      onUploaded()
    } catch (e) {
      setNotice({ tone: "err", text: e instanceof Error ? e.message : String(e) })
    } finally {
      setBusy(false)
    }
  }

  const noticeTone = {
    ok: "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-300",
    warn: "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-300",
    err: "border-red-500/30 bg-red-500/10 text-red-500",
  }

  return (
    <section className="border border-border bg-card">
      <header className="px-4 py-3 border-b border-border">
        <h2 className="text-sm font-semibold">Tải lên nguồn pháp lý</h2>
        <p className="text-xs text-muted-foreground mt-0.5">
          Thông tư, quyết định, văn bản sửa đổi — AI trích xuất, cán bộ kiểm tra rồi mới kích hoạt.
        </p>
      </header>
      <div className="p-4 space-y-3">
        <label className="block border-2 border-dashed border-border p-6 text-center text-muted-foreground cursor-pointer transition-colors hover:border-orange-500 hover:text-orange-500">
          <input type="file" className="hidden" accept=".pdf,.docx,.txt,.md"
                 onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          {file ? (
            <span className="text-sm font-medium text-foreground">{file.name}</span>
          ) : (
            <>
              <span className="block text-sm font-medium">Chọn file văn bản pháp lý</span>
              <span className="block text-xs mt-1">PDF, DOCX, TXT, MD — tối đa 25 MB</span>
            </>
          )}
        </label>
        <div className="flex flex-wrap items-center gap-3">
          <select value={docType} onChange={(e) => setDocType(e.target.value)}
                  className="bg-background border border-border px-3 py-2 text-sm outline-none focus:border-orange-500">
            <option value="CIRCULAR">Thông tư (CIRCULAR)</option>
            <option value="DECISION">Quyết định (DECISION)</option>
            <option value="REGULATION">Quy định (REGULATION)</option>
            <option value="AMENDMENT">Văn bản sửa đổi (AMENDMENT)</option>
          </select>
          <Button className="bg-orange-500 hover:bg-orange-600 text-white"
                  onClick={upload} disabled={!file || busy}>
            {busy ? "Đang tải lên & trích xuất…" : "Tải lên & Trích xuất"}
          </Button>
        </div>
        {notice && <p className={`border px-3 py-2 text-xs ${noticeTone[notice.tone]}`}>{notice.text}</p>}
      </div>
    </section>
  )
}

// ─── Documents: chờ duyệt / đã kích hoạt ────────────────────────────────────

function PendingActivationSection({ docs, loaded, onActivated }: {
  docs: DocumentRow[]; loaded: boolean; onActivated: () => void
}) {
  return (
    <section>
      <SectionHeading
        title="Chờ duyệt"
        count={loaded ? docs.length : undefined}
        hint="Xem và chỉnh sửa điều khoản AI trích xuất, sau đó kích hoạt để đưa vào kho RAG"
      />
      {!loaded && <ListSkeleton rows={2} />}
      {loaded && docs.length === 0 && (
        <EmptyRow>Không có nguồn nào chờ duyệt.</EmptyRow>
      )}
      <div className="border border-border divide-y divide-border empty:border-0">
        {docs.map((d) => <PendingDocRow key={d.document_id} doc={d} onActivated={onActivated} />)}
      </div>
    </section>
  )
}

function PendingDocRow({ doc, onActivated }: { doc: DocumentRow; onActivated: () => void }) {
  const [busy, setBusy] = React.useState(false)
  const [reasons, setReasons] = React.useState<string[] | null>(null)
  const [open, setOpen] = React.useState(false)
  const [provisions, setProvisions] = React.useState<Provision[] | null>(null)
  const [provErr, setProvErr] = React.useState<string | null>(null)

  const activate = async () => {
    if (busy) return
    setBusy(true); setReasons(null)
    try {
      await api.activateDocument(doc.document_id)
      onActivated()
    } catch (e) {
      setReasons(extractReasons(e))
    } finally {
      setBusy(false)
    }
  }

  const doDelete = async () => {
    if (busy || !confirm(`Xóa "${doc.document_number || doc.filename}"?`)) return
    setBusy(true)
    try {
      await api.deleteDocument(doc.document_id)
      onActivated()
    } catch (e) {
      setReasons([e instanceof Error ? e.message : String(e)])
    } finally {
      setBusy(false)
    }
  }

  const toggleProvisions = async () => {
    if (open) { setOpen(false); return }
    setOpen(true)
    if (provisions !== null) return
    try {
      const p = await api.documentProvisions(doc.document_id)
      setProvisions(p)
    } catch (e) {
      setProvErr(e instanceof Error ? e.message : String(e))
    }
  }

  const rejected = doc.approval_status === "REJECTED"
  return (
    <div className="bg-card">
      <div className="flex items-center gap-3 px-4 py-2.5">
        <div className="min-w-0 flex-1">
          <div className="text-sm font-medium truncate">{doc.document_number || doc.filename}</div>
          <div className="text-[11px] text-muted-foreground truncate">
            {TYPE_LABEL[doc.type] ?? doc.type} · {doc.filename} · {PROCESSING_LABEL[doc.processing_status] ?? doc.processing_status}
          </div>
        </div>
        {doc.injection_suspected && (
          <Badge variant="outline" className="text-[10px] text-red-500 border-red-500/40 shrink-0">
            Nghi chèn lệnh?
          </Badge>
        )}
        <Badge variant="outline" className={`text-[10px] shrink-0 ${
          rejected ? "text-red-500 border-red-500/40" : "text-amber-500 border-amber-500/40"
        }`}>
          {APPROVAL_LABEL[doc.approval_status] ?? doc.approval_status}
        </Badge>
        <Button size="sm" variant="ghost" onClick={toggleProvisions} disabled={busy}
                className="shrink-0 text-xs text-muted-foreground hover:text-foreground">
          {open ? "▴ điều khoản" : "▾ điều khoản"}
        </Button>
        {!rejected && (
          <Button size="sm" variant="outline" onClick={activate} disabled={busy}
                  className="shrink-0 border-emerald-500/40 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/10">
            {busy ? "…" : "Kích hoạt"}
          </Button>
        )}
        <Button size="sm" variant="ghost" onClick={doDelete} disabled={busy}
                className="shrink-0 text-red-500 hover:bg-red-500/10 hover:text-red-500">
          Xóa
        </Button>
      </div>

      {open && (
        <div className="border-t border-border px-4 py-3">
          {provisions === null && !provErr && (
            <p className="text-xs text-muted-foreground">Đang tải điều khoản…</p>
          )}
          {provErr && <p className="text-xs text-red-500">{provErr}</p>}
          {provisions?.length === 0 && (
            <p className="text-xs text-muted-foreground italic">
              Chưa có điều khoản nào được trích xuất (LLM chưa chạy hoặc tài liệu không có điều khoản quy phạm).
            </p>
          )}
          {provisions && provisions.length > 0 && (
            <div className="space-y-2 max-h-72 overflow-y-auto">
              <p className="text-[11px] text-muted-foreground mb-1">{provisions.length} điều khoản trích xuất được:</p>
              {provisions.map((p) => (
                <ProvisionItem key={p.version_id} provision={p} documentId={doc.document_id} />
              ))}
            </div>
          )}
        </div>
      )}

      {reasons && (
        <div className="mx-4 mb-2 border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-500 space-y-0.5">
          {reasons.map((r, i) => <div key={i}>• {r}</div>)}
        </div>
      )}
    </div>
  )
}

function ProvisionItem({ provision, documentId }: { provision: Provision; documentId: string }) {
  const [expanded, setExpanded] = React.useState(false)
  const [editing, setEditing] = React.useState(false)
  const [draft, setDraft] = React.useState(provision.content)
  const [saving, setSaving] = React.useState(false)
  const [saveErr, setSaveErr] = React.useState<string | null>(null)

  const heading = provision.heading_path.length > 0
    ? provision.heading_path.join(" > ")
    : provision.article ? `Điều ${provision.article}${provision.clause ? `, khoản ${provision.clause}` : ""}` : "—"

  const save = async () => {
    setSaving(true); setSaveErr(null)
    try {
      await api.updateProvision(documentId, provision.version_id, draft)
      setEditing(false)
    } catch (e) {
      setSaveErr(e instanceof Error ? e.message : String(e))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="border border-border bg-muted/30 text-xs">
      <button className="w-full flex items-start gap-2 px-3 py-2 text-left hover:bg-muted/50"
              onClick={() => { setExpanded(!expanded); if (editing) setEditing(false) }}>
        <span className="font-medium min-w-0 flex-1 truncate">{heading}</span>
        <span className="text-muted-foreground shrink-0">{expanded ? "▴" : "▾"}</span>
      </button>
      {expanded && !editing && (
        <div className="px-3 pb-2 border-t border-border pt-2 space-y-2">
          <p className="text-muted-foreground whitespace-pre-wrap leading-relaxed">{draft}</p>
          <Button size="sm" variant="outline" className="text-xs h-6 px-2"
                  onClick={(e) => { e.stopPropagation(); setEditing(true) }}>
            Chỉnh sửa
          </Button>
        </div>
      )}
      {expanded && editing && (
        <div className="px-3 pb-2 border-t border-border pt-2 space-y-2">
          <textarea rows={6} value={draft} onChange={(e) => setDraft(e.target.value)}
            className="w-full bg-background border border-orange-500 px-2 py-1.5 text-xs outline-none leading-relaxed resize-y" />
          {saveErr && <p className="text-red-500">{saveErr}</p>}
          <div className="flex gap-2">
            <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white h-6 px-2 text-xs"
                    onClick={save} disabled={saving}>
              {saving ? "Đang lưu…" : "Lưu"}
            </Button>
            <Button size="sm" variant="ghost" className="h-6 px-2 text-xs"
                    onClick={() => { setEditing(false); setDraft(provision.content) }} disabled={saving}>
              Hủy
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

function ActiveSourcesSection({ docs, loaded }: { docs: DocumentRow[]; loaded: boolean }) {
  return (
    <section>
      <SectionHeading
        title="Nguồn đang hoạt động"
        count={loaded ? docs.length : undefined}
        hint="APPROVED + ACTIVE — đây là toàn bộ căn cứ pháp lý mà tab RAG được phép dùng"
      />
      {!loaded && <ListSkeleton rows={3} />}
      {loaded && docs.length === 0 && (
        <EmptyRow>Chưa có nguồn nào được kích hoạt — RAG sẽ không có căn cứ để trả lời.</EmptyRow>
      )}
      <div className="border border-border divide-y divide-border empty:border-0">
        {docs.map((d) => (
          <div key={d.document_id} className="flex items-center gap-3 px-4 py-2.5 bg-card">
            <div className="min-w-0 flex-1">
              <div className="text-sm font-medium truncate">{d.document_number || d.filename}</div>
              <div className="text-[11px] text-muted-foreground truncate">
                {TYPE_LABEL[d.type] ?? d.type} · {d.filename}
              </div>
            </div>
            <Badge variant="outline" className="text-[10px] text-emerald-600 dark:text-emerald-400 border-emerald-500/40 shrink-0">
              Đang hoạt động
            </Badge>
          </div>
        ))}
      </div>
    </section>
  )
}

// ─── Shared bits ─────────────────────────────────────────────────────────────

function SectionHeading({ title, count, hint }: { title: string; count?: number; hint: string }) {
  return (
    <div className="mb-2">
      <h2 className="text-sm font-semibold">
        {title}
        {count !== undefined && <span className="text-muted-foreground font-normal"> · {count}</span>}
      </h2>
      <p className="text-xs text-muted-foreground mt-0.5">{hint}</p>
    </div>
  )
}

function EmptyRow({ children }: { children: React.ReactNode }) {
  return (
    <div className="border border-border bg-card px-4 py-6 text-center text-xs text-muted-foreground">
      {children}
    </div>
  )
}

function ListSkeleton({ rows }: { rows: number }) {
  return (
    <div className="border border-border divide-y divide-border" aria-hidden>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="px-4 py-3 bg-card">
          <div className="h-3 w-2/5 bg-muted animate-pulse" />
          <div className="h-2.5 w-3/5 bg-muted animate-pulse mt-2" />
        </div>
      ))}
    </div>
  )
}
