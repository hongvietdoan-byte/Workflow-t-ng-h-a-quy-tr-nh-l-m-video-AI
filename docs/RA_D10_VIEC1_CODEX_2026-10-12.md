# Rà tự kiểm Đ10 việc 1 — Codex — 12/10/2026

- Nhánh: `codex/d10-viec1-goi-gui-kem`; nền `be29b3c`.
- Phạm vi: `core/package_overrides.py`, `core/shots.py`, `tests/test_package_overrides.py`.
- Ghim OUTFIT nhận `wearer`/`character`, kiểm người trong shot; một nhãn OUTFIT được suy ra, nhiều nhãn yêu cầu chọn rõ. Lưu wearer suy ra để hoàn tác giữ đúng người.
- Hash chỉ khóa ảnh từ lineage và khóa cast/outfit/plate/aspect; bỏ motion/takes/camera_plan.
- `base_refs` phải là danh sách gói thật, không tự dựng gói. Đường ghi vẫn CAS trên raw scenes.data + revision và savepoint audit; không sửa jobs/sent_package.
- Ghim giữ góc phụ nhân vật; ảnh đã có được ghim đúng slot, không nhân đôi góc phụ. Nền/OUTFIT thay nhóm cùng vai trò như trước.
- `ref_unreadable` tối đa một lần trong lượt apply.
- Shot có chỉnh gói nhưng số shot biến mất ở replace_from/store_plan: diag `override_orphaned`, warn, sau commit kế hoạch tránh diag.commit cắt transaction đang viết.
- Cờ OFF: load/apply/check no-op cũ; save/undo từ chối trước ghi; orphan helper không ghi diag khi OFF. Không bật mặc định.
- CWD: `_root`/resolve giữ root tuyệt đối; regression chdir sang thư mục chứa ảnh sai xác nhận không đọc theo CWD.
- Không test bị nới: caller test cũ bổ sung base_refs theo hợp đồng mới; assertions cũ giữ nguyên.
- Không lời gọi API/trả tiền; không data thật; không đổi runner/lock_exceptions/end_frames/place_refs/scene_storyboard/admin_auth/TODO/PLAN.
- Không file mã/test mới; các file đã đăng ký areas, không đổi version (55).
- ĐỎ lượt 1: 19 pass + 5 fail đúng lỗi thiếu base_refs/hash/pin/wearer/warning.
- ĐỎ lượt 2: 9 pass + 2 fail orphan replace_from/store_plan.
- XANH lượt 3: 116 passed trong 142,67 giây; 5 file: package_overrides, sent_package, v3, shot_lessons_db_order, multishot_fixes.
- Chưa thử thật trên dữ liệu sản xuất; chưa chạy cả bộ Windows; chưa commit/push theo phân công root.

## Đề bài rà độc lập từ related_areas

`py tools/related_areas.py core/package_overrides.py core/shots.py tests/test_package_overrides.py`

- Chứa: core_infra, step1.
- Gọi shots: step2, autopilot, plates3d, step3, step4, budget, step5, dashboard_ui.
- Cờ dùng chung: knowledge, step4.
- Ưu tiên rà hợp đồng save/undo yêu cầu base_refs; pin nhiều người/cùng role; hash đầu vào ảnh; replan giữ chỉnh + cảnh báo orphan; OFF không đổi byte; raw CAS/audit bất biến jobs.
- Test CHẬM bắt buộc khi tích hợp: test_editor_apply.py, test_editor_review.py, test_rough_cut.py, test_ui_v2_acceptance.py.
- Reviewer chỉ đọc diff và caller; root quyết test cả bộ + commit/push.

## RÀ KỸ độc lập + vòng sửa gom (12/10/2026)

- 1 lỗi TRUNG: `save` suy wearer từ slot OUTFIT nhưng bỏ qua kiểm cast trong `_resolve`; gói cũ có nhãn OTHER vẫn ghi chỉnh dù shot hiện chỉ có KELLY.
- Sửa: kiểm wearer sau bước suy ra trên cùng snapshot `data` dùng CAS; từ chối trước scenes/audit. Explicit wearer/character vẫn giữ kiểm cũ.
- Hồi quy: `test_d10_outfit_wearer_must_belong_to_shot_even_when_inferred` (3 tham số): ĐỎ **1 failed, 2 passed** (wearer suy ra), không nới assertion/test cũ.
- Đã đọc đường gọi đổi: `llm_io.apply` → store_plan; `llm_runner` và `director_two_pass` → replace_from. Warning nằm sau commit kế hoạch; OFF return trước diag; không thêm API. Các khu related_areas còn lại chỉ đọc shots, không đổi hợp đồng.
- `save`/`undo` hiện không có caller sản xuất ngoài test: yêu cầu base_refs không làm vỡ Dashboard/runner khi chưa nối. Caller sau này phải truyền đúng gói trước apply.
- Đã đối chiếu raw CAS/savepoint rollback, `_user_locked`, replan + undo định danh shot, hash khóa ảnh, nhiều OUTFIT, ghim giữ góc phụ/không nhân đôi, warning dedup, root tuyệt đối, OFF no-op, jobs.sent_package bất biến.
- Không thấy lỗi chặn còn lại trong phạm vi; cả bộ Windows dành bước tích hợp root. Không commit/push, không data thật/API.
- XANH sau rà: **119 passed / 154,46 giây**, cùng 5 file đã chạy phiên làm (`test_package_overrides`, `test_sent_package`, `test_v3`, `test_shot_lessons_db_order`, `test_multishot_fixes`). `git diff --check` sạch.
