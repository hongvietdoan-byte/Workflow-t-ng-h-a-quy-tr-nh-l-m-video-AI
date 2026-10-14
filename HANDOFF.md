# Bàn giao Đ11v4 — chủ thể cuối
- Root đã đọc diff vòng sửa2P2. QA cuối actualcomponent/fakeDB tại1440/1280:0pageerror/overflow, cảnh báo cuối/danh tính rõ, số geometry vẫn hiện; root đã xem1280. Server riêng đã dừng, fixture exact đã xóa. PNG/metrics docs/images/d11/subject_end_qc_*; sẵn sàng pushnhánh, chưa cả bộ/production/adapterA.
- Nhánh codex/d11-viec4-chu-the-cuoi, nền 347ab560; chưa commit/push.
- Đã sửa camera_match_qc + camera_match_ui: ID chưa xác minh luôn VÀNG; thiếu trạng thái cuối explicit; ID đầu/cuối khác không so cỡ/mắt; giữ horizon.
- Caller giữ geometry tham khảo nhưng warning tên chưa xác minh ID và end_actor=None.
- ĐỎ 4 failed/11 passed → XANH 74 passed/2,72 s; 7 test file, --tb=no, dict môi trường giả trước import pytest.
- RA: docs/RA_D11_VIEC4_CHU_THE_CUOI_CODEX_2026-10-14.md.
- Source approved_camera_plan ID/end state chưa tồn tại trên main: adapter CHỜ A, không tự tạo schema.
- Bước kế root review, AppTest nếu cần, cập nhật CODEX_TASKS/TODO, commit; cả bộ Windows trước gộp.
- Không main/live/data/API/env/runner/admin/maintenance; keys/version75 nguyên.

## Vòng sửa sau rà độc lập 14/10
- Gom 2 P2: malformed actor str/list/int vẫn VÀNG và so horizon; warning identity giữ diagnostics khi số khớp.
- UI giữ mọi warning trong một card bullet; code subject_identity_unverified tránh note name-only lặp (chuyển caption), không heuristic theo text.
- ĐỎ 5 failed/16 passed → XANH focused 87 passed/8,00 s (5 file). Chưa commit/push/cả bộ; root đọc diff vòng 2 + rerun component QA PNG 1440/1280.
- QA cuối CHỜ; _qa_subject_qc.py giữ nguyên để root dùng rồi dọn đúng file. Adapter nguồn A vẫn CHỜ, không schema mới.
