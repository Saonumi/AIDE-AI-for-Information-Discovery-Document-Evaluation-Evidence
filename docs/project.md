# VAIC2026 — Temporal Regulatory RAG cho ngân hàng (SHB1)
### Tài liệu tổng hợp toàn hệ thống (architecture · module · kỹ thuật · lý do chọn · điểm khác biệt)

> Đề bài: *Advanced RAG Knowledge Base – AI Chatbot for Complex Banking Document Retrieval.*
> Sản phẩm là MVP 48 giờ, chạy được trên `docker-compose`, giải quyết đủ 4 yêu cầu lõi và có bằng chứng vận hành (§10).

---

## 0. Một câu định vị

> **Hệ thống giải quyết *bằng chứng* trước khi trả lời, và không bao giờ để LLM quyết định điều gì quan trọng.**
> Version nào có hiệu lực tại thời điểm hỏi, sửa đổi áp dụng ra sao, nguồn nào bị loại — tất cả do **luật tất định + graph** quyết. LLM chỉ *viết văn xuôi* trên một gói bằng chứng đã lắp ráp sẵn và có thể kiểm toán lại. Đây là moat khác biệt so với "GraphRAG chatbot" mà đa số đội sẽ làm (§11).

---

## 1. Hệ thống giải quyết gì

| Yêu cầu ban tổ chức | Cách hệ thống xử lý | Module chính |
|---|---|---|
| Tự động lần theo tham chiếu chéo | Structure parsing + cross-reference extraction + graph traversal ≤2 hop | `ingestion/legal_extract`, `query/graph_expansion` |
| Luôn dùng đúng phiên bản có hiệu lực | Temporal Knowledge Graph + **temporal pre-filter (trước top-k)** + validity engine | `query/temporal_filter`, `query/validity` |
| Xử lý sửa đổi/thay thế một phần | Reified `ChangeEvent` + **deterministic patch** + human review | `ingestion/change_event`, `ingestion/patch` |
| Phát hiện quy định đồng thời hiệu lực có khả năng xung đột | Co-valid + scope filter + structured obligation compare + LLM zero-shot (advisory) + employee review | `query/conflict` |
| *(Beyond-the-ask)* Phát hiện policy nội bộ lỗi thời | `ALIGNED_TO` graph + numeric/date compare | `query/impact` |

Ngoài ra MVP có: 2 role (USER/EMPLOYEE), duyệt tài liệu trước khi cho truy vấn, citation tới văn bản/Điều/Khoản/trang, từ chối khi thiếu bằng chứng, audit log, giảm thiểu prompt injection cơ bản, benchmark head-to-head với Standard RAG.

---

## 2. Kiến trúc tổng thể

**Stack (đúng master spec, không thay đổi):** FastAPI · Streamlit · PostgreSQL · OpenSearch (BM25 + kNN vector) · Neo4j · BAAI/bge-m3 · PyMuPDF · Docker Compose.

```
                 ┌────────────────────────── UI (Streamlit) ───────────────────────────┐
                 │ Chat · "Vì sao" panel · Head-to-head · Review inbox · Dashboard ·     │
                 │ KG visualization · Audit                                              │
                 └───────────────────────────────┬──────────────────────────────────────┘
                                                  │ HTTP (JWT, 2 role)
                 ┌────────────────────────── API (FastAPI) ─────────────────────────────┐
                 │  /login /documents /review-tasks /query /compare /graph /audit        │
                 └───────────┬───────────────────────────────────────┬──────────────────┘
       INGESTION (Track A)   │                                        │   QUERY (Track B)
   upload→scan→parse→chunk→  │                                        │  security→understanding→
   extract→resolve→change    │                                        │  temporal_pre-filter→hybrid→
   event→patch→review→       │                                        │  graph_expand→validity→
   activate                  ▼                                        ▼  conflict→impact→evidence→
                 ┌──────────────── Banking Knowledge Layer ──────────────┐  gen→checks→answer+audit
                 │ Local FS  · PostgreSQL · OpenSearch(BM25+vector) · Neo4j│
                 └─────────────────────────────────────────────────────────┘
```

**Ba track song song** (mỗi track = cụm thư mục rời, sửa độc lập):
- **Track A — Ingestion** (`ingestion/`): đường ghi tri thức.
- **Track B — Query** (`query/`): đường đọc + suy luận + Standard-RAG baseline.
- **Track C — UI/Eval/Data** (`ui/`, `eval/`, `data/`): giao diện, đánh giá, corpus demo.

Nền tảng dùng chung được **đóng băng trước** (`packages/`, `infra/`, `llm/`, `api/`) làm hợp đồng để 3 track không giẫm chân.

---

## 3. Cấu trúc thư mục (mỗi folder một chức năng)

```
packages/contracts/   # models Pydantic FROZEN: enums, models, api_schemas
packages/common/      # vn_normalize, vn_tokenize, ids, config
infra/                # postgres(+ORM), opensearch_client, neo4j_client, embeddings, schema.sql, neo4j_schema.cypher
llm/                  # client (anthropic|openai|mock), prompts
api/                  # main (wiring), auth (JWT+RBAC), routes_* (controllers mỏng)
ingestion/            # Track A: 12 module theo pipeline (upload → activate)
query/                # Track B: 13 module (security → output_checks) + standard_rag
ui/                   # Track C: app.py (Streamlit), api_client.py
eval/                 # Track C: run_eval.py, metrics.py
data/                 # Track C: seed.py, golden_questions.json, make_corpus.py, corpus/
tests/                # unit test từng track + conftest (offline: sqlite+demo_mode+mock)
docs/                 # tài liệu (project.md, final_pipeline.md, KE-HOACH-3-TRACK.md)
docker-compose.yml · Dockerfile · requirements.txt · .env.example · pyproject.toml
```

---

## 4. Ingestion pipeline (Track A) — module · kỹ thuật · lý do chọn

Toàn bộ chỉ EMPLOYEE dùng. Tài liệu **luôn** bị quarantine và phải được duyệt trước khi vào retrieval.

| Bước / file | Làm gì | Kỹ thuật đã dùng | Vì sao chọn (vs phương án khác) |
|---|---|---|---|
| 1 `upload.py` | Đăng ký file | SHA-256 dedup, allowlist pdf/docx/txt, giới hạn size, local FS, `DocumentRow` QUARANTINED/PENDING | Local FS thay vì MinIO/S3 — đủ cho MVP, ít hạ tầng. Hash chống trùng thay vì so tên file. |
| 2 `injection_scan.py` | Coi tài liệu là dữ liệu không tin cậy | Regex accent-insensitive (EN+VN): "ignore previous instructions", "system prompt"… → flag + `INJECTION_REVIEW` | Rule/regex thay vì classifier train — 48h, đủ để *phát hiện & cô lập*, không tuyên bố "chống hoàn toàn". |
| 3 `pdf_extract.py` | Text + trang + bbox + bold | **PyMuPDF** (lazy import) + python-docx + fallback text | PyMuPDF giữ layout/toạ độ để citation tới đúng trang; PDF-có-text là input chính, OCR chỉ bonus (FinDoc-RAG: PDF→text phẳng làm mất thông tin). |
| 4 `structure_parser.py` | Text → Chương→Điều→Khoản→Điểm | Regex `^Điều\s+\d+`, `^\d+\.`, `^[a-z]\)` + font/indent; employee sửa được | Cấu trúc pháp lý phân cấp (SAT-Graph) thay vì coi luật là chunk rời. Biết ranh giới điều khoản → citation + amendment target đúng. |
| 5 `chunking.py` | Đơn vị retrieval = Khoản/Điểm | **Clause-aware**, khoản dài → subchunk cùng `provision_id`, **heading_path prepend vào embedding text**; chunk-id tất định `chk-{version_id}-{i}` | Fixed 500-token cắt điều kiện khỏi nghĩa vụ, mất tiêu đề (SAT-Graph/FinDoc-RAG). Chunk-id tất định → reindex khi version đổi cửa sổ hiệu lực là **upsert**, không để lại chunk cũ mở-vô-hạn (bug thật đã bắt & fix). |
| 6 `legal_extract.py` | 5 nhóm: metadata, obligation, cross-ref, amendment, scope | **Regex-first**, LLM `complete_json` chỉ gap-fill; Pydantic validate; `value_normalized` = VND qua `vn_normalize` | ComplianceNLP: biểu diễn nghĩa vụ (subject/action/modality/condition/value/source). Regex-first ⇒ chạy được **offline (mock LLM)**, không phụ thuộc API. Không train model. |
| 7 `entity_resolution.py` | Stable ID tách khỏi locator | UUID + resolve locator qua `provision_lookup_key(doc_no, article, clause, point)` exact match | SAT-Graph: locator ("Khoản 2 Điều 7") **không** phải identity — sẽ vỡ khi điều khoản đổi số/tách/gộp. |
| 8 `change_event.py` | Mô hình hóa sự kiện sửa đổi | Reified `ChangeEvent` node (operation, old/new, before/after version, valid_from, review PENDING) | Edge `V2 SUPERSEDES V1` không trả lời được *ai/dòng nào/khi nào*. SAT-Graph action-node cho provenance + point-in-time. |
| 9 `patch.py` | Tạo V2 từ V1, chỉ sửa phần bị ảnh hưởng | **Deterministic patch** (REPLACE/INSERT/DELETE/REPEAL) + `difflib`; **đúng 1 exact match → draft V2, else NEEDS_REVIEW** | Không để LLM viết lại điều khoản (LLM có thể đúng ngữ nghĩa nhưng sai chính xác). Giữ nguyên phần không sửa ("12 tháng"). |
| 10 `review_inbox.py` | 1 inbox cho mọi candidate | `ReviewTaskRow`, 6 loại task, APPROVE/EDIT/REJECT, audit | Kết quả tự động chưa đủ thành quyết định pháp lý (GReX/consolidation). 1 inbox thay 6 màn → giảm scope frontend. |
| 11 `activate.py` | Duyệt → kích hoạt → đồng bộ | Half-open `[valid_from, valid_to_exclusive)`; embed + index OpenSearch; ghi node/edge Neo4j (HAS_VERSION/DECLARES/TARGETS/BEFORE/AFTER/SUPERSEDES) | Khoảng nửa mở tránh lỗi boundary/overlap của `effective_to > query_date` với ngày inclusive. Chỉ nội dung APPROVED vào retrieval. |
| 12 `service.py` | Facade cho API | `handle_upload / list_documents / list_review_tasks / decide_review_task / activate_document` | Tách controller (API) khỏi logic (track) → sửa độc lập. |

---

## 5. Query pipeline (Track B) — module · kỹ thuật · lý do chọn

USER và EMPLOYEE dùng. Đây là phần chứa lợi thế cạnh tranh.

| Bước / file | Làm gì | Kỹ thuật | Vì sao chọn |
|---|---|---|---|
| 13 `security.py` | Role filter + injection mitigation | Chỉ APPROVED; chặn admin-op cho USER; giới hạn độ dài; **không LLM sinh Cypher** (traversal template-only) | Ngăn bypass role, tool abuse, exfiltration; graph query không do LLM tạo. |
| 14 `understanding.py` | Intent + `query_date` | Rule-first (7 intent) + `vn_normalize.normalize_date`; "hiện hành"→today; LLM chỉ fallback nhãn | VersionRAG: query routing cho tài liệu có version. Rule-first ⇒ rẻ, xác định, không gọi conflict/impact cho mọi query. |
| 15 `temporal_filter.py` | **Temporal pre-filter** | Build `{approved_only, valid_at}` **đưa VÀO retrieval** | ⭐ Lỗi kinh điển: lọc *sau* top-k ⇒ query quá khứ chỉ thấy V2 rồi loại, không bao giờ thấy V1. Temporal phải tham gia retrieval. |
| 16 `hybrid_retrieval.py` | BM25 + Vector + RRF | `bm25_search` + `knn_search` dưới **cùng** temporal filter → **RRF (k=60)** → top-8; **lexical-support gate** cho abstention | BM25 mạnh với số hiệu/Điều-Khoản; vector mạnh với diễn đạt tự nhiên (RIRAG/ComplianceNLP). Gate: kết quả phải có hỗ trợ lexical → chống "bịa" evidence khi hỏi ngoài corpus. |
| 17 `graph_expansion.py` | Cross-ref + change paths | `get_graph().expand(≤2 hop)`, lấy version hợp lệ của khoản được dẫn chiếu (temporal filter lại) | ComplianceNLP cross-ref; GraphRAG Finance vector-seed→graph-expand; allowlist relation. |
| 18 `validity.py` | Kiểm tra hợp lệ cuối | **Deterministic** `is_valid_at`; valid vs excluded kèm `ExclusionReason`; đọc version authoritative từ DB | SAT-Graph: temporal/provenance-aware trước generation; **không giao LLM**. Excluded giữ lý do → panel "Vì sao". |
| 19 `conflict.py` | Xung đột tiềm ẩn (advisory) | Co-valid + scope-overlap; **loại trước**: cùng-provision/amendment/exception/khác-scope; rule compare (money qua `money_to_vnd`, modality, threshold); LLM `complete_json` confirm; `human_review=PENDING` | GReX: conflict là bài khó, số tuyệt đối thấp ⇒ **không** tuyên bố "confirmed conflict", chỉ POTENTIAL + employee review. KNN thu hẹp cặp. |
| 20 `impact.py` | Policy nội bộ lỗi thời | Artifact `ALIGNED_TO` version bị supersede → so numeric/date/modality → `ImpactCandidate` STALE | ComplianceNLP: đối chiếu nghĩa vụ với policy nội bộ tìm compliance gap. Beyond-the-ask (§11). |
| 21 `evidence_package.py` | Gói bằng chứng | `EvidencePackage`(valid, **excluded+reason**, reference_paths, change_paths, conflict, impact); `source_id==version_id` | SAT-Graph provenance; FourCorners tách xác minh khỏi generation; RIRAG grounded. **Không gửi top-k thô cho LLM.** |
| 22 `generation.py` | LLM constrained | `GENERATION_SYSTEM` + delimiter `<EVIDENCE>`; chỉ valid_evidence; citation bắt buộc; tool-free; thiếu bằng chứng → INSUFFICIENT_EVIDENCE | LLM chỉ tổng hợp/diễn giải, **không** chọn version/áp amendment/kết luận conflict. |
| 23 `output_checks.py` | Kiểm tra tất định sau sinh | Mọi `[source_id]` ∈ valid_evidence; không dùng số từ excluded; không rỗng; không lộ system prompt → status | RIRAG/RePASs: cần kiểm entailment/contradiction; nhưng LLM-verifier thứ 2 không đảm bảo đúng ⇒ ưu tiên deterministic checks. |
| 24 `standard_rag.py` | **Baseline head-to-head** | `{approved_only}` **không** valid_at, không graph/validity, top-k thô → LLM | Chứng minh Standard RAG bị **version conflation** ngay trong sản phẩm (§10). |
| 25 `service.py` | Facade | `answer_query / compare / graph_subgraph / list_audit`; ghi `AuditRow` | Audit đầy đủ reasoning path (used/excluded versions, graph paths). |

**Trạng thái câu trả lời (không dùng "VERIFIED" chung chung):** `SOURCE_GROUNDED`, `DETERMINISTIC_CHECKS_PASSED`, `HUMAN_REVIEWED`, `NEEDS_REVIEW`, `INSUFFICIENT_EVIDENCE`.

---

## 6. Banking Knowledge Layer

### 6.1 PostgreSQL (metadata/auth/review/audit) — `infra/schema.sql`, ORM `infra/db_models.py`
Bảng: `users`, `documents`, `provisions`, `provision_versions`, `change_events`, `internal_artifacts`, `review_tasks`, `audit_logs`, `feedback`. Nested (obligation, scope, metadata, extracted) lưu JSON. Ngày lưu `DATE`; `valid_to_exclusive` NULL = ∞. Hỗ trợ Postgres (deploy) và SQLite (local/test) qua cùng ORM.

### 6.2 OpenSearch (`infra/opensearch_client.py`)
Index `provisions`: `content`(text, BM25), `embedding`(knn_vector dim=1024), + `provision_id/version_id/document_id/document_number/heading_path/page/valid_from/valid_to_exclusive/approval_status`. **Temporal + approval filter nằm trong query** (filter clause) → top-k chỉ rút từ version hợp lệ. Hai hàm `bm25_search`/`knn_search` để Track B tự làm RRF.

### 6.3 Neo4j — Regulatory Temporal Graph (`infra/neo4j_schema.cypher`)
- **Node:** Document, Provision, ProvisionVersion, ChangeEvent, InternalArtifact.
- **Edge:** CONTAINS, HAS_VERSION, DECLARES, TARGETS, BEFORE, AFTER, SUPERSEDES, REFERENCES, ALIGNED_TO, POTENTIALLY_CONFLICTS_WITH.
- **Temporal props:** valid_from, valid_to_exclusive, created_at, approved_at, approval_status.
- Traversal **template-only, ≤2 hop, relation allowlist** (LLM không sinh Cypher).

### 6.4 Local File Storage
PDF/DOCX gốc phục vụ citation "mở đúng trang".

> **Lưu ý vận hành (trung thực):** để MVP chạy được **không cần docker** (demo/dev/CI), mỗi client hạ tầng có backend in-memory tương đương ngữ nghĩa: OpenSearch→dict store, Neo4j→**networkx**, bge-m3→hash-embedding, LLM→mock (echo evidence có grounding). Bật bằng `DEMO_MODE=true`. Khi deploy thật (`DEMO_MODE=false`) dùng đúng 4-store + bge-m3 + LLM thật. Đây là hiện thực hoá coding rule "Mock unavailable data", **không thay thế** OpenSearch/Neo4j.

---

## 7. Contracts & shared libs (nền tảng đóng băng)

- `packages/contracts/` — nguồn chân lý duy nhất về hình dạng dữ liệu giữa 3 track: `enums.py`, `models.py` (Provision/ProvisionVersion/ChangeEvent/Chunk/EvidencePackage/Answer/ReviewTask/AuditRecord…, kèm `ProvisionVersion.is_valid_at` = chân lý temporal duy nhất), `api_schemas.py`.
- `packages/common/vn_normalize.py` — ⭐ chuẩn hoá số tiền/ngày tiếng Việt: `"500 triệu" = "500.000.000" = "500tr" = "0,5 tỷ"` → cùng VND. **Patch (bước 9) và conflict/impact compare (19-20) sẽ sai âm thầm nếu thiếu.** Đa số đội bỏ qua. Có test riêng.
- `packages/common/vn_tokenize.py` — segment tiếng Việt cho BM25 (underthesea, fallback whitespace) + **stopword filter** cho abstention.
- `packages/common/ids.py` — UUID + `provision_lookup_key` (resolve locator, **không** làm identity).

---

## 8. API endpoints

| Method | Path | Quyền | Chức năng |
|---|---|---|---|
| POST | `/login` | public | JWT + role |
| POST | `/documents` | EMPLOYEE | upload (quarantine) |
| GET | `/documents` | auth | danh sách + status |
| POST | `/documents/{id}/activate` | EMPLOYEE | kích hoạt sau duyệt |
| GET | `/review-tasks` | EMPLOYEE | inbox review |
| POST | `/review-tasks/{id}/decision` | EMPLOYEE | APPROVE/EDIT/REJECT |
| POST | `/query` | auth | trả lời + EvidencePackage |
| POST | `/compare` | auth | head-to-head vs Standard RAG |
| GET | `/graph/provision/{id}` | auth | subgraph cho KG viz |
| GET | `/audit` | EMPLOYEE | nhật ký |

---

## 9. Security

- **RBAC 2 role** (stdlib HMAC-signed token). USER không upload/approve/không xem audit (đã kiểm chứng 403 ở §10).
- **Prompt-injection mitigation (nhiều lớp, không tuyên bố tuyệt đối):** document quarantine → instruction detection → chỉ index sau duyệt → evidence bọc `<EVIDENCE>` là dữ liệu không tin cậy → tool-free generation → deterministic output checks (không lộ system prompt).
- **LLM bị nhốt:** không chọn version, không áp amendment, không sinh citation, không kết luận conflict, không sinh Cypher, không gọi tool.

---

## 10. Bằng chứng vận hành (acceptance đã chạy)

Chạy `DEMO_MODE=true` (offline, mock LLM), corpus SME 500→700.

**A. Lõi tất định (độc lập LLM) — 9/9 PASS** (`tmp/integration_check.py`):
```
[PASS] Point-in-time (01/03/2026): trả 500 (V1); loại V2 với lý do NOT_VALID_AT_QUERY_DATE
[PASS] Point-in-time cite V1 chứ không V2
[PASS] Current (01/08/2026): trả 700 (V2); cite V2 không V1
[PASS] Out-of-corpus: INSUFFICIENT_EVIDENCE (abstain)
[PASS] Conflict 700 vs 600 (cùng phạm vi, co-valid) được phát hiện
[PASS] Impact: policy nội bộ 500 bị đánh STALE khi quy định lên 700
[PASS] Head-to-head: Standard RAG trả 500 (SAI, bản cũ) — hệ ta trả 700 (ĐÚNG, có cite)
```

**B. Tầng HTTP (FastAPI TestClient) — PASS:** login (USER/EMPLOYEE); USER upload→**403**; USER xem audit→**403**; `/query` → `DETERMINISTIC_CHECKS_PASSED`, cite V2, excluded V1 kèm lý do; `/compare` std=500 / ours=700; employee `/review-tasks` & `/audit`→200.

**C. Unit test:** `python -m pytest tests/ -q` → **76 passed** (vn_normalize 6, ingestion 28, query 9, data_seed 11, eval_metrics 22).

**D. Benchmark head-to-head (`python -m eval.run_eval`, 22 golden questions):**

| Metric | Our system | Std RAG |
|---|---|---|
| Point-in-time accuracy | **100.0%** | 75.0% |
| Cross-reference recall | **100.0%** | 0.0% |
| Stale-policy precision | **100.0%** | 0.0% |
| Superseded-evidence rate *(thấp hơn = tốt)* | **26.3%** | 52.6% |
| Conflict-candidate precision | **66.7%** | 33.3% |
| Abstention accuracy | **90.9%** | 86.4% |
| Current-version accuracy | 66.7% | 0.0% |
| Citation correctness | 47.4% | 57.9% |
| Mean latency (ms) | 127.8 | 156.9 |

> **Đọc bảng cho đúng (trung thực):** các số trên chạy với **mock LLM offline** (mock chỉ echo dòng evidence đầu tiên). Vì vậy các metric **phụ thuộc generation** (*current-version*, *citation correctness*) bị đánh giá thấp — không phản ánh chất lượng lõi. Các metric **độc lập LLM** (*point-in-time, cross-reference recall, superseded-evidence rate, stale-policy, abstention*) là nơi hệ thống thắng áp đảo và **đúng bất kể LLM**. Khi chạy với LLM thật (Google Gemini / AI Studio đọc toàn bộ `valid_evidence` + prompt yêu cầu dùng bản hiện hành và cite quy định), *current-version* và *citation* tăng mạnh. Lõi tất định ở §10.A đã chứng minh câu trả lời trỏ đúng version.

---

## 11. Điểm khác biệt — vs các nhóm khác & vs paper

**Vs các nhóm khác (đề bài đã mách sẵn stack ⇒ mọi đội hội tụ về "GraphRAG + versioning + hybrid").** Khác biệt của dự án này KHÔNG ở stack mà ở:

1. **"LLM bị nhốt" + Verifiable Evidence Trace** — mỗi câu trả lời kèm gói bằng chứng tất định, có **nguồn bị loại + lý do**, kiểm toán viên chạy lại được. Đa số đội để LLM tự quyết mọi thứ → không audit được. (§5 bước 21-23, §9)
2. **Correctness "vô hình" được hiển thị** — temporal pre-filter *trước* top-k, khoảng nửa mở `[from,to)`, reified `ChangeEvent`, deterministic patch, stable-id tách locator. Đa số đội làm sai âm thầm; ta **cho thấy** qua head-to-head + panel "Vì sao".
3. **Head-to-head Standard RAG ngay trong sản phẩm** (`/compare`) — không phải bảng slide. Standard RAG trả 500 (sai) cạnh 700 (đúng): §10.A/B.
4. **Compliance-Gap Radar (stale-policy)** — beyond-the-ask: suy từ "Benefits to the Bank", phát hiện policy nội bộ đang dùng quy định hết hiệu lực. (§5 bước 20)
5. **Chuẩn hoá số/ngày pháp lý tiếng Việt** — rẻ nhưng làm patch + conflict *thật sự chạy*; đa số đội bỏ qua.

**Vs paper — MVP này *hợp nhất & vận hành hoá* nhiều mảnh mà mỗi paper chỉ làm một phần:**

| Paper | Đóng góp | Dự án dùng gì / khác gì |
|---|---|---|
| **SAT-Graph** | Luật phân cấp + action node + entity resolution + temporal/provenance-aware retrieval | Lấy: reified ChangeEvent, stable-id, validity trước generation. Khác: MVP, không formal ontology. |
| **VersionRAG** | QA trên tài liệu có version + query routing; RAG thường bị version conflation | Lấy: intent routing + temporal pre-filter. Đóng khung head-to-head để *chứng minh* conflation. |
| **ComplianceNLP** | Nghĩa vụ (entity/action/modality/condition/source) + cross-ref + đối chiếu policy nội bộ | Lấy: structured obligation + cross-ref + stale-policy. Khác: không train model, regex-first. |
| **RIRAG / RePASs** | Retrieval regulatory + answer grounded + kiểm contradiction/obligation | Lấy: hybrid + grounding + deterministic checks. Khác: không dựa LLM-verifier làm chân lý. |
| **GReX** | Conflict retrieval là bài khó, cần reference graph + dữ liệu train, số tuyệt đối thấp | **Chủ động không** train GReX/không tuyên bố "confirmed conflict" → chỉ POTENTIAL + human review. |
| **GraphRAG Finance** | Vector-seed → graph-expand; KNN thu hẹp cặp | Lấy nguyên tắc cho graph_expansion + conflict candidate. |
| **FourCorners** | Tách xác minh nguồn khỏi generation | Lấy: Evidence Package tách khỏi LLM prose. |
| **FinDoc-RAG** | RAG tài chính đánh giá chưa đủ; PDF cấu trúc/bảng phức tạp | Lấy: benchmark chuyên biệt (golden set) + clause-aware chunking + giữ layout. |

**Tinh thần:** *"Ai cũng dựng được graph. Ít nhóm dựng ĐÚNG, và gần như không nhóm nào biến cái đúng thành sản phẩm-niềm-tin có bằng chứng kiểm toán được."*

---

## 12. Bảng kỹ thuật: đã chọn vs phương án thay thế

| Vấn đề | Đã chọn | Thay thế bị loại | Lý do |
|---|---|---|---|
| Chunking | Clause-aware (Khoản/Điểm) | Fixed 500-token | Không cắt điều kiện khỏi nghĩa vụ; citation rõ |
| ID điều khoản | UUID + lookup_key | `DOC_ART7_CL2` | Locator đổi số/tách/gộp sẽ vỡ |
| Sửa đổi | Deterministic patch + diff | LLM viết lại clause | LLM đúng nghĩa nhưng sai chính xác |
| Sự kiện sửa đổi | Reified ChangeEvent node | Chỉ edge SUPERSEDES | Trả lời được ai/dòng nào/khi nào |
| Thời gian | Half-open `[from,to)` + pre-filter | `effective_to > date` sau top-k | Tránh boundary/overlap + version conflation |
| Retrieval | BM25+Vector+RRF | Chỉ vector | BM25 mạnh số hiệu/Điều-Khoản |
| Conflict | Rule + LLM advisory + review | LLM tự kết luận / train GReX | GReX khó; tránh false-positive/overclaim |
| Extraction | Regex-first + LLM gap-fill | LLM-only | Chạy offline, xác định, không train |
| Verify | Deterministic checks | LLM-judge làm chân lý | LLM-verifier không đảm bảo đúng |
| Graph query | Cypher template ≤2 hop | LLM sinh Cypher tự do | Bảo mật + kiểm soát |
| Auth | JWT + 2 role | SSO/ABAC nhiều phòng ban | Đủ separation-of-duties cho MVP |
| Storage | Local FS | MinIO/S3 | Ít hạ tầng cho 48h |

---

## 13. Hạn chế (trung thực)

- Conflict/impact = **candidate chờ người duyệt**, không phải kết luận pháp lý; chỉ kiểm chứng trên cặp curated.
- Extraction regex-first tối ưu cho corpus tiếng Việt dạng Điều/Khoản chuẩn; văn bản lệch định dạng cần review nhiều hơn.
- Chỉ cam kết PDF **có text**; OCR tổng quát chưa làm.
- Corpus demo nhỏ (mini-corpus + 22 golden questions) để chứng minh không hard-code, chưa phải quy mô SHB thật.
- Số benchmark generation-dependent ở §10.D là **cận dưới (mock LLM)**; cần chạy lại với LLM thật để có số thực tế.
- `DEMO_MODE` in-memory chỉ để chạy không-docker; production phải bật 4-store thật + bge-m3.

---

## 14. Triển khai

```bash
cp .env.example .env            # điền GOOGLE_API_KEY (AI Studio) để dùng LLM thật
docker compose up --build       # postgres + opensearch + neo4j + api(8000) + ui(8501)
# hoặc chạy nhanh không docker:
pip install -r requirements.txt
DEMO_MODE=true SEED_DEMO=1 uvicorn api.main:app --port 8000     # tự seed corpus demo
streamlit run ui/app.py                                         # UI (API_BASE_URL=http://localhost:8000)
python -m pytest tests/ -q      # 76 passed
python -m eval.run_eval         # bảng benchmark head-to-head
```
Tài khoản demo: `employee/employee123` (EMPLOYEE), `user/user123` (USER).

---

## 15. Future vision

GraphRAG đầy đủ · formal OWL/RDF ontology · OCR tổng quát · train PhoBERT/GNN/GReX/Learning-to-Rank · general legal conflict detection · auto quyết "quy định nào thắng" · auto khuyến nghị sửa policy nội bộ · regulatory digital twin · multi-bank deployment · giám sát quy định realtime · SSO/ABAC/HA/monitoring production.
