"use client"

import * as React from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Separator } from "@/components/ui/separator"
import { TooltipProvider } from "@/components/ui/tooltip"
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuTrigger, DropdownMenuSeparator, DropdownMenuLabel,
} from "@/components/ui/dropdown-menu"
import {
  InputGroup, InputGroupAddon, InputGroupButton, InputGroupTextarea,
} from "@/components/ui/input-group"
import { HugeiconsIcon } from "@hugeicons/react"
import {
  PlusSignIcon, ArrowUp02Icon, ArrowRight02Icon, ArrowDown01Icon,
  SparklesIcon, Upload03Icon, InboxIcon, Analytics01Icon,
  DocumentValidationIcon, File02Icon, Settings01Icon,
  SlidersHorizontalIcon, CheckmarkCircle02Icon, Cancel01Icon, CancelCircleIcon,
  Alert02Icon, RemoveCircleIcon, SquareLock01Icon, QuoteDownIcon,
  Database01Icon, Search01Icon, ShareKnowledgeIcon, AiBrain01Icon,
  FlashIcon, SatelliteIcon, Wrench01Icon, Idea01Icon,
  Download01Icon, Attachment01Icon, Moon02Icon, Sun03Icon,
} from "@hugeicons/core-free-icons"
import { useTheme } from "@/components/theme-provider"
import {
  api, type QueryResponse, type Answer, type EvidenceItem, type ExcludedEvidence,
  type ConflictCandidate, type DocumentRow, type HealthDetails,
  type ComplianceReport, type Assessment, type ImpactReport,
} from "@/lib/api"

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type IconT = any

import { ModeChatView } from "@/components/mode-chat"

function Icon({ icon, className }: { icon: IconT; className?: string }) {
  return <HugeiconsIcon icon={icon} strokeWidth={1.8} className={className ?? "size-4"} />
}

// ─── Types & status system ────────────────────────────────────────────────────

type View = "chat" | "modes" | "upload-a" | "review" | "impact" | "upload-b" | "report" | "health"

interface Msg {
  id: string
  role: "user" | "assistant"
  content: string
  answer?: Answer
  evidence?: QueryResponse["evidence"]
  error?: boolean
}

type StatusKind = "ok" | "bad" | "warn" | "muted"
const STATUS_STYLE: Record<StatusKind, { icon: IconT; text: string; ring: string }> = {
  ok: { icon: CheckmarkCircle02Icon, text: "text-emerald-400", ring: "border-emerald-500/30 bg-emerald-500/10" },
  bad: { icon: CancelCircleIcon, text: "text-red-400", ring: "border-red-500/30 bg-red-500/10" },
  warn: { icon: Alert02Icon, text: "text-amber-400", ring: "border-amber-500/30 bg-amber-500/10" },
  muted: { icon: RemoveCircleIcon, text: "text-muted-foreground", ring: "border-border bg-muted/40" },
}

// Backend claim/answer status → UI kind + label. Covers Workflow B statuses.
function statusMeta(status: string): { kind: StatusKind; label: string } {
  const map: Record<string, StatusKind> = {
    COMPLIANT: "ok",
    NON_COMPLIANT: "bad",
    OUTDATED_REFERENCE: "warn",
    MISSING_EVIDENCE: "muted",
    PARTIALLY_COMPLIANT: "warn",
    AMBIGUOUS: "warn",
    NEEDS_HUMAN_REVIEW: "warn",
  }
  return { kind: map[status] ?? "muted", label: status.replace(/_/g, " ") }
}

// ─── Main ─────────────────────────────────────────────────────────────────────

export function ComplianceRAG() {
  const [isSidebarOpen, setIsSidebarOpen] = React.useState(true)
  const [animationsEnabled, setAnimationsEnabled] = React.useState(true)
  const [currentView, setCurrentView] = React.useState<View>("chat")
  const [evidenceOpen, setEvidenceOpen] = React.useState(false)
  const [evidence, setEvidence] = React.useState<QueryResponse["evidence"] | null>(null)
  const [health, setHealth] = React.useState<HealthDetails | null>(null)
  const [report, setReport] = React.useState<ComplianceReport | null>(null)

  React.useEffect(() => {
    const stored = localStorage.getItem("compliance-animations")
    if (stored !== null) setAnimationsEnabled(stored === "true")
    api.health().then(setHealth).catch(() => setHealth(null))
  }, [])

  const toggleAnimations = () => {
    const next = !animationsEnabled
    setAnimationsEnabled(next)
    localStorage.setItem("compliance-animations", String(next))
  }

  const openEvidence = (e: QueryResponse["evidence"]) => {
    setEvidence(e)
    setEvidenceOpen(true)
  }

  const nav = (view: View) => setCurrentView(view)

  return (
    <TooltipProvider>
      <div className="flex h-screen w-full overflow-hidden bg-background text-foreground">
        {/* ── Sidebar ── */}
        <div
          className={`flex flex-col bg-muted/30 transition-all duration-300 relative overflow-hidden ${
            isSidebarOpen ? "w-64" : "w-0"
          }`}
        >
          {animationsEnabled && (
            <div className="pointer-events-none absolute right-0 top-0 h-full w-[1px] bg-gradient-to-b from-transparent via-orange-500 to-transparent animate-border-1 opacity-50" />
          )}
          {isSidebarOpen && (
            <div className="flex h-full flex-col min-w-64">
              {/* Logo */}
              <div className="p-4 relative shrink-0">
                {animationsEnabled && (
                  <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-orange-400 to-transparent animate-border-2 opacity-40" />
                )}
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-[9px] font-bold text-muted-foreground tracking-widest uppercase">
                      SHB · VAIC2026
                    </div>
                    <div className="text-sm font-semibold mt-0.5 leading-snug">
                      Compliance RAG
                    </div>
                  </div>
                  <Button variant="ghost" size="icon" className="size-7" onClick={() => setIsSidebarOpen(false)}>
                    <Icon icon={ArrowDown01Icon} className="size-4 rotate-90" />
                  </Button>
                </div>
              </div>

              {/* Nav */}
              <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
                <NavItem icon={SparklesIcon} label="Hỏi đáp & Tra cứu" active={currentView === "chat"} onClick={() => nav("chat")} />
                <NavItem icon={AiBrain01Icon} label="Chat Modes (Ask · Review)" active={currentView === "modes"} onClick={() => nav("modes")} />

                <SectionLabel color="bg-blue-500" text="Workflow A — Nguồn pháp lý" toneClass="text-blue-400" />
                <NavItem icon={Upload03Icon} label="Thêm văn bản" active={currentView === "upload-a"} onClick={() => nav("upload-a")} />
                <NavItem icon={InboxIcon} label="Duyệt thay đổi" active={currentView === "review"} onClick={() => nav("review")} />
                <NavItem icon={Analytics01Icon} label="Báo cáo tác động" active={currentView === "impact"} onClick={() => nav("impact")} />

                <SectionLabel color="bg-emerald-500" text="Workflow B — Kiểm tra tài liệu" toneClass="text-emerald-400" />
                <NavItem icon={DocumentValidationIcon} label="Kiểm tra tài liệu" active={currentView === "upload-b"} onClick={() => nav("upload-b")} />
                <NavItem icon={File02Icon} label="Kết quả kiểm tra" active={currentView === "report"} onClick={() => nav("report")} />

                <Separator className="my-2" />
                <NavItem icon={Settings01Icon} label="Health & Audit" active={currentView === "health"} onClick={() => nav("health")} />
              </div>

              {/* User */}
              <div className="p-4 shrink-0 relative">
                {animationsEnabled && (
                  <div className="pointer-events-none absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-orange-400 to-transparent animate-border-3 opacity-30" />
                )}
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 bg-blue-950 border border-blue-800 flex items-center justify-center text-[11px] font-bold text-blue-300 shrink-0">
                    PN
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs font-medium truncate">Phan Nguyệt</div>
                    <div className="text-[10px] text-muted-foreground">COMPLIANCE_OFFICER</div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ── Main ── */}
        <div className="flex flex-1 flex-col overflow-hidden min-w-0">
          {/* Header */}
          <div className="flex items-center justify-between px-4 h-12 shrink-0 relative">
            {animationsEnabled && (
              <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-orange-500 to-transparent animate-border-3 opacity-60" />
            )}
            <div className="flex items-center gap-2">
              {!isSidebarOpen && (
                <Button variant="ghost" size="icon" className="size-7" onClick={() => setIsSidebarOpen(true)}>
                  <Icon icon={ArrowDown01Icon} className="size-4 -rotate-90" />
                </Button>
              )}
              <span className="text-sm font-semibold">{VIEW_LABELS[currentView]}</span>
            </div>
            <div className="flex items-center gap-1.5 flex-wrap justify-end">
              <HealthChip label="PostgreSQL" ok={health?.postgres === "connected"} />
              <HealthChip label="OpenSearch" ok={health?.opensearch === "connected"} />
              <HealthChip label="Neo4j" ok={health?.neo4j === "connected"} />
              <HealthChip label={`LLM: ${health?.llm ?? "?"}`} ok={!!health && health.llm !== "mock"} />
              {health?.demo_mode && (
                <Badge variant="outline" className="text-[10px] text-amber-500 border-amber-500/50 bg-amber-500/10 hidden sm:flex items-center gap-1">
                  <Icon icon={Alert02Icon} className="size-3" /> DEMO
                </Badge>
              )}
              <Button variant="ghost" size="icon" className="size-7" onClick={toggleAnimations} title="Bật/tắt animation">
                <Icon icon={SparklesIcon} className={`size-4 ${animationsEnabled ? "text-orange-500" : "opacity-40"}`} />
              </Button>
              <ThemeToggle />
            </div>
          </div>

          {/* View */}
          {currentView === "chat" && <ChatView animationsEnabled={animationsEnabled} onOpenEvidence={openEvidence} />}
          {currentView === "modes" && <ModeChatView />}
          {currentView === "upload-a" && <UploadSourceView />}
          {currentView === "review" && <ReviewInboxView />}
          {currentView === "impact" && <ImpactView />}
          {currentView === "upload-b" && <UploadCheckView onReport={(r) => { setReport(r); nav("report") }} />}
          {currentView === "report" && <ComplianceReportView report={report} onGoUpload={() => nav("upload-b")} />}
          {currentView === "health" && <HealthView health={health} />}
        </div>

        {/* Evidence sheet */}
        <Sheet open={evidenceOpen} onOpenChange={(v) => !v && setEvidenceOpen(false)}>
          <SheetContent side="right" className="w-80 sm:w-96">
            <SheetHeader>
              <SheetTitle className="text-sm">Bằng chứng pháp lý</SheetTitle>
            </SheetHeader>
            <div className="mt-4 space-y-3 overflow-y-auto max-h-[calc(100vh-8rem)] pr-1">
              <p className="text-xs text-muted-foreground">
                Chỉ AUTHORITY_SOURCE APPROVED + ACTIVE tại ngày tra cứu.
              </p>
              {evidence?.valid_evidence.map((e) => (
                <div key={e.version_id} className="border border-border bg-muted/30 p-3 space-y-2">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <AuthorityTag />
                    <span className="text-[11px] font-semibold text-blue-400">
                      {e.document_number} · {e.heading_path.join(" ") || "—"}
                    </span>
                  </div>
                  <QuoteBlock>{e.content}</QuoteBlock>
                  <div className="text-[10px] text-muted-foreground flex gap-3 flex-wrap">
                    <span>version: {e.version_id}</span>
                    <span>valid_from: {e.valid_from}</span>
                    <span>valid_to: {e.valid_to_exclusive ?? "∞"}</span>
                  </div>
                </div>
              ))}
              {evidence?.excluded_evidence.map((x) => (
                <div key={x.version_id} className="border border-red-500/25 bg-red-500/5 p-3 text-[11px] text-red-300 flex gap-2">
                  <Icon icon={RemoveCircleIcon} className="size-4 text-red-400 shrink-0 mt-px" />
                  <span>
                    <strong className="text-red-400">Đã loại:</strong> {x.version_id} ({x.provision_id}) — {x.reason}.
                  </span>
                </div>
              ))}
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </TooltipProvider>
  )
}

// ─── Shared micro-components ──────────────────────────────────────────────────

const VIEW_LABELS: Record<View, string> = {
  chat: "Hỏi đáp & Tra cứu",
  modes: "Chat Modes — Ask Regulations · Document Review",
  "upload-a": "Thêm văn bản pháp lý",
  review: "Duyệt thay đổi",
  impact: "Báo cáo tác động",
  "upload-b": "Kiểm tra tài liệu",
  report: "Kết quả kiểm tra",
  health: "Health & Audit",
}

function SectionLabel({ color, text, toneClass }: { color: string; text: string; toneClass: string }) {
  return (
    <div className="pt-3 pb-1 px-2 flex items-center gap-2">
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${color}`} />
      <span className={`text-[9px] font-bold uppercase tracking-wider ${toneClass}`}>{text}</span>
    </div>
  )
}

function NavItem({ icon, label, active, onClick, badge }: {
  icon: IconT; label: string; active: boolean; onClick: () => void; badge?: number
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-2 px-2 py-1.5 text-sm transition-colors text-left ${
        active ? "bg-secondary text-secondary-foreground" : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
      }`}
    >
      <Icon icon={icon} className="size-4 shrink-0" />
      <span className="flex-1 truncate">{label}</span>
      {badge !== undefined && (
        <Badge variant="destructive" className="text-[10px] h-4 px-1.5 shrink-0">{badge}</Badge>
      )}
    </button>
  )
}

function HealthChip({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className="hidden md:flex items-center gap-1.5 text-[10px] text-muted-foreground border border-border px-2 py-0.5">
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${ok ? "bg-emerald-500" : "bg-amber-500"}`} />
      {label}
    </div>
  )
}

function AuthorityTag() {
  return (
    <Badge variant="secondary" className="text-[10px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 flex items-center gap-1">
      <Icon icon={CheckmarkCircle02Icon} className="size-3" /> AUTHORITY_SOURCE
    </Badge>
  )
}

function QuoteBlock({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-blue-500/5 border border-blue-500/20 px-2 py-1.5 flex gap-2 text-xs italic text-foreground/90">
      <Icon icon={QuoteDownIcon} className="size-3.5 text-blue-400 shrink-0 mt-0.5" />
      <span>{children}</span>
    </div>
  )
}

function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = React.useState(false)
  React.useEffect(() => setMounted(true), [])
  if (!mounted) return null
  return (
    <Button variant="ghost" size="icon" className="size-7" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
      <Icon icon={theme === "dark" ? Sun03Icon : Moon02Icon} className="size-4" />
    </Button>
  )
}

function Callout({ tone, icon, children }: { tone: "amber" | "blue" | "emerald" | "red"; icon: IconT; children: React.ReactNode }) {
  const map = {
    amber: "bg-amber-500/10 border-amber-500/30 text-amber-300",
    blue: "bg-blue-500/10 border-blue-500/30 text-blue-300",
    emerald: "bg-emerald-500/10 border-emerald-500/30 text-emerald-300",
    red: "bg-red-500/10 border-red-500/30 text-red-300",
  }
  const iconTone = { amber: "text-amber-400", blue: "text-blue-400", emerald: "text-emerald-400", red: "text-red-400" }
  return (
    <div className={`border p-3 text-sm flex gap-2.5 ${map[tone]}`}>
      <Icon icon={icon} className={`size-4 shrink-0 mt-0.5 ${iconTone[tone]}`} />
      <div>{children}</div>
    </div>
  )
}

function Spinner({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground p-6 justify-center">
      <Icon icon={SatelliteIcon} className="size-4 animate-spin" /> {label}
    </div>
  )
}

// ─── Chat View ────────────────────────────────────────────────────────────────

function ChatView({ animationsEnabled, onOpenEvidence }: {
  animationsEnabled: boolean; onOpenEvidence: (e: QueryResponse["evidence"]) => void
}) {
  const [messages, setMessages] = React.useState<Msg[]>([])
  const [busy, setBusy] = React.useState(false)
  const [queryDate, setQueryDate] = React.useState("2026-07-18")
  const bottomRef = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, busy])

  const sendMessage = async (text: string) => {
    if (!text.trim() || busy) return
    const userMsg: Msg = { id: crypto.randomUUID(), role: "user", content: text }
    setMessages((prev) => [...prev, userMsg])
    setBusy(true)
    try {
      const res = await api.query(text, queryDate)
      setMessages((prev) => [...prev, {
        id: crypto.randomUUID(), role: "assistant",
        content: res.answer.text, answer: res.answer, evidence: res.evidence,
      }])
    } catch (e) {
      setMessages((prev) => [...prev, {
        id: crypto.randomUUID(), role: "assistant", error: true,
        content: `Không gọi được backend: ${e instanceof Error ? e.message : String(e)}\n\nKiểm tra API đang chạy tại ${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}.`,
      }])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden min-h-0">
      {/* Filter bar */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-border bg-muted/20 text-xs flex-wrap shrink-0">
        <Icon icon={SlidersHorizontalIcon} className="size-3.5 text-muted-foreground" />
        <span className="text-muted-foreground font-medium">Ngày hiệu lực:</span>
        <input type="date" value={queryDate} onChange={(e) => setQueryDate(e.target.value)}
          className="bg-background border border-border px-2 py-1 text-xs outline-none focus:border-orange-500 transition-colors" />
        <Badge variant="secondary" className="text-[10px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 flex items-center gap-1">
          <Icon icon={CheckmarkCircle02Icon} className="size-3" /> Temporal pre-filter ON
        </Badge>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-6 p-6">
            <div className="text-center">
              <h2 className="text-2xl font-semibold mb-2 text-balance">Hỏi về quy định pháp lý</h2>
              <p className="text-muted-foreground text-sm max-w-md">
                Hệ thống chỉ dùng nguồn đã được phê duyệt và đang có hiệu lực tại ngày tra cứu.
              </p>
            </div>
            <div className="flex gap-2 flex-wrap justify-center max-w-xl">
              {["Hạn mức tín dụng SME hiện hành?", "Tỷ lệ nguồn vốn ngắn hạn cho vay trung dài hạn tối đa?", "Quy trình thẩm định tín dụng SME?"].map((q) => (
                <button key={q} onClick={() => sendMessage(q)}
                  className="text-xs px-3 py-1.5 border border-border hover:border-orange-500 hover:text-orange-400 transition-colors">
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl p-4 space-y-4">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} onOpenEvidence={onOpenEvidence} />
            ))}
            {busy && <Spinner label="Đang retrieve + kiểm tra tất định..." />}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <div className="p-4 shrink-0 relative">
        {animationsEnabled && (
          <div className="pointer-events-none absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-orange-500/80 to-transparent animate-border-1 opacity-50" />
        )}
        <div className="mx-auto max-w-3xl">
          <ChatInput animationsEnabled={animationsEnabled} onSend={sendMessage} disabled={busy} />
        </div>
      </div>
    </div>
  )
}

function ChatMessage({ message, onOpenEvidence }: {
  message: Msg; onOpenEvidence: (e: QueryResponse["evidence"]) => void
}) {
  const isUser = message.role === "user"
  const conflicts = message.answer?.conflict_candidates ?? []
  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div className={`w-7 h-7 flex items-center justify-center text-[11px] font-bold shrink-0 mt-0.5 ${
        isUser ? "bg-orange-500 text-white" : "bg-muted text-muted-foreground"
      }`}>
        {isUser ? "PN" : <Icon icon={AiBrain01Icon} className="size-4" />}
      </div>
      <div className={`max-w-[78%] px-4 py-3 text-sm leading-relaxed ${
        isUser ? "bg-orange-500 text-white"
          : message.error ? "bg-red-500/10 border border-red-500/30 text-red-200"
          : "bg-card border border-border"
      }`}>
        <MessageContent content={message.content} />

        {conflicts.length > 0 && (
          <div className="mt-3 space-y-1.5">
            {conflicts.map((c, i) => <ConflictRow key={i} c={c} />)}
          </div>
        )}

        {message.evidence && (message.answer?.citations.length ?? 0) > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3 pt-2 border-t border-border/50">
            {message.answer!.citations.map((c) => (
              <button key={c.source_id} onClick={() => onOpenEvidence(message.evidence!)}
                className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 bg-blue-500/10 border border-blue-500/30 text-blue-400 hover:bg-blue-500/20 transition-colors">
                <Icon icon={File02Icon} className="size-3" /> {c.document_number} · {c.heading_path.join(" ") || "—"}
              </button>
            ))}
            <AuthorityTag />
            {message.evidence.excluded_evidence.length > 0 && (
              <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 text-red-400 border border-red-500/25 bg-red-500/5">
                <Icon icon={RemoveCircleIcon} className="size-3" /> {message.evidence.excluded_evidence.length} bị loại
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function ConflictRow({ c }: { c: ConflictCandidate }) {
  return (
    <div className="border border-amber-500/30 bg-amber-500/5 px-2 py-1.5 text-[11px] text-amber-200 flex gap-2">
      <Icon icon={Alert02Icon} className="size-3.5 text-amber-400 shrink-0 mt-px" />
      <span>
        <strong>Xung đột ({c.reason}):</strong> {c.value_a} vs {c.value_b} — {c.provision_a} ↔ {c.provision_b}.
        Human review: <span className="font-semibold">{c.human_review}</span>.
      </span>
    </div>
  )
}

function MessageContent({ content }: { content: string }) {
  const lines = content.split("\n")
  return (
    <>
      {lines.map((line, i) => {
        if (line === "") return <br key={i} />
        if (line.startsWith("•") || line.startsWith("-")) return <p key={i} className="mb-1">{line}</p>
        if (/^\*[^*].*[^*]\*$/.test(line)) {
          return <p key={i} className="text-xs opacity-60 italic mt-2">{line.slice(1, -1)}</p>
        }
        const parts = line.split(/(\*\*[^*]+\*\*)/)
        return (
          <p key={i} className="mb-0.5">
            {parts.map((p, j) => (p.startsWith("**") ? <strong key={j}>{p.slice(2, -2)}</strong> : p))}
          </p>
        )
      })}
    </>
  )
}

function ChatInput({ animationsEnabled, onSend, disabled }: {
  animationsEnabled: boolean; onSend: (text: string) => void; disabled: boolean
}) {
  const [value, setValue] = React.useState("")
  const handleSend = () => {
    if (!value.trim()) return
    onSend(value)
    setValue("")
  }
  return (
    <div className="relative">
      {animationsEnabled && (
        <div className="pointer-events-none absolute -inset-[1.5px] bg-gradient-to-r from-transparent via-orange-500 to-transparent animate-border-glow opacity-60" />
      )}
      <InputGroup className="relative bg-background">
        <InputGroupTextarea
          placeholder="Hỏi về quy định pháp lý..."
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault()
              handleSend()
            }
          }}
          rows={2}
        />
        <InputGroupAddon align="block-end">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <InputGroupButton variant="ghost" size="icon-sm" className="rounded-full">
                <Icon icon={PlusSignIcon} className="size-4" />
              </InputGroupButton>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-52" onCloseAutoFocus={(e) => e.preventDefault()}>
              <DropdownMenuLabel className="text-xs text-muted-foreground">Upload tài liệu</DropdownMenuLabel>
              <DropdownMenuItem>
                <Icon icon={Upload03Icon} className="size-4" /> Thêm nguồn pháp lý (A)
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Icon icon={DocumentValidationIcon} className="size-4" /> Kiểm tra tài liệu (B)
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem>
                <Icon icon={Attachment01Icon} className="size-4" /> Đính kèm file
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <InputGroupButton size="icon-sm" variant="default" disabled={disabled}
            className="rounded-full ml-auto bg-orange-500 hover:bg-orange-600 text-white" onClick={handleSend}>
            <Icon icon={ArrowUp02Icon} className="size-4" />
          </InputGroupButton>
        </InputGroupAddon>
      </InputGroup>
    </div>
  )
}

// ─── Pipeline strip (shared) ──────────────────────────────────────────────────

function PipelineStrip({ steps, activeIndex, doneTone = "orange" }: {
  steps: string[]; activeIndex: number; doneTone?: "orange" | "emerald"
}) {
  const doneBg = doneTone === "emerald" ? "border-emerald-500 bg-emerald-600" : "border-orange-500 bg-orange-500"
  const doneText = doneTone === "emerald" ? "text-emerald-400" : "text-orange-400"
  return (
    <div className="flex items-center overflow-x-auto pb-2 gap-0">
      {steps.map((s, i) => {
        const done = i < activeIndex
        const active = i === activeIndex
        return (
          <React.Fragment key={s}>
            <div className="flex flex-col items-center gap-1 min-w-[54px]">
              <div className={`w-7 h-7 flex items-center justify-center text-xs font-bold border-2 ${
                done ? `${doneBg} text-white`
                  : active ? "border-orange-500 bg-orange-500 text-white"
                  : "border-border text-muted-foreground"
              }`}>
                {done ? <Icon icon={CheckmarkCircle02Icon} className="size-4" /> : i + 1}
              </div>
              <div className={`text-[9px] text-center leading-tight ${
                done ? doneText : active ? "text-orange-400 font-semibold" : "text-muted-foreground"
              }`}>{s}</div>
            </div>
            {i < steps.length - 1 && (
              <div className={`flex-1 h-0.5 mb-4 ${i < activeIndex ? (doneTone === "emerald" ? "bg-emerald-500/40" : "bg-orange-500/30") : "bg-border"}`} />
            )}
          </React.Fragment>
        )
      })}
    </div>
  )
}

// ─── Upload Source View (A) — document store is real ───────────────────────────

const TYPE_LABEL: Record<string, string> = {
  REGULATION: "Quy định",
  AMENDMENT: "Sửa đổi",
  INTERNAL_POLICY: "Policy nội bộ",
  DECISION: "Quyết định",
  CIRCULAR: "Thông tư",
}

function UploadSourceView() {
  const [docs, setDocs] = React.useState<DocumentRow[] | null>(null)
  const [err, setErr] = React.useState<string | null>(null)
  React.useEffect(() => {
    api.documents().then(setDocs).catch((e) => setErr(String(e)))
  }, [])
  const steps = ["Upload", "Validate", "Extract", "Parse", "LLM Extract", "Review Pkg", "Duyệt HITL", "Activate"]
  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-3xl mx-auto space-y-6">
        <Callout tone="amber" icon={Alert02Icon}>
          File upload sẽ là <strong>AUTHORITY_SOURCE_CANDIDATE</strong> — chưa được dùng làm căn cứ pháp lý cho đến khi nhân viên duyệt xong.
        </Callout>
        <PipelineStrip steps={steps} activeIndex={0} />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="border border-border bg-card p-5 space-y-4">
            <h3 className="font-semibold text-sm">Upload văn bản pháp lý</h3>
            <Dropzone icon={Upload03Icon} tone="orange" title="Kéo thả hoặc click chọn file" sub="PDF, DOCX — tối đa 25 MB" />
            <select className="w-full bg-background border border-border px-3 py-2 text-sm outline-none focus:border-orange-500">
              <option>Thông tư (CIRCULAR)</option>
              <option>Quyết định (DECISION)</option>
              <option>Văn bản sửa đổi (AMENDMENT)</option>
            </select>
            <Button className="w-full bg-orange-500 hover:bg-orange-600 text-white" disabled>
              <Icon icon={Upload03Icon} className="size-4" /> Upload & Xử lý (demo)
            </Button>
          </div>
          <div className="border border-border bg-card p-5 space-y-2">
            <h3 className="font-semibold text-sm mb-2">Kho nguồn pháp lý ({docs?.length ?? 0})</h3>
            {err && <p className="text-xs text-red-400">{err}</p>}
            {!docs && !err && <Spinner label="Đang tải documents..." />}
            {docs?.map((d) => (
              <div key={d.document_id} className="flex items-center justify-between py-2 border-b border-border text-sm last:border-0">
                <div className="min-w-0">
                  <div className="font-medium truncate">{d.document_number}</div>
                  <div className="text-[10px] text-muted-foreground">{TYPE_LABEL[d.type] ?? d.type} · {d.processing_status}</div>
                </div>
                <Badge variant="outline" className={`text-[10px] shrink-0 ${
                  d.approval_status === "APPROVED" ? "text-emerald-400 border-emerald-500/30" : "text-amber-400 border-amber-500/30"
                }`}>
                  {d.approval_status}
                </Badge>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function Dropzone({ icon, tone, title, sub }: { icon: IconT; tone: "orange" | "emerald"; title: string; sub: string }) {
  const hover = tone === "orange" ? "hover:border-orange-500 hover:text-orange-400" : "hover:border-emerald-500 hover:text-emerald-400"
  return (
    <div className={`border-2 border-dashed border-border p-8 text-center text-muted-foreground transition-colors cursor-pointer ${hover}`}>
      <Icon icon={icon} className="size-8 mx-auto mb-2" />
      <div className="text-xs font-medium">{title}</div>
      <div className="text-[11px] mt-1">{sub}</div>
    </div>
  )
}

// ─── Review Inbox View (A) — review queue is real ──────────────────────────────

function ReviewInboxView() {
  const [tasks, setTasks] = React.useState<unknown[] | null>(null)
  const [err, setErr] = React.useState<string | null>(null)
  React.useEffect(() => {
    api.reviewTasks().then(setTasks).catch((e) => setErr(String(e)))
  }, [])
  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-2xl mx-auto space-y-4">
        <Callout tone="blue" icon={InboxIcon}>
          Chỉ ChangeEvent đang <strong>PENDING</strong> mới hiện ở đây. Activate khi còn critical review chưa duyệt → <strong>HTTP 409 REVIEW_NOT_COMPLETED</strong>.
        </Callout>
        {err && <p className="text-xs text-red-400">{err}</p>}
        {!tasks && !err && <Spinner label="Đang tải review queue..." />}
        {tasks && tasks.length === 0 && (
          <div className="border border-border bg-card p-8 text-center text-sm text-muted-foreground">
            <Icon icon={CheckmarkCircle02Icon} className="size-8 mx-auto mb-2 text-emerald-400" />
            Không có thay đổi nào chờ duyệt. Corpus demo đã được APPROVED + ACTIVE.
          </div>
        )}
        {tasks && tasks.length > 0 && (
          <pre className="border border-border bg-card p-4 text-[11px] overflow-x-auto">{JSON.stringify(tasks, null, 2)}</pre>
        )}
      </div>
    </div>
  )
}

// ─── Impact View (A) — real impact report ──────────────────────────────────────

function ImpactView() {
  const DOC = "doc-qd02-2026"
  const [rep, setRep] = React.useState<ImpactReport | null>(null)
  const [err, setErr] = React.useState<string | null>(null)
  React.useEffect(() => {
    api.impactReport(DOC).then(setRep).catch((e) => setErr(String(e)))
  }, [])
  if (err) return <div className="p-6"><Callout tone="red" icon={Alert02Icon}>{err}</Callout></div>
  if (!rep) return <Spinner label="Đang dựng Regulatory Impact Report..." />
  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-3xl mx-auto border border-border bg-card p-5 space-y-5">
        <div>
          <h3 className="font-semibold text-sm">Regulatory Impact Report — {rep.document_number}</h3>
          <p className="text-xs text-muted-foreground mt-1">{rep.executive_summary}</p>
        </div>

        {rep.changes.map((c) => (
          <div key={c.change_event_id} className="grid grid-cols-2 gap-3">
            <div className="bg-red-500/10 border border-red-500/20 p-3 text-sm">
              <div className="text-[10px] font-bold text-red-400 uppercase mb-2">Trước · {c.target_locator}</div>
              {c.before_text}
            </div>
            <div className="bg-emerald-500/10 border border-emerald-500/20 p-3 text-sm">
              <div className="text-[10px] font-bold text-emerald-400 uppercase mb-2">Sau · hiệu lực {c.effective_date}</div>
              {c.after_text}
            </div>
          </div>
        ))}

        <div>
          <div className="text-xs font-bold mb-3 text-muted-foreground uppercase tracking-wider">
            Policy nội bộ bị ảnh hưởng · max: <span className={rep.max_severity === "HIGH" ? "text-red-400" : "text-amber-400"}>{rep.max_severity}</span>
          </div>
          <div className="border border-border divide-y divide-border">
            {rep.impacted_policies.map((p) => (
              <div key={p.artifact_id} className="flex items-center gap-3 p-2.5 text-sm">
                <span className="font-medium w-40 shrink-0 truncate">{p.title}</span>
                <span className="flex-1 text-muted-foreground text-xs">
                  {p.reason}: {p.internal_policy_value} → {p.regulation_value}
                </span>
                <span className={`text-xs font-bold ${p.severity === "HIGH" ? "text-red-400" : "text-amber-400"}`}>{p.severity}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Upload Check View (B) — runs a real compliance check ──────────────────────

const SAMPLE_TARGET = `Hạn mức tín dụng SME tối đa là 500 triệu đồng, thời hạn 12 tháng.
Theo 22/2019/TT-NHNN, tỷ lệ tối đa nguồn vốn ngắn hạn được sử dụng để cho vay trung hạn và dài hạn là 34%.
Đơn vị phải gửi báo cáo thống kê chậm nhất ngày 10 hằng tháng.`

function UploadCheckView({ onReport }: { onReport: (r: ComplianceReport) => void }) {
  const [text, setText] = React.useState(SAMPLE_TARGET)
  const [reviewDate, setReviewDate] = React.useState("2026-07-18")
  const [busy, setBusy] = React.useState(false)
  const [err, setErr] = React.useState<string | null>(null)
  const steps = ["Upload", "Extract", "Claims", "Retrieve", "Compare", "Report"]

  const run = async () => {
    setBusy(true); setErr(null)
    try {
      const { check_id } = await api.createCheck(text, reviewDate)
      const report = await api.checkReport(check_id)
      onReport(report)
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-3xl mx-auto space-y-6">
        <Callout tone="blue" icon={SquareLock01Icon}>
          File này là <strong>REVIEW_TARGET</strong> — chỉ dùng để kiểm tra, <strong>không được</strong> thêm vào legal knowledge base.
        </Callout>
        <PipelineStrip steps={steps} activeIndex={busy ? 3 : 0} doneTone="emerald" />
        <div className="border border-border bg-card p-5 space-y-4">
          <h3 className="font-semibold text-sm">Nội dung tài liệu cần kiểm tra</h3>
          <textarea value={text} onChange={(e) => setText(e.target.value)} rows={7}
            className="w-full bg-background border border-border px-3 py-2 text-sm outline-none focus:border-emerald-500 font-mono leading-relaxed" />
          <div className="flex items-end gap-3 flex-wrap">
            <div>
              <label className="text-xs font-medium text-muted-foreground block mb-1">Ngày áp dụng quy định</label>
              <input type="date" value={reviewDate} onChange={(e) => setReviewDate(e.target.value)}
                className="bg-background border border-border px-3 py-2 text-sm outline-none focus:border-emerald-500" />
            </div>
            <Button className="bg-emerald-600 hover:bg-emerald-700 text-white" onClick={run} disabled={busy}>
              <Icon icon={CheckmarkCircle02Icon} className="size-4" /> {busy ? "Đang kiểm tra..." : "Kiểm tra tuân thủ"}
            </Button>
          </div>
          <div className="text-[11px] text-emerald-300 bg-emerald-500/10 px-2 py-1.5 flex items-center gap-1.5">
            <Icon icon={CheckmarkCircle02Icon} className="size-3.5 text-emerald-400 shrink-0" />
            Chỉ retrieve AUTHORITY_SOURCE APPROVED + ACTIVE tại ngày review. LLM không quyết định status.
          </div>
          {err && <Callout tone="red" icon={Alert02Icon}>{err}</Callout>}
        </div>
      </div>
    </div>
  )
}

// ─── Compliance Report View (B) — real report ──────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const m = statusMeta(status)
  const s = STATUS_STYLE[m.kind]
  return (
    <Badge variant="outline" className={`text-[10px] shrink-0 flex items-center gap-1 ${s.text} ${s.ring}`}>
      <Icon icon={s.icon} className="size-3" /> {m.label}
    </Badge>
  )
}

function ComplianceReportView({ report, onGoUpload }: { report: ComplianceReport | null; onGoUpload: () => void }) {
  if (!report) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="text-center space-y-3 max-w-sm">
          <Icon icon={DocumentValidationIcon} className="size-10 mx-auto text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Chưa có báo cáo. Chạy một lượt kiểm tra ở tab <strong>Kiểm tra tài liệu</strong>.</p>
          <Button variant="outline" size="sm" onClick={onGoUpload}>
            Đến kiểm tra tài liệu <Icon icon={ArrowRight02Icon} className="size-3.5" />
          </Button>
        </div>
      </div>
    )
  }

  const s = report.summary
  const rows = [
    { label: "Compliant", n: s.compliant, icon: CheckmarkCircle02Icon, c: "text-emerald-400" },
    { label: "Non-compliant", n: s.non_compliant, icon: CancelCircleIcon, c: "text-red-400" },
    { label: "Outdated ref", n: s.outdated_reference, icon: Alert02Icon, c: "text-amber-400" },
    { label: "Missing", n: s.missing_evidence, icon: RemoveCircleIcon, c: "text-muted-foreground" },
    { label: "Cần review", n: s.needs_human_review, icon: Search01Icon, c: "text-muted-foreground" },
  ]

  return (
    <div className="flex flex-1 overflow-hidden min-h-0">
      <div className="flex-1 overflow-y-auto p-5 min-w-0">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
          <div>
            <div className="font-semibold">Compliance Review Report</div>
            <div className="text-xs text-muted-foreground mt-0.5 flex items-center gap-2 flex-wrap">
              {report.report_id} · Review date: {report.review_date}
              <Badge variant="outline" className="text-[10px] text-blue-400 border-blue-500/30">REVIEW_TARGET</Badge>
              <Badge variant="outline" className="text-[10px] text-amber-400 border-amber-500/30">{report.status}</Badge>
            </div>
          </div>
        </div>

        <div className="space-y-3 max-w-2xl">
          {report.assessments.map((a) => <AssessmentCard key={a.claim_id} a={a} />)}
        </div>
      </div>

      {/* Summary */}
      <div className="w-52 shrink-0 border-l border-border p-4 overflow-y-auto">
        <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-4">Tổng kết ({s.total_claims})</div>
        {rows.map((row) => (
          <div key={row.label} className="flex justify-between items-center py-1.5 border-b border-border/50 text-xs last:border-0">
            <span className="text-muted-foreground text-[11px] flex items-center gap-1.5">
              <Icon icon={row.icon} className={`size-3.5 ${row.c}`} /> {row.label}
            </span>
            <span className={`font-bold ${row.c}`}>{row.n}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function AssessmentCard({ a }: { a: Assessment }) {
  const ev = a.valid_evidence[0]
  return (
    <div className="border border-border bg-card overflow-hidden">
      <div className="flex items-start justify-between gap-3 p-3">
        <div className="min-w-0">
          <div className="text-[10px] text-muted-foreground mb-1">Claim {a.claim_id.slice(0, 12)}</div>
          <div className="text-sm">&ldquo;{a.source_text}&rdquo;</div>
        </div>
        <StatusBadge status={a.status} />
      </div>
      {ev ? (
        <div className="px-3 pb-3 space-y-1.5">
          <div className="bg-blue-500/5 border border-blue-500/20 p-2 text-xs space-y-1.5">
            <div className="text-[11px] font-semibold text-blue-400 flex items-center gap-2 flex-wrap">
              <span className="inline-flex items-center gap-1">
                <Icon icon={File02Icon} className="size-3" /> {ev.document_number} · {ev.heading_path.join(" ") || "—"}
              </span>
              <AuthorityTag />
            </div>
            <div className="italic text-foreground/80">&ldquo;{ev.content}&rdquo;</div>
            <div className="text-[10px] text-muted-foreground">valid_from: {ev.valid_from} · valid_to: {ev.valid_to_exclusive ?? "∞"}</div>
          </div>
          {a.excluded_evidence.length > 0 && (
            <MetaRow icon={RemoveCircleIcon} tone="red" label="Đã loại">
              {a.excluded_evidence.map((x) => `${x.version_id} (${x.reason})`).join(", ")}
            </MetaRow>
          )}
          {a.explanation && <MetaRow icon={Idea01Icon} tone="muted" label="">{a.explanation}</MetaRow>}
          {a.recommendation && <MetaRow icon={Wrench01Icon} tone="amber" label="Đề xuất">{a.recommendation}</MetaRow>}
        </div>
      ) : (
        <div className="px-3 pb-3">
          <div className="text-xs text-muted-foreground bg-muted/30 p-2">
            {a.explanation ?? "Không tìm thấy căn cứ trong kho đã duyệt tại ngày review."}
          </div>
        </div>
      )}
      <div className="flex items-center gap-2 px-3 pb-2 text-[11px] border-t border-border/50 pt-2">
        <span className="text-muted-foreground">Confidence: {a.confidence}</span>
        <span className="text-muted-foreground">· review: {a.review_status}</span>
      </div>
    </div>
  )
}

function MetaRow({ icon, tone, label, children }: {
  icon: IconT; tone: "red" | "amber" | "muted"; label: string; children: React.ReactNode
}) {
  const map = {
    red: "text-red-300 bg-red-500/5 border border-red-500/20",
    amber: "text-amber-300 bg-amber-500/5 border border-amber-500/20",
    muted: "text-muted-foreground bg-muted/30",
  }
  const iconTone = { red: "text-red-400", amber: "text-amber-400", muted: "text-muted-foreground" }
  return (
    <div className={`text-[11px] p-1.5 flex gap-1.5 ${map[tone]}`}>
      <Icon icon={icon} className={`size-3.5 shrink-0 mt-px ${iconTone[tone]}`} />
      <span>{label && <strong>{label}: </strong>}{children}</span>
    </div>
  )
}

// ─── Health View — real /health/details ────────────────────────────────────────

function HealthView({ health }: { health: HealthDetails | null }) {
  if (!health) return <Spinner label="Đang tải health..." />
  const services = [
    { icon: Database01Icon, name: "PostgreSQL", detail: "metadata, trust, versions — source of truth", value: health.postgres, ok: health.postgres === "connected" },
    { icon: Search01Icon, name: "OpenSearch", detail: "BM25 + vector index", value: health.opensearch, ok: health.opensearch === "connected" },
    { icon: ShareKnowledgeIcon, name: "Neo4j", detail: "graph lineage · impact paths", value: health.neo4j, ok: health.neo4j === "connected" },
    { icon: AiBrain01Icon, name: "LLM", detail: "prose generation only (never decides status)", value: health.llm, ok: health.llm !== "mock" },
    { icon: FlashIcon, name: "Embedding", detail: "BAAI/bge-m3 · dim=1024", value: health.embedding, ok: health.embedding !== "hash_fallback" },
  ]
  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-3xl mx-auto space-y-6">
        {health.demo_mode && (
          <Callout tone="amber" icon={Alert02Icon}>
            DEMO_MODE = true — OpenSearch/Neo4j/LLM đang dùng in-memory fallback. Kết quả không có giá trị benchmark.
          </Callout>
        )}
        <div className="border border-border divide-y divide-border">
          {services.map((s) => (
            <div key={s.name} className="flex items-center gap-3 px-4 py-2.5">
              <Icon icon={s.icon} className="size-4 text-muted-foreground shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-xs font-semibold">{s.name}</div>
                <div className="text-[10px] text-muted-foreground leading-snug">{s.detail}</div>
              </div>
              <span className="text-[10px] text-muted-foreground mr-2 hidden sm:block">{s.value}</span>
              <span className={`text-[10px] font-bold shrink-0 flex items-center gap-1.5 ${s.ok ? "text-emerald-400" : "text-amber-400"}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${s.ok ? "bg-emerald-500" : "bg-amber-500"}`} />
                {s.ok ? "OK" : "FALLBACK"}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export { ComplianceRAG as ComplianceRAGBlock }
