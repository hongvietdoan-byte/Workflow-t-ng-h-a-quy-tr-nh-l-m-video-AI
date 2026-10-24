# Codex 1 — CX23-M82 pha A

24/10/2026: đã đọc thiết kế M8.1 vòng 2 mục 0–16, mockup 7 màn, đề CX23-M82.
Pha A riêng, chưa nối dashboard/app.py/header.py (pha B), không máy tự gửi API trả phí.

Checkpoint test ĐỎ: tests/test_basic_mode.py — 2 failed + 7 errors, 0,43 giây.
Nguyên nhân dự kiến: chưa có core.simple_budget/dashboard.basic/cờ simple_mode.
Đã chốt với root: helper qd3 tách metadata auto_limit khỏi trần cảnh báo cũ;
EP dùng policy hiện hành stage_desk, xác minh danh tính/active/project ở callback;
không sửa file G1 đang do Codex 3 giữ. Sau G1 gộp phải đối chiếu adapter quyền.

Tiếp: helper ngân sách + khung 5 màn/HOLD/pause; targeted đỏ→xanh; đăng ký areas;
browser QA 1440/390 trên dữ liệu giả; root RÀ KỸ trước báo xong.
Chưa code production/DB thật/API, chưa tuyên bố đủ pha A.
