# Compliance Regulatory Knowledge & Document Review Platform (VAIC2026 — SHB1)

Nền tảng giúp cán bộ Pháp chế/Tuân thủ **xây dựng kho quy định đã được xác minh** và dùng chính kho đó để **tự động kiểm tra tác động của văn bản mới** cũng như **mức độ phù hợp của policy, báo cáo và tài liệu nội bộ**.

> **Pitch:** Một luồng giúp pháp chế xác minh quy định trước khi đưa vào kho tri thức; một luồng dùng chính kho đã xác minh đó để kiểm tra policy và báo cáo — **không file nào được mặc định là ground truth**.

Temporal Hybrid GraphRAG chỉ là kỹ thuật nền. Hệ thống **không tự đưa ra kết luận pháp lý cuối cùng** — AI đề xuất, Compliance Officer quyết định.

📄 Chi tiết kiến trúc/module: [`docs/project.md`](docs/project.md) · Spec chuẩn: [`docs/_final_spec_extracted.md`](docs/_final_spec_extracted.md)

## Bài toán

Cán bộ Tuân thủ phải tự đọc văn bản mới, đối chiếu phiên bản, xác định policy bị ảnh hưởng và kiểm tra tài liệu nội bộ có phù hợp quy định hiện hành không. Quy trình thủ công dễ dùng nhầm version, bỏ sót amendment, khó truy vết bằng chứng.

## Trust model

Không tài liệu nào trở thành ground truth chỉ vì được upload. Chỉ nguồn `AUTHORITY_SOURCE` đã **APPROVED + ACTIVE** (qua Human Review + activation hard gate) mới được dùng làm căn cứ pháp lý. File upload để kiểm tra là `REVIEW_TARGET` — không bao giờ vào knowledge base. Activate khi còn critical review pending → **HTTP 409 `REVIEW_NOT_COMPLETED`**.

## Hai workflow

| | Workflow A — Add Regulatory Source | Workflow B — Check Document Compliance |
|---|---|---|
| Vào | Thông tư/quyết định/amendment | Policy/báo cáo/tài liệu nội bộ cần kiểm tra |
| Qua | Parse → review package → Human Review → activation gate → versioning | Claim extraction → retrieve evidence APPROVED+ACTIVE tại review date → so tất định |
| Ra | Nguồn ACTIVE + ChangeEvent + **Regulatory Impact Report** | **Compliance Review Report** theo từng claim (COMPLIANT/NON_COMPLIANT/OUTDATED_REFERENCE/MISSING_EVIDENCE/…) |

**LLM không bao giờ quyết định điều gì quan trọng.** Version/hiệu lực/patch/status do luật tất định + graph quyết; LLM chỉ viết văn xuôi trên evidence đã lắp ráp.

## Chat modes (Mode spec v2 — `docs/VAIC2026_Mode_Based_Chat_and_Review_Expansion_Spec.docx`)

Một AI assistant, các mode có trust boundary khác nhau:

| Mode | Ngữ cảnh | Endpoint |
|---|---|---|
| **Ask Regulations** | Multi-turn RAG; history chỉ của đúng conversation; attachment = context cục bộ, không phải nguồn pháp lý | `POST /conversations` (mode `REGULATORY_ASSISTANT`) → `POST /conversations/{id}/messages` |
| **Document Review — Single** | Review Run **bất biến**: freeze assessment_date + knowledge snapshot + prompt/schema version; explainer chat chỉ dùng evidence đã khóa | `POST /review-runs` → `POST /review-runs/{id}/questions` |
| **Document Review — Batch** | 1 file = 1 Review Run độc lập; recurring issue groups; retry failed-only; re-run all → batch MỚI | `POST /batch-reviews` → `/questions` (scope: entire batch / one report / findings) |

Invariants (test: `tests/test_chat_isolation.py`, `test_review_run.py`, `test_batch_review.py`):
cross-chat leakage 0% · review target không vào KB · kết quả locked (prompt không đổi được status) ·
frozen snapshot (activate nguồn mới không đổi run cũ) · citation allowlist 100% · owner scope từ token.
Prompt/schema riêng theo mode: `backend/app/prompts/` + `backend/app/schemas/` (có version).
UI: tab **Chat Modes (Ask · Review)** trong `frontend/nextjs_app`.

## Yêu cầu

- Python **3.11+** · Docker Desktop (chỉ cho chế độ 4-store)

## Chạy nhanh (không cần docker)

```bash
pip install -r requirements.txt
```

**Linux / macOS / Git Bash:**
```bash
DEMO_MODE=true SEED_DEMO=1 uvicorn api.main:app --port 8000
```

**Windows PowerShell:**
```powershell
$env:DEMO_MODE="true"; $env:SEED_DEMO="1"; uvicorn api.main:app --port 8000
```

Tab mới:
```bash
streamlit run ui/app.py    # UI → http://localhost:8501
```

> `DEMO_MODE=true`: stub in-memory, không cần Docker/API key — trạng thái fallback hiển thị trung thực tại `/health/details` và trang **System Health**.

Tài khoản demo: `compliance/compliance123` (COMPLIANCE_OFFICER) · `employee/employee123` (alias) · `user/user123`.

## Chạy đầy đủ 4-store

```bash
cp .env.example .env          # điền GOOGLE_API_KEY nếu dùng LLM thật
docker compose up --build     # postgres · opensearch · neo4j · api(:8000) · ui(:8501)
```

## Kiểm thử

```bash
python -m pytest tests/ -q          # full suite (T1–T12 của Final spec §11.2)
python -m scripts.golden_benchmark  # acceptance metrics §11.4 trên golden dataset
python -m eval.run_eval             # benchmark head-to-head vs Standard RAG
```

## Golden demo (dữ liệu: `data/golden/`)

1. Đăng nhập `compliance` → Tổng quan có 2 card: Add Regulatory Source / Check Document Compliance.
2. **Thêm nguồn pháp lý**: upload `data/golden/regulatory_sources/tt_08_2026_nhnn.txt` — banner "chưa phải nguồn pháp lý".
3. Bấm Activate ngay → **409 REVIEW_NOT_COMPLETED** hiển thị trên UI.
4. Vào Review inbox → Approve → Activate thành công (V1 đóng, V2 mở, ChangeEvent lưu).
5. **Impact Report**: nhập document ID → executive summary, before/after 34%→30%, policy nội bộ bị ảnh hưởng + severity.
6. **Kiểm tra tuân thủ**: upload `data/golden/review_targets/bao_cao_tuan_thu_outdated.txt` — claim 34%/500tr bị `OUTDATED_REFERENCE`, kèm version đúng, evidence bị loại và recommendation. File không vào KB.
7. **System Health**: PostgreSQL/OpenSearch/Neo4j/embedding/LLM thật hay fallback.

Ground truth để đối chiếu: `data/golden/ground_truth.json`.

## Kiến trúc

```
packages/contracts  Pydantic contracts (FROZEN)    backend/app/workflows/  compliance_checks + impact_analysis (Final spec)
packages/common     vn_normalize, tokenize, ids    backend/app/api/        routes compliance/impact/health details
infra/              postgres · opensearch · neo4j  ingestion/  upload → review → activation gate (đường ghi)
llm/                client (google|openai|mock)    query/      temporal filter → BM25∪vector RRF → graph → evidence
api/                FastAPI + JWT + RBAC           ui/         Streamlit (2 workflow + review + impact + health)
```

PostgreSQL là source of truth trạng thái; OpenSearch/Neo4j là index/graph phục vụ retrieval — không quyết định trạng thái.

## Limitations (trung thực)

- Đang giữa migration: cây legacy (`api/ ingestion/ query/ infra/ ui/`) và cây canonical (`backend/app/`) song song; route mới đã nằm ở `backend/app/`, chưa xóa legacy (spec M10).
- OCR fallback cho PDF scan chưa bật; DOCX parser chưa có — golden dùng text thật từ crawl SBV.
- `EVIDENCE_NOT_VALID`/`TARGET_NOT_RESOLVED` đã chuẩn hóa code nhưng resolver nâng cao (EXACT/MULTIPLE/NOT_FOUND đầy đủ) chưa hoàn chỉnh.
- Sync theo kiểu outbox-lite: index/graph fail không phá Postgres commit và hiển thị `INDEX_SYNC_PENDING` (test T10), nhưng chưa có worker retry tự động.
- Policy mapping tự động chỉ theo citation tường minh ("Điều N + số hiệu"); không map ngữ nghĩa (đúng spec §7.5 — không đoán target).
- Benchmark §11.4: 4 metric đo được đều PASS (`scripts/golden_benchmark.py`); parser/target-resolution metrics chưa đo vì thiếu labeled GT — ghi NOT MEASURED, không bịa số.
