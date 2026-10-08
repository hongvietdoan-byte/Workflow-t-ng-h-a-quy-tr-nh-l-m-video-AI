# Popup quảng cáo cuối phim — ghép lên cảnh cuối (người dùng chốt 08/10, dự án #24)

**Vì sao:** Director #24 sinh 2 shot "nền tối mờ sương, chờ icon hiện ở hậu kỳ" — mỗi shot tốn tiền gen ảnh + clip mà không thêm nội
dung (người dùng xóa tay). Popup / icon / chữ quảng cáo cuối video được **ghép lên ~3–4 s cuối của shot cuối có hành động**, 0 USD.

## Luồng
1. **Director** (`prompts/17_director_shots.md`): không tạo shot nền trống chờ hậu kỳ; shot cuối giữ hành động kết, khung thoáng, ghi
   `end_card_note`.
2. **Code sau Director** (`core/shot_normalize.fold_post_only`, chạy trong `llm_io.validate_for_project`): shot KHÔNG nhân vật, không thoại,
   chỉ "chờ icon/popup/chữ/hậu kỳ/overlay" → bỏ; chữ của nó thành `end_card_note` của shot cuối, giây của nó cộng vào shot cuối (≤ 15 s),
   `obj["end_card"]` ghi shot đã gộp; `normalized` báo lại cho người duyệt.
3. **Cấu hình** (`llm_io._end_popup_from_plan`, hoặc nút "✨ Lấy từ icon của dự án" ở Bản giao › Tinh chỉnh › 🎯 Popup icon cuối phim):
   `projects.render_settings["end_popup"] = {"items": [{"asset_id", "label"}], "headline", "seconds"}` — icon = tài nguyên `prop` tên
   "ICON …" của dự án (vd #421/#422 của #24), dòng lớn lấy từ câu trong ngoặc kép có "sắp ra mắt" của kịch bản. Thiếu icon → diag warn.
4. **Dựng** (`delivery.render` → `core/end_popup.apply`): PIL vẽ khung PNG trong suốt (icon phóng 0 → 115 % → 100 %, lần lượt cách
   0,6 s; tên dưới icon; dòng lớn vàng; nền shot tối đi nhẹ) → ffmpeg `overlay` từ `tổng − seconds`. Font tự chọn loại có đủ dấu tiếng
   Việt (`subtitles.font_for_text`). Lỗi (thiếu file icon…) → diag error `end_popup`, bản dựng giữ nguyên không popup, ghi trong manifest.
   Đổi popup làm bản dựng "cũ" (`render_hash`).

## Kiểm
`tests/test_end_popup_p24.py`: câu trả lời Director thật #24 → 9 shot (2 shot chờ hậu kỳ đã gộp); dựng thật mp4 360×640 3 s → ffprobe
độ dài/kích thước, trích khung 0,5 s (chưa có popup) và 2,9 s (2 icon + chữ). **Chưa chạy trên dự án #24 thật** (cần ▶ Dựng video cuối).
