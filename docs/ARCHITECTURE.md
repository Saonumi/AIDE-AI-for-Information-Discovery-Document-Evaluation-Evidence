# AIDE — Kiến trúc hệ thống chi tiết

> **AI for Information Discovery, Document Evaluation & Evidence**  
> Trợ lý pháp chế ngân hàng SHB — VAIC 2026

---

## Tổng quan

AIDE là hệ thống **Temporal Regulatory RAG** — RAG có nhận thức thời gian — cho văn bản quy phạm pháp luật ngân hàng. Mọi câu trả lời đều có citation truy vết được đến văn bản pháp luật **đang hiệu lực tại thời điểm truy vấn**, không phải phiên bản mới nhất hay cũ nhất.

```
┌─────────────────────────────────────────────────────────────┐
│                   FRONTEND (Next.js 16)                     │
│        Tab "Thêm Nguồn"     │     Tab "RAG"                 │
│    Upload → Review → Kích hoạt   Hỏi đáp / Nhận xét        │
└──────────────┬──────────────────────────┬───────────────────┘
               │  HTTP/REST (JWT Bearer)  │
┌──────────────▼──────────────────────────▼───────────────────┐
│                  BACKEND (FastAPI + Uvicorn)                 │
│  /documents  /conversations  /query  /review-runs  /health  │
└──────┬──────────────┬──────────────────┬────────────────────┘
       │              │                  │
  PostgreSQL     OpenSearch           Neo4j
  (metadata,     (BM25 + kNN         (provision
   turns,         vector              graph +
   reviews,       search)             amendments)
   audit)
```

**Luồng chính:**
- **Workflow A** — Thêm nguồn pháp lý: Upload → Trích xuất → Review → Kích hoạt → Vào kho RAG
- **Workflow B** — Kiểm tra tuân thủ: Hỏi đáp RAG / Nhận xét tài liệu nội bộ

---

## 1. Stack công nghệ

| Thành phần | Công nghệ | Mục đích |
|---|---|---|
| **Backend API** | FastAPI + Uvicorn | REST API, startup lifecycle |
| **Frontend** | Next.js 16, React 19, shadcn/ui, Radix UI | 2-tab UI (Add Source + RAG) |
| **Database** | PostgreSQL 16 / SQLite (fallback) | Metadata, turns, reviews, audit |
| **Search** | OpenSearch 2.13 | BM25 + kNN vector (hybrid retrieval) |
| **Graph DB** | Neo4j 5.18 + APOC | Đồ thị điều khoản, phiên bản, sửa đổi |
| **Embeddings** | BAAI/bge-m3 (1024-dim) | Dense retrieval, đa ngôn ngữ, tối ưu tiếng Việt |
| **LLM** | Google Gemini / Anthropic Claude / OpenAI / Mock | Constrained generation (không dùng tool use) |
| **Auth** | HMAC-SHA256 JWT + PBKDF2 | 2 roles: EMPLOYEE (write), USER (read-only) |
| **Testing** | pytest + SQLite + MockLLM | 218 test offline-safe |
| **Infrastructure** | Docker Compose 4 services | Local dev + Railway deploy |

---

## 2. Cấu trúc thư mục

```
VAIC2026-hehehe/
├── api/                        # Legacy FastAPI entry point (Railway dùng cái này)
│   ├── main.py                 # FastAPI app, CORS, startup, route mounting
│   ├── auth.py                 # JWT + PBKDF2 auth, seed users
│   ├── _facade.py              # Lazy-import bridge (api → service modules)
│   ├── routes_ingest.py        # /documents, /review-tasks
│   ├── routes_query.py         # /query, /compare, /graph, /audit
│   └── routes_chat.py          # /conversations, /conversations/{id}/messages
│
├── backend/app/                # Canonical implementation (workflows, review, chat)
│   ├── api/                    # Spec-compliant API routes (compliance, runs, batch)
│   ├── workflows/
│   │   ├── compliance_checks/  # Workflow B: trích claim → đánh giá → báo cáo
│   │   └── impact_analysis/    # Impact report: chính sách nội bộ vs quy định mới
│   ├── chat/                   # Multi-turn conversation + attachment isolation
│   ├── review/                 # ReviewRun bất biến + batch processing
│   ├── answering/              # Evidence package + LLM generation + output checks
│   ├── retrieval/              # Temporal filter, hybrid search, graph expansion
│   ├── persistence/            # Repository pattern (OpenSearch, PostgreSQL)
│   ├── analysis/               # Conflict detection, impact scoring
│   └── ingestion/              # activation gate (ensure_can_activate)
│
├── ingestion/                  # Track A: 12-module pipeline
│   ├── upload.py               # SHA-256 dedup, type check, file storage
│   ├── injection_scan.py       # Quét prompt injection (regex)
│   ├── pdf_extract.py          # PyMuPDF + python-docx → TextBlock list
│   ├── structure_parser.py     # Điều → Khoản → Điểm regex parsing
│   ├── chunking.py             # Clause-aware chunking (preserves provision_id)
│   ├── legal_extract.py        # Metadata, obligation, cross-ref, amendments (regex + LLM gap-fill)
│   ├── entity_resolution.py    # Stable provision lookup keys
│   ├── change_event.py         # Reified ChangeEvent nodes
│   ├── patch.py                # Deterministic REPLACE/INSERT/DELETE/REPEAL
│   ├── review_inbox.py         # 6 task types: PARSING/INJECTION/REFERENCE/CONFLICT/IMPACT/CHANGE_EVENT
│   ├── activate.py             # Embed → OpenSearch index → Neo4j write
│   ├── activation_gate.py      # Re-export từ backend/app/ingestion/activation/gate.py
│   └── service.py              # Facade: handle_upload, activate_document, list_documents...
│
├── query/                      # Track B: 13-module pipeline
│   ├── security.py             # Role filter, max length, block mitigation
│   ├── understanding.py        # 7 intent types + VN date normalization
│   ├── temporal_filter.py      # Half-open interval filter dict (chạy TRƯỚC top-k)
│   ├── hybrid_retrieval.py     # BM25 + kNN + RRF(k=60) + lexical gate
│   ├── graph_expansion.py      # Cross-reference traversal ≤2 hops
│   ├── validity.py             # is_valid_at() → valid_evidence / excluded_evidence
│   ├── conflict.py             # Co-valid scope overlap, rule-based compare
│   ├── impact.py               # Policy → ALIGNED_TO → superseded?
│   ├── evidence_package.py     # Assemble EvidencePackage (provenance-aware)
│   ├── generation.py           # LLM complete() với <EVIDENCE> block
│   ├── output_checks.py        # Validation sau generation (citation check, injection)
│   ├── standard_rag.py         # Baseline so sánh (không có temporal filter)
│   └── service.py              # Facade: answer_query, compare, graph_subgraph, list_audit
│
├── infra/                      # Data layer
│   ├── postgres.py             # SQLAlchemy engine factory, session_scope
│   ├── db_models.py            # ORM models (tất cả tables)
│   ├── schema.sql              # DDL tham khảo
│   ├── opensearch_client.py    # BM25 + kNN interface (InMemoryStore nếu DEMO_MODE)
│   ├── neo4j_client.py         # Graph traversal (InMemoryGraph nếu DEMO_MODE)
│   └── embeddings.py           # BAAI/bge-m3 hoặc hash_embedding (offline)
│
├── llm/
│   ├── client.py               # 4 providers: Google/Anthropic/OpenAI/Mock
│   └── prompts.py              # System prompts (generation, JSON extraction)
│
├── packages/                   # Frozen contracts (source of truth giữa các track)
│   ├── contracts/
│   │   ├── enums.py            # Tất cả status strings (ProcessingStatus, ApprovalStatus...)
│   │   ├── models.py           # Domain models (Document, Answer, EvidencePackage, Citation...)
│   │   └── api_schemas.py      # HTTP request/response shapes
│   └── common/
│       ├── config.py           # get_settings() — Pydantic Settings từ env vars
│       ├── ids.py              # ID generators + provision_lookup_key()
│       ├── vn_normalize.py     # VN text normalization, date parse, money extract
│       └── vn_tokenize.py      # Vietnamese word tokenization (BM25)
│
├── frontend/nextjs_app/        # Track C: Next.js frontend
│   ├── app/                    # Next.js App Router
│   ├── components/
│   │   ├── add-source.tsx      # Workflow A UI (upload, review, activate)
│   │   ├── rag-tab.tsx         # Workflow B UI (ask + document review)
│   │   ├── compliance-rag.tsx  # 2-tab coordinator
│   │   └── login-view.tsx      # Login form
│   └── lib/
│       └── api.ts              # API client (fetch + JWT + error handling)
│
├── tests/                      # 131 unit + integration tests (Track A/B)
├── backend/tests/              # 87 tests (canonical backend)
├── data/
│   ├── golden/                 # Golden dataset (regulatory docs + ground truth)
│   └── seed.py                 # Demo data loader
├── docs/                       # Architecture, spec, team brief
├── docker-compose.yml          # 4-service stack
├── requirements.txt            # 51 dependencies
└── Dockerfile
```

---

## 3. Track A — Ingestion Pipeline (12 modules)

### Luồng xử lý khi upload

```
Upload file (PDF/DOCX/TXT)
       │
       ▼
[1] upload.py → register_upload()
    - SHA-256 hash dedup (bỏ qua ARCHIVED)
    - Validate type/size
    - Ghi file vào local FS
    - Tạo DocumentRow: QUARANTINED + PENDING
       │
       ▼
[2] pdf_extract.py → _blocks_from_bytes()
    - PDF: PyMuPDF (giữ layout, page number, bold)
    - DOCX: python-docx
    - TXT/fallback: UTF-8 decode
    → List[TextBlock]
       │
       ▼
[3] injection_scan.py → scan_text()
    - Regex patterns (accent-insensitive)
    - Nếu nghi ngờ: tạo INJECTION_REVIEW task
       │
       ▼
[4] legal_extract.py → extract_document_metadata()
    - Regex: số văn bản, ngày ký, ngày hiệu lực
    - LLM gap-fill: enhance_metadata_with_llm()
       │
       ▼
[5] legal_extract.py → llm_extract_provisions()
    - Chia full_text thành chunk 4000 ký tự
    - Mỗi chunk → LLM complete_json() → List[provision dict]
    - Mỗi provision: heading_path, article, clause, point, content
       │
       ▼
[6] _persist_provisions()
    - Tạo ProvisionRow (provision_id, lookup_key)
    - Tạo ProvisionVersionRow (content, valid_from, PENDING)
    - extract_obligation() + extract_scope() deterministic
       │
       ▼
[7] _run_amendment_pipeline() (nếu văn bản có "thay")
    - legal_extract.extract_amendments()
    - change_event.create_change_event() cho từng amendment
    - Tạo CHANGE_EVENT_REVIEW task
       │
       ▼
[8] processing_status = PARSED
       │
       ▼
[9] review_inbox.create_task(PARSING_REVIEW)
    - Luôn tạo (kể cả LLM không trích được gì)
    - confidence: 0.8 nếu có điều khoản, 0.3 nếu không
       │
       ▼
[10] Trả về UploadResponse → Frontend hiển thị ở "Chờ duyệt"
```

### Kích hoạt tài liệu

```
POST /documents/{id}/activate
       │
       ▼
activation_gate.ensure_can_activate()
    - Chặn nếu còn INJECTION_REVIEW hoặc REFERENCE_REVIEW pending
    - PARSING_REVIEW không chặn
       │
       ▼
activate.activate_base_document()
    - Embedding mỗi provision chunk (BAAI/bge-m3)
    - Index vào OpenSearch (BM25 + kNN)
    - Ghi vào Neo4j: CONTAINS, HAS_VERSION, DECLARES edges
    - processing_status = INDEXED, approval_status = APPROVED
    - Timestamp approved_at
       │
       ▼
policy_mapper.map_policy_document()
    - Nếu là INTERNAL_POLICY: tạo ALIGNED_TO links
```

---

## 4. Track B — Query Pipeline (13 modules)

### Luồng trả lời câu hỏi

```
POST /query {text, query_date}
       │
       ▼
[13] security.check_query()
    - Role filter, max length, block mitigation
       │
       ▼
[14] understanding.understand()
    - 7 intent types: CURRENT_QA / POINT_IN_TIME_QA /
      VERSION_HISTORY / CROSS_REFERENCE_QA /
      CHANGE_EXPLANATION / CONFLICT_CHECK / IMPACT_CHECK
    - Normalize ngày VN ("hiện hành" → today)
       │
       ▼
[15] temporal_filter (CRITICAL — chạy TRƯỚC top-k)
    - Filter dict: {approved_only: true, valid_at: query_date}
    - Push vào OpenSearch filter clause (không phải post-hoc)
    - Ngăn version conflation
       │
       ▼
[16] hybrid_retrieval
    - BM25 search (dưới temporal filter)
    - kNN vector search (dưới temporal filter)
    - Reciprocal Rank Fusion (k=60)
    - Lexical gate: phải có BM25 hit
    → top-8 chunks
       │
       ▼
[17] graph_expansion
    - Traversal ≤2 hops, edge allowlist
    - Fetch valid versions của điều khoản được tham chiếu
    - Reapply temporal filter
       │
       ▼
[18] validity.check()
    - is_valid_at(chunk, query_date)
    - valid_evidence vs excluded_evidence + ExclusionReason
       │
       ▼
[19] conflict.detect()
    - Co-valid scope overlap
    - Rule-based compare (money, modality, percentage)
    - LLM advisory (không phải quyết định cuối)
    - Đánh dấu POTENTIAL + PENDING human review
       │
       ▼
[20] impact.assess()
    - Internal artifacts ALIGNED_TO version → superseded?
    → ImpactCandidate list
       │
       ▼
[21] evidence_package.build()
    - EvidencePackage: valid_evidence + excluded + reference_paths
      + change_paths + conflict_candidates + impact_candidates
       │
       ▼
[22] generation.generate()
    - <EVIDENCE> block (chỉ valid_evidence)
    - LLM complete() → text với [source_id] citations
       │
       ▼
[23] output_checks.run()
    - Tất cả [source_id] có trong valid_evidence?
    - Không có số từ excluded evidence?
    - Không injection?
    → Final answer status
       │
       ▼
[25] Ghi AuditRow → QueryResponse(answer, evidence)
```

---

## 5. Hạ tầng dữ liệu

### 5.1 PostgreSQL — Tất cả tables

| Table | Cột chính | Mục đích |
|---|---|---|
| `users` | user_id, username, password_hash (PBKDF2), role | Auth |
| `documents` | document_id, filename, type, document_number, file_hash, processing_status, approval_status, injection_suspected, doc_metadata (JSON) | Document registry |
| `provisions` | provision_id, document_id, lookup_key, heading_path (JSON), article, clause, point | Provision identity |
| `provision_versions` | version_id, provision_id, content, valid_from, valid_to_exclusive, approval_status, page, obligation (JSON), scope (JSON), approved_at | Temporal versions |
| `change_events` | change_event_id, amending_document_id, target_provision_id, operation, old/new_text, before/after_version_id, valid_from, review_status | Amendment history |
| `internal_artifacts` | artifact_id, document_id, title, aligned_to_version_id, obligation (JSON) | Internal policies |
| `review_tasks` | task_id, task_type, document_id, extracted (JSON), diff_before/after, confidence, status, decision, decided_by | Review inbox |
| `audit_logs` | audit_id, user_id, role, query, query_date, payload (JSON), status, latency_ms, prompt_version | Audit trail |
| `conversations` | id, owner_id, mode, title, last_activity_at | Chat sessions |
| `chat_turns` | id, conversation_id, role, content, citations (JSON) | Tin nhắn |
| `conversation_attachments` | id, conversation_id, filename, content, checksum | File đính kèm (local context — KHÔNG vào KB) |
| `review_runs` | run_id, owner_id, assessment_date, snapshot (JSON), target_text, report (JSON), state | Review Run bất biến |
| `batch_review_runs` | batch_id, owner_id, state, total/completed/failed | Batch processing |

### 5.2 OpenSearch Index: `provisions`

| Field | Type | Mục đích |
|---|---|---|
| `content` | text | BM25 full-text search |
| `embedding` | knn_vector (1024-dim) | Dense vector search |
| `provision_id`, `version_id`, `document_id` | keyword | Lookup |
| `heading_path` | keyword[] | Citation |
| `page` | integer | Citation |
| `valid_from`, `valid_to_exclusive` | date | **Temporal pre-filter** |
| `approval_status` | keyword | **Approval filter** |

Temporal filter + approval filter được push vào OpenSearch filter clause — không phải post-hoc. Cả `bm25_search()` và `knn_search()` đều nhận `filters` dict.

### 5.3 Neo4j — Nodes và Edges

**Nodes:** `Document`, `Provision`, `ProvisionVersion`, `ChangeEvent`, `InternalArtifact`

**Edges (allowlist, ≤2 hops):**

| Edge | From → To | Ý nghĩa |
|---|---|---|
| `CONTAINS` | Document → Provision | Văn bản chứa điều khoản |
| `HAS_VERSION` | Provision → ProvisionVersion | Phiên bản tại thời điểm |
| `DECLARES` | ProvisionVersion → Obligation | Nghĩa vụ khai báo |
| `TARGETS` | ChangeEvent → ProvisionVersion | Sửa đổi nhắm vào version nào |
| `BEFORE` / `AFTER` | ProvisionVersion ↔ ProvisionVersion | Trình tự thời gian |
| `SUPERSEDES` | ProvisionVersion → ProvisionVersion | Chain sửa đổi |
| `REFERENCES` | Provision → Provision | Tham chiếu chéo |
| `ALIGNED_TO` | InternalArtifact → ProvisionVersion | Chính sách nội bộ căn cứ vào |
| `POTENTIALLY_CONFLICTS_WITH` | ProvisionVersion → ProvisionVersion | Xung đột tiềm năng |

**LLM không bao giờ sinh Cypher** — chỉ dùng template traversal.

---

## 6. LLM Client (`llm/client.py`)

| Provider | Env var | Model mặc định | Free tier |
|---|---|---|---|
| **Google Gemini** (mặc định) | `GOOGLE_API_KEY` | `gemini-1.5-flash` | 1500 req/ngày, 15 RPM |
| Anthropic Claude | `ANTHROPIC_API_KEY` | claude-sonnet | Paid |
| OpenAI | `OPENAI_API_KEY` | gpt-4o | Paid |
| OpenAI-compatible | `OPENROUTER_API_KEY` | custom | Tùy |
| Mock (fallback) | _(không cần)_ | — | Offline |

**Interface:**
- `complete(system, user, temperature) → str` — text generation
- `complete_json(system, user) → dict` — structured JSON output

**Auto-fallback:** Thiếu key → MockClient (app luôn boot được).

**Railway env vars cho LLM:**
```
LLM_PROVIDER=google
GOOGLE_API_KEY=AIza...
LLM_MODEL=gemini-1.5-flash
LLM_THROTTLE_S=5
```

---

## 7. Authentication (`api/auth.py`)

- **JWT:** HMAC-SHA256, expire 720 phút, secret từ `JWT_SECRET`
- **Password:** PBKDF2 (không plain text)
- **2 roles:**
  - `EMPLOYEE` — upload, review, activate, delete, quyết định review task
  - `USER` — read-only (query, chat, xem documents)
- **Seed accounts:** `compliance` / `compliance123` (EMPLOYEE), `user` / `user123` (USER)

---

## 8. Frontend (`frontend/nextjs_app/`)

**Stack:** Next.js 16, React 19, shadcn/ui, Tailwind CSS v4, TypeScript

### Tab "Thêm Nguồn" (`add-source.tsx`)
```
Upload card
  └── Chọn file + loại văn bản → "Tải lên & Trích xuất"

Chờ duyệt
  └── Mỗi file: tên, loại, trạng thái xử lý
      └── ▾ điều khoản → lazy-load từ GET /documents/{id}/provisions
          └── Mỗi điều khoản: heading_path, nội dung
              └── [Chỉnh sửa] → textarea → [Lưu] (PATCH /provisions/{vid})
      └── [Kích hoạt] [Xóa]

Nguồn đang hoạt động
  └── Tài liệu APPROVED + INDEXED
```

### Tab "RAG" (`rag-tab.tsx`)
```
[Tra cứu quy định] | [Nhận xét tài liệu]

Tra cứu quy định:
  └── Sidebar: danh sách conversations
  └── Chat: multi-turn với citations
      └── Mỗi citation: document_number, heading_path, valid_from→valid_to,
          trang, "Độ phù hợp X%" (retrieval score)
      └── Evidence panel: expand xem nội dung trích dẫn đầy đủ

Nhận xét tài liệu:
  └── Upload file nội bộ (PDF/DOCX/TXT)
  └── Chạy compliance check → kết quả từng claim
  └── Status: COMPLIANT / NON_COMPLIANT / OUTDATED_REFERENCE /
              PARTIALLY_COMPLIANT / MISSING_EVIDENCE / AMBIGUOUS
  └── Batch mode: nhiều file cùng lúc
```

---

## 9. API Routes

### Legacy routes (Railway dùng — `api/main.py`)

| Endpoint | Method | Auth | Mục đích |
|---|---|---|---|
| `/login` | POST | — | Lấy JWT token |
| `/documents` | POST | EMPLOYEE | Upload văn bản |
| `/documents` | GET | USER | List tài liệu (không có ARCHIVED) |
| `/documents/{id}/activate` | POST | EMPLOYEE | Kích hoạt vào RAG |
| `/documents/{id}` | DELETE | EMPLOYEE | Xóa (soft delete → ARCHIVED) |
| `/documents/{id}/provisions` | GET | USER | List điều khoản của văn bản |
| `/documents/{id}/provisions/{vid}` | PATCH | EMPLOYEE | Chỉnh sửa nội dung điều khoản |
| `/review-tasks` | GET | USER | Review inbox |
| `/review-tasks/{id}/decision` | POST | EMPLOYEE | Approve/Reject/Edit task |
| `/query` | POST | USER | Hỏi đáp RAG (temporal) |
| `/compare` | POST | USER | So sánh Standard RAG vs AIDE |
| `/graph/{provision_id}` | GET | USER | Visualize KG subgraph |
| `/audit` | GET | EMPLOYEE | Audit log |
| `/conversations` | POST/GET | USER | Quản lý conversations |
| `/conversations/{id}/messages` | POST | USER | Gửi tin nhắn |
| `/health` | GET | — | Basic health check |

### Canonical routes (`backend/app/api/`)

| Endpoint | Mục đích |
|---|---|
| `POST /compliance-checks` | Tạo compliance review run |
| `GET /compliance-checks/{id}` | Lấy báo cáo compliance |
| `POST /review-runs` | Single review run |
| `GET /review-runs/{id}` | Trạng thái + báo cáo |
| `POST /batch-reviews` | Batch compliance checks |
| `GET /health/details` | Postgres + OpenSearch + Neo4j + LLM status |

---

## 10. Invariants — Không bao giờ vi phạm

| Invariant | Được đảm bảo bởi |
|---|---|
| Temporal pre-filter chạy TRƯỚC top-k retrieval | `query/temporal_filter.py` + OpenSearch filter clause |
| LLM không quyết định validity/amendment — chỉ Python deterministic | `query/validity.py`, `ingestion/patch.py` |
| Mọi câu trả lời phải có citation truy vết đến valid_evidence | `query/output_checks.py` |
| Nhân viên phải review trước khi document active (INJECTION/REFERENCE) | `ingestion/activation_gate.py` |
| Prompt evidence wrapped trong `<EVIDENCE>…</EVIDENCE>` | `llm/prompts.py` |
| Chat attachments không bao giờ vào knowledge base | `backend/app/chat/domain.py` |
| ReviewRun bất biến — snapshot + report locked sau complete | `backend/app/review/service.py` |

---

## 11. Temporal Model

Toàn bộ hệ thống dùng **half-open interval** `[valid_from, valid_to_exclusive)`:

```python
def is_valid_at(version, query_date: date) -> bool:
    return (
        version.approval_status == "APPROVED"
        and version.valid_from <= query_date
        and (version.valid_to_exclusive is None
             or query_date < version.valid_to_exclusive)
    )
```

- `valid_to_exclusive = None` → đang hiệu lực hiện tại
- Khi có văn bản sửa đổi → version cũ nhận `valid_to_exclusive = ngày hiệu lực của văn bản mới`
- Truy vấn ngày trong quá khứ → trả về đúng version hiệu lực ngày đó

---

## 12. Demo Mode (Offline — không cần Docker)

Khi `DEMO_MODE=true`:

| Thành phần | Thay thế bằng |
|---|---|
| PostgreSQL | SQLite (`./data/vaic.db`) |
| OpenSearch | `InMemoryStore` (dict, cùng semantics) |
| Neo4j | `InMemoryGraph` (networkx MultiDiGraph) |
| BAAI/bge-m3 | `hash_embedding()` (deterministic, offline) |
| LLM thật | `MockClient` (echo evidence line) |

```bash
# Chạy toàn bộ app không cần Docker:
DEMO_MODE=true SEED_DEMO=1 uvicorn api.main:app --port 8000
cd frontend/nextjs_app && pnpm dev
```

---

## 13. Deploy

### Docker Compose (4 services)
```yaml
postgres:    image: postgres:16,     port: 5432
opensearch:  image: opensearch:2.13, port: 9200
neo4j:       image: neo4j:5.18,      port: 7474/7687
api:         build: .,               port: 8000
```

### Railway (production)
- **Backend:** `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
- **Frontend:** Next.js deploy từ `frontend/nextjs_app/`

### Env vars quan trọng

| Biến | Mặc định | Mô tả |
|---|---|---|
| `DEMO_MODE` | `false` | In-memory backends |
| `POSTGRES_DSN` | `postgresql+psycopg://...` | DB connection |
| `OPENSEARCH_HOST` | `localhost` | OpenSearch |
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j |
| `LLM_PROVIDER` | `google` | google/anthropic/openai/openrouter/mock |
| `GOOGLE_API_KEY` | — | Gemini API key |
| `LLM_MODEL` | `gemini-flash-latest` | Tên model |
| `LLM_THROTTLE_S` | `0` | Delay giữa LLM calls (tránh 429 free tier) |
| `CORS_ORIGINS` | `*` | Frontend origin (vd: `https://aide.saonumi.io.vn`) |
| `JWT_SECRET` | `change-me-in-prod` | JWT signing key |
| `RETRIEVAL_TOP_K` | `8` | Số chunks retrieve |
| `SEED_DEMO` | `0` | Auto-seed golden corpus khi startup |

---

## 14. Testing

| Suite | Location | Số tests | Coverage |
|---|---|---|---|
| Track A/B unit | `tests/` | 131 | Ingestion, query, auth, models |
| Backend canonical | `backend/tests/` | 87 | Workflows, chat, review, retrieval |
| **Tổng** | | **218** | Tất cả offline (SQLite + MockLLM) |

```bash
pytest tests/ -x -q           # Track A/B
pytest backend/tests/ -x -q   # Canonical
```

---

## 15. Điểm khác biệt vs Standard RAG

| Vấn đề Standard RAG | Giải pháp AIDE |
|---|---|
| Version conflation (trả V2 khi hỏi về V1) | Temporal pre-filter TRƯỚC top-k |
| Không biết văn bản hết hiệu lực | `is_valid_at()` trên từng chunk |
| Không track sửa đổi | Reified ChangeEvent + deterministic patch engine |
| Citation không truy vết được | Chunk ID = version_id, stable lookup keys |
| LLM có thể "nhớ" provision bị thay thế | Evidence wrapped `<EVIDENCE>` delimiters |
| Không biết chính sách nội bộ bị ảnh hưởng | Impact analysis: ALIGNED_TO → superseded? |
| Không có audit trail | AuditRow per query (full reasoning path) |
