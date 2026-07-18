# Compliance Regulatory Knowledge & Document Review Platform

**VAIC2026 — SHB1** · Temporal Hybrid GraphRAG cho nghiệp vụ Pháp chế/Tuân thủ ngân hàng

> Một luồng giúp pháp chế **xác minh quy định trước khi đưa vào kho tri thức**; một luồng dùng chính kho đã xác minh đó để **kiểm tra policy và báo cáo** — không file nào được mặc định là ground truth.

`218 test pass` · `chạy 1 lệnh, không cần Docker` · `4/8 acceptance metric đo được đều PASS, 4 metric ghi rõ NOT MEASURED`

📄 [Kiến trúc chi tiết](docs/project.md) · [Spec chuẩn](docs/_final_spec_extracted.md) · [Brief cho đội](docs/TEAM_BRIEF.md)

---

## ⚡ Chạy trong 60 giây

```bash
pip install -r requirements.txt
DEMO_MODE=true SEED_DEMO=1 uvicorn api.main:app --port 8000     # Linux/macOS/Git Bash
```
```powershell
$env:DEMO_MODE="true"; $env:SEED_DEMO="1"; uvicorn api.main:app --port 8000   # Windows
```

Tab mới → UI:
```bash
streamlit run ui/app.py            # http://localhost:8501
```

Không cần Docker, không cần API key. `DEMO_MODE=true` dùng stub in-memory và **báo trung thực trạng thái fallback** tại `/health/details` + trang System Health.

### Tài khoản demo

| Tài khoản | Mật khẩu | Vai trò |
|---|---|---|
| `compliance` | `compliance123` | EMPLOYEE |
| `user` | `user123` | EMPLOYEE |
| `employee` | `employee123` | EMPLOYEE |

Cả ba đều là `EMPLOYEE` — vai trò nghiệp vụ duy nhất được hỗ trợ.

---

## 🎯 Phép thử quyết định (90 giây)

Đây là thứ phân biệt hệ thống này với mọi công cụ hỏi-đáp-tài-liệu khác. Ban giám khảo tự gõ được:

```
Hỏi: "Tỷ lệ tối đa vốn ngắn hạn cho vay trung dài hạn là bao nhiêu?"

@2026-03-01 → "…là 34%. [ver-ratio-v1]"
              excluded: ver-ratio-v2 — NOT_VALID_AT_QUERY_DATE

@2026-09-01 → "…là 30%. [ver-ratio-v2]"
              excluded: ver-ratio-v1 — NOT_VALID_AT_QUERY_DATE
```

Cùng một câu hỏi, cùng một kho tài liệu, hai câu trả lời đúng — vì **hiệu lực pháp lý phụ thuộc thời điểm**. Không có trục thời gian thì không trả lời được câu thứ hai.

---

## Bài toán

Khi NHNN ban hành văn bản sửa đổi, cán bộ Tuân thủ phải tự xác định: văn bản nào bị sửa, Điều/Khoản nào thay đổi, nội dung trước–sau, ngày hiệu lực, và policy nội bộ nào bị ảnh hưởng. Khi soạn báo cáo mới, họ còn phải kiểm tra từng phát biểu có khớp quy định **đang hiệu lực** không.

Làm tay thì dễ dùng nhầm phiên bản cũ, bỏ sót amendment, và không truy vết được bằng chứng khi bị hỏi lại.

**Ví dụ thật trong golden dataset:** TT 22/2019 quy định tỷ lệ 34%; văn bản 2026 sửa xuống 30% hiệu lực 01/07/2026. Báo cáo tuân thủ nội bộ vẫn ghi 34% → hệ thống gắn `OUTDATED_REFERENCE`, chỉ ra bản đúng, và đề xuất sửa.

---

## Tại sao không dùng NotebookLM / ChatGPT?

Câu trả lời trung thực: **cho phần lớn nhu cầu hỏi đáp tài liệu, NotebookLM tốt hơn và gần như miễn phí.** Chúng tôi không cạnh tranh ở đó.

Nhưng chính tài liệu của Google ghi nhận NotebookLM **chụp ảnh tĩnh nguồn tại thời điểm thêm vào**, và khi có tài liệu mâu thuẫn thì *"đôi khi trộn dữ liệu gây nhầm lẫn, hoặc bám vào thông tin cũ ngay cả khi đã nạp phiên bản mới hơn"* — hiện tượng gọi là **knowledge base contamination**. Khuyến nghị khắc phục: người dùng **tự tách notebook** để tránh trộn cũ với mới.

Với pháp chế, "tự tránh" chính là công việc cần được tự động hoá.

| | NotebookLM | Hệ thống này |
|---|---|---|
| Trả lời theo ngày hiệu lực | Không có khái niệm | `@2026-03-01 → 34%` · `@2026-09-01 → 30%` |
| Sửa đổi văn bản | Thêm 1 file nữa vào đống | `REPLACE_PROVISION` sinh V2, đóng V1, giữ lịch sử |
| Cổng duyệt trước khi thành căn cứ | Upload xong dùng ngay | `409 REVIEW_NOT_COMPLETED` tới khi người duyệt |
| Nguồn nào bị loại và vì sao | Không trả lời được | `excluded_evidence` + lý do (`SUPERSEDED_AT_QUERY_DATE`…) |

Cột cuối quan trọng hơn vẻ ngoài: NotebookLM cho biết nó **dùng** gì; hệ thống này cho biết nó **cố ý không dùng** gì — đó là thứ cán bộ pháp chế cần để dám ký.

---

## Trust model — bất biến trung tâm

Không tài liệu nào trở thành ground truth chỉ vì được upload.

```
is_legal_ground_truth(doc, query_date) =
      trust_class      == AUTHORITY_SOURCE
  AND approval_status  == APPROVED
  AND lifecycle_status == ACTIVE
  AND valid_from <= query_date < valid_to_exclusive
```

| Trust class | Được làm căn cứ pháp lý? |
|---|---|
| `AUTHORITY_SOURCE_CANDIDATE` | Không — vừa upload, chưa duyệt |
| `AUTHORITY_SOURCE` | **Có** — đã approve + activate |
| `INTERNAL_APPROVED` | Không — là đối tượng mapping/impact |
| `REVIEW_TARGET` | Không — file cần kiểm tra, không bao giờ vào KB |
| `UNVERIFIED` | Không |

**LLM không bao giờ quyết định điều gì quan trọng.** Version, hiệu lực, patch, trạng thái đều do luật tất định + graph quyết. LLM chỉ viết văn xuôi trên evidence đã lắp ráp sẵn, và bị chặn ở 4 chỗ: không activate, không ghi DB, không sinh stable ID, không tự chọn ground truth.

---

## Hai workflow

| | **A — Add Regulatory Source** | **B — Check Document Compliance** |
|---|---|---|
| Vào | Thông tư/quyết định/amendment | Policy/báo cáo/tài liệu nội bộ |
| Qua | Parse → review package → Human Review → activation gate → versioning | Claim extraction → retrieve evidence APPROVED+ACTIVE tại review date → so tất định |
| Ra | Nguồn ACTIVE + ChangeEvent + **Regulatory Impact Report** | **Compliance Review Report** theo từng claim |

Trạng thái claim: `COMPLIANT` · `NON_COMPLIANT` · `PARTIALLY_COMPLIANT` · `OUTDATED_REFERENCE` · `MISSING_EVIDENCE` · `AMBIGUOUS` · `NEEDS_HUMAN_REVIEW`

Workflow B không chạy đúng nếu A chưa tạo được kho nguồn đã xác minh — hai bước của cùng một bài toán, không phải hai sản phẩm.

---

## Chat modes

Một AI assistant, các mode có trust boundary khác nhau (spec: `docs/VAIC2026_Mode_Based_Chat_and_Review_Expansion_Spec.docx`):

| Mode | Ngữ cảnh | Endpoint |
|---|---|---|
| **Ask Regulations** | Multi-turn RAG; history chỉ của đúng conversation; attachment = context cục bộ, không phải nguồn pháp lý | `POST /conversations` → `/messages` |
| **Document Review — Single** | Review Run **bất biến**: freeze assessment_date + knowledge snapshot + prompt/schema version | `POST /review-runs` → `/questions` |
| **Document Review — Batch** | 1 file = 1 Review Run độc lập; recurring issue groups; retry failed-only | `POST /batch-reviews` → `/questions` |

Invariants có test: cross-chat leakage 0% · review target không vào KB · kết quả locked (prompt không đổi được status) · frozen snapshot (activate nguồn mới không đổi run cũ) · citation allowlist · owner scope từ token.
→ `tests/test_chat_isolation.py`, `test_review_run.py`, `test_batch_review.py`

---

## 🎬 Golden demo (7 bước, dữ liệu `data/golden/`)

1. Đăng nhập `compliance` → Tổng quan có 2 card: Add Regulatory Source / Check Document Compliance
2. **Thêm nguồn**: upload `data/golden/regulatory_sources/tt_08_2026_nhnn.txt` → banner **"chưa phải nguồn pháp lý"**
3. Bấm Activate ngay → **409 `REVIEW_NOT_COMPLETED`** hiển thị trên UI
4. Review inbox → Approve → Activate thành công (V1 đóng, V2 mở, ChangeEvent lưu)
5. **Impact Report**: executive summary, before/after 34%→30%, policy nội bộ bị ảnh hưởng + severity
6. **Kiểm tra tuân thủ**: upload `data/golden/review_targets/bao_cao_tuan_thu_outdated.txt` → claim 34% bị `OUTDATED_REFERENCE` kèm version đúng, evidence bị loại, recommendation. File **không** vào KB
7. **System Health**: PostgreSQL/OpenSearch/Neo4j/embedding/LLM — thật hay fallback

Ground truth đối chiếu: `data/golden/ground_truth.json`

---

## 🧪 Bằng chứng

```bash
python -m pytest                    # 218 passed — chạy từ gốc repo
python -m scripts.golden_benchmark  # acceptance metrics §11.4 trên golden dataset
python -m eval.run_eval             # head-to-head vs Standard RAG
```

**Acceptance metrics (§11.4)** — số thật, không làm tròn:

| Metric | Kết quả | Ngưỡng | |
|---|---|---|---|
| Claim assessment accuracy | 100% (6/6) | ≥ 85% | ✅ PASS |
| Superseded evidence lọt vào valid_evidence | 0 | ≤ 5% | ✅ PASS |
| Ground-truth admission violations | 0 | 0 | ✅ PASS |
| Activation bypass | 0 | 0 | ✅ PASS |
| Parser boundary accuracy | — | ≥ 90% | ⚠️ NOT MEASURED |
| Amendment operation accuracy | — | ≥ 85% | ⚠️ NOT MEASURED |
| Target resolution accuracy | — | ≥ 85% | ⚠️ NOT MEASURED |
| Citation correctness | — | ≥ 85% | ⚠️ NOT MEASURED |

4 metric chưa đo vì thiếu labeled ground truth cho parse/resolution. Chúng tôi ghi `NOT MEASURED` thay vì bịa số.

**Test scenario theo spec §11.2**: T1 (candidate vô hình trước activation), T2 (409 khi pending), T3 (activate xong dùng được), T4 (review target không vào index), T5–T8 (4 trạng thái claim), T10 (index fail → Postgres giữ nguyên, hiện `INDEX_SYNC_PENDING`), T11 (`DEMO_MODE=false` báo degraded).

---

## Thật hay mock?

Bảng này để ban giám khảo không phải đoán:

| Thành phần | `DEMO_MODE=true` | `docker compose up` |
|---|---|---|
| PostgreSQL | SQLite | ✅ thật |
| OpenSearch | in-memory stub | ✅ thật |
| Neo4j | in-memory stub | ✅ thật |
| Embedding | hash fallback | ✅ BGE-M3 |
| LLM | mock tất định | ✅ Gemini/OpenAI (cần key) |
| Temporal filter · versioning · patch · activation gate · citation check | ✅ **code thật ở cả hai chế độ** | ✅ |

Hàng cuối là điểm quan trọng: **logic quyết định tính đúng đắn không bao giờ bị mock**. Mock chỉ nằm ở tầng hạ tầng và tầng sinh văn xuôi.

---

## Kiến trúc

```
packages/contracts   Pydantic contracts (FROZEN)      backend/app/workflows/   compliance_checks · impact_analysis
packages/common      vn_normalize · tokenize · ids    backend/app/api/         routes compliance · impact · health
infra/               postgres · opensearch · neo4j    ingestion/               upload → review → activation gate
llm/                 client (google|openai|mock)      query/                   temporal filter → BM25∪vector RRF → graph
api/                 FastAPI + JWT + RBAC             ui/                      Streamlit (2 workflow + review + impact)
frontend/nextjs_app  Next.js — Chat Modes (deployed)  data/golden/             golden dataset + ground_truth.json
```

**PostgreSQL là source of truth trạng thái.** OpenSearch/Neo4j là index/graph phục vụ retrieval — không quyết định trạng thái. Index fail không phá Postgres commit (outbox-lite, T10).

Thứ tự xử lý query — **bộ lọc thời gian chạy TRƯỚC top-k**, không phải sau:
```
query + query_date → temporal pre-filter → BM25 ∪ vector → RRF → graph expansion
                   → evidence package (valid + excluded + lý do) → LLM viết văn xuôi
                   → citation allowlist check → answer
```

---

## Phạm vi 48 giờ

**Làm được:** temporal versioning end-to-end · activation hard gate · 2 workflow đầy đủ · Impact Report · Compliance Review Report · golden dataset 8 hạng mục · 218 test · chạy 1 lệnh không cần Docker

**Cố ý bỏ qua:** OCR cho PDF scan · DOCX parser · worker retry tự động · policy mapping ngữ nghĩa · multi-tenant · UI polish

Chúng tôi ưu tiên **một golden domain đủ sâu** (giới hạn tín dụng + tỷ lệ vốn ngắn hạn) thay vì phủ rộng nông — vì bài toán này chỉ có giá trị khi đúng đến từng phiên bản.

---

## ⚠️ Limitations (trung thực)

- **Hai cây code song song**: legacy (`api/ ingestion/ query/ infra/ ui/`) và canonical (`backend/app/`). Runtime hiện chạy legacy; route mới nằm ở `backend/app/`. Chưa cut-over (spec M10).
- **Hai app frontend**: `frontend/nextjs_app` (đang deploy) và `frontend/web` (dựng theo Final spec §10, 10 màn hình). Cần hợp nhất — hiện chưa.
- **Hai cây test**: `tests/` (131 test, có nhãn T1–T12) và `backend/tests/` (bản cũ hơn). Chạy `pytest` từ gốc là 218 test vì cộng cả hai.
- **OCR fallback cho PDF scan chưa bật**, DOCX parser chưa có — golden dùng text thật từ crawl SBV.
- **Resolver nâng cao chưa hoàn chỉnh**: `EVIDENCE_NOT_VALID`/`TARGET_NOT_RESOLVED` đã chuẩn hoá error code, nhưng phân loại EXACT/MULTIPLE/NOT_FOUND đầy đủ thì chưa.
- **Outbox-lite chưa có worker retry tự động**: index/graph fail hiển thị `INDEX_SYNC_PENDING` nhưng phải sync tay.
- **Policy mapping chỉ theo citation tường minh** ("Điều N + số hiệu"), không map ngữ nghĩa — đúng spec §7.5, không đoán target.
- **4 acceptance metric chưa đo** (bảng trên) vì thiếu labeled GT cho parse/resolution.

---

## Chạy đầy đủ 4-store

```bash
cp .env.example .env          # điền GOOGLE_API_KEY nếu dùng LLM thật
docker compose up --build     # postgres · opensearch · neo4j · api(:8000) · ui(:8501) · web(:3000)
```
