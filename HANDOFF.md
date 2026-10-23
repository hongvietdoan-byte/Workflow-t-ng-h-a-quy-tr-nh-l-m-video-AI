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

## Vòng sửa sau rà kỹ (23/10)
- paid_button gọi bằng `key=` (tools/ui_v2_acceptance KEY_RE giữ mẫu khóa) → test_ui_v2_acceptance xanh.
- Máy quét: bắt runner làm gốc lời gọi, `go = st.button()` → `if go:`, form_submit_button, autopilot_manager().start, C.llm,
  submit_pending (máy quét cũ 0/5 mẫu, mới 5/5). Nút mới lộ ra (llm_dir, gen_vid, stale_requeue) đều có giá trên nhãn → _PRICE_ONLY.
- Cờ có `"safety": True` → preset Ổn định giữ BẬT (chỉ cờ này; test so mọi cờ khác không đổi).
- Hoàn tác: start lỗi → "Đã duyệt nhưng chưa khởi chạy — bấm ▶ Tiếp tục"; Manager.start False → "đang chạy sẵn"; đóng kết nối CSDL.
- Chat: kiểm access.need_edit trước khi ghi tin; "hủy" bỏ cả chatask và chatsend.
- CHƯA làm (#8): xóa khóa `paid_ask_<key>` khi nút không còn được vẽ — Streamlit không có móc cuối lượt chạy; hiện chỉ xóa khi nút
  bị disabled hoặc bấm Có/Không. Hậu quả: quay lại màn sau khi đổi màn vẫn thấy hộp hỏi (chưa tốn tiền).
- M8.6: E2 (xem trước / HOLD cho các nút "Duyệt hết") và hoàn tác cho pilot_release.

## Đang dở / chưa làm
- Các nút chỉ có giá (EXCEPTIONS `_PRICE_ONLY`) chưa có xác nhận — để M8.6.
- Chưa rà bằng agent riêng theo quy ước 7 (đã chạy related_areas + test các khu step1/step2/step4/dashboard_ui).
- Chưa kiểm tay trên Dashboard thật (không chạy với khóa API).

## Bước kế
- Gộp vào main (phiên chính), chạy cả bộ test + `-m slow` (test_ui_v2_acceptance).
- Quyết định có đánh dấu cờ verified không: preset "Ổn định" hiện TẮT cờ này.
