# Compliance Regulatory Knowledge & Document Review Platform

> **One-liner:** Nền tảng giúp cán bộ Pháp chế/Tuân thủ ngân hàng xây dựng kho quy định
> **đã được xác minh**, rồi dùng chính kho đó để tự động đánh giá tác động của văn bản mới
> và kiểm tra mức độ phù hợp của policy/báo cáo nội bộ — mọi kết luận đều có version,
> ngày hiệu lực, evidence và Human Review.

> **Câu pitch:** *Một luồng giúp pháp chế xác minh quy định trước khi đưa vào kho tri thức;
> một luồng dùng chính kho đã xác minh đó để kiểm tra policy và báo cáo —
> **không file nào được mặc định là ground truth.***

---

## 1. Vấn đề (Problem)

Cán bộ Tuân thủ SHB hiện phải **tự đọc** văn bản mới của NHNN, **tự đối chiếu** phiên bản
trước–sau, **tự xác định** policy nội bộ nào bị ảnh hưởng, và **tự kiểm tra** từng báo cáo
có còn dẫn đúng quy định hiện hành không. Quy trình thủ công này:

- **Dễ dùng nhầm version** — trích dẫn hạn mức 500 triệu khi quy định đã sửa thành 700 triệu.
- **Dễ bỏ sót amendment** — một thông tư sửa 5 điều của 3 văn bản khác nhau.
- **Không truy vết được** — kết luận "policy X còn phù hợp" không kèm bằng chứng điều khoản nào, trang nào.
- **Rủi ro thật** với chatbot AI thường: LLM trả lời trơn tru trên phiên bản đã hết hiệu lực.

## 2. Giải pháp: hai luồng, một trust model

### Trust model — quy tắc bất biến
**Không tài liệu nào trở thành ground truth chỉ vì được upload.** Chỉ nguồn
`AUTHORITY_SOURCE` đã **APPROVED + ACTIVE** và **còn hiệu lực tại ngày truy vấn**
mới được dùng làm căn cứ pháp lý:

```
is_legal_ground_truth(doc, d) = AUTHORITY_SOURCE ∧ APPROVED ∧ ACTIVE
                                ∧ valid_from ≤ d < valid_to_exclusive
```

### Workflow A — Add Regulatory Source
Upload thông tư/amendment → parse Điều/Khoản/Điểm → sinh review package →
**Human Review từng thay đổi** → hard gate kích hoạt (HTTP **409** nếu còn critical review) →
versioning tất định V1/V2 + ChangeEvent → Regulatory Impact Report (policy nội bộ nào bị ảnh hưởng).

### Workflow B — Check Document Compliance
Upload policy/báo cáo (trust class `REVIEW_TARGET` — **không bao giờ** vào kho pháp lý) →
trích claim (số tiền, tỷ lệ %, deadline, tham chiếu văn bản) → đối chiếu **chỉ** với kho đã duyệt
tại ngày review → phân loại 7 trạng thái:

| Status | Ý nghĩa |
|---|---|
| COMPLIANT | Được quy định hiện hành hỗ trợ đầy đủ |
| NON_COMPLIANT | Mâu thuẫn giá trị/deadline với quy định hiện hành |
| PARTIALLY_COMPLIANT | Đúng một phần |
| OUTDATED_REFERENCE | Dùng giá trị/văn bản của **phiên bản đã bị thay thế** |
| MISSING_EVIDENCE | Không có căn cứ đủ mạnh — hệ thống **không đoán** |
| AMBIGUOUS | Nhiều quy định đồng hiệu lực xung đột |
| NEEDS_HUMAN_REVIEW | Không đủ tín hiệu tất định — chuyển người |

## 3. Bốn điểm khác biệt (vs. các đội cùng stack)

Đề bài cho sẵn stack (Neo4j + hybrid + versioning) nên **mọi đội sẽ pitch giống nhau về stack**.
Khác biệt của chúng tôi nằm ở chỗ khác:

1. **"LLM bị nhốt" — Verifiable Evidence Trace.** LLM không quyết version, không quyết
   validity, không patch, không tự tạo citation. Toàn bộ do Python tất định; LLM chỉ viết
   prose trên evidence package đã được lọc. Panel *"Vì sao câu trả lời này"* hiển thị cả
   **nguồn bị loại kèm lý do** (NOT_VALID_AT_QUERY_DATE / SUPERSEDED / NOT_APPROVED).
2. **Head-to-head ngay trong sản phẩm.** Nút "So sánh": Standard RAG (conflate version)
   trả lời **sai live** bên cạnh hệ của chúng tôi trả lời đúng kèm lý do — không phải bảng slide.
3. **Compliance-Gap Radar.** Regulation đổi → hệ thống chỉ ra **policy nội bộ nào giờ sai**
   (ALIGNED_TO + stale detection) — beyond-the-ask, suy trực tiếp từ cột "Benefits to Bank".
4. **VN number/date normalizer.** "500 triệu" ↔ "500.000.000" ↔ "0,5 tỷ" ↔ ngày kiểu VN —
   không có nó thì mọi phép so patch/conflict/compliance chết im lặng. Đa số đội bỏ qua.

### Correctness "vô hình" được hiển thị (đã implement, phải kể khi demo)
- Temporal pre-filter chạy **trước** top-k retrieval (không phải filter hậu kỳ).
- Khoảng hiệu lực half-open `[valid_from, valid_to_exclusive)` — không bao giờ hai version cùng valid.
- ChangeEvent được reify (node riêng, có evidence), không chỉ là cạnh SUPERSEDES.
- Patch tất định: amendment áp bằng exact-match một lần; 0 hoặc >1 match → bắt buộc human review.
- Stable provision ID tách khỏi locator (đánh số lại điều khoản không phá lịch sử).
- Claim assessment: **relevance gate** (bigram, chống evidence lạc đề trên corpus nhỏ) +
  **trust gate** (evidence pháp lý phải trace về ProvisionVersion — policy nội bộ không bao giờ
  làm căn cứ).

## 4. Kiến trúc

```
Compliance Officer (Streamlit)
   │
FastAPI ── JWT/RBAC ── AuditEvent cho mọi thao tác
   │
   ├── Workflow A: intake → parse → review package → gate 409 → versioning → impact
   ├── Workflow B: claim extract → retrieve(APPROVED+ACTIVE@date) → deterministic compare → report
   │
   ├── PostgreSQL   — source of truth: trust/approval/version/review/audit
   ├── OpenSearch   — BM25 + vector (RRF), temporal + approval filter TRƯỚC ranking
   ├── Neo4j        — REFERENCES / AMENDS / SUPERSEDES / ALIGNED_TO, giới hạn hop
   └── LLM (Anthropic) — CHỈ: extraction có evidence span + viết giải thích. Không quyết gì.
```

Mỗi backend có fallback in-memory (demo offline không cần Docker); health endpoint
khai thật backend nào đang dùng — không giả vờ production.

## 5. Dữ liệu thật (không chỉ mock)

- **Crawl thật** từ SBV + VBPL (robots-aware, checkpoint/resume): 40+ văn bản NHNN,
  **30 quan hệ amendment thật** mined từ nguồn chính thức.
- **PDF thật** dùng trong demo: `31/2026/TT-NHNN` (cho thuê tài chính, 51KB text sạch),
  `85/2025/TT-NHNN` (amendment tín dụng).
- **3 cặp amendment định danh thật** (mined từ SBV): `08/2026→22/2019` (tỷ lệ vốn ngắn hạn
  34%→30%), `10/2026→27/2024` (deadline báo cáo ngày 10→ngày 5), `13/2026→53/2018`
  (dự phòng 0,75%→1,00%). Clause text demo có banner ghi rõ phần nào synthetic —
  **trung thực về nguồn gốc dữ liệu là một feature của sản phẩm tuân thủ.**

## 6. Số liệu (LLM THẬT — đo ngày 18/07/2026)

22 golden questions, LLM thật `gemini-3.1-flash-lite` cho CẢ hai hệ, chạy sạch không rate-limit
(`LLM_PROVIDER=google LLM_THROTTLE_S=4.5 python -m eval.run_eval`):

| Metric | Hệ của chúng tôi | Standard RAG |
|---|---|---|
| **Superseded-evidence rate** (thấp = tốt) | **26,3%** | 89,5% |
| **Cross-reference recall** | **100%** | 0% |
| **Stale-policy precision** | **100%** | 0% |
| **Conflict-candidate precision** | **100%** | 33,3% |
| **Abstention accuracy** | **100%** | 86,4% |
| Citation correctness | 100% | 100% |
| Point-in-time accuracy | 100% | 100% |
| Partial-patch exact match | 100% | 100% |

**Cách đọc cho giám khảo:** với một LLM đủ tốt, Standard RAG *thỉnh thoảng* vẫn ra đáp án
đúng — nhưng **89,5% số câu nó đưa evidence đã bị thay thế vào context** và phó mặc cho LLM
tự chọn. Hệ của chúng tôi loại bỏ evidence hết hiệu lực **bằng code, trước khi LLM nhìn thấy**
(26,3% còn lại là excluded-evidence hiển thị công khai trong panel "Vì sao"). Trong compliance,
"đúng nhờ may" không audit được — "đúng có chứng minh" mới dùng được. Cross-reference,
stale-policy và conflict là các khả năng Standard RAG hoàn toàn không có (0%).

(Latency trong bảng eval bị cộng throttle chống rate-limit free-tier — không dùng làm số demo.)

Test: **97 passed** toàn suite (`python -m pytest tests/ -q`), gồm T2 (409 gate),
T5–T8 (claim assessment 4 trạng thái) theo Final spec §11.2.

## 7. Q&A phòng thủ (giám khảo hỏi xoáy)

| Câu hỏi | Trả lời |
|---|---|
| "LLM hallucinate citation thì sao?" | Citation verifier từ chối mọi citation ngoài allowlist evidence package; câu trả lời bị reject/regenerate. LLM không thể tự tạo nguồn. |
| "Nếu văn bản upload sai/giả?" | Không file nào tự thành ground truth — phải qua Human Review + activate gate. Thử activate khi chưa review: HTTP 409 (demo live được). |
| "Version cũ lẫn vào câu trả lời?" | Temporal filter chạy trước retrieval; version bị loại hiển thị công khai kèm lý do. Superseded-in-valid-evidence đo được = 0 trên demo corpus. |
| "Hai quy định xung đột?" | Không chọn bừa — trả AMBIGUOUS/conflict candidate kèm cả hai nguồn, chuyển người quyết. Demo live: claim 700tr ra AMBIGUOUS vì QĐ-03 (600tr) đồng hiệu lực. |
| "Sao không cho LLM apply amendment?" | Patch là exact-match tất định; LLM rewrite = rủi ro sửa sai nội dung pháp lý không audit được. Đây là quyết định kiến trúc, không phải hạn chế kỹ thuật. |
| "Prompt injection trong tài liệu?" | Injection scan lúc intake + evidence bọc trong delimiter `<EVIDENCE>` không được coi là instruction + tài liệu nghi vấn bị flag cho reviewer. |
| "Scale ra toàn bộ kho SHB?" | Kiến trúc index tách (authority/policy/review-workspace), outbox sync, PostgreSQL là source of truth — thêm tài liệu là thêm data, không đổi code. MVP chọn một golden domain (tín dụng) đủ sâu thay vì phủ rộng nông. |
| "Cái gì còn thiếu?" | Nói thẳng (mục 8) — trung thực về giới hạn là tính năng của sản phẩm compliance. |

## 8. Giới hạn hiện tại (nói trước, không che)

- OCR cho PDF scan font cũ (TCVN3/VNI) chưa bật — 3/15 PDF SBV có text layer sạch được dùng.
- Claim thuần ngữ nghĩa (không có số/ngày) → NEEDS_HUMAN_REVIEW thay vì phân loại tinh
  (cần LLM thật thay mock để bật semantic support).
- Report registry Workflow B đang in-memory (contract Postgres đã sẵn).
- Export DOCX/PDF: data contract JSON sẵn sàng, UI render bảng; export file là phase sau.
- Số liệu generation-dependent trên slide phải chạy lại bằng Anthropic key thật trước khi trình bày.

## 9. Điều chúng tôi KHÔNG tuyên bố (theo spec §13.6)

Không gọi sản phẩm là "GraphRAG" hay "chatbot pháp lý". Không nói hệ thống tự đưa ra
kết luận pháp lý cuối cùng — **AI đề xuất, Compliance Officer quyết định.** Không nói mọi
file upload được thêm vào knowledge base. Không nói production-ready khi đang dùng
demo credentials/fallback.
