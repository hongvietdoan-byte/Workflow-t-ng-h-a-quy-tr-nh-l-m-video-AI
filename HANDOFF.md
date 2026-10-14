# Bàn giao — nhánh claude/tap2-d-nhat-ky-thao-tac (14/10)

**Mục đích**: nhật ký THAO TÁC trên Dashboard (Claude điều khiển Dashboard bằng trình duyệt, chung tài khoản người dùng) để đo khâu khó dùng và tách nguồn người / Claude.

- Bảng `ui_actions` (core/db.py SCHEMA, `CREATE TABLE IF NOT EXISTS` → CSDL cũ tự có khi connect).
- `core/ui_log.py`: `record()` một INSERT, không bao giờ ném lỗi (lỗi → diag một lần/tiến trình), detail che khóa + ≤ 300 ký tự; `summary()` đếm theo action/result/source, ms TB, đổi ý (duyệt↔loại cùng job ≤ 5 phút; gen → hủy cùng dự án ≤ 10 phút), bấm đôi (cùng nút ≤ 10 s, lần 1 'noop').
- Nguồn: mở Dashboard với `?op=claude` → `st.session_state["op_source"]` dính cả phiên (dashboard/common.py `capture_op_source`, gọi trong app.py trước đăng nhập). Không đổi quyền.
- `C.log_ui(...)` nối vào: gen ảnh, ▶ Gen video, duyệt storyboard → gen video (2 màn), duyệt/loại/vẽ lại/bỏ duyệt ảnh (step2 + thẻ v2), gen lại ảnh/video, duyệt/loại clip, hủy job (ảnh + video), lưu motion prompt / lưu cảnh, chạy Đạo diễn + chia shot lại, bật/tắt cờ 🧪, ▶ Dựng video cuối, Xuất bản (Bước 5). Ghi chú chỉ ghi có/không, không ghi nội dung.
- `job_events.actor` KHÔNG đổi; nối qua `ui_actions.job_id`.
- Đọc: `py tools/ui_actions_report.py [--project N] [--source claude] [--hours 24] [--db ...]` (mode=ro).

**Chưa làm**: chưa đánh dấu 'noop' ở nút (gen không xếp được job nào…) — bộ bắt bấm đôi đã sẵn, cần ai đó trả 'noop' ở chỗ biết chắc. Chưa thử trên Dashboard thật.
**Test**: tests/test_ui_log.py (6 test) + 16 file UI/scan liên quan: 183 passed.
