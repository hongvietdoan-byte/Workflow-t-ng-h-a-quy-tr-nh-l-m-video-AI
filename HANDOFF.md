# HANDOFF S14.39 — bảng 💵 gọn + nút "↺ Đặt lại 2 thanh về 0"

- Lỗi vỡ định dạng: `$a ... $b` trong st.markdown bị Streamlit đọc thành công thức (không phải backtick). `project_budget.cost_summary` nay trả thêm `md` (đã thoát `$`) và `line` ("Đã chi $x · còn lại ≈ $y · tổng ≈ $z"); `text` giữ nguyên cho cổng duyệt.
- Ô tích 'Đợt thử' không tích được: do `disabled=True` có chủ ý từ S14.6 (shell_parts.money_reset_block). Khối nhiều ô đã bỏ.
- Nút mới: `budget_rounds.reset_two` (qua `start_new`: đóng đợt + mở đợt mới + đặt lại mốc Claude; giữ mức dự tính; audit `budget_round` + `reset_money`; lý do mặc định). UI: `shell_parts.reset_two_button` (khóa `shell_mr_two`; non-owner thấy nút khóa).
- Test: tests/test_money_two_bars.py; cập nhật tests/test_ui_shell.py. Chưa chạy cả bộ.
