import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'VAIC2026 — Compliance Knowledge & Document Review Platform',
  description:
    'Nền tảng giúp cán bộ Pháp chế/Tuân thủ xác minh nguồn pháp lý và kiểm tra mức độ phù hợp của tài liệu nội bộ.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  )
}
