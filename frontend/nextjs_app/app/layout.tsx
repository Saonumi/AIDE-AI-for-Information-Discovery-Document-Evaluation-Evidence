import type React from "react"
import type { Metadata } from "next"
import { JetBrains_Mono } from "next/font/google"
import "./globals.css"
import { ThemeProvider } from "@/components/theme-provider"

const fontSans = JetBrains_Mono({ subsets: ["latin"], variable: "--font-sans" })

export const metadata: Metadata = {
  title: "Compliance RAG Platform — SHB VAIC2026",
  description: "Temporal Regulatory RAG for SHB bank",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className={fontSans.variable} suppressHydrationWarning>
      <body className="antialiased">
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false} storageKey="chatgpt-theme">
          {children}
        </ThemeProvider>
      </body>
    </html>
  )
}
