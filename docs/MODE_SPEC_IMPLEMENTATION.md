# Mode-Based Chat & Review Expansion — Báo cáo triển khai (§16.3)

Spec: `docs/VAIC2026_Mode_Based_Chat_and_Review_Expansion_Spec.docx` (v2.0).
Toàn bộ thay đổi nằm trên codebase canonical đang chạy — không tạo codebase thứ hai.

## 1. File tạo/sửa và lý do

### Backend — mới
| File | Lý do (spec) |
|---|---|
| `backend/app/chat/domain.py` | ChatMode, Conversation, ChatTurn, ConversationAttachment (§9.1) |
| `backend/app/chat/service.py` | Conversation service + isolation policy: owner_id+conversation_id enforce tại service layer; contextualize follow-up trong ĐÚNG 1 hội thoại (§3.1, §9) |
| `backend/app/api/routes_chat.py` | `/conversations*` (§12.2); owner từ auth token (§12.3) |
| `backend/app/review/domain.py` | ReviewRunState machine (§5.2), BatchItemStatus, BatchChatScope |
| `backend/app/review/service.py` | Review Run bất biến: freeze snapshot + versions → assess → verify allowlist → LOCK; rerun = run MỚI (§5, §5.3) |
| `backend/app/review/explainer.py` | Explainer bounded vào locked run JSON; guard đổi-status → từ chối; đổi-parameter → `CREATE_NEW_REVIEW_RUN` (§7.3, §10.3) |
| `backend/app/review/batch.py` | 1 file = 1 run độc lập, shared snapshot, bounded pool, recurring groups, retry failed-only, full rerun → batch mới (§8) |
| `backend/app/api/routes_review_runs.py` | `/review-runs*` (§12.2) |
| `backend/app/api/routes_batch_reviews.py` | `/batch-reviews*` (§12.2) |
| `backend/app/core/prompt_loader.py` | Loader prompt/schema có version (§10.1) |
| `backend/app/prompts/*.md` (5 file) | regulatory_assistant / review_evaluator / review_explainer / batch_summarizer / shared_safety_rules — prompt RIÊNG theo mode (§10.1, Phụ lục B) |
| `backend/app/schemas/*.schema.json` (5 file) | review_claim / claim_assessment / review_report / batch_review_report / evidence_reference (§10.1, Phụ lục A) |

### Backend — sửa
| File | Thay đổi |
|---|---|
| `infra/db_models.py` | +6 bảng: conversations, chat_turns, conversation_attachments, review_runs, batch_reviews, batch_review_items (§12.1) — additive, `create_all` tự thêm |
| `backend/app/domain/compliance.py` | +3 TrustClass: CONVERSATION_ATTACHMENT, USER_MESSAGE, REVIEW_RESULT (§4) |
| `backend/app/api/main.py` | Mount 3 router mới (guarded include — không chặn boot) |

### Frontend — mới/sửa
| File | Thay đổi |
|---|---|
| `frontend/nextjs_app/components/mode-chat.tsx` | Mode switch (§11.1), Single Review workspace (§11.2), Batch progress + recurring + scope selector (§11.3) |
| `frontend/nextjs_app/lib/api.ts` | +types/endpoints conversations, review-runs, batch-reviews |
| `frontend/nextjs_app/components/compliance-rag.tsx` | +nav "Chat Modes (Ask · Review)" |

### Tests — mới
`tests/test_chat_isolation.py` (7) · `tests/test_review_run.py` (9) · `tests/test_batch_review.py` (7)

## 2. Migration / schema
- SQLAlchemy `create_all` thêm 6 bảng mới — backward-compatible, không đổi bảng cũ, không cần data migration.
- API/source flow cũ giữ nguyên 100% (`/compliance-checks` cũ vẫn chạy — sẽ gỡ khi UI mới thay hoàn toàn, xem Limitations).

## 3. Cách chạy
```bash
# backend (offline demo: sqlite + in-memory store + mock LLM)
DEMO_MODE=true python -m uvicorn backend.app.api.main:app --port 8000
# frontend
cd frontend/nextjs_app && pnpm dev   # tab "Chat Modes (Ask · Review)"
```
- **Single review:** POST `/review-runs` `{filename, text, assessment_date}` → locked report; hỏi tiếp qua `/review-runs/{id}/questions`.
- **Batch review:** POST `/batch-reviews` `{files:[{filename,text}], assessment_date}` → progress per file, recurring issues; `/rerun` `{full:false}` = retry failed-only.

## 4. Versions đang dùng
| Thành phần | Version |
|---|---|
| parser | `review-parser-1.0` |
| prompt evaluator | `review-evaluator-1.0` |
| prompt explainer | `review-explainer-1.0` |
| prompt assistant | `regulatory-assistant-1.0` |
| schema assessment | `claim-assessment-1.0` |
Mỗi Review Run lưu `versions{parser,prompt,schema}` + `knowledge_snapshot_id` trong audit metadata.

## 5. Test command + kết quả
```bash
python -m pytest tests backend/tests -q     # FULL SUITE: 218 passed, 0 fail
python -m pytest tests/test_chat_isolation.py tests/test_review_run.py tests/test_batch_review.py -q  # 23/23 pass
```

## 6. Metric isolation/leakage (đo bằng test tất định)
| Metric (§15.2) | Kết quả |
|---|---|
| Cross-conversation leakage | 0% (`test_cross_conversation_attachment_isolation`, `test_new_chat_empty_memory`) |
| Review-target → global KB leakage | 0% (`test_review_target_never_indexed`, spy trên `index_chunk`) |
| Chat message → index | 0 lần gọi store (`test_chat_messages_never_indexed`) |
| Unapproved-source usage | 0% (retrieval chỉ đọc APPROVED — pipeline hiện có + allowlist verify) |
| Citation allowlist validity | 100% (`test_citation_allowlist_within_snapshot`, `test_explainer_citations_from_run_only`) |
| Locked result vs prompt injection | status không đổi (`test_prompt_injection_cannot_change_result`) |
| Frozen snapshot | old run bất biến sau activation; rerun → snapshot id mới (`test_frozen_snapshot_*`) |
| Batch isolation / partial failure / retry | per-file 100%; 1 file fail không hỏng batch; retry chỉ chạy lại failed (`test_partial_failure_and_retry_only_failed`) |
| Regression source flow | 0 test cũ fail (full suite xanh) |

## 6b. Integration test trên Docker 4-store (đã chạy thật)
`docker compose up -d postgres opensearch neo4j` + backend local (`DEMO_MODE=false`, `SEED_DEMO=1`):
- `/health/details`: postgres/opensearch/neo4j = **connected**, llm = google (embedding = hash_fallback vì chưa cài FlagEmbedding/bge-m3 — fallback có chủ đích).
- E2E qua HTTP: login → conversation → Ask Regulations (Gemini thật, 3 citations, checks passed) → Review Run `READY` + `OUTDATED_REFERENCE` đúng golden → explainer 4 citations → injection bị khóa (`result_locked`, status không đổi) → batch 3/3 completed, recurring group count=2 → batch chat.
- Dữ liệu persist thật trong Postgres (conversations/chat_turns/review_runs/batch_* có rows); OpenSearch index `provisions` 8 chunks.
- 2 bug chỉ lộ trên Postgres thật đã fix: `users.role`/`audit_logs.role` VARCHAR(16) tràn với `COMPLIANCE_OFFICER` (→32); opensearch-py 3.x đòi keyword arg `index=` trong `indices.exists/create`.
- Frontend: `pnpm build` production PASS.

## 7. Known limitations
- Reproducibility: engine so sánh là tất định (mock LLM = 100% deterministic); với LLM thật chỉ phần văn xuôi/polish thay đổi — status không đổi vì LLM không quyết status. Label drift chưa được log riêng.
- Upload trong UI chat mode nhận `.txt/.md` (đọc client-side); PDF/DOCX đi qua pipeline extraction hiện có ở luồng Add Regulatory Source — chưa nối vào Review Run upload.
- Batch worker pool mặc định 1 worker (SQLite-safe); tăng `BATCH_WORKERS` khi chạy Postgres.
- Tab "Kiểm tra tài liệu" (compliance-check cũ) vẫn giữ song song theo quy tắc M14.1 (không xóa route cũ trước khi UI mới thay thế hoàn toàn); Document Review mode là đường chính mới.
- `HUMAN_REVIEWED`/`CANCELLED` state có trong state machine nhưng chưa có UI thao tác.
- Explainer chọn finding theo overlap từ khóa (tất định); chưa có semantic matching đa finding.
