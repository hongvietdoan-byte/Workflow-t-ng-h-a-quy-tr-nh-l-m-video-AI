# HANDOFF — S14.28 (nhánh `s14-28-refs-outfit`, 05/10)

Thiết kế người dùng duyệt 05/10 (dòng `S14.28 ·` trong `docs/KE_HOACH_SUA_SAU_DU_AN_8.md`). Chưa push, chưa sửa TODO.md.

## Đã làm
- **Thứ tự màn Kịch bản** — v2 (`step1_v2.py`): hero → ① Kịch bản (dòng chế độ + ô kịch bản + phân tích cảnh) → 🖼 Tham chiếu
  (`card-script-refs-`) → ② → ③. Giao diện cũ (`step1.py`): 1a Kịch bản (dòng chế độ ở đầu fold) → 🖼 Tham chiếu (fold `refs_`, gập) → 1b …
- **Trước kịch bản**: khối tham chiếu chỉ còn 1 dòng `HINT` (không form). **Sau phân tích**: expander/fold gập; dòng "Đã nhận ra: …" (Bible +
  `characters`/`location` của cảnh, có ảnh hay chưa) + ô `ref_for_{pid}` gắn theo tên đã nhận ra. Kho tự ghép theo tên giữ nguyên.
- **3 thẻ Sắp có** → `modes_line(pid)`: 1 dòng, 3 nút tắt (giữ khóa `coming_…`). Ghi chú S11 ở docstring `step1_refs.py`: chế độ video ref /
  cover nhảy thì ô gắn VIDEO ref đứng TRƯỚC kịch bản.
- **Loại `outfit` "Trang phục"** (`core/assets.py` KINDS + bí danh thư mục `trang phuc`, `outfit(s)`, `costume(s)`, `skin(s)`).
  `add_outfit_images()` (kiểm nhân vật có trong Bible TRƯỚC khi lưu → AssetError; Kho chung = chờ duyệt G2 → KHÔNG set, `note` nói rõ),
  `outfit_label()`. Form: chọn "Trang phục" → ô `ref_outfit_for_{pid}` "cho nhân vật …".
- **Chặn gửi nhầm**: match_character / scene_references / auto_attach `main` / guess_role / health / asset_vision / prompts / llm_runner đều
  lọc theo loại riêng → outfit không thành ảnh nhân vật/đồ vật/địa điểm (có test). `context_text` ghi "trang phục … không phải nhân vật".
  Kho tài nguyên (`admin.py`) tự có loại mới qua `KINDS` (lọc, tạo, nguồn thư mục).
- **Danh sách nhân vật**: bảng Character Bible thêm cột "Trang phục"; popover mỗi nhân vật đổi nhãn thành "👗 Trang phục: mặc định FF /
  <tên bộ> · chọn bộ khác" (`outfit_line`), chọn được cả Trang phục của Kho (`outfit_pool`). Nút tạo bộ 2 ảnh giữ nguyên.

## Test
- Đỏ→xanh: `tests/test_assets.py::OutfitKindTests` (5), `tests/test_ui_script.py` `test_s14_28_*` (4 v2 + 1 giao diện cũ).
- Sửa theo thiết kế: `test_new_project_shows_empty_state_hero_and_the_input_panel`, `test_screens_dashboard::test_script_screen_has_the_inputs_and_references_panel`.
- `test_ui_v2_acceptance` xanh (không khóa nào mất; không thêm RENAMED).

## Mở / rủi ro
- Chưa chụp ảnh giao diện thật (dòng 3 nút "sắp có" ở màn hẹp, vị trí khối tham chiếu).
- Popover trang phục nằm trong expander "🖼 Ảnh tham chiếu của từng nhân vật" (có thể đang gập); cột bảng Bible luôn hiện.
- Trang phục tải vào Kho chung phải duyệt rồi chọn tay ở 👗 (theo G2) — người dùng có thể muốn dùng ngay cho dự án đang làm.
- Bí danh thư mục `skin` giờ là loại Trang phục khi đồng bộ thư mục (trước: thư mục tên "skin" thành tên tài nguyên).
