# RegVault — Team Brief: Sản phẩm, Đặc tả kỹ thuật & Kho tri thức code

> Tài liệu nội bộ cho team: hiểu sản phẩm để thuyết trình, hiểu kỹ thuật để trả lời giám khảo,
> hiểu code để không ai bị hỏi bí. Đọc kèm: [`PITCH.md`](PITCH.md) (pitch ngoài),
> [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md) (kịch bản demo), [`project.md`](project.md) (kiến trúc sâu).

---

## 1. RegVault trong 30 giây (học thuộc)

**RegVault = kho quy định ngân hàng đã được xác minh + máy kiểm tra tuân thủ chạy trên chính kho đó.**

Hai luồng, một nguyên tắc:
- **Luồng A — Add Regulatory Source:** thông tư/quyết định/văn bản sửa đổi upload vào KHÔNG tự động thành nguồn pháp lý. Nó phải qua parse → review package → **con người duyệt** → activation gate → versioning. Chỉ khi đó nó mới là `AUTHORITY_SOURCE`.
- **Luồng B — Check Document Compliance:** policy/báo cáo nội bộ upload vào để **kiểm tra**, không bao giờ vào kho tri thức. Máy trích từng claim ("hạn mức 500 triệu", "tỷ lệ 34%"), đối chiếu với kho đã duyệt **tại đúng ngày review**, trả về COMPLIANT / NON_COMPLIANT / OUTDATED_REFERENCE / MISSING_EVIDENCE… kèm bằng chứng.

Nguyên tắc xuyên suốt (câu ăn điểm): **"Không file nào được mặc định là ground truth, và LLM không bao giờ quyết định điều gì quan trọng."** Version, hiệu lực, patch sửa đổi, trạng thái tuân thủ — tất cả do luật tất định (deterministic Python) + graph quyết. LLM chỉ viết văn xuôi trên bằng chứng đã lắp ráp sẵn.

---

## 2. Vì sao thắng đám đông (differentiation — dùng khi thuyết trình)

Đa số đội sẽ nộp "chatbot RAG hỏi đáp văn bản". RegVault khác ở 4 điểm mà chatbot RAG thường sai:

| # | Năng lực | Chatbot RAG thường | RegVault |
|---|----------|--------------------|----------|
| 1 | **Đúng phiên bản theo thời gian** | Trả lời theo chunk giống nhất — hay dính văn bản đã hết hiệu lực | Temporal filter chạy **trước** top-k; hỏi "tháng 3/2026" ra 500tr (V1), hỏi "hiện nay" ra 700tr (V2), kèm lý do loại V1 |
| 2 | **Sửa đổi một phần (partial amendment)** | Không áp dụng được "thay cụm X bằng Y tại Khoản 2" | Patch engine tất định: REPLACE_TEXT/REPLACE_PROVISION/INSERT_AFTER/DELETE/REPEAL, exact-match, lệch là đẩy human review |
| 3 | **Tác động lên nội bộ** | Không biết policy nội bộ nào bị ảnh hưởng | Impact Report: amendment đóng V1 → mọi policy `ALIGNED_TO` V1 bị flag kèm severity |
| 4 | **Biết từ chối** | Bịa khi không có căn cứ | MISSING_EVIDENCE khi kho không đủ mạnh; citation ngoài allowlist bị chặn |

Demo head-to-head có sẵn trong UI (trang "So sánh"): Standard RAG trả lời sai 500tr, RegVault trả 700tr đúng — cùng câu hỏi, cùng corpus.

---

## 3. Đặc tả kỹ thuật (trả lời giám khảo Vòng 2)

### 3.1 Stack & kiến trúc

```
Streamlit UI ──HTTP──> FastAPI (JWT + RBAC: COMPLIANCE_OFFICER)
                          │
        ┌─────────────────┼──────────────────────┐
   Luồng A (ghi)     Luồng B (đọc)          Truy vấn/QA
   ingestion/*       workflows/              query/*
   upload→parse→     compliance_checks/*     temporal filter
   review→GATE→      claim→evidence→         → BM25 ∪ vector RRF
   version→index     compare→report          → graph expansion
                          │                  → evidence package
        ┌────────────┬────┴────────┬─────────────┐
   PostgreSQL    OpenSearch      Neo4j        LLM client
   (source of    (BM25+vector,   (AMENDS,     (google|openai|
   truth trạng   temporal        SUPERSEDES,   openrouter|mock)
   thái)         metadata)       ALIGNED_TO)
```

- **PostgreSQL là nơi duy nhất quyết định trạng thái** (approval, version, review). OpenSearch/Neo4j chỉ là index/graph phục vụ retrieval — sync fail thì Postgres vẫn đúng, doc gắn cờ `INDEX_SYNC_PENDING` (outbox-lite, test T10).
- **Mọi backend có bản in-memory fallback** → `DEMO_MODE=true` chạy offline không cần Docker/API key. `/health/details` introspect **instance thật** đang chạy (không echo config) — fallback không bao giờ bị giấu.

### 3.2 Data model lõi (5 khái niệm phải thuộc)

1. **Document** — file + metadata + `approval_status` + `type` (REGULATION/AMENDMENT/INTERNAL_POLICY).
2. **Provision** — danh tính ỔN ĐỊNH của một Điều/Khoản/Điểm, tách khỏi nội dung.
3. **ProvisionVersion** — nội dung theo thời gian, khoảng nửa-mở `[valid_from, valid_to_exclusive)`. Amendment không sửa V1; nó **đóng** V1 và **mở** V2. Lịch sử bất biến.
4. **ChangeEvent** — bản ghi "ai sửa gì": operation, before/after version, ngày hiệu lực, review_status.
5. **InternalArtifact (ALIGNED_TO)** — policy nội bộ neo vào một version cụ thể; version bị supersede → policy bị flag trong Impact Report.

### 3.3 Trust model (điểm ăn tiền phần An toàn AI)

```
is_legal_ground_truth = AUTHORITY_SOURCE ∧ APPROVED ∧ ACTIVE
                        ∧ valid_from ≤ query_date < valid_to_exclusive
```

- Upload luồng A = `AUTHORITY_SOURCE_CANDIDATE` — retrieval chính thức **không thấy** (test T1).
- Upload luồng B = `REVIEW_TARGET` — **không bao giờ** được index/persist làm nguồn (test T4).
- Activate khi còn critical review → **HTTP 409 `REVIEW_NOT_COMPLETED`** ở service layer (không route nào bypass được — test T2/T3).
- Prompt-injection: nội dung file bọc trong `<EVIDENCE>` delimiter, là DATA không phải lệnh; có injection scan khi upload; golden có file injection để demo.
- Citation verifier: câu trả lời chỉ được cite ID trong allowlist evidence — cite bịa bị từ chối (test T12).

### 3.4 Compliance engine (luồng B) — thuật toán

1. **Claim extraction** (rule-based): tách câu, giữ câu có fact kiểm được — tiền VND, %, deadline, số hiệu văn bản, modality ("không được", "tối đa"). Regex + chuẩn hóa tiếng Việt (`vn_normalize`), không LLM.
2. **Evidence retrieval per claim:** đi qua đúng pipeline QA (temporal pre-filter → BM25 ∪ vector → RRF → graph expansion → supersession resolution) — chỉ thấy nguồn APPROVED tại review date.
3. **So sánh tất định:** fact của claim vs fact của evidence hiện hành vs fact của version đã bị thay thế:
   - khớp hiện hành → COMPLIANT · khớp bản CŨ → OUTDATED_REFERENCE · lệch → NON_COMPLIANT
   - vừa khớp vừa lệch → PARTIALLY_COMPLIANT · khớp nhưng có quy định đồng-hiệu-lực xung đột → AMBIGUOUS
   - không có gì đủ mạnh → MISSING_EVIDENCE · không có fact so được → NEEDS_HUMAN_REVIEW
4. **Report:** JSON ổn định (Phụ lục B.3 spec) — mỗi claim kèm valid_evidence, excluded_evidence + lý do loại, explanation, recommendation, confidence.

**LLM đứng ở đâu?** Chỉ ở bước viết giải thích văn xuôi (và có mock thay thế). Status KHÔNG BAO GIỜ do LLM chọn.

### 3.5 Impact engine (luồng A, sau activate)

`ChangeEvent APPROVED` → tìm mọi `InternalArtifact` aligned với `before_version` → so obligation (ngưỡng tiền chuẩn hóa VND, modality) với version mới → severity: lệch ngưỡng = HIGH, lệch modality = MEDIUM, chỉ aligned = LOW. Mapping `ALIGNED_TO` được tạo **tự động theo citation tường minh** khi activate policy ("Điều 1 88/2026/QĐ-NHNN" → đúng provision đó); 0 hoặc >1 ứng viên → không đoán (nguyên tắc spec: no guessing).

### 3.6 API chính

| Method | Path | Ý nghĩa |
|---|---|---|
| POST | `/login` | JWT (compliance/compliance123) |
| POST | `/documents` + `/documents/{id}/activate` | Luồng A: upload + activate (409 nếu còn review) |
| GET/POST | `/review-tasks`, decision | Human review inbox |
| POST/GET | `/compliance-checks`, `/{id}/report` | Luồng B end-to-end |
| GET | `/regulatory-sources/{id}/impact-report` | Regulatory Impact Report |
| POST | `/query`, `/compare` | QA + head-to-head vs Standard RAG |
| GET | `/health/details` | Backend thật/fallback, `BACKEND_DEGRADED` |

Error envelope ổn định: `{"error": {"code": "REVIEW_NOT_COMPLETED", "message", "details": {"reasons": [...]}}}` — UI match theo `code`, không parse text.

---

## 4. Kho tri thức code — cái gì nằm ở đâu, test nào chứng minh

### 4.1 Bản đồ module

| Vùng | Đường dẫn | Nội dung | Test chứng minh |
|---|---|---|---|
| Contracts | `packages/contracts/` | Enum + Pydantic models FROZEN (wire format chung 3 track) | mọi test import |
| Chuẩn hóa TV | `packages/common/vn_normalize.py`, `vn_tokenize.py` | tiền→VND, ngày, stopword tiếng Việt | `test_vn_normalize.py` |
| Hạ tầng | `infra/` | postgres ORM, opensearch client, neo4j client, embeddings — mỗi cái kèm in-memory fallback | `test_trust_gates.py` (T11) |
| Luồng A | `ingestion/` (12 module) | upload→quarantine→injection scan→parse→review inbox→**activation gate**→patch→index | `test_ingestion_pipeline.py`, `test_activation_gate.py` (T2/T3), `test_ingestion_patch.py` (T9), `test_policy_mapping_and_sync.py` (T10) |
| Luồng QA | `query/` (13 module) | temporal filter, hybrid RRF, graph expansion, validity, conflict, evidence package, citation check, standard_rag baseline | `test_query_pipeline.py` (T12), `test_temporal_filter.py` |
| **Luồng B** | `backend/app/workflows/compliance_checks/` | claim_extractor → assessor → report_builder → service | `test_compliance_check.py` (T5-T8), `test_trust_gates.py` (T4), `test_golden_dataset.py` |
| **Impact** | `backend/app/workflows/impact_analysis/` | candidate_finder, impact_engine, report_builder, **policy_mapper** | `test_impact_report.py`, `test_policy_mapping_and_sync.py` |
| Domain mới | `backend/app/domain/compliance.py`, `impact.py` | TrustClass, UploadPurpose, ComplianceStatus, `is_legal_ground_truth`, report contracts | như trên |
| API mới | `backend/app/api/routes_{compliance_checks,impact_reports,health}.py` + `core/errors.py` | 3 nhóm route Final-spec + 6 error code ổn định | smoke TestClient + T11 |
| UI | `ui/app.py` (canonical entry: `frontend/streamlit_app/app.py`) | 11 trang: Tổng quan 2-card, Add Source, Kiểm tra tuân thủ, Review inbox, Impact Report, System Health, Hỏi đáp, So sánh, KG, Dashboard, Audit | `test_eval_metrics.py::test_ui_imports` |
| Crawl | `crawl/` + `data/crawl/` | crawler SBV/VBPL/TVPL + hybrid pairs — **số hiệu & quan hệ sửa đổi THẬT** (08/2026→22/2019...) | `crawl/audit.py` |
| Golden | `data/golden/` + `ground_truth.json` | 9 fixture: base+amendment+hợp nhất (text SBV thật), 2 policy, 4 review target (compliant/outdated/thiếu căn cứ/injection) | `test_golden_dataset.py` — GT là **load-bearing**, engine chạy thật trên từng file |
| Benchmark | `scripts/golden_benchmark.py` | 4 metric §11.4 đo thật; metric thiếu labeled GT ghi NOT MEASURED | chạy `python -m scripts.golden_benchmark` |

### 4.2 Con số nói được ngay

- **108 test pass** (`python -m pytest tests/ -q`), phủ đủ **12/12 test bắt buộc** T1–T12 của spec.
- Benchmark golden: **claim accuracy 100% (6/6)**, 0 superseded-evidence lọt vào valid, 0 ground-truth-admission violation, 0 activation bypass.
- Corpus thật: crawl SBV 40+ văn bản, 3 cặp amendment hoàn chỉnh 2 đầu (vd `08/2026/TT-NHNN` sửa `22/2019/TT-NHNN` — tỷ lệ vốn ngắn hạn 34%→30%, dùng làm golden domain).
- Đã qua **PM-audit độc lập** (agent riêng soi từng claim "đã xong") — 4 blocker nó tìm ra đều đã vá và có commit riêng (`ea0464e`).

### 4.3 Hạn chế PHẢI nói trung thực nếu bị hỏi (đừng giấu — giấu là mất điểm Trust)

- Repo đang giữa migration: cây legacy (`api/ ingestion/ query/...`) và cây canonical (`backend/app/`) song song; module mới đã ở đúng chỗ canonical, phần dọn legacy là việc sau hackathon.
- OCR cho PDF scan chưa bật (golden dùng text thật từ crawl); DOCX parser chưa có.
- Policy mapping chỉ theo citation tường minh — theo đúng spec "không đoán", nhưng nghĩa là policy không cite số hiệu sẽ không tự map (cần người map tay).
- Metric parser/target-resolution ghi NOT MEASURED vì thiếu labeled ground truth — chúng tôi không bịa số.
- Với DEMO_MODE, embedding/LLM là fallback — hiển thị công khai ở System Health; benchmark generation-dependent chỉ tính khi chạy LLM thật.

---

## 5. Mapping 6 tiêu chí chấm điểm (100đ) — đứng đâu, nói gì

### 5.1 Chất lượng triển khai kỹ thuật — 20đ
**Bằng chứng:** 108 test + 12/12 test spec + benchmark PASS + clone-run một lệnh không cần Docker (`DEMO_MODE=true`). Kiến trúc 4-store có fallback từng lớp. Versioning nửa-mở + patch tất định là phần khó nhất và có test dày nhất.
**Câu nói:** "Mỗi invariant an toàn của hệ thống là một test có thể chạy lại trước mặt anh/chị ngay bây giờ."

### 5.2 Kiến trúc AI-Native & Đổi mới — 20đ
**Bằng chứng:** không phải "RAG + prompt". Đổi mới nằm ở: (1) temporal pre-filter TRƯỚC retrieval; (2) provision identity tách khỏi content → amendment là thao tác dữ liệu, không phải re-ingest; (3) hai luồng trust tách biệt — file kiểm tra không bao giờ nhiễm vào kho; (4) impact propagation qua graph ALIGNED_TO.
**Câu nói:** "AI-native không có nghĩa là LLM làm mọi thứ — mà là thiết kế để LLM chỉ đứng ở chỗ nó giỏi (ngôn ngữ), còn chỗ phải đúng tuyệt đối (hiệu lực, phiên bản, trạng thái) là code tất định."

### 5.3 Tính khả thi kinh doanh & Lộ trình Pilot — 20đ
**Bằng chứng:** persona duy nhất rõ ràng (Compliance Officer SHB); bài toán đo được (giờ công đọc-đối chiếu văn bản, rủi ro dùng nhầm version); pilot path: chạy trên 1 golden domain (giới hạn tín dụng) → mở rộng theo mảng nghiệp vụ; on-prem được (toàn stack self-host, LLM swap được).
**Câu nói:** "Pilot không cần migration dữ liệu: bắt đầu bằng chính quy trình review văn bản mới mà phòng Tuân thủ đang làm tay hằng tuần."
*(Phần này cần người phụ trách business bồi thêm số liệu — brief này chỉ nêu khung.)*

### 5.4 UX AI-Native & Tư duy thiết kế — 15đ
**Bằng chứng:** landing 2 card đúng 2 job-to-be-done; banner "chưa phải nguồn pháp lý" trên candidate; lỗi 409 hiển thị thành hướng dẫn hành động ("mở Review inbox"); mỗi kết luận mở được evidence + **lý do loại** nguồn cũ (panel "Vì sao"); badge fallback/real ở System Health — người dùng luôn biết đang tin cái gì.
**Câu nói:** "UX của chúng tôi thiết kế quanh một câu hỏi: *người pháp chế cần thấy gì để DÁM ký?* — đó là evidence, version, ngày hiệu lực và cái gì đã bị loại."

### 5.5 An toàn AI, Grounding & Độ tin cậy — 15đ (điểm mạnh nhất của mình)
**Bằng chứng:** trust model + hard gate 409 + citation allowlist + evidence delimiter chống injection (có golden injection file demo được) + MISSING_EVIDENCE thay vì bịa + health trung thực + audit trail. Tất cả có test: T1–T12.
**Câu nói:** "Hallucination không phải bug phải vá — nó bị chặn từ kiến trúc: LLM không có quyền tạo fact, cite ngoài allowlist bị từ chối, và khi thiếu căn cứ hệ thống nói thẳng là thiếu."

### 5.6 Trình bày & Bảo vệ giải pháp — 10đ
Dùng `DEMO_SCRIPT.md`. Khung 4 phút đề xuất: 0:00–0:30 vấn đề (một câu chuyện: NHNN đổi tỷ lệ 34%→30%, báo cáo nội bộ vẫn ghi 34%) → 0:30–2:30 demo sống 2 luồng (upload → 409 → approve → activate → Impact Report → upload báo cáo → OUTDATED_REFERENCE đỏ kèm khuyến nghị) → 2:30–3:30 head-to-head vs Standard RAG → 3:30–4:00 trust model + pilot. Q&A: xem mục 6.

---

## 6. Q&A dự kiến (Vòng 3 — 2 phút hỏi đáp)

| Câu hỏi giám khảo | Trả lời ngắn |
|---|---|
| "Khác gì ChatGPT + upload file?" | ChatGPT không biết văn bản nào đang có hiệu lực ngày nào, không áp dụng được sửa đổi một phần, và coi mọi file upload là sự thật. Ba cái đó là toàn bộ nghề của pháp chế — và là phần tất định của RegVault. |
| "LLM sai thì sao?" | LLM không được quyền sai chỗ quan trọng — nó không chọn version, không quyết status, không tạo citation. Sai nhất là văn xuôi kém, và mock-mode chứng minh hệ vẫn chạy đúng không cần LLM. |
| "Dữ liệu thật hay tự chế?" | Số hiệu văn bản + quan hệ sửa đổi mine từ crawl SBV thật (08/2026/TT-NHNN sửa 22/2019/TT-NHNN). Nội dung điều khoản trong demo domain được stylize và dán nhãn rõ — ground_truth.json khai báo từng phần. |
| "Scale thế nào?" | Postgres/OpenSearch/Neo4j đều scale ngang chuẩn công nghiệp; ingest là pipeline theo document nên song song hóa tự nhiên; điểm nghẽn duy nhất là human review — và đó là feature, không phải bug: chỉ nguồn được duyệt mới vào kho. |
| "Nếu parser sai thì sao?" | Mọi extraction mang evidence + confidence; lệch giữa rule và LLM tạo critical review task; và gate chặn activate tới khi người duyệt xong. Sai của máy dừng ở bàn review, không lọt vào kho. |
| "Chưa làm được gì?" | Đọc thẳng mục Limitations trong README (OCR, dọn legacy tree, mapping ngữ nghĩa). Giám khảo tin đội biết rõ giới hạn của mình hơn đội nói "xong hết". |

---

## 7. Checklist theo 3 vòng

**Vòng 1 — AI sơ loại (tự động đọc repo):** README đã đúng chuẩn (tên sản phẩm, one-liner, trust model, 2 workflow, run 1 lệnh, limitations). Giữ README sạch — nó là thứ AI đọc đầu tiên. ✅
**Vòng 2 — Giám khảo chuyên môn:** họ sẽ clone và soi. Điểm dẫn đường: `README → golden demo 7 bước → pytest → scripts/golden_benchmark → docs/TEAM_BRIEF.md (file này) → docs/project.md`. Mỗi thành viên nắm chắc mục 3 + 4 của brief này.
**Vòng 3 — Demo Day (4'+2'):** chạy theo `DEMO_SCRIPT.md`; backup: quay video demo trước phòng khi mạng/máy trục trặc; người trả lời Q&A dùng mục 6.
