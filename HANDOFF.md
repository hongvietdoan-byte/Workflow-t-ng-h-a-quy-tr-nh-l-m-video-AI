# Codex 1 — CX24-M82B core targeted images

Nền c6937f89; nhánh codex/v31-m82b-targeted. Chỉ core/batch.py + test; không UI/runner/autopilot/bg_poll.
Đã đọc spec CODEX_TASKS.md CX24-M82B và callers queue_images/image_gates.
Test fixture mới: **10 ĐỎ / 6,50 giây** trước API scene_ids/job_ids; thêm test runner.only hiện có.

Tiếp: optional scene_ids sau pilot, trước gates; None giữ nguyên hành vi; trả job_ids fresh/redo.
Kiểm 6 acceptance + tập rỗng/generator/kiểu sai; targeted tối đa ba lượt, không fullsuite.
Giá selected phải dùng API hiện có, không tính tay. cost.estimate_images chưa nhận selection;
đã báo root việc này để chốt phạm vi, không tự mở API core/cost.py ngoài phân công.
Phải RÀ KỸ và root push từng commit. Không API trả phí/dữ liệu thật/secret.
