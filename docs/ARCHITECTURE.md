# AIDE — Kiến trúc hệ thống chi tiết

> AI for Information Discovery, Document Evaluation & Evidence  
> Trợ lý pháp chế ngân hàng SHB — VAIC 2026

---

## Tổng quan

AIDE là hệ thống RAG thời gian (Temporal RAG) cho văn bản quy phạm pháp luật ngân hàng. Mọi câu trả lời đều có citation truy vết được đến văn bản pháp luật đang hiệu lực tại thời điểm truy vấn.

```
┌─────────────────────────────────────────────────────────┐
│                     FRONTEND (Next.js)                  │
│   Login → Tab "Add Source" │ Tab "RAG"                  │
│              ↓                    ↓                     │
│        Ingestion UI         Ask / Review UI             │
└────────────────┬────────────────────┬───────────────────┘
                 │  HTTP/REST         │
┌────────────────▼────────────────────▼───────────────────┐
│                   BACKEND (FastAPI)                     │
│  /documents  /chat  /query  /review-runs  /batch-reviews│
└────┬──────────────┬──────────────┬──────────────────────┘
     │              │              │
  PostgreSQL    OpenSearch       Neo4j
  (metadata,    (BM25 +        (provision
   turns,        vector         graph +
   reviews)      search)        amendments)
```

---

## Track A — Ingestion Pipeline

### Luồng xử lý khi upload văn bản

```
Upload file (PDF/DOCX/TXT)
       │
       ▼
[Step 1] register_upload()          → DocumentRow (PENDING) vào PostgreSQL
       │
       ▼
[Step 2] _blocks_from_bytes()       → PyMuPDF / python-docx → list TextBlock
       │
       ▼
[Step 3] injection_scan.scan_text() → Quét prompt injection
         → Nếu nghi ngờ: tạo INJECTION_REVIEW task cho nhân viên
       │
       ▼
[Step 4] legal_extract.extract_document_metadata()
         + enhance_metadata_with_llm()
         → Trích xuất: document_number, issued_date, valid_from
         → LLM bổ sung nếu regex miss
       │
       ▼
[Step 5] llm_extract_provisions(full_text)   ← PRIMARY (LLM)
         fallback: parse_structure(blocks)   ← FALLBACK (rule-based)
         │
         LLM prompt: PROVISION_EXTRACTION_SYSTEM
         → Trả về JSON list: [{heading_path, article, clause, content}]
         → parse_structure: regex Điều/Khoản/Điểm + accumulate body
       │
       ▼
[Step 6] _persist_provisions()
         Mỗi provision:
         → legal_extract.extract_obligation()  (rule-based: nghĩa vụ)
         → legal_extract.extract_scope()       (rule-based: phạm vi)
         → ProvisionRow + ProvisionVersionRow (status=PENDING) vào PostgreSQL
         → Nếu có cross-reference: tạo REFERENCE_REVIEW task
       │
       ▼
[Step 7] Amendment detection (nếu là văn bản sửa đổi)
         legal_extract.extract_amendments()
         → change_event.create_change_event()
         → Tạo CHANGE_EVENT_REVIEW task cho nhân viên
       │
       ▼
DocumentRow.processing_status = PARSED
         → Chờ nhân viên duyệt (INVARIANT: chưa index)
       │
       ▼
[Step 8] Employee approve → activate_document()
         → activate_base_document(): ProvisionVersion → APPROVED
         → Index vào OpenSearch (BM25 + vector)
         → Index vào Neo4j (provision node + amendment edges)
```

### Các module ingestion

| Module | Vị trí | Vai trò |
|--------|--------|---------|
| `upload.py` | `ingestion/` | Register upload, dedup by hash |
| `pdf_extract.py` | `ingestion/` | PyMuPDF → TextBlock list |
| `structure_parser.py` | `ingestion/` | Rule-based Điều/Khoản parser (fallback) |
| `legal_extract.py` | `ingestion/` | Regex + LLM: metadata, obligation, scope, amendments, **provisions** |
| `injection_scan.py` | `ingestion/` | Scan prompt injection patterns |
| `review_inbox.py` | `ingestion/` | Tạo/list/decide review tasks |
| `activate/` | `ingestion/` | Activate base doc + change events → index |
| `change_event.py` | `ingestion/` | Create change event từ amendment |
| `service.py` | `backend/app/ingestion/` | Facade: wires steps 1-8, single DB session |

---

## Track B — Query Pipeline

### Luồng xử lý câu hỏi RAG

```
User gửi câu hỏi
       │
       ▼
[B0] chat/service.py — pre-routing
     ├─ _is_chitchat(text)?
     │    → YES: LLM với AIDE_PERSONA_SYSTEM → trả lời ngay
     │    → NO: tiếp tục
     ├─ _attachment_context()?
     │    → Có file đính kèm + user hỏi về file → surface nội dung file
     └─ _contextualize(text, history) → resolve follow-up pronoun
       │
       ▼
[B1] query/understanding.py — Intent classification
     → QueryIntent: POINT_IN_TIME | HISTORY | CURRENT | COMPARISON
       │
       ▼
[B2] query/temporal_filter.py — Temporal pre-filter (INVARIANT: chạy TRƯỚC top-k)
     → Chỉ lấy ProvisionVersion có valid_from ≤ query_date < valid_to_exclusive
     → ApprovalStatus == APPROVED (không lấy PENDING)
       │
       ▼
[B3] query/hybrid_retrieval.py — BM25 + Vector search (OpenSearch)
     → BM25 score + cosine similarity → RRF fusion
     → Top-k candidates (đã qua temporal filter)
       │
       ▼
[B4] query/graph_expansion.py — Neo4j graph expansion
     → Traverse amendment edges → lấy thêm provision liên quan
     → Supersession resolution: nếu version A bị thay bởi B → ưu tiên B
       │
       ▼
[B5] query/validity.py — Validity check
     → Loại các version đã hết hiệu lực tại query_date
     → Tách valid_evidence vs excluded_evidence (kèm lý do)
       │
       ▼
[B6] query/conflict.py — Conflict detection
     → So sánh valid_evidence: phát hiện giá trị mâu thuẫn cùng provision
     → Output: conflict_candidates (chỉ báo cáo, không kết luận)
       │
       ▼
[B7] query/impact.py — Impact detection
     → Xem nếu quy định ảnh hưởng artifact nội bộ
       │
       ▼
[B8] answering/generation.py — LLM generation (AIDE persona)
     → LLM chỉ viết prose dựa trên valid_evidence
     → Gắn [source_id] cho mỗi kết luận
     → Nếu không đủ bằng chứng: "INSUFFICIENT_EVIDENCE"
     → Fallback deterministic nếu LLM lỗi
       │
       ▼
[B9] answering/output_checks.py — Post-generation validation
     → Kiểm tra citation có thật trong evidence
     → Update AnswerStatus
       │
       ▼
Answer: {text, citations[{source_id, document_number, heading_path, content, valid_from}], status}
```

### Các module query

| Module | Vai trò |
|--------|---------|
| `understanding.py` | Intent classification |
| `temporal_filter.py` | Pre-filter theo ngày (INVARIANT) |
| `hybrid_retrieval.py` | BM25 + vector RRF |
| `graph_expansion.py` | Neo4j traversal + supersession |
| `validity.py` | Lọc valid vs excluded |
| `conflict.py` | Phát hiện mâu thuẫn |
| `impact.py` | Impact on internal artifacts |
| `evidence_package.py` | Đóng gói EvidencePackage |
| `generation.py` (answering) | LLM synthesis với AIDE persona |
| `output_checks.py` | Post-gen citation validation |

---

## Track C — Document Review Pipeline

### Luồng nhận xét tài liệu

```
User upload file cần review (policy/báo cáo nội bộ)
       │
       ▼
[C1] Trích xuất text (PyMuPDF backend /extract-text)
       │
       ▼
[C2] claim_extractor.extract(text, review_run_id)
     PRIMARY: _extract_with_llm()
       → CLAIM_EXTRACTION_SYSTEM prompt
       → LLM trả về [{section, text}] — chỉ điều khoản/nghĩa vụ thực sự
       → Bỏ qua: header, ngày ký, quốc hiệu, nơi nhận, chữ ký
     FALLBACK: _extract_rule_based()
       → Regex sentence split + keyword trigger (phải/không được/tỷ lệ/tiền)
       → _BOILERPLATE_RE lọc các dòng khung

     mine_facts(claim_text) cho mỗi claim:
       → money_vnd, percents, deadline_days, dates, doc_refs
       │
       ▼
[C3] assessor.assess(claim, query_date) — MỖI CLAIM
     → Build EvidencePackage qua RAG pipeline (B2-B5)
     → So sánh StructuredFacts claim vs evidence:
       COMPLIANT           → giá trị khớp với quy định hiện hành
       NON_COMPLIANT       → giá trị không khớp
       PARTIALLY_COMPLIANT → một phần khớp
       OUTDATED_REFERENCE  → khớp với version cũ đã bị supersede
       AMBIGUOUS           → mâu thuẫn giữa các nguồn
       MISSING_EVIDENCE    → không tìm được quy định liên quan
       NEEDS_HUMAN_REVIEW  → không có fact so sánh được (ngữ nghĩa)
       │
       ▼
[C4] report_builder.build()
     → ReviewRunReport: {assessments, summary, knowledge_snapshot_id}
     → Kết quả LOCKED — không thay đổi sau khi tạo (immutable)
       │
       ▼
[C5] Follow-up chat (explainer)
     → User hỏi thêm về finding cụ thể
     → LLM giải thích trong context của ReviewRun đã lock
```

### Batch Review

- Nhiều file → mỗi file tạo ReviewRun độc lập song song
- `routes_batch_reviews.py` quản lý batch state
- `recurring_issues`: finding trùng giữa các file

---

## Cơ sở dữ liệu

### PostgreSQL — Metadata & State

```
documents               → Văn bản upload (metadata, status, hash)
provision_rows          → Điều/khoản/điểm (lookup_key, heading_path)
provision_version_rows  → Phiên bản nội dung (valid_from, valid_to, approval_status)
review_task_rows        → HITL review queue (INJECTION/PARSING/REFERENCE/CHANGE_EVENT)
change_event_rows       → Sự kiện sửa đổi (amendment patches)
conversations           → Chat conversations (mode, owner)
chat_turn_rows          → Tin nhắn (role, content, citations JSON)
conversation_attachments → File đính kèm local context (NOT legal source)
review_run_rows         → Document Review runs (locked, immutable)
```

### OpenSearch — Full-text + Vector Search

```
index: provisions
fields:
  - content (text, BM25)
  - embedding (dense_vector, cosine)
  - document_number, valid_from, valid_to_exclusive (temporal filter)
  - approval_status (chỉ index APPROVED)
  - heading_path, page
```

### Neo4j — Provision Graph

```
Nodes:
  (:Provision {provision_id, document_id, lookup_key})
  (:ProvisionVersion {version_id, valid_from, valid_to_exclusive})
  (:Document {document_id, document_number})

Relationships:
  (:Document)-[:HAS_PROVISION]->(:Provision)
  (:Provision)-[:HAS_VERSION]->(:ProvisionVersion)
  (:ProvisionVersion)-[:SUPERSEDES]->(:ProvisionVersion)
  (:ProvisionVersion)-[:AMENDS]->(:ProvisionVersion)
  (:ProvisionVersion)-[:REFERENCES]->(:Provision)
```

---

## LLM Usage — Điểm dùng AI

| Điểm | Prompt | Vai trò | Fallback |
|------|--------|---------|---------|
| Ingestion metadata | `EXTRACTION_SYSTEM` | Điền document_number/valid_from khi regex miss | Giữ regex result |
| **Ingestion provisions** | `PROVISION_EXTRACTION_SYSTEM` | Tách điều khoản thực sự từ full_text | `parse_structure()` rule-based |
| RAG generation | `GENERATION_SYSTEM` (AIDE) | Viết câu trả lời từ valid_evidence | `_fallback_text()` deterministic |
| Conflict check | `CONFLICT_SYSTEM` | Advisory: có xung đột không? | Bỏ qua (không block) |
| **Claim extraction** | `CLAIM_EXTRACTION_SYSTEM` | Xác định điều khoản trong doc review | `_extract_rule_based()` |
| **Chitchat/persona** | `AIDE_PERSONA_SYSTEM` | AIDE trả lời greeting/hỏi về bản thân | Hardcode fallback |

**Bất biến LLM** (không được vi phạm):
- LLM **không** quyết định validity (Python rules quyết định)
- LLM **không** áp dụng amendment (change_event.py quyết định)
- LLM **không** kết luận conflict (chỉ advisory)
- Evidence luôn wrapped trong `<EVIDENCE>...</EVIDENCE>` (anti-injection)

---

## API Endpoints

### Auth
| Method | Path | Mô tả |
|--------|------|-------|
| POST | `/auth/login` | Đăng nhập, trả JWT |
| GET | `/auth/me` | Session hiện tại |

### Ingestion (Add Source)
| Method | Path | Mô tả |
|--------|------|-------|
| POST | `/documents` | Upload văn bản → trigger pipeline A |
| GET | `/documents` | Danh sách văn bản |
| POST | `/documents/{id}/activate` | Employee duyệt → index |
| GET | `/reviews` | Review task queue |
| POST | `/reviews/{id}/decide` | APPROVE/REJECT/EDIT |

### Chat (RAG)
| Method | Path | Mô tả |
|--------|------|-------|
| POST | `/conversations` | Tạo conversation mới |
| GET | `/conversations` | Danh sách conversations |
| GET | `/conversations/{id}` | Chi tiết + turns + attachments |
| POST | `/conversations/{id}/messages` | Gửi tin nhắn |
| POST | `/conversations/{id}/attachments` | Đính kèm file local context |

### Document Review
| Method | Path | Mô tả |
|--------|------|-------|
| POST | `/review-runs` | Tạo ReviewRun từ 1 file |
| GET | `/review-runs/{id}` | Kết quả + assessments |
| POST | `/review-runs/{id}/rerun` | Chạy lại (tạo run mới) |
| POST | `/review-runs/{id}/ask` | Follow-up chat về finding |
| POST | `/batch-reviews` | Batch nhiều file |
| GET | `/batch-reviews/{id}` | Kết quả batch |

### Query (direct RAG)
| Method | Path | Mô tả |
|--------|------|-------|
| POST | `/query` | Truy vấn trực tiếp (không qua chat history) |

### Graph
| Method | Path | Mô tả |
|--------|------|-------|
| GET | `/graph/provision/{id}` | Subgraph xung quanh provision |

---

## Frontend (Next.js)

```
nextjs_app/
├── app/
│   ├── layout.tsx          → Root layout, ThemeProvider
│   └── page.tsx            → ComplianceRAGBlock
├── components/
│   ├── compliance-rag.tsx  → Shell: header + tab Add Source / RAG
│   ├── add-source.tsx      → Tab upload, review queue, activate
│   ├── rag-tab.tsx         → Segmented: Tra cứu quy định / Nhận xét tài liệu
│   │   ├── AskMode         → ChatGPT-style, sidebar conversations, attachments
│   │   ├── ChatBubble      → User bubble cam / Assistant full-width
│   │   ├── EvidencePanel   → Expandable citations với nội dung trích dẫn
│   │   ├── ReviewMode      → Upload + ReviewRun result + follow-up chat
│   │   ├── SingleResult    → Findings + FindingCard + EvidenceRow
│   │   └── BatchResult     → Batch items + recurring issues
│   └── login-view.tsx      → Login form + AIDE tagline
└── lib/
    ├── api.ts              → HTTP client + TypeScript interfaces
    └── labels.ts           → VN labels mapping
```

---

## Deployment

```
Docker Compose (local dev):
  backend    → FastAPI (uvicorn) — port 8000
  frontend   → Next.js — port 3000
  postgres   → PostgreSQL 16
  opensearch → OpenSearch 2.x (BM25 + vector)
  neo4j      → Neo4j 5.x (graph)

Railway (production):
  backend service  → auto-deploy từ main branch
  frontend service → auto-deploy từ main branch
  Managed PostgreSQL + OpenSearch
```

---

## Key Invariants (không được vi phạm)

1. **Temporal pre-filter TRƯỚC top-k** — không bao giờ retrieve rồi mới filter ngày
2. **LLM không quyết định validity** — Python deterministic rules quyết định
3. **LLM không áp dụng amendment** — change_event.py + activate.py quyết định
4. **Employee review bắt buộc** trước khi bất kỳ document nào vào retrieval
5. **Evidence wrapped `<EVIDENCE>`** — anti prompt-injection
6. **ReviewRun immutable** — kết quả lock sau khi tạo, chat chỉ giải thích
7. **Attachment KHÔNG phải legal source** — không index, không vào RAG kho
8. **Citation traceable** — mọi claim phải có source_id → ProvisionVersion thật
