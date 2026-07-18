"use client"

// AIDE shell (spec §1, §9) — CHỈ hai tab: Add Source và RAG.
//   Add Source   xây + xác minh kho quy định (upload → review → activate)
//   RAG          tra cứu quy định · nhận xét tài liệu (segmented control bên trong)
// Không có tab riêng cho Review Queue / Compliance Report / Impact / Batch —
// tất cả nằm trong ngữ cảnh của hai tab trên.

import * as React from "react"
import { Button } from "@/components/ui/button"
import { TooltipProvider } from "@/components/ui/tooltip"
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { HugeiconsIcon } from "@hugeicons/react"
import { Moon02Icon, Sun03Icon, ComputerIcon, Logout01Icon } from "@hugeicons/core-free-icons"
import { useTheme } from "@/components/theme-provider"
import { getSession, logout, type Session } from "@/lib/api"
import { LoginView } from "@/components/login-view"
import { AddSourceTab } from "@/components/add-source"
import { RagTab } from "@/components/rag-tab"

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type IconT = any

function Icon({ icon, className }: { icon: IconT; className?: string }) {
  return <HugeiconsIcon icon={icon} strokeWidth={1.8} className={className ?? "size-4"} />
}

type Tab = "add-source" | "rag"

const TABS: { id: Tab; label: string; hint: string }[] = [
  { id: "add-source", label: "Add Source", hint: "Bổ sung & xác minh nguồn pháp lý" },
  { id: "rag", label: "RAG", hint: "Tra cứu quy định · Nhận xét tài liệu" },
]

// Vai trò backend (EMPLOYEE/COMPLIANCE_OFFICER) → nhãn tiếng Việt
const ROLE_LABEL: Record<string, string> = {
  EMPLOYEE: "Chuyên viên tuân thủ",
  COMPLIANCE_OFFICER: "Chuyên viên tuân thủ",
}

export function ComplianceRAG() {
  const [session, setSession] = React.useState<Session | null>(null)
  const [ready, setReady] = React.useState(false)
  const [tab, setTab] = React.useState<Tab>("add-source")

  React.useEffect(() => {
    setSession(getSession())
    setReady(true)
  }, [])

  if (!ready) return null
  if (!session) return <LoginView onLogin={setSession} />

  return (
    <TooltipProvider>
      <div className="flex h-screen w-full flex-col overflow-hidden bg-background text-foreground">
        {/* Top bar: identity · hai tab · session (spec §1) */}
        <header className="flex items-center gap-4 px-4 h-14 shrink-0 border-b border-border relative">
          <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-orange-500 to-transparent opacity-50" />

          <div className="leading-none shrink-0">
            <div className="text-[9px] font-bold text-muted-foreground tracking-widest uppercase">SHB · VAIC2026</div>
            <div className="text-sm font-semibold mt-0.5">AIDE</div>
          </div>

          <nav className="flex items-center gap-1 self-stretch" aria-label="Điều hướng chính">
            {TABS.map((t) => (
              <button key={t.id} onClick={() => setTab(t.id)} title={t.hint}
                aria-current={tab === t.id ? "page" : undefined}
                className={`px-3 text-sm font-medium border-b-2 transition-colors ${
                  tab === t.id
                    ? "border-orange-500 text-foreground"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                }`}>
                {t.label}
              </button>
            ))}
          </nav>

          <div className="flex items-center gap-2 ml-auto shrink-0">
            <div className="text-right hidden sm:block leading-none">
              <div className="text-xs font-medium">{session.username}</div>
              <div className="text-[10px] text-muted-foreground mt-0.5">{ROLE_LABEL[session.role] ?? session.role}</div>
            </div>
            <ThemeToggle />
            <Button variant="ghost" size="icon" className="size-8" title="Đăng xuất"
                    onClick={() => { logout(); setSession(null) }}>
              <Icon icon={Logout01Icon} className="size-4" />
            </Button>
          </div>
        </header>

        {/* Nội dung tab — cả hai luôn mounted để giữ state khi chuyển tab */}
        <main className="flex flex-1 flex-col overflow-hidden min-h-0">
          <div className={tab === "add-source" ? "flex flex-1 flex-col min-h-0" : "hidden"}>
            <AddSourceTab />
          </div>
          <div className={tab === "rag" ? "flex flex-1 flex-col min-h-0" : "hidden"}>
            <RagTab />
          </div>
        </main>
      </div>
    </TooltipProvider>
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
        <Button variant="ghost" size="icon" className="size-8" title={`Giao diện: ${current.label}`}>
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

export { ComplianceRAG as ComplianceRAGBlock }
