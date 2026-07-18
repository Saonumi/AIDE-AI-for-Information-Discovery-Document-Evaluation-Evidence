# Deploy lên Railway — hướng dẫn cụ thể

2 phương án. Nếu chỉ cần demo online nhanh cho ban giám khảo → **Phương án A** (5 phút, 2 service).
Nếu cần đúng kiến trúc 4-store → **Phương án B** (5 service).

Repo đã có sẵn `railway.json` (root): builder = Dockerfile, start command = `uvicorn ... --port $PORT` — backend service KHÔNG cần chỉnh start command thủ công.

> **Trước khi làm bất cứ gì:** file `.env` local đang chứa `GOOGLE_API_KEY` và `OPENROUTER_API_KEY` thật.
> Kiểm tra `.env` không bị commit (`git check-ignore .env` phải in ra `.env`), và **rotate key trước khi repo public**.
> Trên Railway, key đặt trong Service Variables — không bao giờ đưa vào repo.

---

## Phương án A — Lite (DEMO_MODE, không cần database)

Backend chạy in-memory store + mock/real LLM. Đủ cho demo chấm điểm UI + API.

### A1. Backend
1. https://railway.app → **New Project → Deploy from GitHub repo** → chọn repo này.
2. Railway đọc `railway.json` → build Dockerfile, start đúng `$PORT`. Không cần chỉnh gì.
3. **Settings → Networking → Generate Domain** (được URL dạng `https://<backend>.up.railway.app`).
4. **Variables:**
   | Biến | Giá trị |
   |---|---|
   | `DEMO_MODE` | `true` |
   | `SEED_DEMO` | `1` |
   | `JWT_SECRET` | chuỗi random dài (vd `openssl rand -hex 32`) |
   | `LLM_PROVIDER` | `google` (hoặc `mock` nếu không muốn dùng key) |
   | `LLM_MODEL` | `gemini-3.1-flash-lite` |
   | `GOOGLE_API_KEY` | key của bạn |
5. Deploy xong, verify: `curl https://<backend>.up.railway.app/health/details`
   → mong đợi các store `memory/fallback`, app chạy OK (Lite chấp nhận `degraded`).

### A2. Frontend
1. Cùng project → **+ New → GitHub Repo** → chọn LẠI repo này (service thứ 2).
2. **Settings → Source → Root Directory:** `frontend/nextjs_app` (quan trọng — service này build Next.js, KHÔNG dùng Dockerfile Python ở root; root directory khác nên `railway.json` root không áp vào).
3. **Variables:**
   | Biến | Giá trị |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | `https://<backend>.up.railway.app` (URL từ A1.3, **không** có `/` cuối) |
4. Railway (railpack) tự nhận Next.js + pnpm (`pnpm-lock.yaml` có sẵn): build `pnpm build`, start `next start` (tự đọc `$PORT`).
5. **Generate Domain** cho frontend → mở URL, tab **Chat Modes (Ask · Review)** phải gọi được API.

> `NEXT_PUBLIC_*` là biến **build-time**. Đổi giá trị thì phải **Redeploy** frontend mới ăn.

---

## Phương án B — Full 4-store (Postgres + OpenSearch + Neo4j)

Cần plan **Hobby** ($5/tháng) trở lên — riêng OpenSearch ăn ~1GB RAM, free trial không đủ.

### B1. PostgreSQL (managed)
1. Trong project → **+ New → Database → Add PostgreSQL**.
2. Xong. Railway tự tạo `PGUSER/PGPASSWORD/PGDATABASE/RAILWAY_PRIVATE_DOMAIN` cho service tên `Postgres`.

### B2. OpenSearch (Docker image + volume)

1. Trong project → nút **+ New** (góc phải trên) → chọn **Docker Image**.
2. Ô "Enter a Docker image..." — dán CHÍNH XÁC chuỗi này (image Docker Hub, không cần prefix registry):
   ```
   opensearchproject/opensearch:2.13.0
   ```
   → Enter → Railway tạo service và bắt đầu pull image (~700MB, chờ 1-3 phút).
3. **Đổi tên service** (bắt buộc — tên service chính là hostname nội bộ):
   click service → **Settings** → mục **Service Name** → xóa tên tự sinh, gõ:
   ```
   opensearch
   ```
4. **Variables** tab → click **Raw Editor** (góc phải) → dán nguyên khối 4 dòng → **Update Variables**:
   ```
   discovery.type=single-node
   plugins.security.disabled=true
   DISABLE_INSTALL_DEMO_CONFIG=true
   OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m
   ```
5. **Volume**: click chuột phải vào service `opensearch` trên canvas → **Attach Volume**
   (hoặc + New → Volume rồi chọn service) → ô **Mount path** gõ:
   ```
   /usr/share/opensearch/data
   ```
6. Service sẽ tự redeploy sau khi đổi variables/volume. **KHÔNG bấm Generate Domain** — store này chỉ nói chuyện nội bộ qua `opensearch.railway.internal:9200`.
7. Kiểm tra: **Deployments → View Logs** — thấy dòng kiểu `[opensearch] ... started` / `Cluster health status changed ... to [GREEN]` là OK.
   Nếu log báo OOM / container restart liên tục: Settings → **Resources** → kéo Memory lên `2 GB`.

### B3. Neo4j (Docker image + volume)

1. **+ New → Docker Image** → dán:
   ```
   neo4j:5.18
   ```
2. **Settings → Service Name** đổi thành:
   ```
   neo4j
   ```
3. **Variables → Raw Editor** → dán (TỰ THAY `MatKhauManh123` bằng mật khẩu của bạn, giữ nguyên format `neo4j/<password>`):
   ```
   NEO4J_AUTH=neo4j/MatKhauManh123
   NEO4J_server_memory_heap_initial__size=256m
   NEO4J_server_memory_heap_max__size=256m
   NEO4J_server_memory_pagecache_size=128m
   ```
   3 dòng memory là BẮT BUỘC trên Railway: thiếu chúng (hoặc set to hơn RAM limit của container) Neo4j 5
   validate fail lúc boot — `Invalid memory configuration - exceeds physical memory` → crash-loop,
   không bao giờ thấy `Started.`. Chú ý `__` (2 gạch dưới) trong tên biến — escape của dấu `.`.
   Settings → Resources: Memory ≥ 1 GB.
4. **Attach Volume** → Mount path:
   ```
   /data
   ```
5. KHÔNG Generate Domain. Backend sẽ gọi nội bộ `bolt://neo4j.railway.internal:7687`.
6. Logs thấy `Started.` là OK.

### B4. Backend

1. **+ New → GitHub Repo** → chọn repo này. Railway đọc `railway.json` ở root → tự build Dockerfile + start đúng `$PORT`, không chỉnh gì thêm.
2. **Settings → Service Name** đổi thành `backend` (cho dễ nhìn — tên này không ảnh hưởng config).
3. **Settings → Networking → Generate Domain** → ghi lại URL (dùng cho frontend ở B5).
4. **Variables → Raw Editor** → dán nguyên khối, rồi TỰ THAY 3 chỗ: `MatKhauManh123` (mật khẩu Neo4j ở B3), `JWT_SECRET`, `GOOGLE_API_KEY`:
   ```
   DEMO_MODE=false
   SEED_DEMO=1
   DB_BACKEND=postgres
   POSTGRES_DSN=postgresql+psycopg://${{Postgres.PGUSER}}:${{Postgres.PGPASSWORD}}@${{Postgres.RAILWAY_PRIVATE_DOMAIN}}:5432/${{Postgres.PGDATABASE}}
   OPENSEARCH_HOST=opensearch.railway.internal
   OPENSEARCH_PORT=9200
   OPENSEARCH_SCHEME=http
   NEO4J_URI=bolt://neo4j.railway.internal:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=MatKhauManh123
   JWT_SECRET=doi-thanh-chuoi-random-dai-64-ky-tu
   LLM_PROVIDER=google
   LLM_MODEL=gemini-3.1-flash-lite
   GOOGLE_API_KEY=AIza...key-cua-ban
   ```
   Lưu ý: giữ NGUYÊN cú pháp `${{Postgres.PGUSER}}` — đó là reference variable, Railway tự điền khi runtime. Điều kiện: service Postgres ở B1 mang đúng tên `Postgres` (tên mặc định khi Add PostgreSQL; nếu bạn đã đổi tên, sửa các `${{Postgres.*}}` theo tên đó).
5. **Update Variables** → service redeploy. Chờ deploy xanh.

Ghi chú:
- `${{Postgres.PGUSER}}` là **reference variable** của Railway — tự điền từ service Postgres. Prefix `postgresql+psycopg://` là BẮT BUỘC (driver SQLAlchemy); đừng dùng nguyên `DATABASE_URL` Railway cấp (thiếu `+psycopg`).
- Private network chỉ hoạt động giữa service **cùng project/environment**; hostname = tên service viết thường + `.railway.internal`.
- Deploy backend SAU KHI 3 store Running — backend không crash nếu store chưa lên (nó fallback), nhưng seed sẽ rơi vào memory và mất công seed lại (redeploy với `SEED_DEMO=1`).

### B5. Frontend
Giống hệt A2.

### B6. Verify sau deploy (chạy từ máy bạn)
```bash
BASE=https://<backend>.up.railway.app
curl -s $BASE/health/details
# mong đợi: postgres/opensearch/neo4j đều "connected"
# (embedding "hash_fallback" là bình thường — chưa cài bge-m3, xem Bẫy #5)

TOKEN=$(curl -s -X POST $BASE/login -H "Content-Type: application/json" \
  -d '{"username":"compliance","password":"compliance123"}' | python -c "import sys,json;print(json.load(sys.stdin)['token'])")

# golden scenario: policy 500tr → OUTDATED_REFERENCE
curl -s -X POST $BASE/review-runs -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"filename":"policy.txt","text":"Hạn mức tín dụng SME tối đa là 500 triệu đồng.","assessment_date":"2026-07-18"}'
```

---

## Bẫy đã biết (đã dính khi test local — tránh lặp lại)

1. **`$PORT`**: `railway.json` đã bind `--port $PORT`; nếu tự tạo service bỏ qua file này sẽ gặp "Application failed to respond".
2. **Postgres enforce VARCHAR**: đã fix trong code (`role` VARCHAR(32) trong `users` + `audit_logs`); deploy nhánh cũ trước fix → seed crash `StringDataRightTruncation`.
3. **opensearch-py 3.x**: đã fix (`indices.exists(index=...)`); nhánh cũ silently fallback về in-memory dù OpenSearch xanh — triệu chứng: health báo `fallback_memory` trong khi container Running.
4. **Frontend gọi sai API**: `NEXT_PUBLIC_API_URL` phải đặt TRƯỚC build; thiếu → frontend gọi `http://localhost:8000` → connection refused trên production.
5. **Embedding degraded**: image không cài FlagEmbedding (~2GB) → `embedding: hash_fallback`, health `degraded` nhưng mọi flow chạy bình thường. Muốn "ok" hoàn toàn: thêm `FlagEmbedding` vào `requirements.txt` + RAM backend ≥2GB (không khuyến nghị cho demo).
6. **Chi phí**: Full stack B ≈ 2–3GB RAM tổng, tính tiền theo usage — tắt project sau khi chấm xong.

## Gắn domain riêng (custom domain)

Layout khuyến nghị: frontend = `app.<domain>`, backend = `api.<domain>`.

### 1. Backend → `api.<domain>`
1. Service backend → **Settings → Networking → Public Networking → + Custom Domain**.
2. Gõ `api.<domain>` → Railway hiện giá trị CNAME target (dạng `<xxx>.up.railway.app`).
3. Sang trang quản trị DNS của domain (Cloudflare/Namecheap/GoDaddy/...) thêm record:
   ```
   Type:  CNAME
   Name:  api
   Value: <xxx>.up.railway.app   (copy đúng giá trị Railway hiện)
   ```
4. Quay lại Railway chờ trạng thái domain chuyển xanh (DNS propagate 1–30 phút). TLS cert (Let's Encrypt) Railway tự cấp — không phải làm gì.

### 2. Frontend → `app.<domain>`
Làm y hệt: + Custom Domain `app.<domain>` → thêm CNAME `app` → chờ xanh.

### 3. BẮT BUỘC sau khi backend có domain mới
Frontend đang build với `NEXT_PUBLIC_API_URL` cũ (URL `*.up.railway.app`). Đổi:
1. Service frontend → Variables → sửa:
   ```
   NEXT_PUBLIC_API_URL=https://api.<domain>
   ```
2. **Redeploy frontend** (biến build-time — không redeploy là frontend vẫn gọi URL cũ).
Backend không phải sửa gì (CORS đang mở `*`).

### Lưu ý theo nhà cung cấp DNS
- **Cloudflare**: bật proxy (đám mây cam) được, nhưng đặt SSL/TLS mode = **Full** (đừng để Flexible — sẽ loop redirect). Nếu gặp lỗi cert lúc verify, tạm chuyển sang DNS only (đám mây xám) cho tới khi Railway cấp cert xong rồi bật lại.
- **Root/apex domain** (`<domain>` không có subdomain): CNAME không gắn được vào apex theo chuẩn DNS. Dùng CNAME flattening (Cloudflare hỗ trợ sẵn) hoặc ALIAS/ANAME nếu provider có; không có thì dùng `www.<domain>` + redirect apex → www.
- Railway **không cấp IP tĩnh** — luôn dùng CNAME, đừng cố tạo A record.

## Checklist nộp bài
- [ ] `.env` không nằm trong git, key đã rotate
- [ ] Backend `/health/details`: 3 store `connected`
- [ ] Frontend mở được, tab Chat Modes chạy end-to-end (Ask → Review → Batch)
- [ ] `SEED_DEMO=1` đã chạy ít nhất 1 lần (corpus golden có trong store)
- [ ] Ghi 2 URL (frontend + backend) vào tài liệu nộp
