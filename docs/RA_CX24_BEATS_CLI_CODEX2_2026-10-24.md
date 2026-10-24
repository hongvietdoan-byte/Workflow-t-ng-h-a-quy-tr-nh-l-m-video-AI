# Rà soát CX24-BEATS-CLI — Codex 2

- Nhánh: `codex/v31-beats-cli`; worktree: `.codex-wt/v31-beats-cli`.
- Đề bài: `tools/stage_auto.py --beats` dùng cùng lượt ghép xem trước như nút N5; bổ sung `--beats-crew --project N --scene S` và in phép đo được chọn cho từng shot.
- Thay đổi: N5 và CLI gọi chung `core.stage_auto.render_beats_sheet()` và `crew_preview()`. `--beats-crew` lưu đúng đường dẫn N5; `--beats <thư_mục>` giữ đường dẫn tùy chọn và tự dùng preview đang chạy. Không có preview thì dùng lượt đã lưu hiện hành như N5.
- An toàn: chế độ ghép ảnh mở SQLite bằng `mode=ro` + `query_only`, không gọi `core.db.connect`, không migration và không bật cờ stage_auto. Đường dẫn rỗng hoặc kết hợp hai cờ ảnh bị từ chối trước khi vào luồng chạy tác vụ thông thường. Lỗi dữ liệu crew sai kiểu được báo theo cảnh, không làm dừng vòng CLI. Test chỉ dùng SQLite/đường dẫn giả và Blender giả; không gọi API, không truy cập dữ liệu thật, không phát sinh chi phí.
- Rà độc lập: vòng đầu phát hiện P2 ở `--beats ""` và hai P3; đã sửa cả ba. Vòng rà lại không còn P1/P2. Tác dụng phụ dự kiến là ảnh/preview và khóa filesystem; đường N5 hiện hữu vẫn đi qua `_start`.
- Kiểm thử đỏ → xanh: trước sửa, regression cho `--beats` dùng kết nối có migration và `--beats-crew` chưa được hỗ trợ đều đỏ. Sau sửa: `tests/test_v31_beats_cli.py`, `tests/test_v31_m48_sheet_pick.py` và hai kiểm tra ánh xạ `devsys/areas.json`: **13 passed (2.06s)**. `git diff --check` sạch.
- Đăng ký file: thêm `tests/test_v31_beats_cli.py` vào vùng `plates3d`; giữ nguyên `areas.json` version.
- Chưa gộp vào `main`; cần chạy đủ bộ test Windows tại bước tích hợp theo quy ước dự án.
