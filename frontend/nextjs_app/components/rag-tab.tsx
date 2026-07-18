"use client"

// Tab RAG (spec §3–§8) — không gian làm việc của cán bộ Pháp chế/Tuân thủ.
// Một segmented control chuyển giữa hai mode, KHÔNG phải hai tab navigation:
//   ASK_REGULATIONS   Tra cứu quy định — multi-turn RAG, mỗi conversation độc lập
//   DOCUMENT_REVIEW   Nhận xét tài liệu — ReviewRun bất biến + chat giải thích
// Context hai mode tách rời: đổi mode không trộn lịch sử (DoD §11.12).

import * as React from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  api,
  type BatchReview, type ChatCitation, type ChatTurnT, type Conversation,
  type EvidenceItem, type ReviewRunAssessment, type ReviewRunReport, type ReviewRunResult,
} from "@/lib/api"

type Mode = "ask" | "review"

// Icon nội tuyến (không thêm dependency). Nét mảnh, hợp tông SHB.
function IconSend() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="size-4">
      <path d="M12 19V5M5 12l7-7 7 7" />
    </svg>
  )
}
function IconPlus() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="size-5">
      <path d="M12 5v14M5 12h14" />
    </svg>
  )
}

// Khung prompt cao cấp theo sample_ui: viền gradient cam (SHB) chạy quanh khi
// focus, nền mờ, bo tròn. Dùng chung cho cả hai ô chat.
function PromptShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative group/prompt">
      <div className="pointer-events-none absolute -inset-[1.5px] rounded-2xl bg-[linear-gradient(90deg,transparent,#f97316,transparent)] animate-border-glow opacity-40 blur-[2px] transition-opacity duration-500 group-focus-within/prompt:opacity-90" />
      <div className="relative flex items-end gap-2 rounded-2xl border border-border bg-card/90 backdrop-blur-sm pl-4 pr-2 py-2 shadow-sm">
        {children}
      </div>
    </div>
  )
}

// ─── Status vocabulary (shared) ───────────────────────────────────────────────

const STATUS: Record<string, { label: string; cls: string }> = {
  COMPLIANT: { label: "Phù hợp", cls: "text-emerald-600 dark:text-emerald-400 border-emerald-500/40 bg-emerald-500/10" },
  NON_COMPLIANT: { label: "Không phù hợp", cls: "text-red-500 border-red-500/40 bg-red-500/10" },
  PARTIALLY_COMPLIANT: { label: "Phù hợp một phần", cls: "text-amber-600 dark:text-amber-400 border-amber-500/40 bg-amber-500/10" },
  OUTDATED_REFERENCE: { label: "Lỗi thời", cls: "text-orange-600 dark:text-orange-400 border-orange-500/40 bg-orange-500/10" },
  MISSING_EVIDENCE: { label: "Thiếu bằng chứng", cls: "text-zinc-500 dark:text-zinc-400 border-zinc-500/40 bg-zinc-500/10" },
  AMBIGUOUS: { label: "Chưa rõ ràng", cls: "text-purple-600 dark:text-purple-400 border-purple-500/40 bg-purple-500/10" },
  NEEDS_HUMAN_REVIEW: { label: "Cần người kiểm tra", cls: "text-blue-600 dark:text-blue-400 border-blue-500/40 bg-blue-500/10" },
}

function StatusPill({ status }: { status: string }) {
  const s = STATUS[status] ?? { label: status, cls: "text-muted-foreground border-border" }
  return <Badge variant="outline" className={`text-[10px] shrink-0 ${s.cls}`}>{s.label}</Badge>
}

const inputCls =
  "w-full border border-border bg-background px-3 py-2 text-sm outline-none focus:border-orange-500 transition-colors"

// ─── RAG shell: segmented control + mode isolation ────────────────────────────

export function RagTab() {
  const [mode, setMode] = React.useState<Mode>("ask")
  return (
    <div className="flex flex-1 flex-col overflow-hidden min-h-0">
      <div className="flex items-center gap-3 px-4 py-2.5 border-b border-border shrink-0">
        <div role="tablist" aria-label="Chế độ RAG" className="inline-flex border border-border">
          <ModeButton active={mode === "ask"} onClick={() => setMode("ask")}>Tra cứu quy định</ModeButton>
          <ModeButton active={mode === "review"} onClick={() => setMode("review")}>Nhận xét tài liệu</ModeButton>
        </div>
        <span className="text-[11px] text-muted-foreground hidden lg:block">
          {mode === "ask"
            ? "Hỏi đáp trên kho quy định đã duyệt & đang hiệu lực · mỗi cuộc trò chuyện có bộ nhớ riêng"
            : "Upload policy/báo cáo để đối chiếu quy định · kết quả khóa theo từng lần đánh giá"}
        </span>
      </div>
      {/* Cả hai mode luôn mounted nhưng ẩn — state không rò rỉ giữa hai loại RAG,
          đồng thời không mất khi người dùng chuyển qua lại (spec §6). */}
      <div className={mode === "ask" ? "flex flex-1 min-h-0" : "hidden"}><AskMode /></div>
      <div className={mode === "review" ? "flex flex-1 min-h-0" : "hidden"}><ReviewMode /></div>
    </div>
  )
}

function ModeButton({ active, onClick, children }: {
  active: boolean; onClick: () => void; children: React.ReactNode
}) {
  return (
    <button role="tab" aria-selected={active} onClick={onClick}
      className={`px-4 py-1.5 text-sm font-medium transition-colors ${
        active ? "bg-orange-500 text-white" : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
      }`}>
      {children}
    </button>
  )
}

// ─── Mode 1: Tra cứu quy định (§4) ────────────────────────────────────────────

function AskMode() {
  const [convs, setConvs] = React.useState<Conversation[]>([])
  const [convId, setConvId] = React.useState<string | null>(null)
  const [turns, setTurns] = React.useState<ChatTurnT[]>([])
  const [attachments, setAttachments] = React.useState<{ id: string; filename: string }[]>([])
  const [text, setText] = React.useState("")
  const [queryDate, setQueryDate] = React.useState("")
  const [busy, setBusy] = React.useState(false)
  const scrollRef = React.useRef<HTMLDivElement>(null)

  const refreshList = React.useCallback(() => {
    api.listConversations()
      .then((cs) => setConvs(cs.filter((c) => c.mode === "REGULATORY_ASSISTANT")))
      .catch(() => {})
  }, [])
  React.useEffect(refreshList, [refreshList])

  React.useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" })
  }, [turns])

  const open = async (id: string) => {
    setConvId(id)
    const data = await api.getConversation(id)
    setTurns(data.turns)
    setAttachments(data.attachments)
  }

  const newChat = () => {
    // Cuộc trò chuyện mới = bộ nhớ rỗng (§4.3). Conversation thật tạo ở lần gửi đầu.
    setConvId(null); setTurns([]); setAttachments([]); setText("")
  }

  const send = async () => {
    if (!text.trim() || busy) return
    let id = convId
    setBusy(true)
    const q = text
    setText("")
    setTurns((t) => [...t, { id: `tmp-${Date.now()}`, role: "user", content: q, citations: [] }])
    try {
      if (!id) { id = (await api.createConversation("REGULATORY_ASSISTANT")).id; setConvId(id) }
      await api.postMessage(id, q, queryDate || undefined)
      await open(id)
      refreshList()
    } catch (e) {
      setTurns((t) => [...t, {
        id: `err-${Date.now()}`, role: "assistant",
        content: `Lỗi: ${e instanceof Error ? e.message : String(e)}`, citations: [],
      }])
    } finally {
      setBusy(false)
    }
  }

  const attach = async (file: File) => {
    let id = convId
    if (!id) { id = (await api.createConversation("REGULATORY_ASSISTANT")).id; setConvId(id); refreshList() }
    await api.addAttachment(id, file.name, await file.text())
    await open(id)
  }

  return (
    <div className="flex flex-1 overflow-hidden min-h-0">
      {/* Lịch sử chat — ranh giới isolation hiển thị rõ (§4.3, §7) */}
      <aside className="w-56 border-r border-border flex-col shrink-0 hidden md:flex">
        <div className="p-2 border-b border-border">
          <Button size="sm" className="w-full bg-orange-500 hover:bg-orange-600 text-white" onClick={newChat}>
            + Cuộc trò chuyện mới
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {convs.length === 0 && (
            <p className="text-[11px] text-muted-foreground px-1 py-2">Chưa có cuộc trò chuyện nào.</p>
          )}
          {convs.map((c) => (
            <button key={c.id} onClick={() => open(c.id)}
              className={`w-full text-left px-2 py-1.5 text-xs truncate border transition-colors ${
                c.id === convId ? "border-orange-500/60 bg-orange-500/10" : "border-transparent hover:bg-muted/50"
              }`}>
              {c.title ?? c.id}
            </button>
          ))}
        </div>
      </aside>

      {/* Nội dung hội thoại — column ChatGPT-style, căn giữa */}
      <div className="flex flex-1 flex-col min-w-0">
        <div ref={scrollRef} className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
            {turns.length === 0 && <AskEmptyState onPick={setText} />}
            {turns.map((t) => (
              <ChatBubble key={t.id} role={t.role} content={t.content} citations={t.citations} />
            ))}
            {busy && <div className="text-xs text-muted-foreground animate-pulse pl-1">Đang tra cứu kho quy định…</div>}
          </div>
        </div>

        <div className="shrink-0 border-t border-border bg-background/80 backdrop-blur-sm py-4">
          <div className="max-w-3xl mx-auto px-4 space-y-2">
            {attachments.length > 0 && (
              <div className="flex gap-1.5 flex-wrap">
                {attachments.map((a) => (
                  <Badge key={a.id} variant="outline" className="text-[10px] text-amber-600 dark:text-amber-400 border-amber-500/40">
                    {a.filename} · context cục bộ, không phải nguồn pháp lý
                  </Badge>
                ))}
              </div>
            )}
            <PromptShell>
              <label className="cursor-pointer shrink-0 rounded-full p-2 text-muted-foreground hover:text-orange-500 hover:bg-muted/60 transition-colors" title="Đính kèm file context cục bộ (.txt/.md)" aria-label="Thêm file">
                <IconPlus />
                <input type="file" accept=".txt,.md" className="hidden"
                  onChange={(e) => e.target.files?.[0] && attach(e.target.files[0])} />
              </label>
              <textarea rows={1}
                className="flex-1 resize-none bg-transparent outline-none text-sm leading-relaxed py-1.5 max-h-40 placeholder:text-muted-foreground/70"
                placeholder="Nhập câu hỏi về quy định…"
                value={text} onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send() } }} />
              <div className="flex items-center gap-1 shrink-0 pb-0.5">
                <input type="date"
                  className="w-[118px] rounded-lg border border-border bg-background/60 px-2 py-1 text-xs outline-none focus:border-orange-500"
                  value={queryDate} onChange={(e) => setQueryDate(e.target.value)}
                  title="Hỏi quy định tại một thời điểm (tùy chọn)" aria-label="Ngày truy vấn" />
                <Button size="icon" onClick={send} disabled={busy || !text.trim()}
                  className="size-9 rounded-full bg-orange-500 hover:bg-orange-600 text-white shadow-sm disabled:opacity-40"
                  aria-label="Gửi câu hỏi">
                  <IconSend />
                </Button>
              </div>
            </PromptShell>
            <p className="text-[10px] text-muted-foreground/60 text-center">
              SHB · AIDE — câu trả lời luôn kèm bằng chứng truy vết được
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

function AskEmptyState({ onPick }: { onPick: (q: string) => void }) {
  const samples = [
    "Hạn mức tín dụng SME hiện tại là bao nhiêu?",
    "Quy định này có hiệu lực từ khi nào?",
    "Lịch sử sửa đổi tỷ lệ vốn ngắn hạn cho vay trung dài hạn?",
  ]
  return (
    <div className="text-center pt-12 space-y-5">
      <div>
        <h3 className="text-sm font-semibold">Tra cứu quy định hiện hành</h3>
        <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
          Hỏi quy định tại một thời điểm, lịch sử sửa đổi, hay căn cứ Điều/Khoản. Mỗi câu trả lời
          kèm bằng chứng truy vết được. Cuộc trò chuyện mới bắt đầu với bộ nhớ rỗng.
        </p>
      </div>
      <div className="space-y-1.5">
        {samples.map((s) => (
          <button key={s} onClick={() => onPick(s)}
            className="w-full text-left text-xs border border-border px-3 py-2 hover:border-orange-500 hover:bg-orange-500/5 transition-colors">
            {s}
          </button>
        ))}
      </div>
    </div>
  )
}

// dd/mm/yyyy cho cán bộ pháp chế; giữ nguyên nếu không phải ISO YYYY-MM-DD.
function fmtDate(iso?: string): string {
  const m = iso ? /^(\d{4})-(\d{2})-(\d{2})/.exec(iso) : null
  return m ? `${m[3]}/${m[2]}/${m[1]}` : (iso ?? "")
}

// Thay [source_id] thô trong câu trả lời bằng chip số [n] khớp danh sách bằng
// chứng (vẫn truy vết: n ↔ source_id). Token không khớp giữ nguyên literal.
function renderCitedContent(content: string, idToNum: Map<string, number>): React.ReactNode[] {
  const out: React.ReactNode[] = []
  const re = /\[([^\]\s]+)\]/g
  let last = 0, k = 0, m: RegExpExecArray | null
  while ((m = re.exec(content)) !== null) {
    const n = idToNum.get(m[1])
    if (n === undefined) continue
    if (m.index > last) out.push(content.slice(last, m.index))
    out.push(
      <sup key={`c${k++}`} className="text-[10px] font-semibold text-orange-600 dark:text-orange-400">[{n}]</sup>,
    )
    last = m.index + m[0].length
  }
  if (last < content.length) out.push(content.slice(last))
  return out.length ? out : [content]
}

const INSUFFICIENT_VN = "Không tìm thấy văn bản quy phạm pháp luật phù hợp trong kho dữ liệu. Thử đặt câu hỏi khác hoặc kiểm tra kho văn bản đã có tài liệu liên quan chưa."

function ChatBubble({ role, content, citations }: {
  role: string; content: string; citations: ChatCitation[]
}) {
  const isUser = role === "user"
  const display = (!isUser && content === "INSUFFICIENT_EVIDENCE") ? INSUFFICIENT_VN : content
  const idToNum = React.useMemo(() => {
    const map = new Map<string, number>()
    citations.forEach((c, i) => { if (!map.has(c.source_id)) map.set(c.source_id, i + 1) })
    return map
  }, [citations])

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] rounded-2xl rounded-tr-sm bg-orange-500 text-white px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap shadow-sm">
          {display}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div className="text-sm leading-relaxed whitespace-pre-wrap text-foreground">
        {renderCitedContent(display, idToNum)}
      </div>
      {citations.length > 0 && <EvidencePanel citations={citations} />}
    </div>
  )
}

// Bằng chứng ngay dưới câu trả lời (§4.2) — mỗi citation expand được để đọc nội dung trích dẫn.
function EvidencePanel({ citations }: { citations: ChatCitation[] }) {
  const [open, setOpen] = React.useState(false)
  const [expanded, setExpanded] = React.useState<Set<number>>(new Set())
  const toggle = (i: number) =>
    setExpanded((s) => { const n = new Set(s); n.has(i) ? n.delete(i) : n.add(i); return n })

  return (
    <div className="mt-2 rounded-xl border border-blue-500/20 bg-blue-500/5 overflow-hidden">
      <button onClick={() => setOpen(!open)} aria-expanded={open}
        className="w-full flex items-center gap-2 px-3 py-2 text-[11px] font-semibold text-blue-600 dark:text-blue-400 hover:bg-blue-500/10 transition-colors">
        <span>{open ? "▾" : "▸"}</span>
        {citations.length} nguồn căn cứ
        <Badge variant="outline" className="text-[9px] ml-auto text-emerald-600 dark:text-emerald-400 border-emerald-500/40 bg-emerald-500/10">
          Đã xác thực
        </Badge>
      </button>
      {open && (
        <ul className="divide-y divide-blue-500/10">
          {citations.map((c, i) => (
            <li key={i}>
              <button onClick={() => toggle(i)}
                className="w-full flex items-start gap-2.5 px-3 py-2.5 text-left hover:bg-blue-500/10 transition-colors group">
                <span className="shrink-0 text-[11px] font-bold text-orange-500 mt-0.5">[{i + 1}]</span>
                <div className="flex-1 min-w-0">
                  <div className="text-[12px] font-semibold text-foreground truncate">
                    {c.document_number ?? c.source_id}
                  </div>
                  {c.heading_path && c.heading_path.length > 0 && (
                    <div className="text-[11px] text-muted-foreground truncate">
                      {c.heading_path.join(" › ")}
                    </div>
                  )}
                  <div className="text-[10px] text-muted-foreground/70 mt-0.5 flex gap-2">
                    {c.valid_from && <span>Hiệu lực: {fmtDate(c.valid_from)}{c.valid_to_exclusive ? ` → ${fmtDate(c.valid_to_exclusive)}` : " → nay"}</span>}
                    {typeof c.page === "number" && <span>Trang {c.page}</span>}
                  </div>
                </div>
                <span className="shrink-0 text-[10px] text-blue-500 opacity-0 group-hover:opacity-100 transition-opacity mt-0.5">
                  {expanded.has(i) ? "thu gọn" : "xem nội dung"}
                </span>
              </button>
              {expanded.has(i) && c.content && (
                <div className="px-3 pb-3 pt-1 ml-7">
                  <blockquote className="border-l-2 border-orange-400 pl-3 text-[12px] text-foreground/80 leading-relaxed italic whitespace-pre-wrap bg-orange-500/5 py-2 pr-2 rounded-r-lg">
                    {c.content}
                  </blockquote>
                </div>
              )}
              {expanded.has(i) && !c.content && (
                <div className="px-3 pb-3 pt-1 ml-7 text-[11px] text-muted-foreground italic">
                  Nội dung trích dẫn chưa được lưu cho phiên bản này.
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// ─── Mode 2: Nhận xét tài liệu (§5, §8) ───────────────────────────────────────

interface ReviewFile { filename: string; text: string }

function ReviewMode() {
  const [run, setRun] = React.useState<ReviewRunResult | null>(null)
  const [batch, setBatch] = React.useState<BatchReview | null>(null)

  const reset = () => { setRun(null); setBatch(null) }

  if (!run && !batch) {
    return <ReviewIntake onSingle={setRun} onBatch={setBatch} />
  }
  if (batch) return <BatchResult batch={batch} setBatch={setBatch} onNew={reset} />
  return <SingleResult run={run!} setRun={setRun} onNew={reset} />
}

function ReviewIntake({ onSingle, onBatch }: {
  onSingle: (r: ReviewRunResult) => void
  onBatch: (b: BatchReview) => void
}) {
  const [files, setFiles] = React.useState<ReviewFile[]>([])
  const [date, setDate] = React.useState("")
  const [scope, setScope] = React.useState("")
  const [busy, setBusy] = React.useState(false)
  const [err, setErr] = React.useState<string | null>(null)

  const addFiles = async (list: FileList) => {
    setErr(null)
    const out: ReviewFile[] = []
    for (const f of Array.from(list).slice(0, 5)) {
      try {
        // .txt/.md đọc thẳng; PDF/DOCX nhờ backend trích xuất (PyMuPDF /extract-text).
        const isText = /\.(txt|md|csv|json|text)$/i.test(f.name)
        const text = isText ? await f.text() : (await api.extractText(f)).text
        out.push({ filename: f.name, text })
      } catch (e) {
        setErr(`${f.name}: ${e instanceof Error ? e.message : String(e)}`)
      }
    }
    setFiles((cur) => [...cur, ...out].slice(0, 5))
  }

  const start = async () => {
    if (!files.length) { setErr("Cần chọn ít nhất một file để nhận xét."); return }
    if (!date) { setErr("Cần chọn ngày đánh giá."); return }
    setErr(null); setBusy(true)
    try {
      if (files.length === 1) {
        onSingle(await api.createReviewRun(files[0].filename, files[0].text, date))
      } else {
        onBatch(await api.createBatchReview(files, date))  // mỗi file một Review Run độc lập
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-lg mx-auto space-y-5">
        <div>
          <h3 className="text-base font-semibold">Nhận xét tài liệu</h3>
          <p className="text-sm text-muted-foreground mt-1 leading-relaxed">
            Tải policy, quy trình hoặc báo cáo cần kiểm tra. Hệ thống đối chiếu với quy định
            <strong className="text-foreground"> đã duyệt &amp; đang hoạt động</strong> tại ngày đánh giá và chỉ ra điểm chưa phù hợp.
          </p>
        </div>

        <div className="border border-blue-500/30 bg-blue-500/10 p-3 text-xs text-blue-600 dark:text-blue-300 leading-relaxed">
          File ở đây là <strong>tài liệu chỉ để kiểm tra</strong> — không được thêm vào
          kho pháp lý, không thành nguồn căn cứ, không xuất hiện ở mode tra cứu.
        </div>

        <label className="block border-2 border-dashed border-border p-6 text-center text-muted-foreground cursor-pointer transition-colors hover:border-emerald-500 hover:text-emerald-500">
          <input type="file" accept=".txt,.md,.pdf,.docx" multiple className="hidden"
                 onChange={(e) => e.target.files && addFiles(e.target.files)} />
          <span className="block text-sm font-medium">Chọn file</span>
          <span className="block text-xs mt-1">1 file = Single Review · nhiều file = Batch (tối đa 5)</span>
        </label>

        {files.length > 0 && (
          <ul className="border border-border divide-y divide-border">
            {files.map((f, i) => (
              <li key={i} className="flex items-center gap-2 px-3 py-2 text-sm">
                <span className="flex-1 truncate">{f.filename}</span>
                <button onClick={() => setFiles((cur) => cur.filter((_, j) => j !== i))}
                        className="text-xs text-muted-foreground hover:text-red-500 transition-colors">Bỏ</button>
              </li>
            ))}
          </ul>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-1">
            <label htmlFor="review-date" className="text-xs font-medium">Ngày đánh giá</label>
            <input id="review-date" type="date" className={inputCls} value={date}
                   onChange={(e) => setDate(e.target.value)} />
          </div>
          <div className="space-y-1">
            <label htmlFor="review-scope" className="text-xs font-medium">
              Phạm vi kiểm tra <span className="text-muted-foreground font-normal">(không bắt buộc)</span>
            </label>
            <input id="review-scope" className={inputCls} placeholder="vd: tín dụng SME"
                   value={scope} onChange={(e) => setScope(e.target.value)} />
          </div>
        </div>

        {err && <p className="text-xs text-red-500 border border-red-500/30 bg-red-500/10 px-3 py-2">{err}</p>}

        <Button className="w-full bg-emerald-600 hover:bg-emerald-700 text-white" onClick={start}
                disabled={busy || !files.length || !date}>
          {busy ? "Đang chạy nhận xét…" : "Bắt đầu nhận xét"}
        </Button>
      </div>
    </div>
  )
}

// ─── Single Review result: tài liệu | findings | chat (§5.4) ─────────────────

function SingleResult({ run, setRun, onNew }: {
  run: ReviewRunResult; setRun: (r: ReviewRunResult) => void; onNew: () => void
}) {
  const report = run.report
  const [activeClaim, setActiveClaim] = React.useState<string | null>(null)
  const [busy, setBusy] = React.useState(false)

  const rerun = async () => {
    if (busy || !report) return
    setBusy(true)
    try { setRun(await api.rerunReviewRun(run.review_run_id, report.assessment_date)) }
    finally { setBusy(false) }
  }

  if (!report) {
    return (
      <div className="flex-1 flex items-center justify-center p-6 text-sm text-muted-foreground">
        Review Run {run.review_run_id} — trạng thái {run.state}. Chưa có báo cáo.
        <Button size="sm" variant="outline" className="ml-3" onClick={onNew}>Nhận xét tài liệu khác</Button>
      </div>
    )
  }

  return (
    <div className="flex flex-1 overflow-hidden min-h-0">
      <ReviewDocPanel report={report} onNew={onNew} onRerun={rerun} rerunning={busy} />

      <div className="flex flex-1 flex-col min-w-0">
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <FindingsOverview report={report} />
          <div className="space-y-3">
            {report.assessments.map((a) => (
              <FindingCard key={a.claim_id} a={a}
                active={activeClaim === a.claim_id}
                onClick={() => setActiveClaim(activeClaim === a.claim_id ? null : a.claim_id)} />
            ))}
          </div>
        </div>
        <FollowUpChat
          placeholder="Hỏi thêm về kết quả nhận xét…"
          ask={(q) => api.askReviewRun(run.review_run_id, q, activeClaim ?? undefined)}
          onNewRun={onNew}
        />
      </div>
    </div>
  )
}

function ReviewDocPanel({ report, onNew, onRerun, rerunning }: {
  report: ReviewRunReport; onNew: () => void; onRerun: () => void; rerunning: boolean
}) {
  return (
    <aside className="w-56 border-r border-border flex-col shrink-0 hidden md:flex">
      <div className="p-3 border-b border-border">
        <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Tài liệu</div>
        <div className="text-sm font-medium mt-1 break-words">{report.target_document.filename ?? "Tài liệu kiểm tra"}</div>
        <Badge variant="outline" className="text-[9px] mt-1.5 text-blue-600 dark:text-blue-400 border-blue-500/40">
          {TRUST_LABEL[report.target_document.trust_class] ?? report.target_document.trust_class}
        </Badge>
      </div>
      <div className="p-3 text-[11px] text-muted-foreground space-y-1 border-b border-border">
        <div>Ngày đánh giá: <span className="text-foreground">{report.assessment_date}</span></div>
        <div className="truncate">Snapshot: {report.knowledge_snapshot_id}</div>
        <div>Prompt {report.versions.prompt} · Schema {report.versions.schema}</div>
        <Badge variant="outline" className="text-[9px] text-amber-600 dark:text-amber-400 border-amber-500/40 mt-1">
          Kết quả đã khóa
        </Badge>
      </div>
      <div className="p-2 mt-auto space-y-1.5">
        <Button size="sm" variant="outline" className="w-full" onClick={onRerun} disabled={rerunning}>
          {rerunning ? "Đang tạo…" : "Đánh giá lại (Run mới)"}
        </Button>
        <Button size="sm" variant="ghost" className="w-full" onClick={onNew}>Tài liệu khác</Button>
      </div>
    </aside>
  )
}

function FindingsOverview({ report }: { report: ReviewRunReport }) {
  const summary: Record<string, number> = report.summary ?? {}
  // total_claims là TỔNG, không phải một trạng thái → tách ra, đừng hiện thành pill.
  const total = summary.total_claims ?? report.assessments.length
  const entries = Object.entries(summary).filter(([k, n]) => k !== "total_claims" && n > 0)
  const attention = entries
    .filter(([k]) => k.toUpperCase() !== "COMPLIANT")
    .reduce((sum, [, n]) => sum + n, 0)
  const allOk = total > 0 && attention === 0

  return (
    <div className="border border-border bg-card rounded-lg p-4">
      <div className="flex items-baseline justify-between gap-2 mb-3">
        <div className="text-sm font-semibold">Tổng quan</div>
        <div className="text-xs text-muted-foreground">Đã kiểm tra {total} nội dung</div>
      </div>

      {total === 0 ? (
        <p className="text-xs text-muted-foreground">Chưa trích xuất được nội dung nào để kiểm tra.</p>
      ) : allOk ? (
        <div className="text-sm font-medium text-emerald-600 dark:text-emerald-400">
          Tất cả nội dung đều phù hợp với quy định hiện hành.
        </div>
      ) : (
        <>
          <p className="text-xs text-muted-foreground mb-2">
            <span className="font-semibold text-foreground">{attention}</span> nội dung cần chú ý
          </p>
          <div className="flex flex-wrap gap-2">
            {entries.map(([k, n]) => {
              const meta = STATUS[k.toUpperCase()]
              return (
                <span
                  key={k}
                  className={`inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border ${meta?.cls ?? "border-border text-muted-foreground"}`}
                >
                  <span className="font-bold">{n}</span>
                  {meta?.label ?? k}
                </span>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}

function FindingCard({ a, active, onClick }: {
  a: ReviewRunAssessment; active: boolean; onClick: () => void
}) {
  return (
    <div className={`border bg-card transition-colors ${active ? "border-orange-500/60" : "border-border"}`}>
      <button onClick={onClick} aria-expanded={active}
              className="w-full flex items-start justify-between gap-3 p-3 text-left hover:bg-muted/30 transition-colors">
        <span className="text-sm min-w-0">
          <span className="text-muted-foreground text-[10px] block mb-0.5">
            Nội dung tài liệu {active ? "(đang chọn — chat sẽ hỏi về mục này)" : ""}
          </span>
          &ldquo;{a.source_text}&rdquo;
        </span>
        <StatusPill status={a.status} />
      </button>

      <div className="px-3 pb-3 space-y-2">
        {a.findings.map((f, i) => (
          <div key={i} className="text-[11px] text-orange-600 dark:text-orange-300">▸ {f}</div>
        ))}
        {a.explanation && <p className="text-[11px] text-muted-foreground leading-relaxed">{a.explanation}</p>}

        {a.valid_evidence.slice(0, 3).map((e) => <EvidenceRow key={e.version_id} e={e} />)}

        {a.recommendation && (
          <div className="text-[11px] text-emerald-600 dark:text-emerald-400 border border-emerald-500/25 bg-emerald-500/5 px-2 py-1.5">
            Đề xuất: {a.recommendation}
          </div>
        )}

        <div className="flex items-center gap-2 pt-0.5">
          <span className="text-[10px] text-muted-foreground">Độ tin cậy {Math.round(a.confidence * 100)}%</span>
          {a.requires_human_review && (
            <Badge variant="outline" className="text-[9px] text-blue-600 dark:text-blue-400 border-blue-500/40">
              Cần người kiểm tra
            </Badge>
          )}
        </div>
      </div>
    </div>
  )
}

function EvidenceRow({ e }: { e: EvidenceItem }) {
  return (
    <div className="text-[11px] border-l-2 border-blue-500/40 pl-2 py-0.5">
      <div className="text-blue-600 dark:text-blue-400 font-medium">
        {e.document_number}
        {e.heading_path.length > 0 && <span className="font-normal"> · {e.heading_path.join(" › ")}</span>}
      </div>
      {e.content && <div className="text-muted-foreground italic mt-0.5 leading-relaxed">&ldquo;{e.content}&rdquo;</div>}
      <div className="text-muted-foreground/80 mt-0.5">
        hiệu lực {e.valid_from}
        {e.valid_to_exclusive ? ` → ${e.valid_to_exclusive}` : " → nay"}
        {typeof e.page === "number" ? ` · tr.${e.page}` : ""}
      </div>
    </div>
  )
}

// ─── Batch result: bảng file | findings của file đã chọn | chat (§8) ─────────

function BatchResult({ batch, setBatch, onNew }: {
  batch: BatchReview; setBatch: (b: BatchReview) => void; onNew: () => void
}) {
  const [selected, setSelected] = React.useState<string | null>(null)
  const [busy, setBusy] = React.useState(false)

  const selectedItem = batch.items.find((i) => i.item_id === selected)
  const retryFailed = async () => {
    if (busy) return
    setBusy(true)
    try { setBatch(await api.rerunBatch(batch.batch_review_id)) }
    finally { setBusy(false) }
  }

  return (
    <div className="flex flex-1 overflow-hidden min-h-0">
      <aside className="w-64 border-r border-border flex flex-col shrink-0">
        <div className="p-3 border-b border-border">
          <div className="text-sm font-semibold">Batch Review</div>
          <div className="text-[11px] text-muted-foreground mt-1">
            {batch.completed_documents}/{batch.total_documents} hoàn tất
            {batch.failed_documents > 0 && ` · ${batch.failed_documents} lỗi`}
          </div>
          <div className="flex gap-1.5 mt-2">
            {batch.failed_documents > 0 && (
              <Button size="sm" variant="outline" onClick={retryFailed} disabled={busy}>
                {busy ? "…" : "Chạy lại file lỗi"}
              </Button>
            )}
            <Button size="sm" variant="ghost" onClick={onNew}>Batch khác</Button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {batch.items.map((i) => (
            <button key={i.item_id} onClick={() => setSelected(i.item_id)}
              className={`w-full text-left px-3 py-2.5 border-b border-border transition-colors ${
                selected === i.item_id ? "bg-orange-500/10" : "hover:bg-muted/40"
              }`}>
              <div className="text-xs font-medium truncate">{i.filename}</div>
              <div className="mt-1"><BatchStatusBadge status={i.status} error={i.error} /></div>
            </button>
          ))}
        </div>
      </aside>

      <div className="flex flex-1 flex-col min-w-0">
        {!selectedItem ? (
          <div className="flex-1 flex flex-col items-center justify-center text-sm text-muted-foreground gap-3 p-6">
            <p>Chọn một tài liệu bên trái để xem finding và hỏi thêm.</p>
            {batch.recurring_issues.length > 0 && (
              <div className="w-full max-w-md space-y-1.5">
                <div className="text-[10px] font-bold uppercase tracking-wider">Vấn đề lặp lại giữa các file</div>
                {batch.recurring_issues.map((g, i) => (
                  <div key={i} className="border border-orange-500/30 bg-orange-500/5 p-2 text-[11px] text-left">
                    <StatusPill status={g.finding_type} /> × {g.occurrence_count}
                    {g.shared_value && <span className="text-muted-foreground"> · {g.shared_value}</span>}
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <BatchItemDetail batch={batch} itemId={selectedItem.item_id} />
        )}
      </div>
    </div>
  )
}

function BatchItemDetail({ batch, itemId }: { batch: BatchReview; itemId: string }) {
  const item = batch.items.find((i) => i.item_id === itemId)!
  const [run, setRun] = React.useState<ReviewRunResult | null>(null)
  const [err, setErr] = React.useState<string | null>(null)

  React.useEffect(() => {
    setRun(null); setErr(null)
    if (!item.review_run_id) return
    api.getReviewRun(item.review_run_id).then(setRun).catch((e) => setErr(String(e)))
  }, [item.review_run_id])

  if (!item.review_run_id) {
    return (
      <div className="flex-1 flex items-center justify-center p-6 text-sm text-muted-foreground text-center">
        {item.filename} — {BATCH_STATUS_LABEL[item.status] ?? item.status}{item.error ? `: ${item.error}` : " (chưa có kết quả rà soát)."}
      </div>
    )
  }

  return (
    <>
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div className="text-sm font-semibold">{item.filename}</div>
        {err && <p className="text-xs text-red-500">{err}</p>}
        {!run && !err && <div className="text-xs text-muted-foreground animate-pulse">Đang tải báo cáo…</div>}
        {run?.report && (
          <>
            <FindingsOverview report={run.report} />
            <div className="space-y-3">
              {run.report.assessments.map((a) => (
                <FindingCard key={a.claim_id} a={a} active={false} onClick={() => {}} />
              ))}
            </div>
          </>
        )}
      </div>
      <FollowUpChat
        placeholder={`Hỏi thêm về ${item.filename}…`}
        ask={(q) => api.askBatch(batch.batch_review_id, q, "ONE_REPORT", item.review_run_id ?? undefined)}
      />
    </>
  )
}

const BATCH_STATUS_LABEL: Record<string, string> = {
  COMPLETED: "Hoàn tất",
  FAILED: "Lỗi",
  PENDING: "Chờ xử lý",
  RUNNING: "Đang chạy",
}

const TRUST_LABEL: Record<string, string> = {
  AUTHORITY_SOURCE_CANDIDATE: "Nguồn chờ xác minh",
  AUTHORITY_SOURCE: "Nguồn có thẩm quyền",
  INTERNAL_APPROVED: "Nội bộ đã duyệt",
  REVIEW_TARGET: "Tài liệu kiểm tra",
  UNVERIFIED: "Chưa xác minh",
  CONVERSATION_ATTACHMENT: "File đính kèm hội thoại",
  USER_MESSAGE: "Tin nhắn người dùng",
  REVIEW_RESULT: "Kết quả rà soát",
}

function BatchStatusBadge({ status, error }: { status: string; error: string | null }) {
  const map: Record<string, string> = {
    COMPLETED: "text-emerald-600 dark:text-emerald-400 border-emerald-500/40",
    FAILED: "text-red-500 border-red-500/40",
    PENDING: "text-amber-600 dark:text-amber-400 border-amber-500/40",
    RUNNING: "text-blue-600 dark:text-blue-400 border-blue-500/40",
  }
  return (
    <Badge variant="outline" className={`text-[9px] ${map[status] ?? "text-muted-foreground border-border"}`}
           title={error ?? undefined}>
      {BATCH_STATUS_LABEL[status] ?? status}
    </Badge>
  )
}

// ─── Follow-up chat: bounded to the current run (§5.5) ────────────────────────

function FollowUpChat({ placeholder, ask, onNewRun }: {
  placeholder: string
  ask: (q: string) => Promise<{ answer: string; action?: string; result_locked?: boolean; citations?: ChatCitation[] }>
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
    } catch (e) {
      setLog((l) => [...l, { q: question, a: `Lỗi: ${e instanceof Error ? e.message : String(e)}` }])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="border-t border-border shrink-0">
      {log.length > 0 && (
        <div className="max-h-48 overflow-y-auto p-3 space-y-3">
          {log.map((e, i) => (
            <div key={i} className="text-xs space-y-1">
              <div className="text-orange-600 dark:text-orange-400 font-medium">❯ {e.q}</div>
              <div className="whitespace-pre-wrap text-muted-foreground leading-relaxed">{e.a}</div>
              {e.locked && (
                <Badge variant="outline" className="text-[9px] text-red-500 border-red-500/40">
                  Kết quả đã khóa — chat giải thích không đổi kết luận gốc
                </Badge>
              )}
              {e.action === "CREATE_NEW_REVIEW_RUN" && onNewRun && (
                <Button size="sm" variant="outline" className="mt-1" onClick={onNewRun}>Tạo Review Run mới</Button>
              )}
            </div>
          ))}
        </div>
      )}
      <div className="p-3 pt-2">
        <PromptShell>
          <input className="flex-1 bg-transparent outline-none text-sm py-1.5 placeholder:text-muted-foreground/70"
                 placeholder={placeholder} value={q}
                 onChange={(e) => setQ(e.target.value)}
                 onKeyDown={(e) => { if (e.key === "Enter") send() }} />
          <Button size="icon" onClick={send} disabled={busy || !q.trim()}
                  className="size-9 rounded-full bg-orange-500 hover:bg-orange-600 text-white shrink-0 disabled:opacity-40"
                  aria-label="Gửi">
            {busy ? <span className="text-xs">…</span> : <IconSend />}
          </Button>
        </PromptShell>
      </div>
    </div>
  )
}
