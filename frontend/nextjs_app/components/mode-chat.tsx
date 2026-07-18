"use client"

// Mode-based AI chat (Mode spec §11) — one assistant, two operating modes:
//   Ask Regulations   multi-turn RAG, isolation per conversation
//   Document Review   Single/Batch Review Runs + bounded explainer chat
// Trust rule surfaced in the UI: chat files are LOCAL context, review targets
// are never legal evidence, results are locked per run.

import * as React from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import {
  api, type BatchReview, type ChatTurnT, type Conversation, type ReviewRunResult,
} from "@/lib/api"

const STATUS_TONE: Record<string, string> = {
  COMPLIANT: "text-emerald-400 border-emerald-500/40 bg-emerald-500/10",
  NON_COMPLIANT: "text-red-400 border-red-500/40 bg-red-500/10",
  PARTIALLY_COMPLIANT: "text-amber-400 border-amber-500/40 bg-amber-500/10",
  OUTDATED_REFERENCE: "text-orange-400 border-orange-500/40 bg-orange-500/10",
  MISSING_EVIDENCE: "text-zinc-400 border-zinc-500/40 bg-zinc-500/10",
  AMBIGUOUS: "text-purple-400 border-purple-500/40 bg-purple-500/10",
  NEEDS_HUMAN_REVIEW: "text-blue-400 border-blue-500/40 bg-blue-500/10",
}

function StatusPill({ status }: { status: string }) {
  return (
    <Badge variant="outline" className={`text-[10px] ${STATUS_TONE[status] ?? ""}`}>
      {status}
    </Badge>
  )
}

const inputCls =
  "w-full border border-border bg-background px-2 py-1.5 text-xs focus:outline-none focus:border-orange-500/60"

export function ModeChatView() {
  const [mode, setMode] = React.useState<"ask" | "review">("ask")
  return (
    <div className="flex flex-1 flex-col overflow-hidden min-h-0">
      {/* §11.1 chat header mode switch */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-border shrink-0">
        <Button size="sm" variant={mode === "ask" ? "default" : "outline"}
                onClick={() => setMode("ask")}>Ask Regulations</Button>
        <Button size="sm" variant={mode === "review" ? "default" : "outline"}
                onClick={() => setMode("review")}>Document Review</Button>
        <span className="text-[10px] text-muted-foreground ml-2 hidden md:block">
          {mode === "ask"
            ? "Multi-turn RAG · chỉ nhớ trong hội thoại hiện tại · attachment = context cục bộ"
            : "Review Run bất biến · file là REVIEW_TARGET, không vào knowledge base"}
        </span>
      </div>
      {mode === "ask" ? <AskRegulations /> : <DocumentReview />}
    </div>
  )
}

// ─── Mode 1: Ask Regulations ─────────────────────────────────────────────────

function AskRegulations() {
  const [convs, setConvs] = React.useState<Conversation[]>([])
  const [convId, setConvId] = React.useState<string | null>(null)
  const [turns, setTurns] = React.useState<ChatTurnT[]>([])
  const [attachments, setAttachments] = React.useState<{ id: string; filename: string }[]>([])
  const [text, setText] = React.useState("")
  const [queryDate, setQueryDate] = React.useState("")
  const [busy, setBusy] = React.useState(false)

  const refreshList = React.useCallback(() => {
    api.listConversations()
      .then((cs) => setConvs(cs.filter((c) => c.mode === "REGULATORY_ASSISTANT")))
      .catch(() => {})
  }, [])
  React.useEffect(refreshList, [refreshList])

  const open = async (id: string) => {
    setConvId(id)
    const data = await api.getConversation(id)
    setTurns(data.turns)
    setAttachments(data.attachments)
  }

  const newChat = async () => {
    const c = await api.createConversation("REGULATORY_ASSISTANT")
    refreshList()
    await open(c.id)
  }

  const send = async () => {
    if (!text.trim() || busy) return
    let id = convId
    if (!id) id = (await api.createConversation("REGULATORY_ASSISTANT")).id
    setBusy(true)
    const q = text
    setText("")
    setTurns((t) => [...t, { id: `tmp-${Date.now()}`, role: "user", content: q, citations: [] }])
    try {
      await api.postMessage(id, q, queryDate || undefined)
      await open(id)
      refreshList()
    } finally {
      setBusy(false)
    }
  }

  const attach = async (file: File) => {
    let id = convId
    if (!id) {
      id = (await api.createConversation("REGULATORY_ASSISTANT")).id
      refreshList()
    }
    const content = await file.text()
    await api.addAttachment(id, file.name, content)
    await open(id)
  }

  return (
    <div className="flex flex-1 overflow-hidden min-h-0">
      {/* conversation list — isolation boundary made visible (§11.5) */}
      <div className="w-52 border-r border-border p-2 space-y-1 overflow-y-auto shrink-0 hidden md:block">
        <Button size="sm" variant="outline" className="w-full" onClick={newChat}>+ New Chat</Button>
        {convs.map((c) => (
          <button key={c.id} onClick={() => open(c.id)}
            className={`w-full text-left px-2 py-1.5 text-xs truncate border ${
              c.id === convId ? "border-orange-500/60 bg-orange-500/10" : "border-transparent hover:bg-muted/50"}`}>
            💬 {c.title ?? c.id}
          </button>
        ))}
      </div>

      <div className="flex flex-1 flex-col min-w-0">
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {turns.length === 0 && (
            <p className="text-xs text-muted-foreground">
              Hỏi đáp quy định trên kho APPROVED + ACTIVE. New Chat = bộ nhớ rỗng;
              không hội thoại nào nhìn thấy dữ liệu của hội thoại khác.
            </p>
          )}
          {turns.map((t) => (
            <div key={t.id} className={`max-w-[85%] ${t.role === "user" ? "ml-auto" : ""}`}>
              <div className={`border p-2.5 text-xs whitespace-pre-wrap ${
                t.role === "user" ? "border-blue-500/30 bg-blue-500/10" : "border-border bg-muted/30"}`}>
                {t.content}
              </div>
              {t.citations.length > 0 && (
                <div className="mt-1 flex gap-1 flex-wrap">
                  {t.citations.map((c, i) => (
                    <Badge key={i} variant="outline" className="text-[9px] text-blue-400 border-blue-500/40">
                      {c.document_number ?? c.source_id}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
        <div className="p-3 border-t border-border space-y-2 shrink-0">
          {attachments.length > 0 && (
            <div className="flex gap-1 flex-wrap">
              {attachments.map((a) => (
                <Badge key={a.id} variant="outline" className="text-[9px] text-amber-400 border-amber-500/40">
                  📎 {a.filename} · context cục bộ — KHÔNG phải nguồn pháp lý
                </Badge>
              ))}
            </div>
          )}
          <div className="flex gap-2 items-center">
            <textarea rows={2} className={inputCls} placeholder="Hỏi về quy định hiện hành…"
              value={text} onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send() } }} />
            <div className="space-y-1 shrink-0">
              <input type="date" className={inputCls} value={queryDate}
                     onChange={(e) => setQueryDate(e.target.value)} title="Query date (tùy chọn)" />
              <div className="flex gap-1">
                <label className="cursor-pointer text-[10px] border border-border px-2 py-1 hover:bg-muted/50">
                  📎<input type="file" accept=".txt,.md" className="hidden"
                           onChange={(e) => e.target.files?.[0] && attach(e.target.files[0])} />
                </label>
                <Button size="sm" onClick={send} disabled={busy}>{busy ? "…" : "Gửi"}</Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Mode 2: Document Review (Single | Batch) ────────────────────────────────

function DocumentReview() {
  const [scale, setScale] = React.useState<"single" | "batch">("single")
  return (
    <div className="flex flex-1 flex-col overflow-hidden min-h-0">
      <div className="flex items-center gap-2 px-4 py-1.5 border-b border-border shrink-0">
        <Button size="sm" variant={scale === "single" ? "secondary" : "ghost"}
                onClick={() => setScale("single")}>Single Review</Button>
        <Button size="sm" variant={scale === "batch" ? "secondary" : "ghost"}
                onClick={() => setScale("batch")}>Batch Review</Button>
      </div>
      {scale === "single" ? <SingleReview /> : <BatchReviewView />}
    </div>
  )
}

function ExplainerChat({ ask, onNewRun }: {
  ask: (q: string) => Promise<{ answer: string; action?: string; result_locked?: boolean }>
  onNewRun?: () => void
}) {
  const [log, setLog] = React.useState<{ q: string; a: string; locked?: boolean; action?: string }[]>([])
  const [q, setQ] = React.useState("")
  const [busy, setBusy] = React.useState(false)

  const send = async () => {
    if (!q.trim() || busy) return
    setBusy(true)
    const question = q
    setQ("")
    try {
      const r = await ask(question)
      setLog((l) => [...l, { q: question, a: r.answer, locked: r.result_locked, action: r.action }])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="border-t border-border p-3 space-y-2 shrink-0">
      <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
        Ask about this review — explainer chỉ dùng evidence đã khóa của run
      </div>
      <div className="max-h-40 overflow-y-auto space-y-2">
        {log.map((e, i) => (
          <div key={i} className="text-xs space-y-1">
            <div className="text-blue-400">❯ {e.q}</div>
            <div className="whitespace-pre-wrap text-muted-foreground">{e.a}</div>
            {e.locked && <Badge variant="outline" className="text-[9px] text-red-400 border-red-500/40">🔒 Result locked</Badge>}
            {e.action === "CREATE_NEW_REVIEW_RUN" && onNewRun && (
              <Button size="sm" variant="outline" onClick={onNewRun}>Create New Review Run</Button>
            )}
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <input className={inputCls} placeholder='vd: "vì sao?", "đề xuất sửa thế nào?"' value={q}
               onChange={(e) => setQ(e.target.value)}
               onKeyDown={(e) => e.key === "Enter" && send()} />
        <Button size="sm" onClick={send} disabled={busy}>{busy ? "…" : "Hỏi"}</Button>
      </div>
    </div>
  )
}

function SingleReview() {
  const [filename, setFilename] = React.useState("policy.txt")
  const [text, setText] = React.useState("")
  const [date, setDate] = React.useState("")
  const [run, setRun] = React.useState<ReviewRunResult | null>(null)
  const [busy, setBusy] = React.useState(false)
  const [err, setErr] = React.useState("")

  const loadFile = async (f: File) => { setFilename(f.name); setText(await f.text()) }

  const start = async (assessmentDate?: string) => {
    if (!text.trim() || !(assessmentDate ?? date)) { setErr("Cần upload file và chọn assessment date."); return }
    setErr(""); setBusy(true)
    try { setRun(await api.createReviewRun(filename, text, assessmentDate ?? date)) }
    catch (e) { setErr(String(e)) }
    finally { setBusy(false) }
  }

  const report = run?.report
  return (
    <div className="flex flex-1 flex-col overflow-hidden min-h-0">
      <div className="flex gap-2 items-end p-3 border-b border-border flex-wrap shrink-0">
        <label className="cursor-pointer text-xs border border-border px-3 py-1.5 hover:bg-muted/50">
          📄 Upload file
          <input type="file" accept=".txt,.md" className="hidden"
                 onChange={(e) => e.target.files?.[0] && loadFile(e.target.files[0])} />
        </label>
        <input type="date" required className={inputCls + " w-40"} value={date}
               onChange={(e) => setDate(e.target.value)} title="Assessment date (bắt buộc)" />
        <Button size="sm" onClick={() => start()} disabled={busy}>
          {busy ? "Đang chạy Review Run…" : "Start Review"}
        </Button>
        {run && (
          <Button size="sm" variant="outline" onClick={() => start(date)} disabled={busy}>
            ↻ New Review Run
          </Button>
        )}
        {err && <span className="text-[10px] text-red-400">{err}</span>}
      </div>
      <textarea rows={4} className={inputCls + " mx-3 mt-2 shrink-0"} value={text}
                placeholder="…hoặc dán nội dung policy/báo cáo cần review (REVIEW_TARGET — không vào KB)"
                onChange={(e) => setText(e.target.value)} />

      {report && (
        <div className="flex-1 overflow-y-auto p-3 space-y-3 min-h-0">
          <div className="flex gap-2 flex-wrap text-[10px] text-muted-foreground">
            <Badge variant="outline" className="text-[9px]">run: {report.review_run_id}</Badge>
            <Badge variant="outline" className="text-[9px]">snapshot: {report.knowledge_snapshot_id}</Badge>
            <Badge variant="outline" className="text-[9px]">prompt: {report.versions.prompt}</Badge>
            <Badge variant="outline" className="text-[9px]">schema: {report.versions.schema}</Badge>
            <Badge variant="outline" className="text-[9px] text-amber-400 border-amber-500/40">🔒 IMMUTABLE</Badge>
          </div>
          {report.assessments.map((a) => (
            <div key={a.claim_id} className="border border-border bg-muted/20 p-3 space-y-1.5">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <span className="text-xs font-medium">“{a.source_text}”</span>
                <StatusPill status={a.status} />
              </div>
              {a.findings.map((f, i) => (
                <div key={i} className="text-[11px] text-orange-300">▸ {f}</div>
              ))}
              <div className="text-[11px] text-muted-foreground">{a.explanation}</div>
              {a.valid_evidence.slice(0, 2).map((e) => (
                <div key={e.version_id} className="text-[10px] text-blue-400 border-l-2 border-blue-500/40 pl-2">
                  {e.document_number} · {e.heading_path.join(" ")} · hiệu lực {e.valid_from} · tr.{e.page}
                </div>
              ))}
              {a.recommendation && (
                <div className="text-[11px] text-emerald-400">✎ Đề xuất sửa: {a.recommendation}</div>
              )}
              <div className="flex gap-2 items-center">
                <span className="text-[10px] text-muted-foreground">confidence {Math.round(a.confidence * 100)}%</span>
                {a.requires_human_review && (
                  <Badge variant="outline" className="text-[9px] text-blue-400 border-blue-500/40">HUMAN REVIEW: Required</Badge>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {run && (
        <ExplainerChat
          ask={(q) => api.askReviewRun(run.review_run_id, q)}
          onNewRun={() => start(date)}
        />
      )}
    </div>
  )
}

function BatchReviewView() {
  const [files, setFiles] = React.useState<{ filename: string; text: string }[]>([])
  const [date, setDate] = React.useState("")
  const [batch, setBatch] = React.useState<BatchReview | null>(null)
  const [scope, setScope] = React.useState("ENTIRE_BATCH")
  const [runId, setRunId] = React.useState("")
  const [busy, setBusy] = React.useState(false)

  const addFiles = async (list: FileList) => {
    const add = await Promise.all(
      Array.from(list).map(async (f) => ({ filename: f.name, text: await f.text() })))
    setFiles((cur) => [...cur, ...add])
  }

  const start = async () => {
    if (!files.length || !date || busy) return
    setBusy(true)
    try { setBatch(await api.createBatchReview(files, date)) }
    finally { setBusy(false) }
  }

  const retry = async () => batch && setBatch(await api.rerunBatch(batch.batch_review_id))
  const fullRerun = async () => batch && setBatch(await api.rerunBatch(batch.batch_review_id, true))

  return (
    <div className="flex flex-1 flex-col overflow-hidden min-h-0">
      <div className="flex gap-2 items-center p-3 border-b border-border flex-wrap shrink-0">
        <label className="cursor-pointer text-xs border border-border px-3 py-1.5 hover:bg-muted/50">
          📄 Thêm nhiều file
          <input type="file" accept=".txt,.md" multiple className="hidden"
                 onChange={(e) => e.target.files && addFiles(e.target.files)} />
        </label>
        <span className="text-[10px] text-muted-foreground">{files.length} file</span>
        <input type="date" className={inputCls + " w-40"} value={date}
               onChange={(e) => setDate(e.target.value)} />
        <Button size="sm" onClick={start} disabled={busy || !files.length || !date}>
          {busy ? "Đang chạy…" : `Run Batch (${files.length} runs độc lập)`}
        </Button>
        {batch && batch.failed_documents > 0 && (
          <Button size="sm" variant="outline" onClick={retry}>↻ Retry failed only</Button>
        )}
        {batch && (
          <Button size="sm" variant="ghost" onClick={fullRerun}>Re-run all → batch mới</Button>
        )}
      </div>

      {batch && (
        <div className="flex-1 overflow-y-auto p-3 space-y-3 min-h-0">
          <div className="flex gap-2 flex-wrap">
            <Badge variant="outline" className="text-[9px]">batch: {batch.batch_review_id}</Badge>
            <Badge variant="outline" className="text-[9px]">snapshot: {batch.knowledge_snapshot_id}</Badge>
            <Badge variant="outline" className="text-[9px] text-emerald-400 border-emerald-500/40">
              {batch.completed_documents}/{batch.total_documents} completed
            </Badge>
            {batch.failed_documents > 0 && (
              <Badge variant="outline" className="text-[9px] text-red-400 border-red-500/40">
                {batch.failed_documents} failed
              </Badge>
            )}
          </div>

          {/* §11.3 progress table per file */}
          <table className="w-full text-[11px]">
            <thead><tr className="text-left text-muted-foreground">
              <th className="py-1">File</th><th>Status</th><th>Review Run</th><th>Error</th>
            </tr></thead>
            <tbody>
              {batch.items.map((i) => (
                <tr key={i.item_id} className="border-t border-border">
                  <td className="py-1">{i.filename}</td>
                  <td><StatusPill status={i.status} /></td>
                  <td className="text-muted-foreground">{i.review_run_id ?? "—"}</td>
                  <td className="text-red-400">{i.error ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <Separator />
          <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
            Recurring issue groups
          </div>
          {batch.recurring_issues.length === 0 && (
            <p className="text-[11px] text-muted-foreground">Không có vấn đề lặp lại giữa các file.</p>
          )}
          {batch.recurring_issues.map((g, i) => (
            <div key={i} className="border border-orange-500/30 bg-orange-500/5 p-2 text-[11px]">
              <StatusPill status={g.finding_type} /> × {g.occurrence_count}
              {g.shared_value && <span className="text-muted-foreground"> · giá trị: {g.shared_value}</span>}
              <div className="text-muted-foreground mt-1">↳ {g.affected_document_ids.join(", ")}</div>
            </div>
          ))}
        </div>
      )}

      {batch && (
        <div className="border-t border-border px-3 pt-2 shrink-0">
          <div className="flex gap-2 items-center text-[10px]">
            <span className="text-muted-foreground">Chat scope:</span>
            <select className={inputCls + " w-44"} value={scope} onChange={(e) => setScope(e.target.value)}>
              <option value="ENTIRE_BATCH">Entire batch</option>
              <option value="ONE_REPORT">One report</option>
            </select>
            {scope === "ONE_REPORT" && (
              <select className={inputCls + " w-56"} value={runId} onChange={(e) => setRunId(e.target.value)}>
                <option value="">— chọn report —</option>
                {batch.items.filter((i) => i.review_run_id).map((i) => (
                  <option key={i.item_id} value={i.review_run_id!}>{i.filename}</option>
                ))}
              </select>
            )}
          </div>
          <ExplainerChat ask={(q) => api.askBatch(batch.batch_review_id, q, scope, runId || undefined)} />
        </div>
      )}
    </div>
  )
}
