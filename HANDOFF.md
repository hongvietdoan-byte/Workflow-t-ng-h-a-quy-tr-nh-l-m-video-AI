# Bàn giao Đ12v2 nối caller Bước 5

- Nhánh `codex/d12-viec2-noi-sfx`, base `43205faf`; hoàn tất code/rá/QA, chuẩn bị commit + push nhánh riêng. Không sửa TODO/main/live/tiền.
- Xong caller chung bảng duyệt, ACL, OPT_IN_ONLY; sau rà sửa gom strong bounded SHA + cheap UI, full metadata/catalog snapshot, source clip/Kho guards, selection strict, stage+atomic manifest với lock/CAS có giới hạn writer legacy.
- New stage không gọi ensure_duration/UPDATE Kho; durationNone giữ None. File mới core/motion_sfx_safe.py khai areas version76.
- GREEN cuối **88 passed /4,28s**, 2 file tests/test_motion_sfx_caller.py + tests/test_motion_sfx.py, --tb=no; diff --check sạch (CRLF warning).
- RA chi tiết: docs/RA_D12_VIEC2_CALLER_CODEX_2026-10-14.md. Tổng writer6 + rà/sửa6 lượt pytest hẹp đã ghi minh bạch; không chạy cả bộ.
- Root QA actual sfx_assistant 1440/1280 qua harness D:/AI-Video-Pipeline/.codex-wt/_qa_motion_sfx_step5.py, fake clip trong /7/videos; provider forbidden.
- Root đọc diff sửa lần hai + QA Windows Edge headless actual Step5 đã xong: 1440/1280 code→bảng duyệt→apply giả1cue/readonly, 2 PNG trong docs/images/d12, pageErrors0/overflow=false; metrics lưu cùng ảnh. Chỉ fake env/DB/clip/provider.
- Còn: cả bộ Windows trước gộp; clip/BYĐ thật cần phạm vi riêng. Không claim tuyệt đối crossprocess CAS hoặc chất lượng SFX từ fixture.

## Việc kế sau lượt 14/10 16:12

- Fetch cuối: origin/main `10d29b34`; commit mới chỉ bàn giao D6 máy chính, không giải phóng nguồn A. Đ18v1 `d52253e6`, v2 `6e80e98e`, v3 `80dfcf6a` vẫn chưa ancestor main.
- Đ11v2 Dashboard/autopilot, Đ11v3 editor, Đ11v4 snapshot ID/end_actor/approved blocking, Đ11v5 và Đ18v4 dùng registry A duy nhất: tiếp sau dependency gộp. Không tạo registry thứ hai. Nhóm runner và seedance_refs chỉ nhận khi mail chốt rõ; native pet QA thuộc máy chính.
- Audit độc lập không còn việc code riêng đủ điều kiện ngoài caller vừa hoàn tất. C5 mix_bus/post_fx đã main; performance/portable/BURST/ref_audio/subject warnings đã push, không làm lại. Không dừng do hạn mức: lần đọc trong lượt là 33% ĐÃ DÙNG khung5h, 67% còn; tuần71% ĐÃ DÙNG. Reset5h 14/10 20:35:26 Asia/Saigon.
- Lượt sau đọc mail/Sổ việc/bảng ưu tiên mới, kiểm branch đã gộp để tránh nhân đôi. Dời cùng lịch sau reset tự nhiên, không tạo lịch trùng. Chưa gửi thư main mới; báo cáo này nằm trên nhánh để phiên rà/gộp nhận.
- An toàn test: patch.object thay OBJECT os.environ bằng dict giả trước imports/calls/spawns; mock registry/credentials/provider/model, native env whitelist; pytest --tb=no, không showlocals/log/đọc bí mật. Không main merge/pull/restart live/API/data thật/dashboard.env/admin_auth/maintenance worker.
