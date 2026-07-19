<div align="center">

# AIDE

### AI for Information Discovery, Document Evaluation & Evidence

**Trợ lý AI có nhận thức thời gian cho Pháp chế & Tuân thủ ngân hàng**

**Đúng quy định · Đúng phiên bản · Có bằng chứng**

<br/>

**Vietnam AI Innovation Challenge 2026**  
**Sản phẩm hoàn thiện trong 48 giờ · Team AIDE · Banking Legal & Compliance**

<br/>

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Uvicorn-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![OpenSearch](https://img.shields.io/badge/OpenSearch-2.13-005EB8?logo=opensearch&logoColor=white)
![Neo4j](https://img.shields.io/badge/Neo4j-5.18-4581C3?logo=neo4j&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Test cases](https://img.shields.io/badge/Test%20cases-218-2E8B57)

</div>

---

## AIDE trong 30 giây

| Câu hỏi | Trả lời |
|---|---|
| **Dành cho ai?** | Cán bộ Pháp chế và Tuân thủ ngân hàng |
| **Giải quyết việc gì?** | Xác minh nguồn pháp lý, tra cứu đúng phiên bản có hiệu lực và rà soát tài liệu nội bộ |
| **Khác biệt ở đâu?** | Nguồn phải được con người phê duyệt; truy xuất được lọc theo thời gian; mọi kết quả đều có bằng chứng |
| **AI làm gì?** | Đọc tài liệu, trích xuất có cấu trúc, tìm kiếm, so sánh và giải thích |
| **Con người làm gì?** | Kiểm tra, chỉnh sửa, phê duyệt nguồn và quyết định cuối cùng |
| **MVP chứng minh gì?** | Một workflow end-to-end hoạt động thật, có giao diện, backend, retrieval, audit và khả năng deploy |

> **AIDE không chỉ trả lời từ tài liệu. AIDE kiểm soát tài liệu nào, phiên bản nào và bằng chứng nào được phép hỗ trợ cho một nhận xét tuân thủ.**

---

## Mục lục

- [Bài toán](#bài-toán)
- [Bối cảnh và nhu cầu ngành](#bối-cảnh-và-nhu-cầu-ngành)
- [Giải pháp](#giải-pháp)
- [Điểm khác biệt](#điểm-khác-biệt)
- [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
- [Pipeline end-to-end](#pipeline-end-to-end)
- [Phân trách nhiệm giữa LLM, hệ thống và con người](#phân-trách-nhiệm-giữa-llm-hệ-thống-và-con-người)
- [Tính năng](#tính-năng)
- [Trạng thái sản phẩm](#trạng-thái-sản-phẩm)
- [Stack công nghệ](#stack-công-nghệ)
- [Cấu trúc repository](#cấu-trúc-repository)
- [Khởi chạy nhanh](#khởi-chạy-nhanh)
- [Cấu hình môi trường](#cấu-hình-môi-trường)
- [API chính](#api-chính)
- [Kịch bản demo](#kịch-bản-demo)
- [Kiểm thử](#kiểm-thử)
- [Triển khai](#triển-khai)
- [Nguyên tắc tin cậy và an toàn](#nguyên-tắc-tin-cậy-và-an-toàn)
- [Đánh giá và giới hạn](#đánh-giá-và-giới-hạn)
- [Lộ trình phát triển](#lộ-trình-phát-triển)
- [Đội ngũ](#đội-ngũ)
- [Tuyên bố sử dụng và bản quyền](#tuyên-bố-sử-dụng-và-bản-quyền)

---

## Bài toán

Khi một thông tư, quyết định hoặc văn bản sửa đổi mới được ban hành, cán bộ Pháp chế/Tuân thủ không chỉ cần **tìm văn bản**. Họ còn phải:

- xác định điều, khoản hoặc điểm nào đã thay đổi;
- đối chiếu nội dung trước và sau sửa đổi;
- kiểm tra ngày bắt đầu và kết thúc hiệu lực;
- theo dõi dẫn chiếu giữa nhiều văn bản;
- phát hiện policy, quy trình hoặc báo cáo nội bộ đang sử dụng căn cứ cũ;
- giải trình kết luận bằng nguồn, phiên bản, điều khoản và đoạn bằng chứng cụ thể.

Ba rủi ro lớn của quy trình thủ công:

| Rủi ro | Hệ quả |
|---|---|
| **Nhầm phiên bản** | Trả lời bằng phiên bản mới nhất thay vì phiên bản có hiệu lực tại thời điểm được hỏi |
| **Bỏ sót sửa đổi hoặc dẫn chiếu** | Không nhận ra điều khoản đã bị thay thế, bãi bỏ hoặc tác động gián tiếp |
| **Thiếu khả năng giải trình** | Không truy ngược được kết luận về văn bản, điều/khoản, trang và đoạn nguồn |

> **Vấn đề không chỉ là tìm thấy văn bản. Vấn đề là chứng minh quy định nào được áp dụng tại đúng thời điểm.**

---

## Bối cảnh và nhu cầu ngành

Nhu cầu ứng dụng AI trong xử lý văn bản, quản trị và kiểm soát tuân thủ đã được đề cập trực tiếp trong các hoạt động của Hiệp hội Ngân hàng Việt Nam. Các nguồn dưới đây cho thấy ngành ngân hàng vừa có áp lực cập nhật chính sách, vừa có nhu cầu ứng dụng AI theo hướng có kiểm soát:

- [Hành trình ứng dụng đổi mới sáng tạo AI trong ngành ngân hàng Việt Nam](https://vnba.org.vn/vi/hanh-trinh-ung-dung-doi-moi-sang-tao-ai-trong-nganh-ngan-hang-viet-nam-18927.htm)
- [Kỹ năng ứng dụng AI vào hoạt động kinh doanh ngân hàng thương mại](https://vnba.org.vn/vi/vnba/study/ky-nang-ung-dung-ai-vao-hoat-dong-kinh-doanh-ngan-hang-thuong-mai-257.htm)
- [AI sẽ là động lực chiến lược định hình truyền thông chính sách và sản phẩm, dịch vụ ngân hàng trong kỷ nguyên số](https://vnba.org.vn/vi/tri-tue-nhan-tao--ai--se-la-dong-luc-chien-luoc-dinh-hinh-truyen-thong-chinh-sach-va-san-pham--dich-vu-ngan-hang-trong-ky-nguyen-so-18702.htm)

Từ đó, nhu cầu người dùng được rút gọn thành năm yêu cầu:

1. Tìm đúng quy định áp dụng.
2. Xác định đúng phiên bản có hiệu lực.
3. Rà soát tài liệu nội bộ bị ảnh hưởng.
4. Truy vết mọi kết luận tới bằng chứng.
5. Giữ quyền quyết định cuối cùng cho cán bộ chuyên môn.

---

## Giải pháp

AIDE tổ chức sản phẩm thành hai khu vực liên kết trên cùng một **Kho pháp lý đã xác minh**.

### 1. Thêm nguồn

Dùng để xây dựng và cập nhật kho pháp lý:

```text
Tải văn bản pháp lý
→ Trích xuất text / OCR
→ LLM đọc và trích xuất có cấu trúc
→ Cán bộ kiểm tra và chỉnh sửa
→ Phê duyệt và kích hoạt
→ Kho pháp lý đã xác minh
```

Một file vừa tải lên chỉ là **nguồn chờ duyệt**. File chỉ được sử dụng cho truy vấn chính thức sau khi được cán bộ kiểm tra và kích hoạt.

### 2. Không gian RAG

#### Tra cứu quy định

Hỏi bằng ngôn ngữ tự nhiên về quy định hiện hành, lịch sử thay đổi, ngày áp dụng hoặc căn cứ pháp lý. Hệ thống trả về văn bản, điều/khoản, phiên bản, ngày hiệu lực và đoạn bằng chứng.

#### Nhận xét tài liệu

Tải policy, hướng dẫn hoặc báo cáo nội bộ để kiểm tra. File này là **đối tượng đánh giá**, không được đưa vào kho pháp lý và không được dùng làm ground truth.

### Quy tắc sản phẩm

- **Tải lên không đồng nghĩa với đáng tin cậy.**
- **Chỉ nguồn `APPROVED + ACTIVE` được dùng làm căn cứ.**
- **Ngày tra cứu hoặc ngày đánh giá quyết định phiên bản được retrieval.**
- **File review luôn được tách khỏi legal knowledge base.**
- **AI đề xuất; con người quyết định.**

---

## Điểm khác biệt

### Phạm vi so sánh: AIDE và Standard RAG

AIDE được so sánh với **Standard RAG** như một **baseline kiến trúc**, không phải để xếp hạng hay công kích một sản phẩm cụ thể.

Standard RAG là đối tượng so sánh phù hợp nhất vì cả hai cùng giải quyết bài toán cốt lõi: nhận tài liệu, truy xuất nội dung liên quan và dùng LLM tạo kết quả. Nhờ giữ nguyên nền tảng chung này, phần so sánh có thể làm rõ chính xác những lớp kiểm soát AIDE bổ sung cho nghiệp vụ Pháp chế/Tuân thủ.

### Vì sao chỉ so sánh với Standard RAG?

1. **Cùng điểm xuất phát kỹ thuật:** cả hai đều sử dụng retrieval và LLM generation, nên khác biệt nằm ở pipeline thay vì tên model.
2. **Tách được giá trị gia tăng của AIDE:** Human Review Gate, quản lý trạng thái nguồn, lọc theo ngày hiệu lực, quan hệ phiên bản và kiểm tra evidence.
3. **Có thể tái lập và kiểm chứng:** repository có baseline `/compare`, trong khi hành vi nội bộ của các sản phẩm thương mại thường không công khai đầy đủ.
4. **Tránh tuyên bố thiếu căn cứ:** AIDE không khẳng định một công cụ cụ thể “không có citation”, “không có versioning” hoặc kém chính xác hơn khi chưa có benchmark chung.
5. **Phù hợp phạm vi Hackathon 48 giờ:** mục tiêu là chứng minh một kiến trúc chuyên biệt cho Compliance, không phải thực hiện market benchmark toàn diện.

> Phần so sánh này đánh giá **pipeline mặc định**, không khẳng định mọi hệ thống RAG đều giống nhau hoặc không thể bổ sung các cơ chế tương tự.

### So sánh pipeline

```text
STANDARD RAG
Tài liệu
→ Chia nhỏ và lập chỉ mục
→ Truy xuất theo mức độ liên quan
→ LLM sinh câu trả lời
→ Câu trả lời + citation
```

```text
AIDE
Nguồn pháp lý chờ duyệt
→ Trích xuất text / OCR
→ LLM đọc và trích xuất có cấu trúc
→ Cán bộ kiểm tra, chỉnh sửa và phê duyệt
→ Nguồn APPROVED + ACTIVE
→ Lọc theo ngày hiệu lực
→ BM25 + kNN + RRF + Graph Expansion
→ Evidence Package
→ Câu trả lời hoặc nhận xét có căn cứ
```

| Điểm kiểm soát | Standard RAG | AIDE |
|---|---|---|
| **Mục tiêu mặc định** | Hỏi đáp dựa trên tập tài liệu đã chọn | Hỗ trợ tra cứu và rà soát tuân thủ có kiểm soát |
| **Nguồn đầu vào** | Corpus do người triển khai hoặc người dùng cung cấp | Nguồn mới chỉ là candidate và phải qua Human Review Gate |
| **Trạng thái nguồn** | Không bắt buộc có vòng đời phê duyệt | `PENDING → APPROVED → ACTIVE` |
| **Thời điểm áp dụng** | Phụ thuộc metadata và cấu hình của từng hệ thống | Approval + temporal filter chạy trước top-k |
| **Phiên bản và sửa đổi** | Không phải thành phần mặc định của RAG | Theo dõi version, amendment và quan hệ graph |
| **File cần rà soát** | Có thể được xử lý trong cùng corpus/workspace | Là `REVIEW_TARGET`, luôn tách khỏi legal knowledge base |
| **Bằng chứng** | Có thể trả citation từ đoạn được retrieval | Citation phải thuộc `valid_evidence` và vượt qua output checks |
| **Đầu ra** | Câu trả lời hoặc tóm tắt | Finding, căn cứ, phiên bản, ngày hiệu lực, lý do và gợi ý |
| **Quyết định cuối cùng** | Phụ thuộc cách triển khai ứng dụng | Thuộc về cán bộ Pháp chế/Tuân thủ |

### Điều AIDE không tuyên bố từ phép so sánh này

- Không tuyên bố Standard RAG không có citation.
- Không tuyên bố AIDE luôn chính xác hơn mọi hệ thống RAG.
- Không tuyên bố các sản phẩm thương mại không thể có approval, versioning hoặc temporal retrieval.
- Không xem kết quả Hackathon là benchmark production hoặc đánh giá thị trường toàn diện.

### USP

> **Standard RAG tìm nội dung liên quan. AIDE kiểm soát nguồn nào, phiên bản nào và bằng chứng nào được phép hỗ trợ cho một nhận xét tuân thủ.**

> **Nguồn đã xác minh · Phiên bản đúng thời điểm · Nhận xét có bằng chứng**

---
## Kiến trúc hệ thống

```mermaid
flowchart TB
    U[Cán bộ Pháp chế / Tuân thủ]

    subgraph FE[Frontend — Next.js 16 / React 19]
        A[Thêm Nguồn\nUpload → Review → Kích hoạt]
        R[Không gian RAG\nTra cứu / Nhận xét tài liệu]
    end

    subgraph API[Backend — FastAPI + Uvicorn]
        AUTH[Authentication]
        DOC[Document & Activation APIs]
        CHAT[Conversation APIs]
        QUERY[Temporal Query APIs]
        REVIEW[Compliance Review APIs]
        AUDIT[Audit & Health APIs]
    end

    subgraph CORE[Core Services]
        INGEST[Text Extraction / OCR]
        LLMREAD[LLM Structured Reading]
        GATE[Human Review & Activation Gate]
        RETRIEVE[Hybrid Temporal Retrieval]
        GRAPH[Graph Expansion]
        GENERATE[Evidence-grounded Generation]
        VERIFY[Output & Citation Checks]
    end

    subgraph DATA[Data Layer]
        PG[(PostgreSQL\nSource of truth)]
        OS[(OpenSearch\nBM25 + kNN)]
        NEO[(Neo4j\nVersion & relation graph)]
    end

    U --> FE
    FE -->|HTTP/REST · JWT Bearer| API
    API --> CORE
    CORE --> PG
    CORE --> OS
    CORE --> NEO
```

### Vai trò của từng kho dữ liệu

| Thành phần | Vai trò | Không được dùng để |
|---|---|---|
| **PostgreSQL** | Source of truth cho metadata, trạng thái, phiên bản, review, conversation và audit | Thay thế bằng trạng thái suy đoán từ search/graph |
| **OpenSearch** | BM25, kNN vector, metadata filter và temporal pre-filter | Quyết định tài liệu đã được phê duyệt hay chưa |
| **Neo4j** | Quan hệ văn bản, điều khoản, phiên bản, sửa đổi, dẫn chiếu và impact path | Tạo quan hệ không có provenance hoặc review |

---

## Pipeline end-to-end

```mermaid
flowchart LR
    SOURCE[Văn bản pháp lý] --> EXTRACT[Trích xuất text / OCR]
    EXTRACT --> LLM1[LLM đọc và trích xuất có cấu trúc]
    LLM1 --> PACKAGE[Gói thông tin kiểm tra\nmetadata · điều khoản · hiệu lực · evidence]
    PACKAGE --> HUMAN{Cán bộ kiểm tra\nChỉnh sửa / Phê duyệt / Từ chối}
    HUMAN -->|Phê duyệt| ACTIVE[Approve & Activate]
    HUMAN -->|Chỉnh sửa| PACKAGE
    HUMAN -->|Từ chối| REJECT[Không đưa vào kho pháp lý]
    ACTIVE --> KB[(Kho pháp lý đã xác minh)]

    QUESTION[Câu hỏi người dùng] --> DATE1[Ngày tra cứu]
    REVIEWFILE[Policy / Báo cáo nội bộ] --> CLAIMS[LLM trích xuất nội dung cần kiểm tra]
    CLAIMS --> DATE2[Ngày đánh giá]

    KB --> FILTER[Approval + Temporal Pre-filter]
    DATE1 --> FILTER
    DATE2 --> FILTER
    QUESTION --> RETRIEVE[BM25 + kNN + RRF]
    CLAIMS --> RETRIEVE
    FILTER --> RETRIEVE
    RETRIEVE --> EXPAND[Graph Expansion ≤ 2 hops]
    EXPAND --> EVIDENCE[Gói bằng chứng hợp lệ]
    EVIDENCE --> LLM2[LLM trả lời / đối chiếu]
    LLM2 --> CHECK[Kiểm tra citation và output]
    CHECK --> ANSWER[Câu trả lời có căn cứ]
    CHECK --> REPORT[Nhận xét có cấu trúc\ntrạng thái · căn cứ · lý do · gợi ý]

    REVIEWFILE -. Không vào legal KB .-> CLAIMS
```

### Bốn cổng kiểm soát

1. **Cổng xác minh nguồn:** output LLM chưa phải ground truth.
2. **Cổng kích hoạt:** chỉ nguồn đã phê duyệt được đưa vào retrieval chính thức.
3. **Cổng thời gian:** phiên bản phải phù hợp ngày tra cứu hoặc ngày đánh giá.
4. **Cổng bằng chứng:** citation phải thuộc evidence package đã được cho phép.

> **Độ tin cậy của AIDE không đến từ việc tin tuyệt đối vào LLM, mà đến từ cách LLM được đặt trong một pipeline có kiểm soát.**

---

## Phân trách nhiệm giữa LLM, hệ thống và con người

AIDE sử dụng cách tiếp cận **LLM-first cho việc hiểu tài liệu**, nhưng giữ các quyết định có tính ràng buộc trong code và Human Review Gate.

| Thành phần | Được phép làm | Không được phép làm |
|---|---|---|
| **LLM** | Đọc văn bản, trích metadata và điều khoản, trích claim, so sánh ngữ nghĩa, giải thích và gợi ý | Tự kích hoạt nguồn, tự chọn ground truth, tự bỏ qua ngày hiệu lực, tự tạo citation ngoài evidence |
| **Code xác định** | Quản lý trạng thái, activation gate, temporal filter, access control, stable ID, citation allowlist và audit | Suy diễn pháp lý mơ hồ thay cán bộ chuyên môn |
| **Cán bộ Pháp chế/Tuân thủ** | Kiểm tra, chỉnh sửa, phê duyệt hoặc từ chối nguồn và kết quả review | Không cần đọc lại toàn bộ corpus khi evidence package đã đủ rõ |

### Vì sao lựa chọn LLM-first trong MVP?

- Phù hợp nhiều định dạng và cách trình bày văn bản.
- Rút ngắn thời gian xây dựng trong Hackathon 48 giờ.
- Cho phép trả về structured output thống nhất cho giao diện review.
- Giữ độ tin cậy bằng Human Review Gate thay vì mặc định tin output AI.

---

## Tính năng

### Thêm nguồn pháp lý

- Upload PDF, DOCX hoặc TXT.
- Kiểm tra loại file, kích thước và SHA-256 deduplication.
- Trích xuất text bằng PyMuPDF, `python-docx` hoặc UTF-8 fallback.
- OCR fallback cho tài liệu không có text layer.
- Quét prompt injection trong nội dung tài liệu.
- LLM trực tiếp trích metadata, điều khoản, hiệu lực, quan hệ sửa đổi và evidence theo structured schema.
- Cho phép cán bộ chỉnh sửa trước khi kích hoạt.
- Activation gate ngăn nguồn chưa đủ điều kiện đi vào kho RAG.

### Tra cứu quy định theo thời gian

- Hỏi đáp bằng tiếng Việt tự nhiên.
- Hỗ trợ quy định hiện hành, truy vấn tại một thời điểm, lịch sử phiên bản và tham chiếu chéo.
- Kết hợp BM25, vector search và Reciprocal Rank Fusion.
- Temporal filter và approval filter chạy trước ranking.
- Mở rộng đồ thị tối đa hai hop theo edge allowlist.
- Trả về citation, ngày hiệu lực và evidence panel.
- Hỗ trợ hội thoại nhiều lượt theo từng conversation độc lập.

### Nhận xét tài liệu nội bộ

- Upload policy, hướng dẫn, báo cáo hoặc tài liệu cần kiểm tra.
- LLM trích claim, nghĩa vụ, ngưỡng, thời hạn và căn cứ được viện dẫn.
- Đối chiếu với nguồn pháp lý đã phê duyệt và còn hiệu lực tại ngày đánh giá.
- Trả kết quả theo từng claim:
  - `COMPLIANT`
  - `NON_COMPLIANT`
  - `PARTIALLY_COMPLIANT`
  - `OUTDATED_REFERENCE`
  - `MISSING_EVIDENCE`
  - `AMBIGUOUS`
  - `NEEDS_HUMAN_REVIEW`
- Kèm căn cứ, bằng chứng, giải thích và đề xuất chỉnh sửa.
- Initial review không sử dụng lịch sử chat.
- File review được cô lập khỏi legal knowledge base.

### Audit và khả năng giải trình

- Lưu lịch sử upload, review, activate, query và compliance check.
- Theo dõi actor, role, timestamp, prompt version và latency.
- Phân biệt `valid_evidence` và `excluded_evidence` cùng lý do loại.
- Kiểm tra citation sau generation trước khi trả kết quả.

---

## Trạng thái sản phẩm

| Capability | Trạng thái | Ghi chú |
|---|---|---|
| Thêm nguồn và Human Review Gate | **Core MVP** | Workflow chính của tab Thêm Nguồn |
| Tra cứu theo thời gian | **Core MVP** | Approval + temporal filter trước retrieval |
| Nhận xét tài liệu | **Core MVP** | Review target tách khỏi legal KB |
| Hội thoại nhiều lượt | **Đã triển khai** | Conversation isolation |
| Hybrid retrieval BM25 + kNN + RRF | **Đã triển khai** | Có fallback trong Demo Mode |
| Neo4j graph expansion | **Đã triển khai** | Giới hạn hop và edge allowlist |
| Change / impact candidate | **Mở rộng** | Cần cán bộ xác nhận |
| Batch review | **API mở rộng** | Không phải luồng trọng tâm của demo 48 giờ |
| Enterprise IAM và approval workflow | **Lộ trình** | Chưa phải phạm vi MVP |
| Production benchmark | **Chưa tuyên bố** | Cần golden dataset lớn hơn và chuyên gia đánh giá |

---

## Stack công nghệ

| Lớp | Công nghệ | Vai trò |
|---|---|---|
| Frontend | Next.js 16, React 19, TypeScript, shadcn/ui, Radix UI, Tailwind CSS v4 | Giao diện upload, review, chat và compliance report |
| Backend | FastAPI, Uvicorn, Pydantic, SQLAlchemy | REST API, workflow orchestration và domain services |
| Metadata DB | PostgreSQL 16 | Documents, provisions, versions, reviews, conversations và audit |
| Local fallback | SQLite | Chạy offline và test không phụ thuộc hạ tầng ngoài |
| Search | OpenSearch 2.13 | BM25, kNN vector, metadata filter và temporal retrieval |
| Graph | Neo4j 5.18 + APOC | Version chain, amendment, cross-reference và impact path |
| Embedding | BAAI/bge-m3, 1024 chiều | Dense retrieval đa ngôn ngữ |
| LLM | Google Gemini, Anthropic Claude, OpenAI, OpenAI-compatible hoặc Mock | Structured reading, claim extraction, explanation và generation |
| Authentication | HMAC-SHA256 JWT, PBKDF2 | Một role kỹ thuật `EMPLOYEE` trong MVP |
| Testing | pytest, SQLite, MockLLM | Unit và integration test offline-safe |
| Deployment | Docker Compose, Railway | Local development và triển khai demo |

> `Compliance Officer` là **persona nghiệp vụ**; `EMPLOYEE` là **role kỹ thuật** được sử dụng trong JWT và backend của MVP.

---

## Cấu trúc repository

```text
.
├── api/                         # FastAPI entry point dùng khi deploy
│   ├── main.py
│   ├── auth.py
│   ├── routes_ingest.py
│   ├── routes_query.py
│   └── routes_chat.py
├── backend/app/                 # Workflow và service implementation mở rộng
│   ├── api/
│   ├── workflows/
│   ├── answering/
│   ├── retrieval/
│   ├── review/
│   ├── chat/
│   ├── analysis/
│   └── persistence/
├── ingestion/                   # Upload, LLM extraction, review và activation
├── query/                       # Temporal retrieval, graph expansion và output checks
├── infra/                       # PostgreSQL, OpenSearch, Neo4j và embedding adapters
├── llm/                         # Multi-provider LLM client và prompts
├── packages/                    # Shared contracts, models, enums và utilities
├── frontend/nextjs_app/         # Next.js frontend
├── tests/                       # Track A/B tests
├── backend/tests/               # Backend workflow tests
├── data/golden/                 # Golden regulatory dataset
├── docs/                        # Architecture và tài liệu kỹ thuật
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

`packages/` là nơi giữ contract dùng chung. Route hoặc script không được bypass activation gate hoặc tự thay đổi trust state.

---

## Khởi chạy nhanh

### Yêu cầu

- Python 3.11+
- Node.js 20+
- pnpm
- Docker và Docker Compose nếu chạy full stack

### 1. Tạo môi trường backend

```bash
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Chạy Demo Mode

Demo Mode sử dụng SQLite, in-memory search/graph, hash embedding và MockLLM để bảo đảm hệ thống có thể khởi động khi không có hạ tầng ngoài.

Linux/macOS:

```bash
DEMO_MODE=true SEED_DEMO=1 \
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Windows PowerShell:

```powershell
$env:DEMO_MODE="true"
$env:SEED_DEMO="1"
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 3. Chạy frontend

```bash
cd frontend/nextjs_app
pnpm install
pnpm dev
```

| Dịch vụ | Địa chỉ |
|---|---|
| Frontend | `http://localhost:3000` |
| Backend API | `http://localhost:8000` |
| Swagger UI | `http://localhost:8000/docs` |
| Health check | `http://localhost:8000/health` |

### 4. Chạy full data stack

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f api
```

### Tài khoản demo

<details>
<summary>Hiển thị credential phát triển</summary>

MVP chỉ sử dụng một tài khoản nghiệp vụ:

| Tài khoản | Mật khẩu | Role | Quyền |
|---|---|---|---|
| `user` | `user123` | `EMPLOYEE` | Upload, kiểm tra, chỉnh sửa, phê duyệt, kích hoạt, tra cứu, nhận xét và xem audit |

Không tồn tại role `USER` hoặc tài khoản `compliance` trong cấu hình MVP cuối cùng.

**Không sử dụng credential demo trong môi trường public hoặc production.**

</details>

---

## Cấu hình môi trường

Tạo file `.env` tại repository root:

```dotenv
# Runtime
DEMO_MODE=false
SEED_DEMO=0

# PostgreSQL
POSTGRES_DSN=postgresql+psycopg://postgres:postgres@localhost:5432/aide

# OpenSearch
OPENSEARCH_HOST=localhost

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=change-me

# LLM
LLM_PROVIDER=google
GOOGLE_API_KEY=your-api-key
LLM_MODEL=gemini-flash-latest
LLM_THROTTLE_S=0

# Security
JWT_SECRET=replace-with-a-long-random-secret
CORS_ORIGINS=http://localhost:3000

# Retrieval
RETRIEVAL_TOP_K=8
```

### LLM providers

| Provider | Biến môi trường chính |
|---|---|
| Google Gemini | `GOOGLE_API_KEY` |
| Anthropic Claude | `ANTHROPIC_API_KEY` |
| OpenAI | `OPENAI_API_KEY` |
| OpenAI-compatible / OpenRouter | `OPENROUTER_API_KEY` |
| Mock | Không cần API key |

Khi thiếu API key, MockClient chỉ nên được sử dụng trong Demo Mode hoặc test. Không dùng kết quả mock để đánh giá chất lượng production.

---

## API chính

### Authentication và documents

| Method | Endpoint | Mục đích |
|---|---|---|
| `POST` | `/login` | Lấy JWT token |
| `POST` | `/documents` | Upload văn bản |
| `GET` | `/documents` | Liệt kê tài liệu |
| `GET` | `/documents/{id}/provisions` | Xem điều khoản đã trích xuất |
| `PATCH` | `/documents/{id}/provisions/{version_id}` | Chỉnh sửa trước activation |
| `POST` | `/documents/{id}/activate` | Kích hoạt nguồn vào RAG |
| `DELETE` | `/documents/{id}` | Soft-delete tài liệu |

### Query, review và audit

| Method | Endpoint | Mục đích |
|---|---|---|
| `GET` | `/review-tasks` | Review inbox |
| `POST` | `/review-tasks/{id}/decision` | Approve, reject hoặc edit task |
| `POST` | `/query` | Temporal regulatory question answering |
| `POST` | `/compare` | So sánh Standard RAG với AIDE |
| `GET` | `/graph/{provision_id}` | Lấy knowledge graph subgraph |
| `GET` | `/audit` | Xem audit trail |
| `GET` | `/health` | Basic health check |
| `GET` | `/health/details` | Trạng thái PostgreSQL, OpenSearch, Neo4j và LLM |

### Conversations và compliance review

| Method | Endpoint | Mục đích |
|---|---|---|
| `POST / GET` | `/conversations` | Tạo hoặc liệt kê conversation |
| `POST` | `/conversations/{id}/messages` | Gửi câu hỏi nhiều lượt |
| `POST` | `/compliance-checks` | Tạo lần kiểm tra tài liệu |
| `GET` | `/compliance-checks/{id}` | Lấy compliance report |
| `POST` | `/review-runs` | Tạo immutable review run |
| `GET` | `/review-runs/{id}` | Xem trạng thái và báo cáo |
| `POST` | `/batch-reviews` | Kiểm tra nhiều tài liệu |

---

## Kịch bản demo

### 1. Xây dựng nguồn pháp lý đã xác minh

1. Đăng nhập bằng `user / user123`.
2. Mở tab **Thêm Nguồn**.
3. Upload thông tư, quyết định hoặc văn bản sửa đổi.
4. Kiểm tra metadata, ngày hiệu lực, điều khoản và evidence do LLM trích xuất.
5. Chỉnh sửa nội dung chưa chính xác.
6. Phê duyệt review task.
7. Kích hoạt tài liệu.
8. Xác nhận tài liệu chuyển sang trạng thái `APPROVED + INDEXED`.

### 2. Tra cứu quy định

1. Mở **RAG → Tra cứu quy định**.
2. Đặt câu hỏi có thời điểm cụ thể, ví dụ:

```text
Quy định này có hiệu lực tại ngày 01/01/2026 không?
```

3. Kiểm tra văn bản, điều/khoản, khoảng hiệu lực và đoạn evidence.
4. Đặt câu hỏi tiếp theo trong cùng conversation.

### 3. Nhận xét tài liệu nội bộ

1. Chuyển sang **RAG → Nhận xét tài liệu**.
2. Upload policy, hướng dẫn hoặc báo cáo nội bộ.
3. Chọn ngày đánh giá.
4. Chạy compliance check.
5. Xem claim, trạng thái, căn cứ, evidence và gợi ý sửa.
6. Kiểm tra các trường hợp `OUTDATED_REFERENCE`, `MISSING_EVIDENCE` hoặc `AMBIGUOUS`.

### 4. So sánh với Standard RAG

Sử dụng `/compare` để quan sát khác biệt giữa retrieval thông thường và AIDE có approval filter, temporal pre-filter, graph expansion và evidence verification.

---

## Kiểm thử

Repository hiện định nghĩa **218 test cases offline-safe** bằng SQLite và MockLLM.

| Suite | Vị trí | Số lượng | Phạm vi |
|---|---|---:|---|
| Track A/B | `tests/` | 131 | Ingestion, query, auth và contracts |
| Backend workflows | `backend/tests/` | 87 | Compliance, chat, review, retrieval và persistence |
| **Tổng** |  | **218** | Unit và integration |

```bash
pytest tests/ -x -q
pytest backend/tests/ -x -q
pytest tests/ backend/tests/ -q
```

Các nhóm test quan trọng:

- temporal validity và half-open interval;
- activation gate;
- document deduplication;
- amendment và version chain;
- hybrid retrieval và RRF;
- citation allowlist;
- attachment isolation;
- immutable review run;
- compliance status classification;
- fallback behavior trong Demo Mode.

> Chỉ công bố trạng thái “218 passed” hoặc coverage cụ thể khi kết quả đã được xác nhận trên clean environment hoặc CI của commit tương ứng.

---

## Triển khai

### Docker Compose

```text
PostgreSQL 16   → 5432
OpenSearch 2.13 → 9200
Neo4j 5.18      → 7474 / 7687
FastAPI API     → 8000
```

```bash
docker compose up -d --build
```

### Railway

Backend command:

```bash
uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

Frontend được deploy độc lập từ:

```text
frontend/nextjs_app/
```

### Checklist trước khi deploy public

- Thay credential `user / user123`.
- Đặt `JWT_SECRET` mạnh.
- Giới hạn `CORS_ORIGINS`.
- Tắt `SEED_DEMO`.
- Xác minh `/health/details` không sử dụng mock/hash/in-memory fallback.
- Cấu hình persistent storage cho file upload.
- Không commit API key hoặc secret vào repository.

---

## Nguyên tắc tin cậy và an toàn

| Invariant | Cơ chế bảo đảm |
|---|---|
| Nguồn chưa duyệt không được trả lời chính thức | Activation gate và approval filter |
| Temporal filter chạy trước top-k | Filter clause trong BM25 và kNN |
| LLM không tự chọn ground truth | Trust state do PostgreSQL và Human Review quyết định |
| LLM không quyết định hiệu lực | `is_valid_at()` và temporal control trong code |
| Citation phải thuộc evidence allowlist | Output checks sau generation |
| Evidence được tách khỏi instruction | Khối evidence có cấu trúc trong prompt |
| File review không vào legal KB | Review workspace và attachment isolation |
| Review run không bị ghi đè | Snapshot và immutable report |
| Neo4j không nhận Cypher do LLM sinh | Traversal template và edge allowlist |
| Mọi thao tác quan trọng có audit | Audit record cho upload, review, activation và query |

### Human-in-the-loop

- AI hỗ trợ trích xuất, tìm kiếm, so sánh và giải thích.
- Cán bộ chịu trách nhiệm kiểm tra, phê duyệt hoặc từ chối nguồn.
- Kết quả có confidence thấp phải chuyển sang review.
- Hệ thống không tự đưa ra quyết định pháp lý cuối cùng.

---

## Đánh giá và giới hạn

AIDE là MVP hoàn thiện trong 48 giờ. README phân biệt rõ giữa **khả năng đã chứng minh trong demo** và **mức độ sẵn sàng production**.

### Những gì MVP chứng minh được

- Workflow thêm nguồn chạy end-to-end.
- Output LLM được con người kiểm tra trước activation.
- Nguồn chưa duyệt không được sử dụng trong truy vấn chính thức.
- Retrieval có approval và temporal filter.
- File review nằm ngoài legal KB.
- Câu trả lời và finding có evidence có thể truy vết.
- Frontend kết nối backend thật và có thể deploy.

### Những gì chưa tuyên bố

- Không tuyên bố thay thế ý kiến pháp lý chính thức.
- Không tuyên bố OCR chính xác với mọi tài liệu scan.
- Không tuyên bố benchmark production trên toàn bộ pháp luật ngân hàng.
- Không tuyên bố AI có thể tự phê duyệt nguồn hoặc kết luận pháp lý.
- Không xem Demo Mode là cấu hình production.

### Giới hạn hiện tại

- OCR và layout parsing chưa bao phủ mọi loại PDF scan phức tạp.
- LLM có thể trích xuất sai metadata, locator hoặc amendment target.
- Golden dataset mới tập trung vào phạm vi demo ngân hàng.
- Một số conflict và impact candidate cần con người xác nhận.
- Demo Mode sử dụng SQLite, in-memory search/graph, hash embedding và MockLLM.
- Repository vẫn duy trì entry point deploy và implementation mở rộng.
- Enterprise IAM, reviewer assignment và audit policy đầy đủ chưa nằm trong MVP.

### Khung đánh giá đề xuất cho pilot

| Chỉ số | Ý nghĩa |
|---|---|
| Version-selection accuracy | Chọn đúng phiên bản tại ngày truy vấn |
| Citation correctness | Citation có thực sự hỗ trợ câu trả lời |
| Source-admission violation | Nguồn chưa duyệt có lọt vào answer hay không |
| Claim assessment accuracy | Độ chính xác trạng thái review theo từng claim |
| Evidence coverage | Tỷ lệ finding có căn cứ đủ mạnh |
| Human correction rate | Tỷ lệ output LLM cần cán bộ chỉnh sửa |

---

## Lộ trình phát triển

### Future Work được xác định như thế nào?

Core MVP đã tập trung chứng minh ba năng lực: xây dựng nguồn pháp lý đã xác minh, tra cứu theo thời gian và rà soát tài liệu nội bộ có bằng chứng. Vì vậy, Future Work không nhằm che giấu các bước bắt buộc chưa hoàn thành, mà tập trung vào ba hướng tiếp theo:

- **nâng độ tin cậy và khả năng đo lường;**
- **đưa workflow vào pilot nghiệp vụ;**
- **mở rộng an toàn tới quy mô doanh nghiệp.**

Lộ trình được ưu tiên theo thứ tự **reliability → pilotability → scalability**, thay vì mở rộng thêm nhiều tính năng AI trước khi chất lượng nguồn và evidence được kiểm chứng.

### Giai đoạn 1 — Củng cố độ tin cậy của MVP

**Mục tiêu:** biến demo end-to-end thành một hệ thống có thể tái lập và đánh giá định lượng.

- Hợp nhất runtime, giảm code trùng lặp và chuẩn hóa một test tree.
- Thiết lập CI để kiểm tra clean install, test suite và migration.
- Nâng chất lượng OCR, layout preservation và structured reading.
- Bổ sung deterministic validation cho số hiệu, ngày, locator, giá trị định lượng và evidence span.
- Xây labeled evaluation cho extraction, version selection, retrieval và citation.
- Đo các chỉ số: version-selection accuracy, citation correctness, source-admission violation, evidence coverage và human correction rate.

**Điều kiện hoàn thành dự kiến:**

- Repository chạy được từ clean environment theo README.
- CI xác nhận test suite trên commit phát hành.
- Không có nguồn chưa duyệt lọt vào answer trong integration test.
- Các metric cốt lõi được công bố cùng dataset và phương pháp đo.

### Giai đoạn 2 — Pilot trong nghiệp vụ Pháp chế/Tuân thủ

**Mục tiêu:** hỗ trợ một nhóm Compliance Officer sử dụng AIDE trong quy trình thử nghiệm có giám sát.

- Role-based access control và phân quyền theo nhiệm vụ.
- Reviewer assignment, approval workflow và audit trail cấp doanh nghiệp.
- Export báo cáo sang DOCX/PDF.
- Batch review, queue processing, retry và trạng thái tác vụ.
- Kết nối hệ thống quản lý tài liệu hoặc kho nội bộ.
- Xây golden dataset cùng chuyên gia Pháp chế/Tuân thủ.
- Thu thập reviewer feedback và đo thời gian tiết kiệm so với quy trình hiện tại.

**Điều kiện hoàn thành dự kiến:**

- Một pilot domain có dữ liệu được thẩm định.
- Báo cáo có thể truy vết từ finding tới evidence và reviewer action.
- Có số liệu về thời gian xử lý, tỷ lệ chỉnh sửa và mức độ chấp nhận của người dùng.

### Giai đoạn 3 — Enterprise Compliance Workspace

**Mục tiêu:** mở rộng AIDE thành hạ tầng tuân thủ có khả năng vận hành ổn định ở quy mô tổ chức.

- Tự động theo dõi và tiếp nhận nguồn quy định mới.
- Phân tích tác động theo policy owner, đơn vị nghiệp vụ và mức độ ưu tiên.
- Mở rộng legal domain nhưng vẫn giữ nguyên trust boundary.
- Đồng bộ PostgreSQL, OpenSearch và Neo4j bằng outbox/worker có retry.
- Secrets management, observability, model monitoring và cost monitoring.
- High availability, backup, disaster recovery và retention policy.
- Đánh giá drift của embedding, retrieval và LLM trong vận hành.
- Tích hợp SSO, DMS, ticketing và hệ thống quản trị rủi ro nội bộ.

**Điều kiện hoàn thành dự kiến:**

- Hệ thống có khả năng audit, phục hồi và theo dõi chất lượng end-to-end.
- Mỗi kết luận vẫn giữ được provenance, version và Human Review Gate khi mở rộng quy mô.
- Không đánh đổi trust model để tăng tốc độ hoặc mức độ tự động hóa.

### Những gì không thuộc định hướng tự động hóa

Ngay cả trong các giai đoạn sau, AIDE không hướng tới:

- tự động đưa ra ý kiến pháp lý cuối cùng;
- tự phê duyệt nguồn pháp lý;
- tự kích hoạt thay đổi phiên bản khi chưa có người xác nhận;
- che giấu trường hợp thiếu bằng chứng hoặc xung đột;
- thay thế trách nhiệm của cán bộ có thẩm quyền.

> **Future Work của AIDE là tăng độ tin cậy, khả năng tích hợp và quy mô vận hành — không phải loại bỏ con người khỏi quyết định pháp lý.**

---

AIDE được thiết kế, phát triển, kiểm thử và triển khai trong khuôn khổ Hackathon 48 giờ với mục tiêu chứng minh rằng một sản phẩm AI cho Pháp chế/Tuân thủ không chỉ cần mô hình ngôn ngữ mạnh, mà còn cần:

- quản trị nguồn;
- nhận thức thời gian;
- bằng chứng có thể truy vết;
- cổng kiểm soát của con người;
- một workflow hoàn chỉnh có thể vận hành và giải trình.

---
## Đội ngũ

### Team AIDE

AIDE được nghiên cứu, thiết kế và phát triển bởi:

| Thành viên |
|---|
| **Nguyễn Ngọc Sáng** |
| **Phan Vinh Khoa** |
| **Lê Tiến Thành** |

---

## Tuyên bố sử dụng và bản quyền

AIDE là hệ thống hỗ trợ nghiên cứu, tra cứu và rà soát tài liệu. Kết quả do hệ thống cung cấp **không phải ý kiến pháp lý chính thức** và không thay thế việc xem xét, phê duyệt của cán bộ có thẩm quyền.

Mã nguồn và tài liệu thuộc Team AIDE, được cung cấp cho mục đích trình diễn, đánh giá cuộc thi và nghiên cứu. Việc tái sử dụng hoặc phân phối cần có sự đồng ý của nhóm, trừ khi repository công bố một giấy phép khác trong file `LICENSE`.

<div align="center">

### AIDE

**AI hỗ trợ · Bằng chứng làm căn cứ · Con người quyết định**

</div>
