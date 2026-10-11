# Rà Đợt 8 việc 1 — 11/10/2026

Base df7c423, nhánh codex/d8-viec1-goi-gui-kem; chưa commit/push. Rà hợp đồng 7 điểm trong THIET_KE_TIEU_NHI_LAO_DAI_D7 mục 3 và callees Kho, camera/package_problem, cast_missing, replan, audit, WATCH, lineage.

## Findings và sửa

1. base_package_hash chỉ lưu: apply nay so hash refs cuối, lệch trả VÀNG override_stale, giữ gói gốc, không áp chỉnh cũ mù.
2. Kho cho ảnh pending/removed/redundant hoặc sai look/phạm vi: resolve dùng assets.USABLE, bảng project_assets và looks.asset_look; xác minh look được khai so metadata thật. Actor/ACL vẫn do caller xác thực, lõi không cấp quyền.
3. Pin nền dùng nhãn khác builder nên append: dùng nhãn place_refs chuẩn, tìm slot nền theo role; thay slot và giữ metadata ref gốc. Không đụng role khác.
4. Undo thiếu root, nền audit giữ ID trước replan: thêm keyword data_dir/base_refs; chỉ ánh xạ ID shot hiện hành khi audit khớp logical shot, resolve lại index/key/role/SHA trước ghi. Nền không còn hợp lệ bị từ chối.

## Bằng chứng

- Đỏ regression trước sửa: 6 failed, 12 passed (hash stale, ba trạng thái Kho, phạm vi/look, pin nền).
- Đỏ undo độc lập: TypeError do API chưa nhận data_dir, 1 failed.
- Nhóm sau sửa: 27 passed, 2 failed vì fixture cũ save gói Kho mặc định nhưng apply gói rỗng; sửa fixture truyền base_refs đúng trước save, giữ assertion.
- Xanh: `PYTHONUTF8=1; py -m pytest -q -p no:cacheprovider tests/test_package_overrides.py tests/test_storyboard_cast_refs_p24.py tests/test_plate_package_single_angle.py` → **29 passed in 1.65s**.
- Tổng 4 lượt pytest sau wake (root chấp nhận lượt bổ sung); không chạy rộng/cả bộ. git diff --check qua trước ghi tài liệu.

## Giới hạn và tự rà

Không đọc/ghi dữ liệu thật, không API/trả tiền, không sửa runner/place_refs/scene_storyboard/end_frames; không UPDATE jobs. Cờ OFF vẫn trả đúng đối tượng refs cũ, save/undo không ghi. CAS raw scenes.data + savepoint audit giữ nguyên; không nới assertion cũ. Code/test đăng ký areas; version không đổi. WATCH/lineage không theo dõi khóa mới; replan giữ khóa và báo stale.

Caller tích hợp phải truyền base_refs cuối sau cap khi save/undo, data_dir tuyệt đối cho SQLite memory hoặc đường dẫn dữ liệu khác CSDL, và thực hiện ACL. Chưa nối Dashboard/runner, chưa nghiệm thu ảnh thật, chưa chạy cả bộ Windows, chưa tuyên bố sửa sản xuất. Root đọc diff và commit theo quy trình.
