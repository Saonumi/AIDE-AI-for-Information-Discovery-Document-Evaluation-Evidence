"use client"

// Tab Add Source (spec §2) — xây kho quy định đã xác minh, một màn duy nhất:
//   Upload → AI trích xuất → Người dùng kiểm tra → Approve/Edit/Reject → Activate
// Trust rule: file upload = AUTHORITY_SOURCE_CANDIDATE; chỉ APPROVED + ACTIVE
// mới được dùng trong RAG. Không có tab Review Queue riêng.

import * as React from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  api, ApiError, type DocumentRow, type ReviewTask, type ReviewDecision,
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
  const [tasks, setTasks] = React.useState<ReviewTask[] | null>(null)
  const [loadErr, setLoadErr] = React.useState<string | null>(null)

  const refresh = React.useCallback(() => {
    Promise.all([api.documents(), api.reviewTasks("PENDING")])
      .then(([d, t]) => { setDocs(d); setTasks(t); setLoadErr(null) })
      .catch((e) => setLoadErr(e instanceof Error ? e.message : String(e)))
  }, [])
  React.useEffect(refresh, [refresh])

  const pendingDocs = docs?.filter((d) => d.approval_status !== "APPROVED") ?? []
  const activeDocs = docs?.filter((d) => d.approval_status === "APPROVED") ?? []

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6">
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Trust rule — vì sao phải review trước khi nguồn được dùng */}
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
        <PendingReviewSection tasks={tasks} docs={docs} onDecided={refresh} />
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

// ─── Pending Review (HITL) ────────────────────────────────────────────────────

function PendingReviewSection({ tasks, docs, onDecided }: {
  tasks: ReviewTask[] | null
  docs: DocumentRow[] | null
  onDecided: () => void
}) {
  const docName = React.useCallback((id: string | null) => {
    if (!id) return null
    const d = docs?.find((x) => x.document_id === id)
    return d ? (d.document_number || d.filename) : id
  }, [docs])

  return (
    <section>
      <SectionHeading
        title="Chờ kiểm tra"
        count={tasks?.length}
        hint="Kết quả AI trích xuất — cán bộ duyệt, chỉnh sửa hoặc từ chối từng mục"
      />
      {tasks === null && <ListSkeleton rows={2} />}
      {tasks?.length === 0 && (
        <EmptyRow>
          Không có mục nào chờ kiểm tra. Tải lên nguồn mới ở trên — kết quả trích xuất sẽ vào đây.
        </EmptyRow>
      )}
      <div className="space-y-2">
        {tasks?.map((t) => (
          <ReviewTaskCard key={t.task_id} task={t} docName={docName(t.document_id)} onDecided={onDecided} />
        ))}
      </div>
    </section>
  )
}

function ReviewTaskCard({ task, docName, onDecided }: {
  task: ReviewTask; docName: string | null; onDecided: () => void
}) {
  const [open, setOpen] = React.useState(false)
  const [editing, setEditing] = React.useState(false)
  const [payload, setPayload] = React.useState("")
  const [busy, setBusy] = React.useState(false)
  const [err, setErr] = React.useState<string | null>(null)

  const decide = async (decision: ReviewDecision) => {
    if (busy) return
    setBusy(true); setErr(null)
    try {
      let edited: Record<string, unknown> | undefined
      if (decision === "EDIT") {
        try { edited = JSON.parse(payload) } catch { throw new Error("Nội dung chỉnh sửa phải là JSON hợp lệ.") }
      }
      await api.decideReviewTask(task.task_id, decision, edited)
      onDecided()
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  const confidencePct = Math.round(task.confidence * 100)
  const injection = task.task_type === "INJECTION_REVIEW"

  return (
    <div className={`border bg-card ${injection ? "border-red-500/40" : "border-border"}`}>
      <button className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-muted/40 transition-colors"
              onClick={() => setOpen(!open)} aria-expanded={open}>
        <Badge variant="outline" className={`text-[10px] shrink-0 ${
          injection ? "text-red-500 border-red-500/40" : "text-blue-500 border-blue-500/40"
        }`}>
          {TASK_LABEL[task.task_type] ?? task.task_type}
        </Badge>
        <span className="text-sm min-w-0 truncate flex-1">
          {docName ?? task.source_ref ?? task.task_id}
          {task.source_ref && docName && (
            <span className="text-muted-foreground text-xs"> · {task.source_ref}</span>
          )}
        </span>
        <span className="text-[11px] text-muted-foreground shrink-0">độ tin cậy {confidencePct}%</span>
        <span className="text-muted-foreground text-xs shrink-0">{open ? "▴" : "▾"}</span>
      </button>

      {open && (
        <div className="border-t border-border px-4 py-3 space-y-3">
          {/* Thông tin AI trích xuất */}
          {Object.keys(task.extracted).length > 0 && (
            <dl className="text-xs space-y-1">
              {Object.entries(task.extracted).map(([k, v]) => (
                <div key={k} className="flex gap-2">
                  <dt className="text-muted-foreground w-40 shrink-0 truncate">{k}</dt>
                  <dd className="min-w-0 break-words flex-1">
                    {typeof v === "string" ? v : JSON.stringify(v)}
                  </dd>
                </div>
              ))}
            </dl>
          )}

          {(task.diff_before || task.diff_after) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
              <div className="border border-red-500/20 bg-red-500/5 p-2.5">
                <div className="text-[10px] font-bold text-red-500 uppercase mb-1.5">Trước</div>
                <p className="whitespace-pre-wrap leading-relaxed">{task.diff_before ?? "—"}</p>
              </div>
              <div className="border border-emerald-500/20 bg-emerald-500/5 p-2.5">
                <div className="text-[10px] font-bold text-emerald-500 uppercase mb-1.5">
                  Sau{task.valid_from ? ` · hiệu lực ${task.valid_from}` : ""}
                </div>
                <p className="whitespace-pre-wrap leading-relaxed">{task.diff_after ?? "—"}</p>
              </div>
            </div>
          )}

          {editing && (
            <textarea rows={6} value={payload} onChange={(e) => setPayload(e.target.value)}
              className="w-full bg-background border border-border px-3 py-2 text-xs font-mono outline-none focus:border-orange-500"
              aria-label="Nội dung trích xuất đã chỉnh sửa (JSON)" />
          )}

          {err && <p className="text-xs text-red-500">{err}</p>}

          <div className="flex flex-wrap gap-2">
            {!editing ? (
              <>
                <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white"
                        onClick={() => decide("APPROVE")} disabled={busy}>
                  Duyệt
                </Button>
                <Button size="sm" variant="outline" disabled={busy}
                        onClick={() => { setEditing(true); setPayload(JSON.stringify(task.extracted, null, 2)) }}>
                  Chỉnh sửa
                </Button>
                <Button size="sm" variant="outline" className="text-red-500 border-red-500/40 hover:bg-red-500/10"
                        onClick={() => decide("REJECT")} disabled={busy}>
                  Từ chối
                </Button>
              </>
            ) : (
              <>
                <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white"
                        onClick={() => decide("EDIT")} disabled={busy}>
                  Lưu chỉnh sửa & duyệt
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setEditing(false)} disabled={busy}>
                  Hủy
                </Button>
              </>
            )}
            {busy && <span className="text-xs text-muted-foreground self-center">Đang ghi quyết định…</span>}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Documents: chờ kích hoạt / đã kích hoạt ─────────────────────────────────

function PendingActivationSection({ docs, loaded, onActivated }: {
  docs: DocumentRow[]; loaded: boolean; onActivated: () => void
}) {
  return (
    <section>
      <SectionHeading
        title="Chờ kích hoạt"
        count={loaded ? docs.length : undefined}
        hint="Đã upload nhưng chưa vào kho RAG — kích hoạt sau khi duyệt xong các mục kiểm tra"
      />
      {!loaded && <ListSkeleton rows={2} />}
      {loaded && docs.length === 0 && (
        <EmptyRow>Không có nguồn nào chờ kích hoạt.</EmptyRow>
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

  const rejected = doc.approval_status === "REJECTED"
  return (
    <div className="px-4 py-2.5 bg-card">
      <div className="flex items-center gap-3">
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
        {!rejected && (
          <Button size="sm" variant="outline" onClick={activate} disabled={busy}
                  className="shrink-0 border-emerald-500/40 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/10">
            {busy ? "Đang kích hoạt…" : "Kích hoạt"}
          </Button>
        )}
      </div>
      {reasons && (
        <div className="mt-2 border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-500 space-y-0.5">
          <div className="font-semibold">Chưa kích hoạt được:</div>
          {reasons.map((r, i) => <div key={i}>• {r}</div>)}
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
