# Codex 1 — CX23-M82 pha A

24/10/2026: đã đọc thiết kế M8.1 vòng 2 mục 0–16, mockup 7 màn, đề CX23-M82.
Pha A riêng, chưa nối dashboard/app.py/header.py (pha B), không máy tự gửi API trả phí.

Checkpoint test ĐỎ: tests/test_basic_mode.py — 2 failed + 7 errors, 0,43 giây.
Nguyên nhân dự kiến: chưa có core.simple_budget/dashboard.basic/cờ simple_mode.
Đã chốt với root: helper qd3 tách metadata auto_limit khỏi trần cảnh báo cũ;
EP dùng policy hiện hành stage_desk, xác minh danh tính/active/project ở callback;
không sửa file G1 đang do Codex 3 giữ. Sau G1 gộp phải đối chiếu adapter quyền.

9950d707: helper ngân sách tách metadata, EP/current user, savepoint/audit,
cờ simple_mode OFF; 9 test xanh 0,24 giây. Areas giữ version 92.
WIP tiếp: năm màn/HOLD/pause, model đọc và bộ đếm gen_auth, callback gọi batch/runner,
paid_confirm và approve_preview hiện có; 12 test xanh 4,60 giây gồm AppTest năm màn.

CÒN MỞ trước nghiệm thu:
- Bind fingerprint/báo giá sau rerun, E4 cho batch initial send; không cho gửi thừa ngoài tập duyệt.
- Proposal hiện dùng core.project_budget.propose cũ: chưa thể gọi là đủ dự toán xấu nhất + tự sửa 40% của thiết kế.
- Chưa thực hiện đủ Q-A/Phương án khác, các thao tác sửa thẻ (pha B), dựng bản xem thử sau duyệt clip;
  phụ đề/bản giao chưa nối nghiệp vụ đầy đủ, không tuyên bố target tám thao tác.
- Browser QA 1440/390 trên dữ liệu giả, ảnh; root RÀ KỸ.
Không đụng entrypoint production/DB thật/API. **Pha A chưa XONG**, không bật cờ.
