# Đ20 việc 5 / CX20-5 — Kho chủ thể, bản build để rà

Nhánh `codex/d20-viec5-kho-chu-the`, base `3fec1686`. **Chưa gộp, chưa thử thật, chưa hoàn thành allocator M1.5.** Đã đọc C-FIX-D19 đầu thiết kế M1.5; C3-3 chỉ cho DRY-RUN. Không gọi API thật, không đọc CSDL/env production, không migration hay bật cờ.

## Phần đã triển khai

- `subject_capacity_guard` mặc định OFF. Khi bật, preflight GET toàn bộ Kho trước upload cả gói; SHA trùng chỉ tính một chỗ, SHA active đã có trong snapshot không cần chỗ mới. Cache thiếu bảng được coi rỗng sau GET thành công, không bootstrap schema trong preflight. Processing/unknown giữ VÀNG.
- Kho 100/100 cần ảnh mới → `CapacityWait`, bắt tại đường chuẩn bị args/kwargs và hoàn thiện gói trong submit loop; job vẫn queued, lý do/cách xử lý vào `WAIT_REASONS`, diag bền và 📥. Không rơi về ảnh đánh dấu hoặc nhánh từ chối/đổi Kling. Không refs → bỏ qua guard.
- G59: với cờ mới bật, factory nhận provider ClipAI đã cấu hình và dùng lại **cùng ApiClient**, không đọc key thay thế, không tự nạp `dashboard.env`. Đối chiếu thật: `tools/launch_dashboard.ps1` nạp cấu hình ở biên launcher; `core/bg_poll.py` xây provider qua factory trong chính tiến trình Dashboard. Runner mới kế thừa client đó thay vì resolve lại env trong bước Kho. Đường factory không truyền provider giữ tương thích khi cờ OFF.
- **Ngoại lệ OFF bắt buộc C3-3:** `run_auto_cleanup` legacy chỉ trả plan/hash + diag `subject_cleanup_plan`, không resolve provider, không DELETE. Giao/cất vẫn gọi scheduler nhưng chỉ lập đề nghị. Owner có dòng 📥 kể cả dự án đã cất. Không cài apply hay nút duyệt/xóa mới.
- `auto_clean_candidates` là policy thuần từ snapshot + evidence đã xác minh; veto unknown/character/active/shared active/restore/processing/pin/job chưa terminal. Dự án xong/cất phải >72h với mốc có timezone; không dùng mtime/updated_at, không tự định nghĩa nháp cũ.
- CLI `tools/subject_cleanup.py --db <bản-sao.sqlite> --snapshot <assets.json>` chỉ mở SQLite `mode=ro`, `query_only=ON`, whitelist metadata snapshot. Scan cache, job/source_job, project và character để hiện dependency. Không DDL, không provider, không apply; thiếu quan hệ chuẩn thì UNKNOWN giữ.

## Bằng chứng đỏ → xanh

- Vòng 1: **7 đỏ**, toàn bộ test mới trước implementation.
- Vòng 2: **36 xanh / 1 đỏ**. Test UI legacy đỏ vì harness thay OBJECT env rỗng thiếu home, Streamlit `Path.home()` không tìm được; không đổi/nới assertion UI.
- Vòng 3: **42 xanh / 5,54 giây**: `tests/test_subject_capacity_d20.py`, `tests/test_subject_auto_cleanup.py`, `tests/test_subject_library_cleanup.py`; `-q --tb=no -p no:cacheprovider`.
- Python native cố định `C:/Users/hongviet.doan/AppData/Local/Python/pythoncore-3.14-64/python.exe`. Harness dùng `patch.object(os, 'environ', dict_fake)` trước imports/calls; vòng cuối cấp USERPROFILE/HOME/TEMP/TMP bằng thư mục tạm và tắt telemetry Streamlit. Không đọc/in env/header/token/payload bí mật, không `py` dưới env rỗng. Provider toàn bộ fake/đóng kín.
- Native submit loop dùng CSDL fixture + provider fake: full100/100 giữ queued, 0 submit, chỉ một job video (không Kling fallback). API policy fixture 5 rejected +3 archived4d +2 archived1d +1 shared active →8 eligible/3 protected; **đây là evidence giả đã xác minh, không phải đã chứng minh legacy DB đủ ownership**.
- Cold DB không tạo bảng; existing SHA full100/100 cần0 chỗ; list lỗi → UNKNOWN/warn/0delete; giao và cất0delete; factory cùng client; CLI đọc DB byte-identical. Chưa chạy cả bộ Windows, chưa GUI/live chất lượng.

## Rà liên quan và 2b.5

Đã chạy `tools/related_areas.py` với toàn bộ module đổi: step4/step2/core_infra/diag; callers Dashboard, assets, autopilot, archive/delivered, budget. Công cụ báo **Test CHẬM bắt buộc khi gộp**. Caller giao/cất được chứng minh0delete; mọi đường gửi thường/pregen/deferred đi chung handler giữ queued. Cờ OFF giữ resolve/fallback cũ, trừ dry-run C3-3 đã nêu. Đường CLI dùng path tuyệt đối, read-only; không paid call mới, không silent network fallback. `devsys/areas.json` đăng ký tool/test/cờ, giữ version87. Root tổ chức rà độc lập riêng trước gộp.

## OPEN — không được coi đã nghiệm thu M1.5

1. **Allocator/reservation liên tiến trình, account scope bền, fairness 4–5 project, frozen payload/fence/outbox chưa triển khai.** Guard là snapshot trước upload, không bảo đảm chống race/oversubscribe ngoài hệ thống. Chưa được bật production.
2. Legacy schema không có đầy đủ owners/refs và mốc lifecycle UTC sau restore. CLI giữ UNKNOWN toàn bộ phần đó, không giả eligible chỉ từ tên/path. Cần hợp đồng dữ liệu + migration được duyệt riêng; fixture8/3 không thay thế bước này.
3. Plan hiện trả trong bộ nhớ/hash và ghi diag đề nghị; chưa có kho plan bất biến, duyệt single-use, TTL/revalidation hay apply. Không có quyền xóa.
4. Rủi ro parser snapshot đã được reviewer xử lý trong vòng rà độc lập dưới đây; không còn OPEN ở phạm vi snapshot thiếu/sai định dạng đã thử.
5. Chưa có ca dữ liệu thật/health account/snapshot hiện thời; cả bộ Windows + rà độc lập còn ở root. Không main/push/TODO/plan/restart/live trong nhánh làm này.

## RÀ KỸ độc lập — sau build `9f027c1d`

- P2: native `list_assets` nhận thiếu `assets`/payload rỗng hoặc trang ngắn mâu thuẫn `count` như snapshot đầy đủ, khiến guard cho upload với sức chứa chưa rõ. Sửa từ chối payload không có danh sách assets, count sai kiểu/âm, tổng nhận vượt count và trang ngắn chưa đủ count; lỗi `incomplete_snapshot` đi vào `QUEUE_UNKNOWN_CAPACITY`.
- Hai regression `test_native_malformed_snapshot_holds_unknown` và `test_native_inconsistent_count_holds_unknown`: **ĐỎ 7 ca / 0,20s → XANH 70 test / 7,38s**, gồm bốn file capacity/auto_cleanup/library_cleanup/subjects. Dùng cùng harness fake OBJECT environ/home và native Python3.14, `--tb=no`; không mạng/credential/provider thật.
- Đã đọc callers archive/delivered → schedule/run (không xóa), autopilot/bg_poll → VideoRunner dùng chung, cả đường deferred và lỗi chuẩn bị gói, inbox, factory/config và CLI. Không thấy P1/P2 khác trong phạm vi này. Rà 2b.5: không nới assertion/test cũ, không bật cờ, không thêm paid call, không đổi areas.version. Snapshot guard vẫn không thay thế allocator/concurrency/fence trong OPEN1; CLI legacy vẫn UNKNOWN.
