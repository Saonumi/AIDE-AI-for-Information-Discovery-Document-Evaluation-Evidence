"use client"

// Màn đăng nhập nội bộ — backend /login cấp Bearer token (EMPLOYEE | USER).
// Toàn bộ API phía sau đều yêu cầu token nên shell gate ở đây trước khi vào app.

import * as React from "react"
import { Button } from "@/components/ui/button"
import { login, type Session } from "@/lib/api"

export function LoginView({ onLogin }: { onLogin: (s: Session) => void }) {
  const [username, setUsername] = React.useState("")
  const [password, setPassword] = React.useState("")
  const [err, setErr] = React.useState<string | null>(null)
  const [busy, setBusy] = React.useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (busy) return
    setBusy(true); setErr(null)
    try {
      onLogin(await login(username.trim(), password))
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : String(ex))
    } finally {
      setBusy(false)
    }
  }

  const field =
    "w-full border border-border bg-background px-3 py-2 text-sm outline-none focus:border-orange-500 transition-colors"

  return (
    <div className="flex h-screen w-full items-center justify-center bg-background text-foreground p-4">
      <div className="w-full max-w-sm border border-border bg-card">
        <div className="p-6 border-b border-border relative">
          <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-orange-500 to-transparent opacity-60" />
          <div className="text-[9px] font-bold text-muted-foreground tracking-widest uppercase">
            SHB · VAIC2026
          </div>
          <h1 className="text-lg font-semibold mt-1">AIDE</h1>
          <p className="text-[10px] text-muted-foreground/80 mt-0.5 leading-snug">
            (AI for Information Discovery, Document Evaluation &amp; Evidence)
          </p>
          <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
            Trợ lý pháp chế &amp; tuân thủ — đăng nhập bằng tài khoản nội bộ do quản trị viên cấp.
          </p>
        </div>
        <form onSubmit={submit} className="p-6 space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="login-username" className="text-xs font-medium">Tên đăng nhập</label>
            <input id="login-username" className={field} autoComplete="username" autoFocus
                   value={username} onChange={(e) => setUsername(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <label htmlFor="login-password" className="text-xs font-medium">Mật khẩu</label>
            <input id="login-password" type="password" className={field} autoComplete="current-password"
                   value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          {err && (
            <p role="alert" className="text-xs text-red-500 border border-red-500/30 bg-red-500/10 px-3 py-2">
              {err}
            </p>
          )}
          <Button type="submit" className="w-full bg-orange-500 hover:bg-orange-600 text-white"
                  disabled={busy || !username.trim() || !password}>
            {busy ? "Đang đăng nhập…" : "Đăng nhập"}
          </Button>

        </form>
      </div>
    </div>
  )
}
