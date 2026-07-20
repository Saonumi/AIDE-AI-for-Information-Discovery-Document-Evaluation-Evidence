import type React from "react"
import type { Metadata } from "next"
import { JetBrains_Mono } from "next/font/google"
import "./globals.css"
import { ThemeProvider } from "@/components/theme-provider"

const fontSans = JetBrains_Mono({ subsets: ["latin", "latin-ext"], variable: "--font-sans" })

export const metadata: Metadata = {
  title: "AIDE (AI for Information Discovery, Document Evaluation & Evidence) — Trợ lý Tuân thủ SHB",
  description: "AIDE — Hệ thống hỏi đáp và kiểm tra tuân thủ quy định pháp lý nội bộ SHB",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="vi" className={fontSans.variable} suppressHydrationWarning>
      <head><meta charSet="utf-8" /></head>
      <body className="antialiased">
        <ThemeProvider attribute="class" defaultTheme="light" enableSystem storageKey="shb-theme">
          {children}
        </ThemeProvider>
      </body>
    </html>
  )
}
