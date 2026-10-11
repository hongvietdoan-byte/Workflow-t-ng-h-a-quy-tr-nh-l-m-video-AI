# Đ10 việc 4 — tự kiểm trước bàn giao (12/10/2026)

- Nhánh `codex/d10-viec4-phieu`, nền `0e86347`; chưa commit/push, chờ phiên chính RÀ KỸ.
- Sửa 6 mục TRUNG và THẤP của `docs/CODEX_TASKS.md`: merge phiếu xong → reopened bằng CAS/event/audit; projection chỉ phiếu đang chặn.
- `blocked`/`waiting_info` lưu trạng thái trước trong technical, quay lại bằng Owner + revision CAS; phiếu cũ thiếu dấu tiếp tục về triaged.
- Bỏ cảnh báo hạn cho closed/resolved/verified/rejected. Cấm đường dẫn tuyệt đối POSIX kể cả `/tmp`, Windows và UNC trong payload.
- Link `?ticket=` được tiêu thụ một lần; sidebar chọn Phiếu thật, sau đó đổi trang bình thường. RENAMED khóa radio `devsys_page` chỉ khi hai cờ bật; cờ TẮT giữ widget không khóa như cũ.
- UI viết ảnh hưởng/nguyên nhân/bằng chứng thành câu; tiền lấy chung `money_usd`; hạn giờ VN + còn/quá số giờ, phiếu xong ghi đã xong.
- Pet chỉ đếm waiting_admin, số đỏ/vàng trong nhóm này; toast waiting_admin/waiting_merge (admin phải hành động), giữ dedupe.
- Broker truyền data_dir tuyệt đối (mặc định thư mục CSDL đã cấu hình); ThreadingHTTPServer + timeout socket 5 giây, vẫn localhost/GET/Owner/readonly.
- Broker riêng đọc chẩn đoán mới hoặc motion chưa duyệt; không import runner. Lý do chỉ tồn tại trong RAM runner không khôi phục được: báo thiếu bằng chứng, không bịa lý do.
- Chi hôm nay từ 00:00 VN, quy về UTC. `budget._spent` so julianday để cùng tính SQLite UTC và ISO UTC; range at trước giữ index.
- ĐỎ lượt 1: nhóm tickets/page/lao_dai 4 hỏng, 54 xanh (projection, reopen, resume); không nới assert.
- Lượt 2: 161 xanh, 1 lỗi fixture dùng draft ngoài CHECK schema; sửa fixture pending.
- XANH lượt 3: 162 passed, 20.25 giây, đúng 3 lượt pytest, không chạy cả bộ.
- Lệnh xanh: `PYTHONUTF8=1 py -m pytest -q -p no:cacheprovider tests/test_tickets.py tests/test_tickets_page.py tests/test_lao_dai.py tests/test_budget_audio_platefix.py tests/test_money_reset.py tests/test_project_reserve.py tests/test_money_policy.py tests/test_spend_gate.py tests/test_devsys_admin_auth.py`.
- Bằng chứng: AppTest đọc/Owner/CAS sẵn có xanh; broker đọc CSDL tmp thực gen_done=[1]; readonly không ghi usage; HTTP client gửi dở header không chặn client khác; ngày VN kiểm cả hai dạng UTC qua mốc 17:00.
- Tự kiểm 2b.5: không nới test, không đường dẫn phụ thuộc cwd mới, không API/sổ chi ghi/mạng ngoài localhost/dữ liệu thật; không đổi runner/khâu gen; không bật cờ.
- Không thêm file mã/test mới, đều đã nằm trong areas.json; không tăng version. Không sửa admin_auth/TODO/PLAN.
- `related_areas.py`: vùng diag/budget/devsys; caller budget ở core_infra, step1–5, knowledge, dashboard_ui. Cần phiên RÀ KỸ đối chiếu caller tiền, OwnerCAS và sidebar trước commit.
- Chưa thử Dashboard/pet GUI trên máy chính hoặc dữ liệu thật; đây là bằng chứng code/fixture và HTTP loopback, không nghiệm thu sản xuất.

## RÀ KỸ độc lập và một vòng sửa

- Rà working diff 9 file từ nền `0e86347`, đối chiếu 6 mục TRUNG + THẤP, skill 2b.5 và CHUẨN; bắt **1 lỗi P2, 0 lỗi nghiêm trọng**.
- P2 `devsys/tickets_page.py`: `st.write` diễn giải Markdown trong ba câu ảnh hưởng/nguyên nhân/bằng chứng; tham chiếu hợp lệ `![bằng chứng](relative/image.png)` thành ảnh, mã test có dấu `*`/`_` bị định dạng.
- ĐỎ độc lập: `test_human_details_render_evidence_as_literal_text` hỏng đúng kiểm ba dòng văn bản nguyên dạng (1 failed / 1.26s). Fixture CSDL tạm chứa Markdown trong shot/nguyên nhân/tệp bằng chứng, render trang thật bằng AppTest.
- Sửa đúng ba dòng `st.write` thành `st.text`; không đổi nội dung, service, quyền hay quyết định. Không nới assert hoặc test cũ.
- XANH sau sửa: nhóm 9 file như lệnh trên **163 passed / 20.50s** (thêm 1 regression); vòng sửa đúng 2 lượt pytest (đỏ hẹp, xanh nhóm), không cả bộ.
- Đã rà CAS/event/audit reopen; projection phiếu đóng/không chặn; resume_state; đường dẫn tuyệt đối; ISO/SQLite UTC/offset và range index của caller tiền; sidebar một lần; Owner/CAS; broker GET/localhost/readonly/TTL/thu hồi/timeout/data_dir; lý do chờ độc lập; pending_unknown/gen_done; pet waiting_admin/toast. Không tìm lỗi thêm trong phạm vi.
- Không API tốn tiền, không dữ liệu thật, không TODO/PLAN/admin_auth/runner/lock_exceptions/end_frames/place_refs/scene_storyboard; không commit/push, không tăng areas.version. Chưa thử GUI/sản xuất; cả bộ Windows và tích hợp do phiên chính thực hiện.
