# VAIC2026 — Compliance Knowledge & Document Review Platform (frontend)

Khung giao diện dựng theo `docs/VAIC2026_Final_Compliance_Knowledge_Review_Master_Spec (1).docx`.
Next.js 16 (App Router) · React 19 · TypeScript · Tailwind 4.

**Đây là khung — không phải bản hoàn thiện thị giác.** Cấu trúc, vị trí thành phần và
luồng dữ liệu bám spec; phần màu sắc/hiệu ứng/typography để trống có chủ đích.

## Chạy

```bash
npm install
npm run dev            # http://localhost:3000
```

Backend ở cổng khác:

```bash
API_PROXY_TARGET=http://localhost:8765 npm run dev
```

Không cần backend vẫn xem được toàn bộ layout: endpoint nào chưa có sẽ dùng fixture
theo Phụ lục B và hiện badge `Dữ liệu mẫu`.

## Dành cho người làm CSS

`src/app/globals.css` là **skeleton stylesheet** — chỉ có position/size/spacing, không
có brand. Thay thế toàn bộ file này là dự kiến; không có gì trong đó ảnh hưởng hành vi.

Class name là ngữ nghĩa và ổn định (không dùng Tailwind utility trong markup), nên có
thể style trực tiếp:

| Hook | Ở đâu |
|---|---|
| `.app-shell`, `.sidenav`, `.topbar`, `.page` | khung tổng |
| `.badge--trust[data-value="AUTHORITY_SOURCE"]` | mỗi giá trị enum một selector riêng |
| `.badge--compliance[data-value="NON_COMPLIANT"]` | 7 trạng thái claim |
| `.banner--warning \| --info \| --mock \| --error` | 4 loại banner tin cậy |
| `.doc-viewer`, `.evidence-highlight[data-span-id]` | trình xem tài liệu |
| `.diff`, `.proposal`, `.claim`, `.summary` | thẻ nội dung chính |
| `.pipeline__step[data-state="done\|current\|pending"]` | stepper |
| `.lineage__edge[data-relation]` | evidence lineage |

Mọi `data-value` / `data-status` / `data-state` đều là giá trị enum nguyên bản, dùng
làm selector được.

## Bản đồ màn hình (spec §10.2)

| # | Nav | Route |
|---|---|---|
| — | Landing 2 card (§10.1) | `/` |
| 1 | Tổng quan | `/overview` |
| 2 | Add Regulatory Source | `/regulatory-sources/new` |
| — | Source Review Package (§10.3) | `/regulatory-sources/[id]` |
| 3 | Source Review Inbox | `/source-review-inbox` |
| 4 | Regulatory Changes | `/regulatory-changes` · `/regulatory-changes/[id]` |
| 5 | Policy Mapping | `/policy-mapping` |
| 6 | Regulatory Impact Reports | `/impact-reports` · `/impact-reports/[id]` |
| 7 | Check Document Compliance | `/compliance-checks/new` |
| 8 | Compliance Review Reports | `/compliance-reports` · `/compliance-checks/[id]` (§10.4) |
| 9 | Tra cứu bằng chứng | `/evidence-query` |
| 10 | Audit & System Health | `/audit-health` |

## Cấu trúc

```
src/
  app/                     App Router; (workspace) là nhóm có sidebar + topbar
  components/
    common/                StatusBadge · Banners · PipelineSteps
    document/              DocumentViewer · EvidenceHighlight      (§10.6)
    review/                BeforeAfterDiff · ChangeProposalCard    (§10.6)
    compliance/            ClaimAssessmentCard · ExecutiveSummary · ClaimFilters (§10.6)
    graph/                 LineageGraph                            (§10.6)
    layout/                SideNav · TopBar · AppLayout · PageHeader
  lib/
    apiClient.ts           transport; không throw, không side-effect
    api.ts                 một hàm cho mỗi dòng bảng §9
    fixtures.ts            dữ liệu mẫu theo Phụ lục B
    labels.ts              nhãn tiếng Việt cho mọi enum
    navigation.ts          10 mục §10.2
    report.ts · session.ts
  types/
    domain.ts              enum §6 — nguồn chân lý duy nhất cho vocabulary
    api.ts                 payload §9 + Phụ lục B
```

## Quy ước bắt buộc giữ

- **Không hard-code chuỗi trạng thái trong JSX.** Mọi nhãn đi qua `lib/labels.ts`;
  mọi giá trị đi qua `types/domain.ts`.
- **Không nuốt lỗi.** Fetch fail → `ApiErrorBanner`; dùng fixture → `DataSourceBanner`.
  Spec §4.2 cấm silent fallback.
- **UI switch theo error code, không parse message** (§9.1).
- **Không có nút approve hàng loạt.** §10.3 yêu cầu quyết định từng proposal.
- **Không dùng chữ "AI kết luận"** cho trạng thái `NEEDS_HUMAN_REVIEW` (§10.5).

## Phần CHƯA có (không che giấu)

1. **PDF renderer** — `DocumentViewer` là khung có nhãn; cơ chế chuyển trang và
   overlay highlight đã chạy, nhưng chưa vẽ nội dung PDF. Cần endpoint phục vụ file
   gốc + pdf.js.
2. **`/auth/login` chưa tồn tại ở backend** — client thử `/auth/login` rồi fallback
   `/login`. Xoá nhánh fallback trong `lib/api.ts` khi backend §9 xong.
3. **Backend vẫn trả role `EMPLOYEE`** — spec §6.1 đã xoá role này. Màn login chặn và
   báo rõ; hiện chưa đăng nhập được vào workspace bằng tài khoản demo cũ.
4. **7 endpoint ngoài bảng §9** (`/overview`, `/documents`, `/regulatory-changes`,
   `/policy-links`, `/impact-reports`, `/review-tasks`, `/compliance-reports`) — cần
   thiết cho các màn hình §10.2 nhưng chưa có trong contract; cần bổ sung vào §9.
5. **Extraction quality score và retry path** (§7.3) chưa có trên UI.
6. **Export báo cáo** (§10.4 "Export / mark actions") chưa có.
