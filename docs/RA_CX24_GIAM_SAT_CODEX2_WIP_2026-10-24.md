# CX24-GIAM-SAT — checkpoint Codex 2 (24/10/2026)

Trạng thái: **ĐANG LÀM**, đây là checkpoint an toàn, chưa phải nghiệm thu hoàn tất.

- Nhánh/worktree: `codex/v31-giam-sat` / `.codex-wt/v31-giam-sat`.
- Đã có rubric 3 trục; bundle tái dùng `devsys.scorer`; tổng điểm tính bằng code; thu thập bằng chứng read-only; worker có hash đầu vào để chặn chạy trên gói đã đổi; khóa, lịch sử và báo cáo; writer M9 có sao lưu, idempotency và kiểm tra đường dẫn kế hoạch.
- Đã nối trang `Kế hoạch đang chạy`, `Sơ đồ tiến độ`, `Sơ đồ dây chuyền`: điểm 3 trục/xu hướng; bảng CHẶN/LỚN; viền đỏ/tím tô việc, đợt và khâu bị ảnh hưởng; nút chỉ soạn lệnh `hop_thu.py giao` để phiên chính duyệt/chạy, không tự giao.
- Kiểm tra: `PYTHONUTF8=1 py -m pytest -q -p no:cacheprovider --tb=no tests/test_devsys_plan_writer.py tests/test_devsys_plan_monitor.py tests/test_devsys_plan_monitor_app.py` — **19 passed** (8,58 s); AppTest tải cả 3 trang với dữ liệu/biến môi trường giả. `py -m py_compile devsys/plan_monitor.py devsys/plan_monitor_worker.py devsys/plan_writer.py devsys/app.py` và `git diff --check` đều đạt.
- Chưa xong: đăng ký area trong `devsys/areas.json` đang do M47B giữ vùng; cần đợi giải phóng hoặc phiên chính chỉ định cách tích hợp. Còn rà cuối caller, luồng publish kế hoạch trên main, cập nhật báo cáo nghiệm thu và gửi event `xong`.
- Đã đồng bộ nhánh worktree này với `origin/main`; `CX24-DEVSYS-FIX` đã gộp main theo hộp thư (0aeef4c6). Không pull/checkout hay thay đổi thư mục live.
- Phạm vi kiểm tra chỉ dùng code và fixture tạm; không mở dự án/dữ liệu thật, không gọi API hay thao tác Computer Use.

Bước kế: kiểm xung đột caller/publish, chờ M47B giải phóng `devsys/areas.json`, đăng ký code/tests/assets, chạy lại nhóm test, hoàn tất RA rồi commit/push và báo `xong CX24-GIAM-SAT`.
