# Rà kỹ C-FIX6 phần B (C-M83-TOOL, tools/load_test_ui.py) — 22/10

Nhánh gốc `cloud/v31-m83-tool` @ a7d7770b → `claude/v31-fix6-m83`. Phần A (Bàn đạo diễn 3D) ở nhánh `claude/v31-fix6-desk`, cùng tên tệp.

## Vòng sửa sau rà kỹ
Chạy `tests/test_load_test_ui.py` trên Windows: trước sửa 4 đỏ (1 test C-FIX6 + 3 test C-FIX5); sau sửa 34 qua, 2 bỏ qua (lượt thật Chromium, đánh dấu slow). Code cũ + test mới: 4 đỏ (B1 + 3 test mới B2/B3), 3 test C-FIX5 xanh (lỗi nằm ở test).
- **B1 VỪA** `test_leak_counter_matches_the_relocate_patterns` đỏ trên Windows: `pat` dựng từ `re.escape(str(real))` (dấu `\` đơn) trong khi JSON đã thoát `\`. Test dựng `pat` bằng `_variants` như relocate (helper `_real_pat`), không nới điều kiện.
- **B1 — 3 test C-FIX5 đỏ sẵn trên Windows** (đều là lỗi test, không phải code):
  - `test_copy_db_opens_the_source_with_mode_ro_even_with_special_characters`: thư mục `a b#%?x` không tạo được (`?` cấm trong tên Windows, WinError 123). Windows dùng `a b#%&x`; nơi khác giữ `?`.
  - `test_relocate_moves_every_real_path_into_the_copy` và `test_relocate_maps_the_projects_folder_onto_the_copy_projects`: relocate chỉ đổi TIỀN TỐ (`C:/…/work/data`), phần đuôi giữ `\` gốc → đường lẫn `/` và `\`, vẫn trỏ đúng tệp trên Windows. Test so bằng `os.path.normpath` cả hai phía; test projects thêm kiểm tiền tố đúng thư mục `projects`.
- **B2 THẤP** `run_level`: mọi lỗi trước khi Streamlit chạy (rò đường thật, cổng thật / bận) → xóa `work` (bản sao CSDL thật + copytree dự án) rồi raise; `--keep` thì giữ. Test `test_run_level_removes_the_work_dir_when_it_stops_on_leaks` (đỏ→xanh).
- **B3 THẤP** bộ đếm rò:
  - `_leaks_in` đếm MỌI lần khớp đường thật sau khi dời, không cắt ở khoảng trắng / dấu phẩy, không hỏi exists. Khớp nằm ở đầu đường của chính bản sao (`own` = `_variants(new_home)`) không tính, cho trường hợp bản sao nằm trong một thư mục thật như Temp.
  - `_variants` thêm dạng JSON ensure_ascii (`\uXXXX`), nên relocate cũng DỜI được đường tên tiếng Việt trong JSON (trước đây bỏ sót cả dời lẫn đếm).
  - Test `test_leak_counter_counts_paths_with_spaces_and_vietnamese_names_in_ascii_json` và `test_relocate_moves_ascii_json_vietnamese_paths_and_ignores_the_copy_inside_a_real_home` (đỏ→xanh).
  - Điều kiện cũ "đường không tồn tại → 0" trong test B1 đổi thành 1: chặt hơn, đúng hướng B3.
- Bỏ `_PATH_END` vì không còn dùng.

## Việc mở
- Đường tương đối kiểu `..\data\…` hoặc đường UNC chưa có mẫu riêng. Chưa gặp trong CSDL thật.
