import Link from 'next/link'

/**
 * Landing page — spec §10.1: "hai hành động rõ ràng".
 *
 * The two cards are the whole product: build a verified legal store (A), then
 * use that store to review a document (B). Nothing else competes for attention
 * here, and chat is deliberately not on this screen (§1.1, §3.3).
 */
export default function LandingPage() {
  return (
    <main className="landing" data-testid="landing">
      <h1 className="page__title">Compliance Knowledge &amp; Document Review Platform</h1>
      <p className="page__subtitle">
        Dành cho cán bộ Pháp chế/Tuân thủ: xác minh nguồn pháp lý trước khi đưa vào kho tri thức, rồi dùng chính kho đã
        xác minh đó để kiểm tra policy và báo cáo nội bộ.
      </p>

      <div className="landing__cards">
        <Link href="/regulatory-sources/new" className="landing__card" data-testid="card-add-regulatory-source">
          <h2>Add Regulatory Source</h2>
          <p>
            Thêm thông tư/quyết định/amendment. Tài liệu phải được review và approve trước khi trở thành nguồn pháp lý.
          </p>
        </Link>

        <Link href="/compliance-checks/new" className="landing__card" data-testid="card-check-document-compliance">
          <h2>Check Document Compliance</h2>
          <p>
            Upload policy/báo cáo/tài liệu để kiểm tra với kho quy định đã được duyệt. File không trở thành ground truth.
          </p>
        </Link>
      </div>

      <p className="page__section">
        <Link href="/overview">Vào Tổng quan →</Link>
      </p>
    </main>
  )
}
