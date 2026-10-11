# Đ10 việc 2 — kỹ thuật, 12/10/2026

Base be29b3c; nhánh codex/d10-viec2-ky-thuat. Chưa commit/push.

- V3 chỉ ghi layout_drift_proposal, nhãn đề xuất chưa áp dụng kèm đường dẫn tuyệt đối thư mục lượt; không đóng finding layout_drift của thay đổi đã áp dụng.
- --approved-blocking và --approved-specs chỉ rõ bản đã duyệt, không coi --hand (thư mục output v2 để so) là baseline. Cờ bật kiểm thiếu tệp trước khi gọi Claude. Cờ tắt không đọc baseline/ghi finding.
- short_lock_block cùng hàm _has_outfit_ids với lock_text; không dựa file gửi được/CWD. Không sửa runner/lock_note.
- Khai short_lock_outfit ở step3, giữ areas version. Test xfail đăng ký finalizer dọn TMP kể cả assert thất bại.

Bằng chứng mock: đỏ 6 failed, 9 passed, 1 xfailed; xanh liên quan 45 passed, 1 xfailed; kiểm cuối 70 passed, 1 xfailed (3 nhóm pytest tổng).
Lệnh cuối: PYTHONUTF8=1 py -m pytest -q -p no:cacheprovider tests/test_d8_technical.py tests/test_change_review.py tests/test_script_cap.py tests/test_lock_ngoai_le.py tests/test_stage_director.py.
Chưa thử thật; không API trả phí, không dữ liệu thật, chưa cả bộ Windows.

Rà liên quan (tools/related_areas.py): chứa step1/core_infra/plates3d; caller assets/step3/step4/knowledge/step2/dashboard_ui/autopilot. Cần rà nguồn proposal không bị coi đã áp dụng, OFF nguyên byte và guard thiếu baseline trước client. Test CHẬM bắt buộc khi gộp: tests/test_ui_v2_acceptance.py.

Tự kiểm: không đổi cờ mặc định; không blocker/job/auto-send; OFF vẫn query danh sách name nhưng thêm cột outfit_image_ids, chuỗi đầu ra cũ giữ đúng test. Không thêm mã mới nên không cần code registry mới.

## Rà độc lập và vòng sửa gom (Codex 12/10)
- Phát hiện **1 P2**: `review_stage_round` nhận một tệp baseline explicit cùng `approved_dir` đã bỏ im tệp đó, thay bằng cặp trong thư mục; guard kiểm cặp nằm sau fallback nên vô hiệu.
- Sửa: kiểm đủ cặp explicit trước fallback. Hai ca `test_stage_partial_explicit_baseline_does_not_fall_back` đỏ **2 failed / 1 passed**, sau sửa nhóm liên quan **73 passed / 1 xfailed, 5,72 s**.
- Thêm ca dedupe cùng lượt + proposal revert: không tạo trùng, không đóng finding official hoặc proposal lượt trước. Nguồn riêng chỉ VÀNG, `refresh_code`/Claude chỉ đóng nguồn của mình.
- Rà `v3_main`: guard thiếu tệp chạy trước `script_cap.start` và `client_from_env`; cờ OFF trả về trước đọc baseline/ghi finding. `--hand` vẫn chỉ để so output v2.
- Rà callers `prompts.lock_text`/`short_lock_block`: dùng chung tiêu chí chuỗi outfit_image_ids khác rỗng, không phụ thuộc file hoặc CWD; không đổi runner. Cờ khai step3, areas version giữ nguyên; finalizer xfail dọn TMP dù assert thất bại.
- Hạn chế: baseline explicit chưa có camera v2 thì ghi thiếu máy bản đã duyệt, chưa kiểm trái/phải; chưa nghiệm thu dữ liệu/ảnh thật. Không gọi API, không chạy cả bộ, không commit/push, không sửa file #24.
- Lệnh xanh: `PYTHONUTF8=1 py -m pytest -q -p no:cacheprovider tests/test_d8_technical.py tests/test_change_review.py tests/test_script_cap.py tests/test_lock_ngoai_le.py tests/test_stage_director.py`.
