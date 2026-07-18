# Kịch bản demo 5 phút — VAIC2026 SHB1

## Chuẩn bị (trước khi lên sân khấu)

```powershell
# Terminal 1 — backend (offline, không cần Docker)
$env:DEMO_MODE="true"; $env:SEED_DEMO="1"
# LLM thật qua OpenRouter (khuyến nghị cho demo):
$env:LLM_PROVIDER="openrouter"; $env:OPENROUTER_API_KEY="sk-or-..."
$env:LLM_MODEL="anthropic/claude-sonnet-4.5"
uvicorn api.main:app --port 8000

# Terminal 2 — UI
streamlit run ui/app.py
```

Đăng nhập: `employee / employee123`. Mở sẵn 3 file trong thư mục:
- `data/golden/review_targets/bao_cao_tuan_thu_outdated.txt`
- `data/golden/review_targets/chinh_sach_compliant.txt`
- 1 file amendment .txt tự soạn (mẫu ở cuối) — hoặc PDF thật `data/crawl/sbv/raw/` (85/2025/TT-NHNN)

Chạy trước 1 lần để warm: trang So sánh + trang Kiểm tra tuân thủ.

---

## Timeline

### 0:00–0:45 — HOOK: cho Standard RAG sai live
Trang **So sánh** → hỏi *"Hạn mức tín dụng SME hiện tại là bao nhiêu?"*.
- Trái (Standard RAG): trộn 500/700 hoặc trích bản cũ — **sai**.
- Phải (hệ ta): 700 triệu, citation đúng version, kèm timeline 500→700.

> **Nói:** "Đây là lý do chatbot pháp lý thường không dùng được trong ngân hàng:
> nó không biết văn bản nào còn hiệu lực. Sản phẩm của chúng tôi bắt đầu từ chỗ đó."

### 0:45–1:15 — Trust model (trang Tổng quan)
Chỉ 2 card: *"Không file nào upload lên tự trở thành căn cứ pháp lý.
Một luồng xác minh nguồn; một luồng dùng kho đã xác minh để kiểm tra tài liệu."*

### 1:15–2:30 — Workflow A: upload → 409 → review → activate
Trang **Thêm nguồn pháp lý**:
1. Upload file amendment (.txt mẫu hoặc PDF 85/2025/TT-NHNN — nhấn mạnh **văn bản NHNN thật crawl từ SBV**).
2. Bấm **Activate ngay** → màn hình đỏ **HTTP 409 REVIEW_NOT_COMPLETED**.
   > **Nói:** "Gate này là business rule ở service layer, không phải UI — API gọi thẳng cũng bị chặn."
3. Sang **Review inbox** → mở task, xem trước/sau + confidence → **Duyệt**.
4. Quay lại → **Activate** → 200, V1 đóng hiệu lực, V2 mở, ChangeEvent ghi nhận.
5. (Nếu còn thời gian) Hỏi đáp point-in-time: *"...vào ngày 01/03/2026?"* → trả bản CŨ đúng,
   panel "Vì sao" hiển thị **bản mới bị loại kèm lý do**.

### 2:30–4:00 — Workflow B: chấm điểm tuân thủ tài liệu (điểm nhấn chính)
Trang **Kiểm tra tuân thủ** → upload `bao_cao_tuan_thu_outdated.txt`:
- Claim "hạn mức 500 triệu" → **⏳ OUTDATED_REFERENCE** + đề xuất: *"500.000.000 là giá trị
  của phiên bản ĐÃ BỊ THAY THẾ; hiện hành: 700.000.000"*.
- Claim "tỷ lệ 34% theo 22/2019/TT-NHNN" → **OUTDATED_REFERENCE** (30% từ 08/2026/TT-NHNN —
  **cặp amendment định danh thật mined từ SBV**).
- Claim deadline → **MISSING_EVIDENCE**: *"Hệ thống không đoán khi thiếu căn cứ."*

Upload tiếp `chinh_sach_compliant.txt`:
- Tỷ lệ 30% → **✅ COMPLIANT** kèm citation hiện hành.
- Hạn mức 700 → **❓ AMBIGUOUS** vì QĐ-03 (600) đồng hiệu lực.
  > **Nói:** "Chatbot thường sẽ nói 'hợp lệ'. Hệ chúng tôi phát hiện có quy định xung đột
  > đồng hiệu lực và đẩy cho con người quyết — đây là hành vi đúng của công cụ tuân thủ."

### 4:00–4:30 — Compliance-Gap Radar + Audit
Trang **Dashboard**: policy nội bộ NB-SME-01 (500tr, aligned V1) bị đánh dấu **stale** sau amendment.
Trang **Audit**: mọi truy vấn/quyết định đều có vết (ai, khi nào, evidence nào, loại gì).

### 4:30–5:00 — Chốt
> "Một luồng xác minh quy định trước khi vào kho tri thức; một luồng dùng kho đã xác minh
> để kiểm tra policy và báo cáo. LLM chỉ viết giải thích — **mọi quyết định về hiệu lực,
> phiên bản, sai/đúng đều là code tất định + con người**. Đó là thứ một ngân hàng
> có thể audit được."

---

## Fallback khi trục trặc

| Sự cố | Xử lý |
|---|---|
| Không có Anthropic key / mạng | Chạy mock LLM (mặc định) — mọi phép tất định vẫn đúng; nói rõ "phần văn phong đang dùng mock offline" |
| Streamlit lỗi | Demo bằng REST (Postman/curl): POST /login → /compliance-checks → /report — JSON tự nói lên tất cả |
| Upload PDF parse yếu | Dùng file .txt mẫu dưới đây (nội dung chuẩn cấu trúc) |
| Quên tài khoản | employee/employee123 · user/user123 |

## File amendment .txt mẫu (Workflow A)

```
QUYẾT ĐỊNH QĐ-09/2026
Điều 1. Sửa đổi Khoản 2 Điều 7 Quyết định QĐ-01/2026
Thay cụm từ "700 triệu đồng" bằng "800 triệu đồng".
Hiệu lực từ ngày 01/08/2026.
```
(Đã smoke-test: upload → 409 → approve → activate 200. LƯU Ý: phải gõ **có dấu** —
văn bản không dấu parser sẽ không tạo review task.)

## Checklist trước giờ G
- [ ] `python -m pytest tests/ -q` → 97 passed
- [ ] Chạy eval với key thật, chụp bảng số vào slide: `LLM_PROVIDER=openrouter LLM_MODEL=anthropic/claude-sonnet-4.5 python -m eval.run_eval` (cần OPENROUTER_API_KEY)
- [ ] Warm cả 2 workflow một lần trên máy demo
- [ ] Slide tuân thủ PITCH.md mục 9 (không tự gọi là GraphRAG/chatbot)
