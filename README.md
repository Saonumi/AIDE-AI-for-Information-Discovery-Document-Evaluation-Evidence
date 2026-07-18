# VAIC2026 — Temporal Regulatory RAG (SHB1)

AI chatbot cho tài liệu quy định ngân hàng, giải quyết **bằng chứng trước khi trả lời**: tự lần tham chiếu chéo, chọn đúng phiên bản tại thời điểm được hỏi, áp dụng sửa đổi một phần bằng patch có kiểm duyệt, cảnh báo quy định xung đột & policy nội bộ lỗi thời — mỗi câu trả lời kèm citation, timeline, nguồn bị loại và trạng thái kiểm tra.

> **LLM không bao giờ quyết định điều gì quan trọng.** Version/hiệu lực/sửa đổi/xung đột do luật tất định + graph quyết; LLM chỉ viết văn xuôi trên gói bằng chứng đã lắp ráp sẵn.

📄 **Tài liệu đầy đủ (kiến trúc, từng module, lý do chọn kỹ thuật, điểm khác biệt vs paper, benchmark): [`docs/project.md`](docs/project.md).**

## Yêu cầu
- Python **3.11+** (`python --version` để kiểm tra)
- Docker Desktop (chỉ cần cho chế độ 4-store bên dưới)

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

Sau đó mở tab mới:
```bash
streamlit run ui/app.py    # UI → http://localhost:8501
```

> `DEMO_MODE=true` dùng stub in-memory — không cần Docker, không cần API key nào.

Tài khoản: `employee/employee123` (EMPLOYEE) · `user/user123` (USER).

## Chạy đầy đủ 4-store (deploy)
```bash
cp .env.example .env          # điền GOOGLE_API_KEY (AI Studio) để dùng LLM thật
docker compose up --build     # postgres · opensearch · neo4j · api(:8000) · ui(:8501)
```

## Kiểm thử & đánh giá
```bash
python -m pytest tests/ -q    # 76 passed
python -m eval.run_eval       # benchmark head-to-head vs Standard RAG
```

## Kiến trúc (mỗi thư mục một chức năng)
```
packages/contracts  models Pydantic (FROZEN)      ingestion/  Track A: upload → activate (đường ghi)
packages/common     vn_normalize, tokenize, ids   query/      Track B: retrieval → answer (+ standard_rag baseline)
infra/              postgres, opensearch, neo4j    ui/         Streamlit (chat, compare, KG viz, review, audit)
llm/                client (anthropic|openai|mock) eval/       harness + metrics
api/                FastAPI + JWT + RBAC           data/       seed + golden questions + corpus
```

## Kịch bản demo (10 cảnh)
Standard RAG fail (head-to-head) → point-in-time (500) vs hiện hành (700) → panel "Vì sao" (nguồn bị loại + lý do) → partial supersession (giữ "12 tháng") → cross-reference + KG viz → compliance-gap radar (policy nội bộ STALE) → conflict 700/600 → prompt-injection flag → INSUFFICIENT_EVIDENCE.
