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

Checkpoint tiếp: bind fingerprint/báo giá sau rerun và callback; OFF chặn callback;
E4 đọc grants-cycle, không reset; 14/14 test xanh 4,34 giây (không rerun sau đó).

CÒN MỞ trước nghiệm thu:
- Core batch/runner hiện gửi cả lô dự án, chưa có API targetedsend đúng tập đã duyệt.
  Hiện giữ chờ toàn lô khi có cảnh hết lượt; chưa đạt HOLD từng mục không chặn mục khác.
  KHÔNG tự mở API core ngoài vùng phân công; root hỏi phiên chính/owner.
- Proposal hiện dùng core.project_budget.propose cũ: chưa thể gọi là đủ dự toán xấu nhất + tự sửa 40% của thiết kế.
- Chưa thực hiện đủ Q-A/Phương án khác, các thao tác sửa thẻ (pha B), dựng bản xem thử sau duyệt clip;
  phụ đề/bản giao chưa nối nghiệp vụ đầy đủ, không tuyên bố target tám thao tác.
- Browser QA 1440/390 chưa làm được, chưa có ảnh. IAB/browser inventory rỗng;
  Chrome native bị hệ thống dừng vì không xác định URL đủ chắc để áp policy.
  Không retry/bypass. Đã kiểm commandline fake preview PID45972/port8529 rồi dừng
  đúng tiến trình sở hữu, không còn listener khác trên cổng; không còn server QA.
- Root RÀ KỸ chưa thực hiện cho M82; G1 quyền cần đối chiếu khi lên main.
Không đụng entrypoint production/DB thật/API. **Pha A chưa XONG**, không bật cờ.

Thư mới 12:31 ưu tiên G1-PLAN-GATES trước M47B/M82. Root giao agent khác thực hiện;
agent M82 dừng tại checkpoint này, không nhận G1 hay sửa task khác.

Thư 12:54 (`20261024-125409`): Claude chốt giai đoạn 1 **HOLD CẢ LÔ**;
targetedsend tách CX24-M82B sau G1-PLAN-GATES; runner.submit_pending đã có only=job_ids,
queue_images mới thiếu chọn scene. UIQA ảnh phiên chính tự kiểm sau gộp, không retry.
Checkpoint guard+AppTest/fakeprovider sẵn root rà, không rerun 14 test vì code không đổi.
Những mục worstcase+40/Q-A/EP/E4 không được mặc nhiên bỏ; RA đã tách rõ.
Root phải xem đường submit_pending toàn dự án có thể gửi queued ngoài quote và ngân sách
cũ chưa đủ scope qd3 trước khi cho mở gửi thật. Agent không tự báo XONG hộp thư.

Gom sửa guard theo root: proposal cũ qd3_complete=False → UI/helper HOLD không duyệt.
selected_send_ready() cố định False → quote/send HOLD cả lô trước provider/queue,
không mở bằng env/simple_mode. Nhánh submit tương lai chỉ tồn tại sau cổng này;
CX24-M82B phải sửa selected jobIDs trước khi mở. Không mở API core ở checkpoint.
Hai test regression ĐỎ2/2,61s → file test Basic 16 XANH/6,20s. Không broad/GUI.
Giai đoạn1 guardcheckpoint sẵn root RÀ KỸ; Q-A/qd3/targeted-send còn HOLD/WIP,
không khẳng định toàn phaA/M8.2 hoặc mục tiêu ≤8 hành động đã hoàn tất.

RÀ KỸ độc lập checkpoint: 0 P1, 1 P2 nhập script trước ý tưởng → thiếu inputs.
Đã sửa bằng public start chỉ khi missing inputs, giữ _actor trước ghi và input cũ.
Regression 1 đỏ/2 qua0,21s; lượt xanh đầu19qua/1lỗi fixture mock thiếu heading3,55s;
sửa đúng hợp đồng fixture, file Basic20xanh2,65s. Test đổi quote chỉ chứng minh
HOLD giai đoạn1; M82B phải kiểm stale path khi mở port. Root đọc fixdiff lần hai.
