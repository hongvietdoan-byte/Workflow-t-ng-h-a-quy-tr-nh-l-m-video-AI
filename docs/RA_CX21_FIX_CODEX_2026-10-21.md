# CX21-FIX — báo cáo triển khai 21/10/2026

Nhánh `codex/v31-fix-21`, worktree `D:/AI-Video-Pipeline/.codex-wt/v31-fix-21`.
Nền `2a2b30ec` (main đã có CX20-2b + CX20-5b). Chưa gộp/chưa push.

## Kết quả theo đề 6 mục

1. `subjects.capacity`: đối soát `processing/asset_id=NULL` theo tên duy nhất trong snapshot; asset đã thấy chiếm đúng một chỗ, không tính thêm upload. Chỉ UNKNOWN khi sha chưa đối soát thuộc gói hiện tại; sha khác giữ một chỗ dự phòng. Không ghi cache trên đường capacity; `ensure_picture` tiếp tục đối soát và chuyển active. Test gọi `submit_pending` hai lượt: một submit giả, lượt sau 0, không upload trùng.
2. `VideoRunner`: khi pregen defer, kiểm sức chứa ở prepare và tái dùng kết quả trong finish; không GET capacity trong SPEND_LOCK. Giữ clean pixels/fingerprint và deferred upload. Probe một thread khác lấy SPEND_LOCK ngay trong list_assets để bắt cả RLock (không dựa vào acquire cùng thread). Cờ OFF giữ đường cũ; `test_video_pregen.py` xanh.
3. `rejected_frame_assets`: kiểm sqlite_master rồi trả [] khi chưa có bảng; không CREATE trên đường đọc của inbox. Regression dùng query_only=ON với CSDL trắng.
4. `data/decisions.json` là code-config tracked: thêm `v31-d03c-c3-3-subject-cleanup-dry-run-2026-10-20` replaces D03b. Sổ không có mục riêng 13/10; duyệt cũ được ghi trong keeps D03b, nên đánh dấu D03b replaced và CHUYỂN TIẾP rõ mọi guard: preflight, dừng thiếu/unknown, không đổi model, chỉ tác vụ cần Kho, bảo vệ owner/nhân vật, mốc trên 3 ngày chỉ làm tiêu chí dry-run. Không cấp quyền xóa. Check mới xác nhận không có lời gọi library, deleted rỗng; tên D03c duy trì bộ kiểm D01–D10.
5. README golden ghi khóa SHA TOÀN CSDL, giữ bản sao đóng băng ngoài Git cùng fixture; native Python3.14, SYSTEMROOT whitelist, venv fail-closed. Guard sys.prefix/base_prefix thêm vào worker launcher. Test replay fixture kiểm SHA nguồn và mtime_ns toàn cây data tổng hợp không đổi.
6. `merge_union`: import không tự chạy CLI; lấy cả ba stage git :1/:2/:3, parse toàn tài liệu trước ghi; dict merge ba phía, areas theo id, stable union list, list primitive một dòng, dict thụt lề. Scalar xung đột/parse lỗi fail-closed không ghi. Có test 20 area thêm ở hai bên khác format, mapping chung, deletion, scalar, stage path và môi trường con whitelist. Git native tìm ở vị trí chuẩn Windows/Linux; thiếu thì dừng rõ.

## Kiểm chứng

Mọi lệnh pytest chạy bằng native `C:/Users/hongviet.doan/AppData/Local/Python/pythoncore-3.14-64/python.exe`.
Launcher thay OBJECT `os.environ` bằng dict whitelist giả bằng `patch.object` TRƯỚC import pytest/conftest/modules. Không dump môi trường. `--tb=no --no-showlocals -q -p no:cacheprovider`; provider/transport tổng hợp, không mạng/chi phí.

- Đỏ: `tests/test_cx21_fix.py`: **6 failed, 1 passed**, tái hiện NULL liên quan/không liên quan, CREATE đường đọc, GET trong lock, thiếu API merge cấu trúc và parse fail-closed.
- Lượt gộp kế: 4 file CX21/capacity/golden/decisions: **95 passed, 1 failed** (tương thích test D01–D10 khi thay D03b); sửa bằng successor D03c giữ chính sách.
- Xanh cuối: **169 passed, 33.58s**, 6 file: `test_cx21_fix.py`, `test_subject_capacity_d20.py`, `test_golden_db_replay.py`, `test_decisions.py`, `test_video_pregen.py`, `test_subject_auto_cleanup.py`.
- Một lần gọi sai cú pháp tùy chọn `--showlocals=no` bị parser từ chối trước collection; đã dùng đúng `--no-showlocals` ở mọi lượt thực thi test.
- Red đo trực tiếp nằm ở nhóm runtime Kho/runner/inbox/merge; kiểm C3-3 và khóa nguồn golden bổ sung trong các lượt gộp. Không tuyên bố đã đo riêng baseline đỏ của hai bổ sung này.

## Tự rà 2b.5 / phạm vi liên quan

Đã chạy `tools/related_areas.py`: step4, step2, core_infra, diag, devsys; caller: archive/delivered, dashboard/common/header, assets, autopilot, plate_layout_qc, continuity_ui. Đọc đường inbox cleanup, schedule_auto_cleanup và submit prepare/finish; không đổi chữ ký caller bên ngoài, widget key hoặc cờ mặc định. Tests capacity cũ cho sha không liên quan đổi kỳ vọng UNKNOWN -> READY theo đề, test mới kiểm còn chỗ dự phòng (không nới guard gói liên quan).

- CWD: config/sổ theo module ROOT; merge stage dùng root Git và repo-relative path; fixture/replay dùng absolute root/scratch.
- Lô/tự động: giữ deferred upload; mỗi gói check trước finish, direct submit cũ còn guard; test submit hai lượt không treo/không nhân bản.
- OFF: không thêm cờ mới, không thay default/verified; không cần đổi package_inputs; `areas.json` giữ version 88, đăng ký test CX21 ở step4.
- Sandbox/tiền: tests giả, worker native whitelist; không gửi provider thật, không đọc token/header/credential payload; không sửa live/data thật/dashboard.env, không restart.
- Không đổi shot_intent/cloud-C, TODO hoặc PLAN. Không có HANDOFF WIP trong kết quả cuối.

## Còn mở / giới hạn

- Chưa chạy cả bộ Windows (phiên chính thực hiện trước gộp); related_areas báo test chậm bắt buộc ở bước gộp.
- Chưa thử thật Kho/API và golden dự án #24/#27; nghiệm thu vận hành vẫn mở, cờ giữ OFF.
- Root mở phiên rà kỹ sạch sau bàn giao; commit nhánh chưa là chấp thuận merge.
- Snapshot capacity không phải reservation; guard submit/provider tiếp tục xử lý thay đổi sức chứa sau snapshot. Upload/reconcile GET khác của ensure_picture giữ hành vi hiện tại; chỉ GET capacity được chuyển ra khỏi khóa theo đề.
- merge JSON scalar thay đổi đồng thời cần giải quyết tay; không đoán để ghi nhầm config.
