# HANDOFF — V3.1 M8.0 "An toàn tiền" (nhánh worktree-agent-af45e0b6236f3887c)

## Đã xong
- `dashboard/paid_confirm.py` (mới): `paid_button` (giá trên nút + xác nhận một lần), hàng chờ hoàn tác 30 s trong session_state
  (`schedule/pending/waiting/cancel/take_due`), `schedule_resume`, thanh `undo_bar` (vẽ ở mọi màn từ app.py).
- Cờ `safe_paid_buttons` (core/features.py, default_on, costs=False, chưa verified).
- 6 chỗ M8.0: chat (Enter chỉ giữ chữ → nút "📨 Gửi · ≈ X USD"), "🎬 Dựng storyboard", "🔍 Claude rà storyboard", "↻ Rà lại",
  "↻ Thử kiểm tra lại" ảnh (step2) và clip (step4) → giá từ hàm có sẵn (cost.llm_button_tag / llm_estimate+llm_tag / CR.rerun_tag).
- "✔ Duyệt storyboard → gửi video" (storyboard_cards + step2) và "✔ Đã duyệt — tiếp tục" (step1_run): xác nhận kèm giá → hẹn 30 s,
  "↩ Hoàn tác" / "▶ Gửi ngay"; tới hạn so lại cổng chờ + fingerprint storyboard, đổi thì không gửi.
- tests/test_safe_paid_buttons.py: quét AST mọi nút tốn tiền; đỏ với code cũ (4 hỏng), xanh sau sửa. devsys/areas.json khu "budget".

## Đang dở / chưa làm
- Các nút chỉ có giá (EXCEPTIONS `_PRICE_ONLY`) chưa có xác nhận — để M8.6.
- Chưa rà bằng agent riêng theo quy ước 7 (đã chạy related_areas + test các khu step1/step2/step4/dashboard_ui).
- Chưa kiểm tay trên Dashboard thật (không chạy với khóa API).

## Bước kế
- Gộp vào main (phiên chính), chạy cả bộ test + `-m slow` (test_ui_v2_acceptance).
- Quyết định có đánh dấu cờ verified không: preset "Ổn định" hiện TẮT cờ này.
