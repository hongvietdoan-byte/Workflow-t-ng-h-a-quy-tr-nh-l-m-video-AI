# CX20-5b — sửa rà Kho chủ thể, 21/10/2026

- Nhánh `codex/d20-viec5-kho-chu-the`; build trước `9f027c1d`, rà trước `70982526`; merge `origin/main` tại `c722f427`. Commit sửa chứa báo cáo này (xem git log).
- Nguồn: sự kiện `hop_thu/su_kien/20261020-232431-phien-chinh-cjr3.json`, việc CX20-5b. Phạm vi: hai VỪA và các THẤP của rà phiên chính; không mở rộng allocator/apply.

## Thay đổi

1. `ClipAISubjectLibrary.list_assets(strict=False)` giữ mặc định legacy cho get/upload: payload rỗng, trang ngắn/count lệch và hết max_pages không phát sinh lỗi strict mới. Chỉ `subjects.capacity` gọi `strict=True`, giữ fail-closed snapshot thiếu/sai định dạng. Mock library nhận cùng tham số. Test cờ OFF gọi native get/upload với count lệch vẫn theo hợp đồng cũ; factory OFF vẫn gọi `subject_library()` không đối số.
2. Cache processing của job khác đã có asset_id trong snapshot không chặn toàn Kho; asset đó vẫn chiếm chỗ theo snapshot. Processing không có asset_id hoặc không có trong snapshot vẫn UNKNOWN, không suy Kho trống hay cho gửi lại upload chưa đối soát.
3. CapacityWait lưu cooling trên chính VideoRunner, dùng cùng thời gian `PREGEN_RECHECK_S`. Heartbeat trong khoảng chờ bỏ qua chuẩn bị/hoàn thiện gói, tránh GET Kho lặp trong SPEND_LOCK; hết hạn thử lại, cờ guard OFF bỏ cooling này. Chạy submit loop hai lần vẫn chỉ một list_assets, job giữ queued, không submit/Kling fallback.
4. Inbox owner bỏ đề nghị cleanup cũ khi `rejected_frame_assets` hiện rỗng; khi còn ứng viên vẫn hiện cả dự án archived. Không thay đổi quyền owner hoặc tạo đường apply.
5. Xóa HANDOFF.md theo yêu cầu giao việc/heartbeat; báo cáo và kết quả nằm trong tài liệu này và CODEX_TASKS.

## Đỏ → xanh và boundary

- Vòng đỏ: `tests/test_subject_capacity_d20.py` **5 failed / 21 passed / 0,59s**. Lỗi tái hiện: strict tác động legacy get/upload; processing đã có snapshot vẫn chặn; cooling chưa có (test submit loop và test expiry/OFF); inbox stale plan.
- Vòng xanh: bốn file `test_subject_capacity_d20.py`, `test_subject_auto_cleanup.py`, `test_subject_library_cleanup.py`, `test_subjects.py`: **77 passed / 6,30s**.
- Vòng liên quan: thêm `test_video_pregen.py` và `test_inbox_clean.py`: **135 passed / 14,34s**. Tất cả chạy `-q --tb=no -p no:cacheprovider`, không nới assertion cũ.
- Python native cố định `C:/Users/hongviet.doan/AppData/Local/Python/pythoncore-3.14-64/python.exe`; harness thay OBJECT `os.environ` bằng dict giả trước pytest/target imports/calls, home/temp đều thư mục tạm; không dùng launcher trong env rỗng. Vòng mở rộng chặn registry OpenKey và urllib urlopen; provider/model fixture giả, không API/network, không đọc/in credential thật hoặc dữ liệu thật.

## Rà liên quan / 2b.5

Đã chạy `tools/related_areas.py` cho adapter/subjects/runner/inbox/test: step4, step2, core_infra, diag; callers Dashboard/header/common, assets, autopilot, archive/delivered, budget. Đọc lại đường chung submit_pending/pregen/deferred, bg_poll/autopilot tạo runner, get/upload và cleanup legacy. Root đã đọc diff sửa và callers inbox/owner, chưa phát hiện lỗi khác. Không thay input/model, không paid call mới, guard OFF giữ legacy, ngoại lệ dry-run C3-3 không đổi. Merge areas giữ toàn bộ upstream và version87, đăng ký tool/test/cờ subject như trước; không thêm file mã mới.

## Giới hạn và bước tích hợp

- Allocator/reservation nguyên tử đa tiến trình, account scope, fairness, fence/outbox/frozen refs vẫn OPEN. Guard/cooling không bảo đảm concurrency hoặc sức chứa nhiều dự án.
- Legacy DB thiếu owners/lifecycle UTC chuẩn: CLI vẫn UNKNOWN, không coi fixture8/3 là bằng chứng native đủ điều kiện xóa. Chưa hoàn tất M1.5.
- Không API/data thật/migration/bật cờ/apply/DELETE mới/live/restart; không push main/TODO/plan. Chưa cả bộ Windows/slow; related_areas yêu cầu test slow trước gộp. Root quản lý push/mailbox/tích hợp và kiểm tra cuối.
