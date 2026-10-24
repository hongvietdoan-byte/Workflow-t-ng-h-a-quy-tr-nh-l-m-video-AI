# Rà soát CX23-DON-RAC-FIX

Ngày 23/10/2026 — nhánh `codex/v31-don-rac-tool`, tiếp tục từ `7297136b` theo đề bài trong `docs/CODEX_TASKS.md`.

## Phạm vi và kết quả

Đã xử lý đủ bảy điểm trong đề:

1. Trạng thái worktree đọc cả file bị Git ignore; chỉ bỏ qua `.pytest_cache` và file `.pyc` trong `__pycache__`. File ignore khác, kể cả payload không phải `.pyc` dưới `__pycache__`, giữ worktree khỏi bị gỡ.
2. Cho phép sao lưu SQLite bằng `Connection.backup()` để an toàn với WAL, nhưng chỉ đúng `repo_root/data/manifest.sqlite`. Vẫn chặn di chuyển manifest và sao lưu `dashboard.env`.
3. Chỉ xét dừng tiến trình Streamlit/pytest đã chạy hơn 15 phút; pytest còn phải có cwd trong repo. Cổng 8501/8502, kết nối `ESTABLISHED` và tiến trình mới được giữ.
4. Tuổi worktree lấy mtime mới nhất của Git admin `index`, `HEAD`, `logs/HEAD`.
5. Xoay vòng bản sao theo dấu thời gian trong tên; tên không có ngày hợp lệ thì dùng `st_ctime`.
6. Tìm gốc repository từ cha của `git rev-parse --git-common-dir`, nên truy vấn từ worktree vẫn nhận gốc chung.
7. Lệnh Git có timeout 60 giây; bước rà worktree fetch `origin` với `--prune` một lần và bỏ qua dọn nếu fetch lỗi.

## Kiểm thử và rà soát

- Vòng ĐỎ mới cho hai hồi quy sau rà độc lập: `2 failed`; các lỗi tái hiện đúng việc cho phép backup manifest cùng tên ở sai thư mục và bỏ qua payload ignore dưới `__pycache__`.
- Sau sửa: bốn kiểm thử tập trung về manifest, CLI `--goc`, SQLite online backup và cache đều xanh.
- Bộ theo đề `PYTHONUTF8=1 py -m pytest -q -p no:cacheprovider --tb=no tests/test_don_rac.py tests/test_hop_thu.py`: **47 passed trong 47,01 giây**.
- `git diff --check`: sạch. Dữ liệu SQLite và payload kiểm thử đều được tạo trong `tmp_path`; không đọc hoặc sửa dữ liệu thật.
- Rà độc lập phát hiện hai vấn đề an toàn đã được sửa trước commit: ngoại lệ manifest giới hạn theo đường dẫn chuẩn; ignored payload trong `__pycache__` không bị phân loại nhầm là cache Python. Rà lại sau sửa xác nhận hai điểm này đã được xử lý. Kiểm thử Windows xác nhận Git liệt kê file payload cụ thể khi dùng `--untracked-files=all --ignored`.
- `related_areas.py` xác định vùng `devsys`; tại bước gộp cần chạy các kiểm thử chậm `tests/test_devsys.py`, `tests/test_devsys_v2.py` và `tests/test_hop_thu.py` hoặc cả bộ.

## Lưu ý còn mở

`tools/hop_thu.py` xác định gốc bằng `git rev-parse --show-toplevel`. Quy trình hiện hành gọi `hop_thu.py gop` từ thư mục repo chính; nếu sau này cần gọi từ một linked worktree để dọn worktree anh em, cần sửa riêng cách xác định gốc của caller và thêm kiểm thử caller.
