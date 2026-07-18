"use client"

import * as React from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { TooltipProvider } from "@/components/ui/tooltip"
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { HugeiconsIcon } from "@hugeicons/react"
import {
  ArrowDown01Icon, SparklesIcon, Upload03Icon, InboxIcon,
  DocumentValidationIcon, CheckmarkCircle02Icon, Alert02Icon,
  SatelliteIcon, Moon02Icon, Sun03Icon, ComputerIcon, Logout01Icon,
} from "@hugeicons/core-free-icons"
import { useTheme } from "@/components/theme-provider"
import { api, getSession, logout, type Session, type DocumentRow } from "@/lib/api"
import { AskRegulationsView, DocumentReviewView } from "@/components/mode-chat"
import { LoginView } from "@/components/login-view"

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type IconT = any

function Icon({ icon, className }: { icon: IconT; className?: string }) {
  return <HugeiconsIcon icon={icon} strokeWidth={1.8} className={className ?? "size-4"} />
}

// ─── Types & nhãn tiếng Việt ─────────────────────────────────────────────────

type View = "chat" | "upload-a" | "review" | "upload-b"

// Vai trò backend (USER/EMPLOYEE) → nhãn tiếng Việt
const ROLE_LABEL: Record<string, string> = {
  EMPLOYEE: "Chuyên viên tuân thủ",
  USER: "Nhân viên tra cứu",
}

const VIEW_LABELS: Record<View, string> = {
  chat: "Hỏi đáp & Tra cứu",
  "upload-a": "Thêm văn bản pháp lý",
  review: "Duyệt thay đổi",
  "upload-b": "Kiểm tra tài liệu",
}

// ─── Main ─────────────────────────────────────────────────────────────────────

export function ComplianceRAG() {
  const [isSidebarOpen, setIsSidebarOpen] = React.useState(true)
  const [animationsEnabled, setAnimationsEnabled] = React.useState(true)
  const [currentView, setCurrentView] = React.useState<View>("chat")
  const [session, setSession] = React.useState<Session | null>(null)
  const [authReady, setAuthReady] = React.useState(false)

  React.useEffect(() => {
    const stored = localStorage.getItem("compliance-animations")
    if (stored !== null) setAnimationsEnabled(stored === "true")
    setSession(getSession())
    setAuthReady(true)
  }, [])

  const toggleAnimations = () => {
    const next = !animationsEnabled
    setAnimationsEnabled(next)
    localStorage.setItem("compliance-animations", String(next))
  }

  const handleLogout = () => {
    logout()
    setSession(null)
  }

  const nav = (view: View) => setCurrentView(view)

  if (!authReady) return null
  if (!session) return <LoginView onLogin={setSession} />

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
                      AIDE
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

                <SectionLabel color="bg-blue-500" text="Nguồn pháp lý" toneClass="text-blue-400" />
                <NavItem icon={Upload03Icon} label="Thêm văn bản" active={currentView === "upload-a"} onClick={() => nav("upload-a")} />
                <NavItem icon={InboxIcon} label="Duyệt thay đổi" active={currentView === "review"} onClick={() => nav("review")} />

                <SectionLabel color="bg-emerald-500" text="Kiểm tra tuân thủ" toneClass="text-emerald-400" />
                <NavItem icon={DocumentValidationIcon} label="Kiểm tra tài liệu" active={currentView === "upload-b"} onClick={() => nav("upload-b")} />
              </div>

              {/* User */}
              <div className="p-4 shrink-0 relative">
                {animationsEnabled && (
                  <div className="pointer-events-none absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-orange-400 to-transparent animate-border-3 opacity-30" />
                )}
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 bg-blue-950 border border-blue-800 flex items-center justify-center text-[11px] font-bold text-blue-300 shrink-0 uppercase">
                    {session.username.slice(0, 2)}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="text-xs font-medium truncate">{session.username}</div>
                    <div className="text-[10px] text-muted-foreground truncate">{ROLE_LABEL[session.role] ?? session.role}</div>
                  </div>
                  <Button variant="ghost" size="icon" className="size-7 shrink-0" title="Đăng xuất" onClick={handleLogout}>
                    <Icon icon={Logout01Icon} className="size-4" />
                  </Button>
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
              <Button variant="ghost" size="icon" className="size-7" onClick={toggleAnimations} title="Bật/tắt hiệu ứng">
                <Icon icon={SparklesIcon} className={`size-4 ${animationsEnabled ? "text-orange-500" : "opacity-40"}`} />
              </Button>
              <ThemeToggle />
            </div>
          </div>

          {/* View */}
          {currentView === "chat" && <AskRegulationsView />}
          {currentView === "upload-a" && <UploadSourceView />}
          {currentView === "review" && <ReviewInboxView />}
          {currentView === "upload-b" && <DocumentReviewView />}
        </div>

      </div>
    </TooltipProvider>
  )
}

// ─── Shared micro-components ──────────────────────────────────────────────────

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

const THEME_OPTIONS = [
  { value: "light", label: "Sáng", icon: Sun03Icon },
  { value: "dark", label: "Tối", icon: Moon02Icon },
  { value: "system", label: "Theo hệ thống", icon: ComputerIcon },
]

function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = React.useState(false)
  React.useEffect(() => setMounted(true), [])
  if (!mounted) return null
  const current = THEME_OPTIONS.find((o) => o.value === theme) ?? THEME_OPTIONS[0]
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="size-7" title={`Giao diện: ${current.label}`}>
          <Icon icon={current.icon} className="size-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-44">
        <DropdownMenuLabel className="text-xs text-muted-foreground">Giao diện</DropdownMenuLabel>
        {THEME_OPTIONS.map((o) => (
          <DropdownMenuItem key={o.value} onClick={() => setTheme(o.value)}
            className={theme === o.value ? "bg-secondary" : ""}>
            <Icon icon={o.icon} className="size-4" /> {o.label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
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
  INTERNAL_POLICY: "Chính sách nội bộ",
  DECISION: "Quyết định",
  CIRCULAR: "Thông tư",
}

// ProcessingStatus / ApprovalStatus backend → nhãn tiếng Việt (fallback: giá trị gốc)
const PROCESS_LABEL: Record<string, string> = {
  RECEIVED: "Đã nhận",
  PROCESSING: "Đang xử lý",
  PARSED: "Đã phân tách",
  EXTRACTED: "Đã trích xuất",
  ENRICHED: "Đã bổ sung",
  INDEXED: "Đã lập chỉ mục",
  REVIEW_REQUIRED: "Chờ duyệt",
  INDEX_SYNC_PENDING: "Chờ đồng bộ",
  ACTIVE: "Đang hiệu lực",
  QUARANTINED: "Cách ly",
  FAILED: "Lỗi",
  EXTRACTION_FAILED: "Lỗi trích xuất",
  PARSING_FAILED: "Lỗi phân tách",
  REJECTED: "Bị từ chối",
  ARCHIVED: "Lưu trữ",
}
const APPROVAL_LABEL: Record<string, string> = {
  PENDING: "Chờ duyệt",
  APPROVED: "Đã duyệt",
  REJECTED: "Từ chối",
  ARCHIVED: "Lưu trữ",
}

function UploadSourceView() {
  const [docs, setDocs] = React.useState<DocumentRow[] | null>(null)
  const [err, setErr] = React.useState<string | null>(null)
  React.useEffect(() => {
    api.documents().then(setDocs).catch((e) => setErr(String(e)))
  }, [])
  const steps = ["Tải lên", "Kiểm tra", "Phân tách", "Trích xuất", "AI trích xuất", "Gói duyệt", "Người duyệt", "Kích hoạt"]
  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-3xl mx-auto space-y-6">
        <Callout tone="amber" icon={Alert02Icon}>
          Tài liệu tải lên chỉ là <strong>nguồn chờ duyệt</strong> — chưa được dùng làm căn cứ pháp lý cho đến khi nhân viên duyệt xong.
        </Callout>
        <PipelineStrip steps={steps} activeIndex={0} />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="border border-border bg-card p-5 space-y-4">
            <h3 className="font-semibold text-sm">Tải lên văn bản pháp lý</h3>
            <Dropzone icon={Upload03Icon} tone="orange" title="Kéo thả hoặc bấm để chọn tệp" sub="PDF, DOCX — tối đa 25 MB" />
            <select className="w-full bg-background border border-border px-3 py-2 text-sm outline-none focus:border-orange-500">
              <option>Thông tư</option>
              <option>Quyết định</option>
              <option>Văn bản sửa đổi</option>
            </select>
            <Button className="w-full bg-orange-500 hover:bg-orange-600 text-white" disabled>
              <Icon icon={Upload03Icon} className="size-4" /> Tải lên & xử lý (demo)
            </Button>
          </div>
          <div className="border border-border bg-card p-5 space-y-2">
            <h3 className="font-semibold text-sm mb-2">Kho nguồn pháp lý ({docs?.length ?? 0})</h3>
            {err && <p className="text-xs text-red-400">{err}</p>}
            {!docs && !err && <Spinner label="Đang tải danh sách văn bản..." />}
            {docs?.map((d) => (
              <div key={d.document_id} className="flex items-center justify-between py-2 border-b border-border text-sm last:border-0">
                <div className="min-w-0">
                  <div className="font-medium truncate">{d.document_number}</div>
                  <div className="text-[10px] text-muted-foreground">{TYPE_LABEL[d.type] ?? d.type} · {PROCESS_LABEL[d.processing_status] ?? d.processing_status}</div>
                </div>
                <Badge variant="outline" className={`text-[10px] shrink-0 ${
                  d.approval_status === "APPROVED" ? "text-emerald-400 border-emerald-500/30" : "text-amber-400 border-amber-500/30"
                }`}>
                  {APPROVAL_LABEL[d.approval_status] ?? d.approval_status}
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
          Chỉ các thay đổi <strong>đang chờ duyệt</strong> hiển thị ở đây. Không thể kích hoạt văn bản khi còn mục quan trọng chưa được duyệt.
        </Callout>
        {err && <p className="text-xs text-red-400">{err}</p>}
        {!tasks && !err && <Spinner label="Đang tải danh sách chờ duyệt..." />}
        {tasks && tasks.length === 0 && (
          <div className="border border-border bg-card p-8 text-center text-sm text-muted-foreground">
            <Icon icon={CheckmarkCircle02Icon} className="size-8 mx-auto mb-2 text-emerald-400" />
            Không có thay đổi nào chờ duyệt. Kho văn bản demo đã được duyệt và đang hiệu lực.
          </div>
        )}
        {tasks && tasks.length > 0 && (
          <pre className="border border-border bg-card p-4 text-[11px] overflow-x-auto">{JSON.stringify(tasks, null, 2)}</pre>
        )}
      </div>
    </div>
  )
}

export { ComplianceRAG as ComplianceRAGBlock }
