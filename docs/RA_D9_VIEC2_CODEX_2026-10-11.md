# Rà kỹ Đợt 9 việc 2 — 11/10/2026

Phạm vi: diff sau `d3cafd5`, trang Phiếu, adapter `from_fix`, service quyết định; không sửa dữ liệu thật, không API, không chạy cả bộ. Kho Đ9v1 đã rà trước đó.

## Kết quả và vòng sửa duy nhất

1. Gộp fingerprint bỏ cách gỡ tạm mới: đã sửa `core/tickets.py` lưu cách hiện hành và `workaround.history` trong cùng SAVEPOINT/CAS/event/audit. Không đổi trạng thái hoặc hạn gốc. Test `test_from_fix_updates_workaround_atomically` kiểm hai cách gỡ, refs gộp, rollback transaction caller và audit thất bại không để lại cập nhật/event.
2. Phiếu closed còn impact chặn lịch sử đứng đầu hàng đợi: đã sửa `devsys/tickets_page.py` xếp closed cuối. Test `test_closed_blocked_queue_is_history`.
3. Duyệt rejected chọn triaged sai lifecycle: đã sửa adapter chọn closed; không bỏ guard transition/CAS. Test `test_rejected_approve_closes_with_cas` kiểm đóng, người đóng, SLA và revision cũ bị chặn.

Chạy `$env:PYTHONUTF8='1'; py -m pytest -q -p no:cacheprovider tests/test_tickets_page.py tests/test_tickets.py`: ĐỎ **3 failed, 30 passed / 2,60 s** → XANH **33 passed / 2,53 s**. Không nới assertion hoặc chạy test rộng. Root còn đọc diff sửa và kiểm cả bộ trước gộp.

Root rà diff trong cùng vòng bổ sung hai điểm: navigation khi cờ OFF phải giữ danh sách trang cũ và không redirect query; đường dẫn tương đối phải neo repo root thay vì CWD. Đã sửa cả hai. Test AppTest lấy đúng đoạn navigation từ AST app.py, kiểm bốn tổ hợp cờ; test path dùng connect giả/CWD TMP, không mở CSDL thật, kiểm default/relative/absolute. ĐỎ hợp lệ **4 failed, 1 passed / 2,32 s** (lượt đầu có lỗi tên đối số mock đã chỉnh) → nhóm hai file **38 passed / 8,52 s**. Không chạy app.py đầy đủ hoặc mở rộng test.

## Giao diện và giới hạn nghiệm thu

8502 chưa có đăng nhập admin phía server: UI chỉ đọc đúng yêu cầu; mọi nút quyết định/lý do/bulk khóa. Không actor/role từ session_state, không ACL tạm. Hai cờ mặc định OFF; đọc SQLite theo PIPELINE_DB qua mode=ro/query_only, không migration. Service không đổi trần hoặc chi tiền.

Chứng cứ UI do phiên làm tạo từ CSDL tạm, server riêng đã dừng: [ảnh 1440×900](images/d9/readonly1440x900.png), [số đo](images/d9/readonly1440x900.measurement.json). Phiên rà đã đọc ảnh và JSON, không chạy lại GUI: mở chi tiết 1 bấm, 0 cuộn; liên kết mở đúng phiếu 0 bấm; console_errors rỗng. Chứng cứ phản ánh bản trước vòng sửa ba lỗi, bố cục UI không đổi.

**Chưa nghiệm thu quyết định ≤2 bấm/0 cuộn**: nút disabled không chứng minh thao tác quyết định; trường decision_clicks/decision_scrolls null. Cần server auth thật để nghiệm thu phần ghi, tự sang phiếu kế và bulk UI. Không coi phần hoãn này đã hoàn tất.

Đối chiếu thêm: không HTML unsafe mới, user_projection scope dự án giữ nguyên, widget keys cũ không đổi, occurrence đếm open/merge, pet link query giữ phiếu ngoài bộ lọc. Không chỉnh Dashboard/#24/env/data/TODO/PLAN; không commit/push trong phiên rà/sửa.
