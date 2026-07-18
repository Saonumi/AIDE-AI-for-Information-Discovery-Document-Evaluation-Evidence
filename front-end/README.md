# SHB1 Front-end — Trợ lý Quy định Ngân hàng (Temporal RAG)

Giao diện web cho hệ thống **VAIC2026 · SHB1**. Là một SPA thuần
**HTML/CSS/JavaScript** — không cần Node, không cần build — gọi trực tiếp tới
backend FastAPI qua HTTP.

## Chạy nhanh

1. **Khởi động backend** (từ thư mục gốc dự án):

   ```bash
   uvicorn api.main:app --reload           # http://localhost:8000
   # hoặc: docker compose up
   ```

   Bật seed demo để có sẵn dữ liệu:

   ```bash
   SEED_DEMO=1 uvicorn api.main:app --reload
   ```

2. **Phục vụ front-end**:

   ```bash
   python front-end/serve.py               # http://localhost:5173
   ```

   Rồi mở <http://localhost:5173> trong trình duyệt.

   > Có thể mở thẳng `index.html`, nhưng một số trình duyệt chặn `fetch()` từ
   > origin `file://`. Dùng `serve.py` (hoặc bất kỳ static server nào) là chắc chắn nhất.

3. **Đăng nhập** bằng tài khoản demo:
   - `employee` / `employee123` — vai trò **Nhân viên** (đầy đủ trang)
   - `user` / `user123` — vai trò **Người dùng** (Hỏi đáp, So sánh, Đồ thị)

   Nếu backend chạy ở địa chỉ khác, sửa **Địa chỉ API** ngay trên màn hình đăng nhập.

## Các trang

| Trang | Vai trò | Endpoint | Mô tả |
|-------|---------|----------|-------|
| 💬 Hỏi đáp | USER, EMPLOYEE | `POST /query` | Câu trả lời + trạng thái + trích dẫn + timeline + panel *"Vì sao câu trả lời này"* (nguồn hợp lệ & nguồn bị loại kèm lý do). |
| ⚖️ So sánh | USER, EMPLOYEE | `POST /compare` | Head-to-head Standard RAG (sai theo thời gian) vs hệ thống Temporal/Graph. |
| 🕸️ Đồ thị KG | USER, EMPLOYEE | `GET /graph/provision/{id}` | Trực quan hoá subgraph điều khoản/phiên bản/sửa đổi bằng SVG force-layout tự viết. |
| 📥 Hộp thư rà soát | EMPLOYEE | `GET /review-tasks`, `POST /review-tasks/{id}/decision` | Duyệt / sửa & duyệt / từ chối, xem diff trước–sau. |
| 📚 Tài liệu | EMPLOYEE | `GET /documents`, `POST /documents`, `POST /documents/{id}/activate` | Tải lên, chỉ số tổng quan, cảnh báo injection, kích hoạt tài liệu. |
| 🧾 Audit | EMPLOYEE | `GET /audit` | Nhật ký truy vấn với nguồn đã dùng / bị loại và độ trễ. |

## Cấu trúc

```
front-end/
├── index.html          # khung ứng dụng (login + app shell)
├── css/style.css       # theme ngân hàng SHB (light), responsive
├── js/
│   ├── config.js       # cấu hình + nhãn tiếng Việt + câu hỏi mẫu
│   ├── api.js          # HTTP client (khớp ui/api_client.py), không ném lỗi mạng
│   ├── components.js   # hàm render dùng chung (answer, evidence, badge, toast)
│   ├── graph.js        # force-directed graph bằng SVG, không phụ thuộc CDN
│   └── app.js          # bootstrap + router + tất cả page controller
├── serve.py            # static server tiện dụng cho demo
└── README.md
```

## Ghi chú kỹ thuật

- **Token** lưu ở `localStorage` (`shb1.token`), gửi qua header `Authorization: Bearer`.
- **Địa chỉ API** lưu ở `localStorage` (`shb1.apiBase`), đổi được lúc đăng nhập.
- Toàn bộ tài nguyên **self-contained** (không tải CDN) → chạy được offline khi demo.
- Nhãn trạng thái/loại trừ/xung đột khớp đúng enum trong `packages/contracts/enums.py`.
- Client được thiết kế **resilient**: khi API lỗi, mỗi trang hiện thông báo thân thiện
  thay vì vỡ giao diện.
