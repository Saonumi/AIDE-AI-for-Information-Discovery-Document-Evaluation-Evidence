# Kế hoạch triển khai 48h — Advanced RAG Banking (SHB1)
### Bản chia việc cho 3 Project Manager, mỗi PM quản 1 team agent AI dev song song

> Nguồn: "Pipeline tổng thể cuối cùng cho hackathon 48 giờ" + Problem Statement SHB1 (VAIC 2026).
> Stack: **giữ 4 store** (OpenSearch + Neo4j + PostgreSQL + Local FS) theo quyết định — kèm fallback ở §9.

---

## 0. Ba nguyên tắc tổ chức (đọc trước khi chia việc)

1. **Contract-first.** Không team nào code logic trước khi Phase 0 đóng băng: graph schema, DB schema, JSON schema (Chunk / EvidencePackage / ReviewTask / Answer), và danh sách API endpoint. Sau khi đóng băng, 3 team code song song dựa trên contract + mock, không chờ nhau.
2. **Seed fixture ngay Ngày 1.** Track A giao một **bộ dữ liệu mẫu đã dựng sẵn** (dump JSON nạp được vào cả 4 store) trong ~3h đầu. Nhờ đó Track B (retrieval/reasoning) và Track C (UI) làm việc trên dữ liệu thật mà **không phải chờ** pipeline ingestion hoàn chỉnh. Đây là chốt chặn quan trọng nhất để song song hoá.
3. **Loose coupling qua API + mock server.** Track C code dựa trên **mock server** trả EvidencePackage canned; khi B xong endpoint thật thì chỉ đổi base URL.

---

## 1. Bản đồ pipeline → track (26 bước ai làm)

| Bước pipeline | Track |
|---|---|
| 0. Mini-corpus + ground truth | **C** |
| 1. Login & role check | A |
| 2. Upload / quarantine / registration | A |
| 3. File & prompt-injection scan (ingest) | A |
| 4. PDF text + layout extraction | A |
| 5. Structure parsing (Điều/Khoản) | A |
| 6. Clause-aware chunking | A |
| 7. Legal information extraction (LLM structured) | A |
| 8. Entity resolution + Stable ID | A |
| 9. ChangeEvent + version resolution | A |
| 10. Deterministic partial patch | A |
| 11. Employee review inbox (backend) | A |
| 12. Approve / activate / index vào OpenSearch+Neo4j | A |
| 13. Query security & role filter | B |
| 14. Query understanding + intent + query_date | B |
| 15. Temporal pre-filter | B |
| 16. Hybrid retrieval (BM25+Vector+RRF) | B |
| 17. Graph expansion + cross-reference | B |
| 18. Validity & supersession resolution | B |
| 19. Potential conflict detection | B |
| 20. Internal impact / stale-policy | B |
| 21. Evidence package | B |
| 22. Constrained LLM generation | B |
| 23. Deterministic output checks | B |
| 24. Evidence-backed answer (API shape) | B |
| 25. Audit / dashboard / feedback | A (ghi) + C (hiển thị) |
| **Standard RAG baseline (head-to-head)** | B |
| **KG visualization** | C |
| **UI: chat, citation, timeline, review inbox, dashboard, compare, "Why" panel** | C |
| **Eval harness + metrics** | C |
| **VN number/date normalizer + tokenizer (shared lib)** | Phase 0 (dùng bởi A & B) |

---

## 2. Timeline 48h (mốc chung)

| Khoảng | Mục tiêu | Go/No-Go |
|---|---|---|
| **H0–H3** | Phase 0: đóng băng contract + shared lib + seed fixture. All-hands. | ✅ Contract merged, fixture nạp được vào 4 store |
| **H3–H6** | Hạ tầng lên: Docker Compose 4 store chạy + healthcheck. | ⚠️ **GO/NO-GO 4-store** (xem §9) |
| **H6–H30** | 3 track build song song trên contract + fixture | Mỗi track có "vertical slice" chạy được ở H20 |
| **H30–H40** | Tích hợp thật (bỏ mock), nối A→B→C end-to-end | ✅ 1 câu hỏi chạy full pipeline thật |
| **H40–H46** | Eval + head-to-head + polish demo 10 cảnh | ✅ Standard RAG fail live, hệ ta pass |
| **H46–H48** | Buffer + tập pitch + quay video dự phòng | — |

**Quy tắc vàng:** đến H30 mọi thứ chưa nối được end-to-end thì cắt tính năng, KHÔNG cắt "đường xương sống chạy được". Một demo end-to-end đơn giản luôn thắng một kiến trúc phức tạp không chạy.

---

## 3. PHASE 0 — Contracts & shared libs (ALL-HANDS, H0–H3)

Đây là phần 3 PM ngồi cùng nhau chốt. Sản phẩm Phase 0 nằm trong `packages/contracts/` và là **single source of truth**.

### 3.1. Graph schema (Neo4j) — theo §4 pipeline
- **Node:** Document, Provision, ProvisionVersion, ChangeEvent, Obligation, InternalArtifact, ReviewTask
- **Edge:** CONTAINS, HAS_VERSION, DECLARES, TARGETS, BEFORE, AFTER, SUPERSEDES, REFERENCES, ALIGNED_TO, POTENTIALLY_CONFLICTS_WITH
- **Temporal props:** `valid_from`, `valid_to_exclusive` (nửa mở `[from, to)`), `created_at`, `approved_at`, `approval_status`

### 3.2. DB schema (Postgres) — bảng
`users(role)`, `documents(metadata, file_hash, processing_status, approval_status)`, `chunks`, `review_tasks(task_type, payload, decision)`, `audit_log`, `feedback`.

### 3.3. JSON contracts (Pydantic models — dùng chung A/B/C)
- `Chunk` (chunk_id, provision_id, version_id, heading_path[], content, page)
- `Obligation` (subject, action, modality, condition, value, source_provision)
- `ChangeEvent` (operation, old_text, new_text, target_locator, valid_from, source_page, review_status)
- `EvidencePackage` (query_date, valid_evidence[], excluded_evidence[{version_id, reason}], reference_paths[], change_paths[], conflict_candidates[], impact_candidates[])
- `Answer` (text, citations[], timeline, status ∈ {SOURCE_GROUNDED, DETERMINISTIC_CHECKS_PASSED, HUMAN_REVIEWED, NEEDS_REVIEW, INSUFFICIENT_EVIDENCE})
- `ReviewTask` (task_type ∈ {PARSING, CHANGE_EVENT, REFERENCE, CONFLICT, IMPACT, INJECTION}, source_ref, extracted, diff, confidence)

### 3.4. API contract (OpenAPI — B & C code dựa trên đây từ H3)
```
POST /login                              → {token, role}
POST /documents           (EMPLOYEE)     upload → {document_id, status}
GET  /documents                          list + status
GET  /review-tasks        (EMPLOYEE)     → ReviewTask[]
POST /review-tasks/{id}/decision (EMP)   {APPROVE|EDIT|REJECT}
POST /documents/{id}/activate (EMPLOYEE)
POST /query                              {text, query_date, mode?} → {answer: Answer, evidence: EvidencePackage}
POST /compare                            {text, query_date} → {standard_rag: Answer, our_system: Answer}
GET  /graph/provision/{id}               → {nodes[], edges[]}  (cho KG viz)
GET  /audit               (EMPLOYEE)     → audit rows
```

### 3.5. Shared libs (`packages/common/`) — build ngay, dùng bởi A & B
- **`vn_normalize`** — chuẩn hoá số tiền ("500 triệu" ↔ "500.000.000" ↔ "500tr"), ngày ("01/07/2026" ↔ "ngày 01 tháng 7 năm 2026"), đơn vị. **Bắt buộc có sớm** vì patch (A) và conflict comparison (B) chết nếu thiếu.
- **`vn_tokenize`** — pyvi/underthesea cho BM25 tiếng Việt.
- **`ids`** — sinh UUID + quy tắc stable-id (tách identity khỏi locator).
- **`config`** — connection strings, model names, prompt versions.

### 3.6. Seed fixture (`fixtures/`) — Track A giao, mọi người dùng
Kịch bản chuẩn "SME 500→700": 1 văn bản gốc, 1 sửa đổi, 2 policy nội bộ, 1 cặp conflict (700 vs 600 co-valid), 2 stale policy — ở **cả 3 dạng**: (a) JSON nạp Postgres, (b) Cypher nạp Neo4j, (c) docs nạp OpenSearch. → B/C có dữ liệu thật ngay H3.

---

## 4. TRACK A — Platform & Ingestion  *(PM-A)*

**Mandate:** Dựng toàn bộ hạ tầng + đường ghi (write path). Kết thúc: knowledge layer được populate và có review inbox hoạt động. **Đây là track nặng nhất → cân nhắc team agent lớn hơn.**

**Owns (bước):** 1–12, 25(ghi), + Docker Compose 4 store, + seed fixture.

**Task list:**
- A1. Docker Compose: OpenSearch + Neo4j + Postgres + volume FS + healthcheck. **(H3–H6, ưu tiên #1)**
- A2. Auth JWT + middleware `require_authenticated` / `require_employee` + seed 2 user.
- A3. Upload → SHA-256 dedup → quarantine → registration (metadata Postgres).
- A4. Injection scan (regex rule) lúc ingest → flag `INJECTION_SUSPECTED` → tạo ReviewTask.
- A5. PDF extract (PyMuPDF): text + page + bbox + bold.
- A6. Structure parser Điều/Khoản/Điểm (regex + font/indent) → cho phép Employee sửa.
- A7. Clause-aware chunking + heading_path vào embedding text + parent/child.
- A8. Legal extraction (LLM structured JSON + Pydantic validate + source span + confidence): metadata, obligation, cross-ref, amendment, scope.
- A9. Entity resolution + stable ID (exact match số hiệu+locator; fuzzy/LLM chỉ tạo candidate).
- A10. ChangeEvent + version resolution (reified node, source span).
- A11. Deterministic patch (REPLACE/INSERT/DELETE/REPEAL; 1 exact match → draft V2, else NEEDS_REVIEW). **Dùng `vn_normalize`.**
- A12. Review inbox backend (bảng `review_tasks` + decision API).
- A13. Approve → activate → set `[valid_from, valid_to_exclusive)` → tạo edge Neo4j → sinh embedding → index OpenSearch (BM25+vector).
- A14. Audit write (mọi hành động).

**Produces (interface cho B/C):** 4 store đã populate; endpoint `/documents`, `/review-tasks`, `/activate`; seed fixture; Neo4j có sẵn version chain + ChangeEvent + REFERENCES + ALIGNED_TO.

**Consumes:** Phase 0 contracts + shared libs.

**Definition of Done:** Upload 1 PDF sửa đổi → hệ tự trích Target/Operation/Old/New/Valid_from → tạo ReviewTask → Employee approve → V2 xuất hiện trong OpenSearch + Neo4j với khoảng hiệu lực đúng.

**Rủi ro riêng:** A8 (LLM extraction) là phần noisy nhất → dựa vào review inbox làm lưới an toàn; chuẩn bị fixture đã-trích-sẵn để demo không phụ thuộc extraction real-time.

---

## 5. TRACK B — Query, Retrieval & Reasoning  *(PM-B)*

**Mandate:** Đường đọc (read path) + toàn bộ "bộ não" + baseline head-to-head. Đây là **track chứa lợi thế cạnh tranh** — làm đúng phần này = thắng.

**Owns (bước):** 13–24 + Standard RAG baseline.

**Task list:**
- B1. Query security + role filter (chỉ APPROVED; chặn admin API; template Cypher, cấm LLM sinh Cypher tự do).
- B2. Query understanding: intent (7 loại) + `query_date` (regex ngày + rule "hiện tại/trước/sửa đổi") + LLM classifier fallback.
- B3. **Temporal pre-filter** (approval=APPROVED AND valid_from ≤ date AND (valid_to_exclusive IS NULL OR date < valid_to_exclusive)) — **áp dụng TRƯỚC top-k**. *(Điểm hơn đám đông #1.)*
- B4. Hybrid retrieval: BM25 (dùng `vn_tokenize`) + Vector (e5/BGE) + RRF, top 5–10.
- B5. Graph expansion: seed → Neo4j traversal ≤2 hop qua REFERENCES/HAS_VERSION/BEFORE/AFTER/SUPERSEDES/DECLARES (relation allowlist).
- B6. Validity & supersession resolution (Python deterministic + Neo4j) — **LLM không tham gia**.
- B7. Conflict detection (co-valid → scope filter → KNN candidate → structured obligation compare + rule mismatch → LLM JSON judge → POTENTIAL_CONFLICT → review). **Dùng `vn_normalize`.** Loại: version cũ/mới, amendment, general/exception, khác product/customer/jurisdiction.
- B8. Internal impact / stale-policy: V2 SUPERSEDES V1, policy ALIGNED_TO V1 → STALE_CANDIDATE → so con số/deadline/modality/scope.
- B9. **Evidence Package** (valid + **excluded kèm lý do** + reference_paths + change_paths + conflict + impact). *(Nguyên liệu cho "Why" panel.)*
- B10. Constrained LLM generation (chỉ valid_evidence; delimiter; citation ID bắt buộc; tool-free; INSUFFICIENT_EVIDENCE khi thiếu).
- B11. Deterministic output checks (citation tồn tại? thuộc valid? có dùng số từ excluded? lộ system prompt? thực thi instruction trong evidence?) → status flags.
- B12. `/query` + `/compare` endpoints (Answer + EvidencePackage).
- B13. **Standard RAG baseline** (index tất cả version + top-k + LLM, không temporal) — để head-to-head. *(Rẻ, ~1–2h, nhưng là vũ khí demo.)*

**Produces:** `/query`, `/compare` trả Answer + EvidencePackage; conflict & impact candidates ghi Neo4j.

**Consumes:** 4 store đã populate (hoặc seed fixture cho tới khi A xong); contracts; shared libs.

**Definition of Done:** Hỏi cùng câu với 2 ngày khác nhau → trả đúng V1/V2; `/compare` cho thấy Standard RAG sai còn hệ ta đúng + citation + excluded reason.

**Rủi ro riêng:** B7 (conflict) dễ false-positive → **curate 1 cặp rõ ràng cho demo**, không tổng quát hoá; đóng khung `POTENTIAL_CONFLICT → human review`.

---

## 6. TRACK C — Frontend, Eval & Demo  *(PM-C)*

**Mandate:** Bộ mặt sản phẩm + bằng chứng định lượng + kịch bản thắng. **Track này biến "correctness vô hình" của B thành thứ giám khảo NHÌN THẤY.**

**Owns:** bước 0, 25(hiển thị), UI toàn bộ, KG viz, eval, demo.

**Task list:**
- C1. **Mini-corpus + golden set** (§ pipeline A.0): 3–5 PDF tiếng Việt có text, 20–40 Điều/Khoản, 1 cross-ref, 2 version chain, 1 partial supersession, 1 conflict pair, 2 stale policy, **15–25 golden questions + ground truth JSON**. Thiết kế sao cho **Standard RAG demonstrably fail** (câu point-in-time + version conflation).
- C2. Streamlit shell + auth + role switch (USER/EMPLOYEE).
- C3. Chat UI: câu trả lời + **citation click mở đúng trang PDF** + timeline (V1→ChangeEvent→V2) + warning + status badge.
- C4. **"Why this answer" panel** — render EvidencePackage: nguồn dùng + **nguồn bị loại kèm lý do**. *(Wedge 4.1 — trust moat, demo-gold.)*
- C5. **Head-to-head compare UI** — gọi `/compare`, hiển thị **song song** Standard RAG vs hệ ta. *(Wedge 4.2 — hook mở màn.)*
- C6. **KG visualization** (pyvis / Neo4j browser embed) — Provision → versions → ChangeEvent → references. *(Deliverable bắt buộc + wow.)*
- C7. **Compliance-gap radar UI** — list policy nội bộ STALE khi regulation đổi. *(Wedge 4.3 — chốt business ROI.)*
- C8. Employee review inbox UI (1 màn: PDF nguồn + target + extracted + diff + confidence + APPROVE/EDIT/REJECT) + dashboard (chờ duyệt / conflict / stale / injection / query fail).
- C9. Audit view + user feedback (đúng/sai/thiếu nguồn/không liên quan/cần nhân viên xem).
- C10. **Eval harness**: chạy golden set qua cả 2 hệ, xuất bảng metrics (§7 pipeline: current-version acc, point-in-time acc, cross-ref recall, superseded-evidence rate, partial-patch exact match, conflict precision, citation correctness, stale-policy precision, abstention acc, injection containment, latency).
- C11. **Kịch bản demo 10 cảnh** (tái sắp xếp: head-to-head lên đầu) + slide + video dự phòng.

**Produces:** UI toàn bộ; bảng benchmark; corpus + golden set (cả A & B đều dùng để test).

**Consumes:** API contract (mock trước, thật sau); `/graph`; EvidencePackage; Neo4j.

**Definition of Done:** Demo được 10 cảnh không sập; bảng benchmark cho thấy delta rõ vs Standard RAG; KG viz + "Why" panel + compare hoạt động.

**Lưu ý phụ thuộc:** C dùng **mock server** (canned EvidencePackage từ fixture) tới khi B xong `/query` thật → không bị chặn.

---

## 7. Bốn mũi nhọn — ai chịu trách nhiệm (RACI)

| Wedge | Data/Logic (R) | UI/Hiển thị (R) | Ghi chú |
|---|---|---|---|
| **4.1 Verifiable Evidence Trace** ("LLM bị nhốt") | B (EvidencePackage + excluded reasons) | C ("Why" panel C4) | Moat chính. Phải hiển thị nguồn bị loại + lý do. |
| **4.2 Head-to-head Standard RAG** | B (baseline B13 + `/compare`) | C (compare UI C5) | Hook mở màn demo. |
| **4.3 Compliance-Gap Radar** | B (B8) + A (InternalArtifact + ALIGNED_TO) | C (radar C7) | Beyond-the-ask, map ROI. |
| **4.4 VN number/date normalizer** | Phase 0 shared lib | — | A (patch) + B (conflict) cùng dùng. Build sớm. |
| **KG viz** (deliverable) | A (Neo4j populate) | C (C6) | Bắt buộc theo đề. |

Mỗi wedge có **2 chủ**: đừng để rơi vào khe giữa Data và UI. PM đồng bộ ở mỗi integration checkpoint.

---

## 8. Integration checkpoints (chống tích hợp phút chót)

| Mốc | Kiểm tra | Chủ trì |
|---|---|---|
| H6 | 4 store up + fixture nạp được | PM-A |
| H20 | Mỗi track có 1 vertical slice chạy trên fixture | 3 PM |
| H30 | A→B nối thật (bỏ fixture ở B): query chạy trên dữ liệu A ingest | PM-A + PM-B |
| H34 | B→C nối thật (bỏ mock ở C): UI gọi `/query` thật | PM-B + PM-C |
| H40 | End-to-end 10 cảnh chạy 1 lượt không sập | 3 PM |
| H44 | Benchmark xong + head-to-head rõ delta | PM-C |

---

## 9. Risk register + fallback (bắt buộc vì giữ 4 store)

| Rủi ro | Xác suất | Fallback |
|---|---|---|
| **4-store không lên kịp ở H6** | Cao | Theo chính pipeline: **giữ Neo4j** (version/reference là lõi), thay OpenSearch bằng vector/full-text đơn giản (pgvector+tsvector). Quyết ở checkpoint H6, KHÔNG để trôi. |
| OpenSearch + Neo4j ăn RAM trên box deploy | TB | Giảm heap; hoặc Neo4j Aura free + OpenSearch managed; hoặc chạy demo local, deploy chỉ để "có link". |
| BGE-M3 OOM/chậm | TB | Đổi `multilingual-e5-base` hoặc embedding API. |
| LLM extraction (A8) noisy | Cao | Fixture đã-trích-sẵn cho demo; review inbox là lưới an toàn (pitch như tính năng). |
| Conflict false-positive (B7) | Cao | Curate 1 cặp; đóng khung POTENTIAL_CONFLICT + human review. |
| Tích hợp phút chót | Cao | Contract-first + mock + checkpoint H30/H34. |

**Người sở hữu quyết định H6 go/no-go:** PM-A. Nếu no-go, degrade stack ngay, không thương lượng.

---

## 10. Sở hữu demo & pitch

- **Câu pitch chốt** (PM-C thuộc lòng): *"Ai cũng xây được GraphRAG. Khác biệt của chúng em là hệ thống giải quyết bằng chứng trước khi trả lời và không bao giờ để LLM quyết định điều gì quan trọng — chọn đúng phiên bản tại thời điểm được hỏi, áp dụng sửa đổi bằng patch tất định, mỗi câu trả lời kèm dấu vết bằng chứng mà kiểm toán viên tự chạy lại được. Trên cùng graph đó, hệ thống chỉ ra tài liệu nội bộ nào đang dùng quy định đã hết hiệu lực."*
- **Thứ tự cảnh:** head-to-head (hook) → point-in-time → "Why" panel → partial supersession → cross-ref + KG viz → compliance-gap radar → conflict/injection/abstention.
- Slide phải có mục **Future work** (OWL/RDF, OCR tổng quát, train PhoBERT/GNN/GReX, general conflict, auto-decide winner, SSO/HA...) — trung thực về scope ghi điểm với giám khảo kỹ thuật.

---

*Ghi chú phân bổ nhân lực: Track A nặng nhất (hạ tầng + ingestion), nên team agent lớn nhất. Track B là lõi cạnh tranh, cần agent giỏi nhất về reasoning/retrieval. Track C rộng nhưng nhiều việc song song được, hợp với nhiều agent làm UI đồng thời.*
