# Rà Đ20 việc 6 — trang Sổ lỗi

- Nhánh `codex/d20-viec6-so-loi`, nền `8a2296aa`; chỉ code/giao diện đọc file trong git, 0 USD.
- Thêm trang 📕 Sổ lỗi: bộ lọc trạng thái/workstream/dự án; số hiển thị/tổng, coverage khâu/workstream/dự án trên tập đã lọc. Cảnh báo `problems()` luôn tính toàn sổ, kể cả mục đã bị lọc khỏi bảng.
- Sửa `plan_map.open_errors_by_stage`: đọc nguồn chuẩn `errors.load()` (`items`, schema v1), kiểm hợp đồng trước đếm. OPEN/IN_PROGRESS/FIXED_UNVERIFIED/REOPENED còn mở; VERIFIED/WONT_FIX không đếm; khâu null vào NEN. Thiếu file giữ None; JSON/schema/hợp đồng sai báo rõ, không giả 0 lỗi.
- Khâu có lỗi mở hiện viền đỏ; màu cảnh báo kiểm trước tiền vẫn giữ khi chưa có lỗi mở. Nhãn giải thích đã cập nhật.
- Không có HTML do dữ liệu sổ sinh: dataframe và cảnh báo Streamlit hiển thị văn bản. Không thêm nút ghi, cờ, API, quyền hay đường gửi.

## Bằng chứng

- Đỏ trước: 9/9 regression mới đỏ (nguồn items bị đếm 0, schema không bị từ chối, chưa có trang).
- Xanh đầu: 30 test của `test_errors_page`, `test_devsys_plan_map`, `test_tickets_page`.
- Rà NHẸ root bắt alias `[7]` gây TypeError: đã kiểm alias là chuỗi + regression schema đỏ. Bổ sung AppTest thật lọc dự án, cảnh báo VERIFIED thiếu real_run_evidence toàn sổ; XML kiểm viền đỏ khi khâu có lỗi mở.
- Cuối: 52 test xanh trong 10,26s, gồm bốn file trên và `tests/test_error_registry.py`. Một lượt trước 51 xanh/1 lỗi decode CLI CP1252; chạy lại Python `-X utf8` khắc phục cấu hình interpreter, không sửa/nới test.
- Mỗi lần pytest: trước imports/pytest dùng `patch.object(os, 'environ', dict_giả)`; HOME/USERPROFILE/TEMP/TMP giả trong fixture, không đọc/in env thật. Không API hoặc dữ liệu sản xuất; AppTest chỉ module trang, không chạy toàn app.
- `tools/related_areas.py` + tìm callers: app → render, plan_map.build → open_errors_by_stage; không có thay đổi vòng đời job/tiền/quyền. Đã khai mã/test trong khu vực devsys; version giữ 87.
- Tự rà mục 2b.5: không nới test, đường file chuẩn tuyệt đối theo module, không chạm tự động/hàng loạt/cờ gửi, không so chữ bỏ dấu, không tiêu đề thành nội dung, không mạng hay tốn tiền.
- `git diff --check` không lỗi khoảng trắng. Chưa cả bộ Windows/slow, chưa mở UI live/khởi động lại dịch vụ: để phiên tích hợp.

## Việc mở

- Phiên chính đọc diff/test xanh trước gộp; chạy cả bộ Windows gồm slow theo related_areas, tăng version một lần ở tích hợp rồi cập nhật trạng thái/push/khởi động lại theo quy trình.
- `.test-home/` là fixture untracked, không commit. Auto-review chặn lệnh dọn exact path đã kiểm (blocked by policy); giữ nguyên, không thử đường khác.
