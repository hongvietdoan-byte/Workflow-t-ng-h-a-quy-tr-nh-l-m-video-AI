# HANDOFF — cloud (nhánh `claude/read-s14-45-cloud-tasks-ngb0q2`)

Nhánh DỰNG LẠI 06/10 chiều trên `main` 52c08f6 (main đã có S14.11, S14.46, S14.47 khung chat; phiên khác đang làm S14.25). Credit cloud:
người dùng báo còn $73/100. Bản cũ trước khi dựng lại: commit 4dfea0f (chỉ còn trong reflog / nhánh cục bộ cloud).

## Trên nhánh (chưa có trên main) — phiên chính rà + cả bộ test Windows rồi gộp
- **S14.45** bảng chấm hiệu quả quy trình: `devsys/workflow.py`, `devsys/workflow_runs.jsonl` (19 nhánh nhập từ 'Số đo:'), trang devsys
  'Hiệu quả quy trình', skill mục 2 ghi số đo sau mỗi nhánh gộp. Rà nhẹ.
- **S14.24** agent chấm bài học CHẾ ĐỘ BÓNG: `core/lesson_judge.py` (cờ `lesson_judge` TẮT, ghi `lesson_reviews` ai_agent, không đổi bài
  học/knowledge; chủ đề đã bỏ đọc qua `core/retired_topics.matches`), khối trong tab Bài học (nút có giá). **RÀ KỸ** (lời gọi Claude tốn tiền).
- Sửa lỗi có sẵn: `dashboard/steps/step1_characters.py` thiếu `from typing import Optional` (Dashboard không import được trên Linux).
- Test `test_users`: đọc `query_params` cả dạng chuỗi (Streamlit 1.65) lẫn danh sách.
- **S14.50** (đổi từ S14.47) bản đồ 'Ai quyết' code / Claude / người: `devsys/decisions.json` + `devsys/decisions.py` + trang devsys.
- **S14.51** (đổi từ S14.48) màu nhân vật đo bằng code: `core/palette.py`, cột `characters.palette`, cờ `palette_check` TẮT, nối Tổ QC;
  bản nới theo ánh sáng + so trong cảnh. Còn: hiệu chỉnh ngưỡng trên ~20 khung #8 (báo nhầm ≤ 10 % mới bật).
- **TODO P1** đo thời gian gọi Claude: `llm_calls.latency_ms` / `request_id`, `HttpResponse.headers`, lỗi HTTP kèm request-id,
  `perf.llm_latency` + mục ⏱ ở Giám sát.
- **S14.29 bỏ hẳn**: gỡ khỏi kế hoạch + TODO; code cất ở `docs/cat_giu/S14_29_ma_thiet_bi/`.
- Tài liệu: `docs/PHAN_TICH_PROMPT_SPIDER_2026-10-06.md` (dòng việc đề xuất S14.50, S14.51 — phiên chính thêm vào kế hoạch).

## KHÔNG mang sang (trùng main / phiên khác)
- S14.25 Đợt 6a (phiên khác đang làm trên `cloud/S14.25`), S14.11 (main đã có bản riêng).

## Khi gộp
- `devsys/areas.json`: file mới đã khai (lesson_judge, palette, workflow, decisions + test); KHÔNG tăng version (tăng ở nhánh tích hợp).
- Kiểm lại số S14.50 / S14.51 chưa bị phiên khác dùng.
- Ghi số đo nhánh: `py -m devsys.workflow add … --mode cloud`.
