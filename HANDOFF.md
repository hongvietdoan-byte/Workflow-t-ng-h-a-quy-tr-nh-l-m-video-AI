# HANDOFF S14.38 — dọn màn Kịch bản (chat là cửa duy nhất)
- Bỏ popover "✍ Sửa toàn văn" (paste_) và "📎 Đính kèm" (up_) ở khung chat (cờ idea_to_script BẬT); file thả thẳng vào chat_input (cùng loại file). Cờ TẮT: giữ 2 tab cũ (up_/paste_).
- Đã có kịch bản + dán bản đầy đủ -> thẻ "Thay kịch bản hiện tại bằng bản mới N cảnh?" (Thay = như ↺ Làm lại rồi chờ ▶ Phân tích; Hủy). Dán đoạn/vài cảnh -> hỏi Thêm vào / Thay thế / Hủy.
- Thêm expander "Xem kịch bản (N cảnh)" (st.code có nút sao chép) trong step1_v2.
- Mã: dashboard/steps/step1_box.py (decide, resolve, _cards, script_view); test: tests/test_ui_script.py (test_s14_38_*).
