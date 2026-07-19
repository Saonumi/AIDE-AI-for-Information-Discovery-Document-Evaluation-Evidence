"use client"

// MÃ n Ä‘Äƒng nháº­p ná»™i bá»™ â€” backend /login cáº¥p Bearer token (EMPLOYEE | USER).
// ToÃ n bá»™ API phÃ­a sau Ä‘á»u yÃªu cáº§u token nÃªn shell gate á»Ÿ Ä‘Ã¢y trÆ°á»›c khi vÃ o app.

import * as React from "react"
import { Button } from "@/components/ui/button"
import { login, type Session } from "@/lib/api"
import dragonArt from "@/lib/dragonArt"

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
    <div className="relative flex h-screen w-full items-center justify-center overflow-hidden bg-background text-foreground p-4">
      {/* Ná»n ASCII rá»“ng â€” mÆ°á»£n tá»« trang About Us cá»§a agriflow-core (dragonArt). Má»,
          khÃ´ng tÆ°Æ¡ng tÃ¡c, khÃ´ng chá»n Ä‘Æ°á»£c; Ã´ Ä‘Äƒng nháº­p ná»•i lÃªn trÃªn (z-10). */}
      <div aria-hidden className="pointer-events-none select-none absolute inset-0 flex items-center justify-center overflow-hidden">
        <pre className="font-mono leading-none text-[0.2rem] sm:text-[0.3rem] md:text-[0.4rem] text-orange-500/40 dark:text-orange-400/35">
          {dragonArt}
        </pre>
      </div>

      <div className="relative z-10 w-full max-w-sm border border-border bg-card/95 backdrop-blur-sm shadow-xl">
        <div className="p-6 border-b border-border relative">
          <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-orange-500 to-transparent opacity-60" />
          <div className="text-[9px] font-bold text-muted-foreground tracking-widest uppercase">
            SHB Â· VAIC2026
          </div>
          <h1 className="text-lg font-semibold mt-1">AIDE</h1>
          <p className="text-[10px] text-muted-foreground/80 mt-0.5 leading-snug">
            (AI for Information Discovery, Document Evaluation &amp; Evidence)
          </p>
          <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
            Trá»£ lÃ½ phÃ¡p cháº¿ &amp; tuÃ¢n thá»§ â€” Ä‘Äƒng nháº­p báº±ng tÃ i khoáº£n ná»™i bá»™ do quáº£n trá»‹ viÃªn cáº¥p.
          </p>
        </div>
        <form onSubmit={submit} className="p-6 space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="login-username" className="text-xs font-medium">TÃªn Ä‘Äƒng nháº­p</label>
            <input id="login-username" className={field} autoComplete="username" autoFocus
                   value={username} onChange={(e) => setUsername(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <label htmlFor="login-password" className="text-xs font-medium">Máº­t kháº©u</label>
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
            {busy ? "Äang Ä‘Äƒng nháº­pâ€¦" : "ÄÄƒng nháº­p"}
          </Button>

        </form>
      </div>
    </div>
  )
}
