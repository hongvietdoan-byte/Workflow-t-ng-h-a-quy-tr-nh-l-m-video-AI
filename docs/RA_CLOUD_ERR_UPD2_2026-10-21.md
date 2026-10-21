# C-ERR-UPD2 — sổ lỗi theo 9 nhánh gộp 21/10 (cloud-D, 21/10)

Nhánh `cloud/v31-err-upd2` từ `origin/main`. Chỉ `devsys/errors.json`. Commit lấy từ `git log` (từng commit "Gộp …" của nhánh; `ffa85d2` chỉ
là commit chốt tích hợp), test lấy từ tệp test thật (mọi node `file::test` đã chạy xanh: 54 qua). Không mục nào VERIFIED.

| Mã | Trạng thái | Lý do |
|---|---|---|
| P31-G30, P31-G58 | FIXED_UNVERIFIED | M1.5 guard Kho chủ thể (`88812a4`, cờ `subject_capacity_guard` TẮT): Kho đầy/không rõ → giữ hàng đợi, không gửi ảnh thô / không lùi Kling. Allocator đa tiến trình còn mở |
| P31-G32 | FIXED_UNVERIFIED | guard Kho + C-G36B (`447fde9b`, cờ `refusal_skip_same_picture` TẮT) |
| P31-G3, P33-A10 | IN_PROGRESS | M3.2 (`6d88be6`) chỉ whitebox: VÀNG eye > 5°, mức slightly_high; plate_camera / vật che chưa |
| P31-G2, P31-G49 | OPEN (+ lý do) | mốc tỉ lệ người / bậc dưới chân chưa làm |
| P31-G1 | IN_PROGRESS | M3.4 shadow (`7c3a979`) chỉ PHÁT HIỆN đổi nơi trong nhóm (REVIEW) |
| P31-G46, P31-G43 | IN_PROGRESS | M3.1 map (`447fde9b`) + M3.3 câu đề xuất (`e53363f`), cờ TẮT, chưa thay câu trong prompt |
| P31-G41/44/45/47/50 | OPEN (+ lý do) | M3.3 có nhưng ca chưa có test riêng (G41: hướng chạy chưa ghép) |
| P33-A5 | FIXED_UNVERIFIED | DP1 `b503691` + C-FIX-THAP-4 `a50b298` (regex hẹp), cờ TẮT — bỏ sót ở C-ERR-UPD trước |

Không đổi: DP7 (M4.6 benchmark — hạ tầng đo, không đóng mã lỗi), C-FIX-THAP-3/5 (không gắn mã), P31-G51/G52 (M3.4 không nêu, M4.2/M4.3 giữ).
**G59** (luồng nền "chưa cấu hình Kho chủ thể", CX20-5 đã sửa) KHÔNG có dòng định nghĩa trong tài liệu nguồn (chỉ nhắc ở CODEX_TASKS) → không
thêm mục (sổ chỉ nhận mã có nguồn) — phiên chính quyết thêm nguồn + mục nếu cần.
Kiểm: `python -m devsys.errors check` Hợp lệ (86 mục — FIXED_UNVERIFIED 16, IN_PROGRESS 9, OPEN 59, WONT_FIX 2); tests/test_error_registry.py xanh.
