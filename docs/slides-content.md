# AIDE — Nội dung slide (10 slides, bản cuối)

> Định vị: **Trợ lý AI cho Pháp chế và Tuân thủ ngân hàng**
> Persona duy nhất: Cán bộ Pháp chế/Tuân thủ
> Tagline: **AI hỗ trợ. Bằng chứng làm căn cứ. Con người quyết định.**

---

## Slide 1 — AIDE

**Tiêu đề:** AIDE — Trợ lý AI cho Pháp chế và Tuân thủ ngân hàng

**Thông điệp định vị:** Đúng quy định — Đúng phiên bản — Có bằng chứng

**Ba khả năng chính:**
- Xác minh nguồn pháp lý
- Tra cứu quy định hiện hành
- Rà soát tài liệu nội bộ

**Hình ảnh:**
```
Nguồn pháp lý → AIDE → Cán bộ Pháp chế/Tuân thủ
                   ↓
       Xác minh • Tra cứu • Rà soát
```

**Thuyết trình:** "AIDE là trợ lý AI dành riêng cho cán bộ Pháp chế và Tuân thủ ngân hàng. Hệ thống giúp xây dựng kho quy định đã được xác minh, tra cứu đúng nội dung có hiệu lực và rà soát policy hoặc báo cáo nội bộ dựa trên bằng chứng."

---

## Slide 2 — Agenda

**Tiêu đề:** AGENDA — LỘ TRÌNH TRÌNH BÀY

| # | Nội dung |
|---|---|
| I | Xác định vấn đề — Quy trình thủ công, nhầm phiên bản, bỏ sót |
| II | Bằng chứng và nhu cầu người dùng — Evidence từ VNBA, ngân hàng |
| III | Công trình liên quan và khoảng trống — Document AI/RAG vs nghiệp vụ |
| IV | Giải pháp đề xuất — Thêm nguồn → Kho xác minh → Tra cứu/Nhận xét |
| V | Pipeline tổng thể — End-to-end trong một hình |
| VI | Thành phần và công nghệ — Mỗi bước dùng gì |
| VII | So sánh pipeline và USP — RAG thông thường vs AIDE |
| VIII | Giá trị, MVP, giới hạn và lộ trình |

**Hình ảnh (8 card liên kết):**
```
Vấn đề → Evidence → Khoảng trống → Giải pháp
      → Pipeline → Công nghệ → USP → Giá trị
```

---

## Slide 3 — Xác định vấn đề

**Tiêu đề kết luận:** ĐÚNG VĂN BẢN CHƯA ĐỦ — PHẢI ĐÚNG PHIÊN BẢN VÀ ĐÚNG THỜI ĐIỂM

**Quy trình hiện tại:**
```
Có quy định mới
→ Tìm văn bản liên quan
→ Kiểm tra sửa đổi và dẫn chiếu
→ Xác định ngày hiệu lực
→ Rà soát policy/báo cáo nội bộ
→ Viết nhận xét và bằng chứng
```

**Pain points:**
- Nguồn và tài liệu phân tán
- Quan hệ sửa đổi chồng chéo
- Đối chiếu nhiều văn bản thủ công
- Dễ sử dụng nhầm phiên bản
- Khó xác định tài liệu nội bộ bị ảnh hưởng
- Khó chứng minh và giải trình kết luận

**Nguồn dẫn chứng:** INDA — theo dõi thông tư NHNN ngày càng khó do khối lượng lớn, thay đổi liên tục, nhiều quan hệ chồng chéo, mất thời gian tra cứu thủ công.

**Thông điệp cuối:** "Vấn đề không chỉ là tìm thấy văn bản, mà là xác định quy định nào được áp dụng tại một thời điểm cụ thể."

**Thuyết trình:** "Cán bộ không chỉ đọc một thông tư riêng lẻ. Họ phải theo dõi văn bản gốc, văn bản sửa đổi, ngày hiệu lực và tác động đến policy nội bộ. Quá trình này hiện phụ thuộc nhiều vào việc tìm kiếm và đối chiếu thủ công."

---

## Slide 4 — Bằng chứng và nhu cầu người dùng

**Tiêu đề kết luận:** PAIN POINT VÀ NHU CẦU AI ĐÃ ĐƯỢC XÁC NHẬN TRONG NGÀNH NGÂN HÀNG

**4 Evidence cards:**

### Card 1 — TỐN THỜI GIAN — DỄ BỎ SÓT
**Tra cứu thủ công tốn thời gian và dễ bỏ sót**
Việc theo dõi thông tư NHNN gặp khó khăn do tài liệu lớn, quy định thay đổi liên tục, quan hệ pháp lý chồng chéo và phải mở nhiều văn bản để đối chiếu. INDA liệt kê lợi ích AI: giảm thời gian tra cứu, tăng tốc triển khai quy định, giảm rủi ro bỏ sót.
**Nguồn: INDA — "AI Đọc Hiểu Thông Tư NHNN: Cách Ngân Hàng Tự Động Hóa Công Tác Pháp Chế Và Tuân Thủ Năm 2026"**

### Card 2 — AI CHO TUÂN THỦ
**AI không chỉ được dùng cho chăm sóc khách hàng**
VNBA ghi nhận nhiều ngân hàng VN đã ứng dụng AI trong quản trị, tín dụng, kế toán, kiểm soát tuân thủ và xử lý dữ liệu văn bản. AI phải đi kèm quản trị dữ liệu, an toàn thông tin và kiểm soát rủi ro.
**Nguồn: Hiệp hội Ngân hàng Việt Nam — "Hành trình ứng dụng đổi mới sáng tạo AI trong ngành ngân hàng Việt Nam"**

### Card 3 — NHU CẦU TRIỂN KHAI THỰC TẾ
**Ngành ngân hàng đang chủ động trang bị kỹ năng AI**
VNBA tổ chức khóa đào tạo AI cho lãnh đạo cấp chi nhánh, cấp phòng và cán bộ quản lý. Nội dung: ChatGPT, Gemini, NotebookLM và ứng dụng AI trong nghiệp vụ, quản trị và vận hành.
**Nguồn: Trung tâm Đào tạo – VNBA — "Kỹ năng ứng dụng AI vào hoạt động kinh doanh ngân hàng thương mại"**

### Card 4 — AI AN TOÀN — CÓ KIỂM SOÁT
**AI là hướng đi chiến lược nhưng phải bảo đảm an toàn**
VNBA nhận định AI đang trở thành động lực cốt lõi của ngành ngân hàng. Việc ứng dụng phải diễn ra an toàn, có kiểm soát và phù hợp với định hướng quản trị rủi ro.
**Nguồn: VNBA — "Trí tuệ nhân tạo sẽ là động lực chiến lược định hình truyền thông chính sách và sản phẩm, dịch vụ ngân hàng trong kỷ nguyên số"**

**Chuỗi kết luận:**
```
Quy định thay đổi liên tục
→ Tra cứu và đối chiếu tốn thời gian
→ Nguy cơ bỏ sót hoặc dùng sai phiên bản
→ Ngành đã chủ động ứng dụng AI
→ Cần AI có kiểm soát nguồn và bằng chứng
```

**Nhu cầu người dùng rút ra:** tìm đúng quy định, xác định đúng phiên bản, rà soát tài liệu nhanh hơn, truy vết kết luận, giữ quyền kiểm soát cho cán bộ.

**Thuyết trình:** "Các nguồn cho thấy cả pain point và market readiness đều tồn tại. Nhu cầu không chỉ là dùng AI để đọc nhanh hơn, mà là dùng AI trong một workflow có xác minh nguồn, hiệu lực và bằng chứng."

---

## Slide 5 — Công trình liên quan và khoảng trống

**Tiêu đề kết luận:** HỎI ĐÁP TÀI LIỆU KHÔNG ĐỒNG NGHĨA VỚI BẢO ĐẢM TUÂN THỦ

**Trái — Pipeline Document AI/RAG:**
```
Thu thập tài liệu → OCR và xử lý → Chia nhỏ nội dung
→ Embedding → Kho tìm kiếm → Truy xuất
→ LLM tạo câu trả lời có dẫn nguồn
```
Khả năng: tìm kiếm quy định, tóm tắt, hỏi đáp, so sánh, citation.
Đầu ra: **Câu trả lời + Trích dẫn**

**Phải — Nghiệp vụ tuân thủ cần thêm:**
- Nguồn phải được con người xác minh
- Có trạng thái chờ duyệt/phê duyệt/kích hoạt
- Lọc phiên bản theo ngày hiệu lực
- Phân biệt nguồn pháp lý và file cần review
- Kết quả nhận xét phải có cấu trúc
- Trường hợp thiếu bằng chứng phải được cảnh báo
- Quyết định cuối cùng thuộc về cán bộ

Đầu ra: **Nhận xét + Bằng chứng + Hành động đề xuất**

**Khoảng trống:** "Một câu trả lời có nguồn chưa chắc đã sử dụng đúng căn cứ pháp lý tại đúng thời điểm."

**Câu kết:** "RAG giúp tìm và trả lời từ tài liệu. AIDE kiểm soát tài liệu nào được phép trở thành căn cứ."

**Thuyết trình:** "AIDE không phủ nhận giá trị của RAG. AIDE sử dụng RAG làm nền tảng, sau đó bổ sung lớp nghiệp vụ về phê duyệt nguồn, hiệu lực và review tài liệu nội bộ."

---

## Slide 6 — Giải pháp đề xuất

**Tiêu đề kết luận:** MỘT KHO PHÁP LÝ ĐÃ XÁC MINH — HAI CHẾ ĐỘ LÀM VIỆC

**Cấu trúc 3 phần:**

### 1. Thêm nguồn
Tải văn bản pháp lý → Trích xuất text/OCR → LLM trực tiếp đọc và trích xuất → Tạo dữ liệu có cấu trúc → Cán bộ kiểm tra và chỉnh sửa → Phê duyệt và kích hoạt

### 2. Kho pháp lý đã xác minh
Chỉ chứa nguồn: là văn bản pháp lý, đã được cán bộ phê duyệt, đang hoạt động, phù hợp với ngày tra cứu.

### 3. Không gian RAG
- **Tra cứu quy định:** quy định hiện hành, lịch sử thay đổi, ngày hiệu lực, bằng chứng pháp lý
- **Nhận xét tài liệu:** tải policy/báo cáo nội bộ, trích xuất nội dung quan trọng, đối chiếu với nguồn đã phê duyệt, finding và gợi ý điều chỉnh

**Business rules:**
- Tải lên ≠ đáng tin cậy
- Chỉ nguồn đã phê duyệt và kích hoạt mới được dùng
- File review không đi vào kho pháp lý
- LLM đề xuất, con người quyết định

**Hình ảnh:**
```
THÊM NGUỒN → KHO PHÁP LÝ ĐÃ XÁC MINH → KHÔNG GIAN RAG
                                             ├─ Tra cứu
                                             └─ Nhận xét
```

**Thuyết trình:** "Add Source tạo ra nguồn đáng tin cậy; RAG sử dụng chính nguồn đó để tra cứu hoặc rà soát tài liệu."

---

## Slide 7 — Pipeline tổng thể

**Tiêu đề kết luận:** TỪ TÀI LIỆU ĐẦU VÀO ĐẾN KẾT QUẢ CÓ BẰNG CHỨNG

*Vẽ trong một hình duy nhất.*

**Nhánh xây dựng kho:**
```
Văn bản pháp lý → Trích xuất text/OCR
→ LLM đọc và trích xuất có cấu trúc
→ Metadata + Điều/Khoản + Hiệu lực + Evidence
→ Cán bộ kiểm tra, chỉnh sửa và phê duyệt
→ Kích hoạt → Kho pháp lý đã xác minh
```

**Nhánh tra cứu:**
```
Câu hỏi + Ngày tra cứu
→ Lọc nguồn đã phê duyệt và còn hiệu lực
→ Truy xuất điều khoản liên quan
→ LLM tạo câu trả lời
→ Văn bản + Điều/Khoản + Ngày hiệu lực + Bằng chứng
```

**Nhánh nhận xét tài liệu:**
```
Policy/Báo cáo nội bộ
→ Trích xuất text và nội dung quan trọng
→ Kết hợp ngày đánh giá
→ Truy xuất nguồn pháp lý phù hợp
→ LLM đối chiếu
→ Trạng thái + Căn cứ + Lý do + Gợi ý
```

**4 điểm kiểm soát trên pipeline:**
- **Cổng 1 — Xác minh nguồn:** Tải lên ≠ Căn cứ pháp lý
- **Cổng 2 — Phê duyệt:** Chỉ nguồn đã phê duyệt mới được kích hoạt
- **Cổng 3 — Thời gian hiệu lực:** Ngày đánh giá quyết định phiên bản được sử dụng
- **Cổng 4 — Tách file review:** Tài liệu nội bộ không đi vào kho pháp lý

**Câu kết:** "LLM đọc tài liệu — Con người xác minh nguồn — AIDE tạo kết quả kèm bằng chứng."

---

## Slide 8 — Thành phần và công nghệ

**Tiêu đề:** MỖI THÀNH PHẦN GIẢI QUYẾT MỘT PHẦN CỦA PIPELINE

| Lớp | Thành phần | Vai trò |
|---|---|---|
| Giao diện | Web application | Upload, review, approve, tra cứu, xem báo cáo |
| Xử lý tài liệu | Text extraction/OCR | Đọc PDF, DOCX, scan và giữ vị trí trang |
| Hiểu tài liệu | LLM structured output | Trích metadata, điều khoản, ngày hiệu lực và claim |
| Kiểm soát nguồn | Human Review Gate | Kiểm tra, chỉnh sửa, phê duyệt hoặc từ chối |
| Kho dữ liệu | Database | Lưu tài liệu, phiên bản, trạng thái và lịch sử review |
| Tổ chức tri thức | Chunk theo cấu trúc | Giữ ngữ cảnh Điều/Khoản khi chia tài liệu |
| Truy xuất | Lexical/vector search | Tìm nội dung pháp lý liên quan |
| Kiểm soát thời gian | Bộ lọc ngày hiệu lực | Chọn đúng phiên bản tại ngày đánh giá |
| Phân tích | LLM | Sinh câu trả lời hoặc nhận xét có cấu trúc |
| Kiểm chứng | Evidence package | Hiển thị văn bản, điều, khoản, trang và đoạn nguồn |

**Điểm cần nói rõ:**
- Add Source không dùng rule-based parser — LLM trực tiếp đọc và trích xuất
- Human Review Gate bảo đảm độ tin cậy
- Chỉ trình bày công nghệ thực sự chạy trong demo

**Thuyết trình:** "Trong MVP, nhóm lựa chọn LLM-first để giảm thời gian phát triển parser riêng. Đánh đổi là kết quả trích xuất cần con người kiểm tra trước khi sử dụng."

---

## Slide 9 — So sánh pipeline và USP

**Tiêu đề kết luận:** KHÁC BIỆT KHÔNG NẰM Ở LLM — MÀ NẰM Ở PIPELINE KIỂM SOÁT

**RAG thông thường:**
```
Tài liệu → OCR → Chunking → Embedding
→ Knowledge Base → Retrieval → LLM
→ Câu trả lời có dẫn nguồn
```
Mục tiêu: **Tra cứu và hỏi đáp tài liệu**

**Pipeline AIDE:**
```
Nguồn chờ duyệt → Text extraction/OCR
→ LLM trích xuất có cấu trúc
→ Cán bộ kiểm tra → Phê duyệt và kích hoạt
→ Kho pháp lý đã xác minh
→ Lọc theo ngày hiệu lực
→ Tra cứu hoặc nhận xét tài liệu
→ Output có evidence và gợi ý
```
Mục tiêu: **Kiểm soát nguồn và hỗ trợ rà soát tuân thủ**

**Bảng so sánh:**

| Tiêu chí | AI đọc hiểu/RAG | AIDE |
|---|---|---|
| Mục tiêu | Hỏi đáp, tóm tắt | Tra cứu và rà soát |
| Nguồn đầu vào | Tài liệu trong kho | Nguồn phải được phê duyệt |
| Phiên bản | Phụ thuộc corpus | Lọc theo ngày hiệu lực |
| File review | Không phải trọng tâm | Tách khỏi kho pháp lý |
| Đầu ra | Answer + citation | Finding + evidence + suggestion |
| Con người | Kiểm chứng câu trả lời | Phê duyệt nguồn và kết quả |

**USP:** "AIDE kiểm soát tài liệu nào, phiên bản nào và bằng chứng nào được phép hỗ trợ cho một nhận xét tuân thủ."

**Câu định vị:** "Không chỉ là AI đọc hiểu thông tư — mà là một workflow tuân thủ được con người xác minh."

---

## Slide 10 — Giá trị, MVP, giới hạn và lộ trình

**Tiêu đề kết luận:** TẬP TRUNG PHẠM VI — CHỨNG MINH GIÁ TRỊ — MỞ RỘNG AN TOÀN

**Giá trị theo đối tượng:**

| Đối tượng | Giá trị |
|---|---|
| Cán bộ Pháp chế/Tuân thủ | Tra cứu nhanh hơn, đúng phiên bản, phát hiện căn cứ lỗi thời, có evidence |
| Trưởng bộ phận | Chuẩn hóa kết quả, theo dõi trạng thái phê duyệt, dễ xử lý trường hợp cần xem xét |
| Đơn vị nghiệp vụ | Biết nội dung cần cập nhật, nhận gợi ý cụ thể, giảm vòng trao đổi với Pháp chế |
| Quản trị rủi ro/Kiểm toán | Truy vết nguồn → phiên bản → evidence → finding, dễ giải trình |

**Phạm vi MVP 48 giờ:**

Cần chứng minh:
- Một persona: cán bộ Pháp chế/Tuân thủ
- Một bộ dữ liệu pháp lý tập trung
- Add Source chạy end-to-end
- LLM trích xuất có cấu trúc
- Human Review và activation
- Tra cứu quy định + Nhận xét tài liệu
- Output có evidence
- Frontend kết nối backend thật
- Deploy để giám khảo thao tác

Không cố hoàn thiện:
- Toàn bộ pháp luật ngân hàng
- OCR hoàn hảo
- Enterprise IAM đầy đủ
- Batch review quy mô lớn
- Tự động quyết định pháp lý
- Production-scale benchmark

**Giới hạn hiện tại:**
- LLM có thể trích xuất sai metadata
- Có thể hiểu nhầm điều khoản hoặc sửa đổi
- OCR lỗi ảnh hưởng kết quả
- Dataset còn giới hạn
- Chưa có deterministic validation đầy đủ
- Security và audit chưa đạt production
- Human Review vẫn bắt buộc

**Lộ trình:**

| Giai đoạn | Nội dung |
|---|---|
| 1 — Nâng độ tin cậy | Kiểm tra số hiệu và ngày, xác minh Điều/Khoản, kiểm tra evidence, OCR nâng cao, mở rộng eval dataset |
| 2 — Quy trình an toàn | Phân quyền, audit log, phân công và phê duyệt, xuất báo cáo |
| 3 — Mở rộng doanh nghiệp | Batch review, theo dõi quy định mới, phân tích tác động, mở rộng domain, tích hợp hệ thống quản lý tài liệu |

**Câu kết bài:**
> AIDE hỗ trợ.
> Bằng chứng làm căn cứ.
> Con người quyết định.

---

## Nguồn tham khảo (4 nguồn)

1. **INDA** — "AI Đọc Hiểu Thông Tư NHNN: Cách Ngân Hàng Tự Động Hóa Công Tác Pháp Chế Và Tuân Thủ Năm 2026"
   https://inda.vn/ai-doc-hieu-thong-tu-nhnn/

2. **Hiệp hội Ngân hàng Việt Nam** — "Hành trình ứng dụng đổi mới sáng tạo AI trong ngành ngân hàng Việt Nam"
   https://vnba.org.vn/vi/hanh-trinh-ung-dung-doi-moi-sang-tao-ai-trong-nganh-ngan-hang-viet-nam-18927.htm

3. **Trung tâm Đào tạo – VNBA** — "Kỹ năng ứng dụng AI vào hoạt động kinh doanh ngân hàng thương mại"
   https://vnba.org.vn/vi/vnba/study/ky-nang-ung-dung-ai-vao-hoat-dong-kinh-doanh-ngan-hang-thuong-mai-257.htm

4. **Hiệp hội Ngân hàng Việt Nam** — "Trí tuệ nhân tạo sẽ là động lực chiến lược định hình truyền thông chính sách và sản phẩm, dịch vụ ngân hàng trong kỷ nguyên số"
   https://vnba.org.vn/vi/tri-tue-nhan-tao--ai--se-la-dong-luc-chien-luoc-dinh-hinh-truyen-thong-chinh-sach-va-san-pham--dich-vu-ngan-hang-trong-ky-nguyen-so-18702.htm
