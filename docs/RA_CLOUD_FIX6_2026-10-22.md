# C-FIX6 phần A — sửa lỗi rà kỹ C-M48-DESK-CORE (22/10)

- Nhánh: `claude/v31-fix6-desk`, nền `origin/cloud/v31-m48-desk-core` @ 13eee058 (dựng trên tích hợp M2).
- 0 USD: không gọi API, provider giả, Blender giả. Không thêm cờ. Không sửa TODO.md / hộp thư / main.
- Phần B (C-M83-TOOL, `tools/load_test_ui.py`) KHÔNG làm ở đây.

## Từng mục

| # | Mức | Sửa (file:dòng sau sửa) | Test (đỏ → xanh) |
|---|---|---|---|
| 1 | CAO | MỘT cổng S-C `stage_desk.paid_hold` (core/stage_desk.py:1026). Nối ở `runner._Runner._desk_hold` (core/runner.py:278), gọi trong `_submit_pending` (core/runner.py:483) sau Tổ rà soát, trước `_gate_hold` → mọi đường gửi job ảnh + video: nút Gen ảnh (batch.queue_images, kể cả tick "vẫn gen"), autopilot `_images_phase` / `_videos_phase`, gen video, gửi lại / gen lại. Không giữ job đã có `external_id` (đã trả tiền). Mã diag `stage_desk_hold` ∈ `HOLD_CODES` + `diag.MERGE_CODES` + 📥 (core/inbox.py:71). Autopilot `_desk_wait` (core/autopilot.py:589) → `_Wait("stage_desk")` có câu, đọc ĐÚNG lý do runner vừa giữ (cả shot cùng nhóm gửi). Rà quy ước 7 tìm thêm 2 đường trả phí theo shot KHÔNG qua runner → cùng hàm: ảnh khung cuối core/end_frames.py:457 (+ autopilot `_end_frame_phase` chờ có câu, core/autopilot.py:870) và phép thử Seedance / bản cuối từ mẫu core/quality_samples.py:123. batch.image_gates (core/batch.py:122) báo trước, câu nói rõ tick "vẫn gen" không thay ngoại lệ EP | `test_v31_fix6_desk.py` PaidPathsTests: `test_gen_image_button_path_holds_even_when_the_person_ticks_go_anyway`, `test_autopilot_image_phase_holds_and_waits_for_the_person`, `test_paid_video_path_holds`, `test_resend_path_holds`, `test_exception_lets_the_job_go`; ReviewGateTests: `test_autopilot_waits_when_the_runner_held_a_group_leader`, `test_inbox_lists_a_clip_held_by_the_desk_gate`; `OffRunnerPaidPathsTests.test_quality_sample_is_held_before_any_spend`; `EndFrameHoldTests.test_end_frame_is_held_before_any_spend` |
| 2 | VỪA | `check_stage_desk_ep_only` / `_paid_gate` / `_reset_confirm` (tests/test_decisions.py) gọi hàm thật trên dự án tạm + đoạn sân khấu giả: Director/tool/autopilot bị từ chối, người được sửa không phải EP, user None khi đăng nhập BẬT không phải EP, N4 nguồn cố định `claude_code`; S-C: không đánh dấu → không VÀNG/không giữ, đánh dấu → HOLD (cả `runner._desk_hold`), Đạo diễn tự chốt vẫn HOLD, ngoại lệ thiếu lý do bị từ chối; S-D: chưa xác nhận không cất, xác nhận ghi dấu, chỉ shot đổi máy cũ. Không còn `inspect.getsource` | `py -m core.decisions check` khớp; `test_decisions.py` xanh |
| 3 | VỪA | Không thêm cờ. `paid_gate` chỉ chạy khi có `desk_gate.json` với `required` (EP đã đánh dấu) — core/stage_desk.py:959; không có → `[]`, không đọc sân khấu (không VÀNG cho crew/state.json dở; Bước 2 không chạy `scene_status` mỗi lần vẽ). Runner / batch / autopilot chỉ thêm một `os.path.isfile`. Tệp đánh dấu hỏng → HOLD có câu (không đoán "không bắt buộc") | `NoMarkSameAsBeforeTests.test_half_done_crew_without_marks_adds_no_yellow_and_reads_nothing`, `test_runner_sends_exactly_like_before_without_marks` (so có / không cổng: cùng trạng thái job, cùng 1 lần gửi) |
| 4 | VỪA | `approve`: kiểm `expected_marks` trong `fn` của `_sync` (core/stage_desk.py:727) — kiểm-và-ghi cùng khóa S | `MarksInsideLockTests.test_camera_written_while_waiting_for_the_lock_is_refused` |
| 5 | VỪA | `reset_preview` (core/stage_desk.py:774) không còn đánh dấu mọi shot có máy là cũ: `plates_stale_after` / `images_stale_after` rỗng, `may_go_stale` (có thể cũ), `marks_before`; `reset` ghi `marks_before` TRONG khóa. Lượt EP duyệt sau: `_close_reset` (core/stage_desk.py:795) tính shot ĐỔI máy → ghi `desk_reset_stale.json` (nền / ảnh đã vẽ / world map) RỒI mới xóa `desk_reset.json`; `scene_status["reset_stale"]`. Dấu cũ không có `marks_before` → như trước | `ResetOnlyChangedTests.test_only_shots_whose_camera_changed_go_stale_and_the_list_is_kept`; `check_stage_desk_reset_confirm` |
| 6 | THẤP | `_start` nhả khóa khi ghi tiến độ lỗi (core/stage_desk.py:395); `_Hold.acquire` dọn tệp + thẻ khi `os.write` lỗi (279); `hold_segments` nhả mọi lỗi (326); gỡ khóa cũ nguyên tử `_remove_if_same` (173: `os.replace` sang tệp riêng → so nội dung → `os.link` trả lại nếu đã đổi chủ); `user=None` khi đăng nhập BẬT không là EP (`login_on` 463, `_need_ep`); N11 `render_plates` lấy khóa S qua `_sync` (876) | LockRobustnessTests: `test_progress_write_error_releases_the_lock`, `test_lock_write_error_leaves_no_lock_and_releases_earlier_ones`, `test_stale_lock_removal_never_removes_a_fresh_lock`, `test_no_user_with_sign_in_on_is_not_the_executive_producer`, `test_render_plates_takes_the_stage_lock` |

Test sửa theo hành vi mới (không nới):
- `test_v31_m48_desk_core.py`: `test_paid_gate_warns_by_default…` (chưa đánh dấu → `[]`, mục 3); `test_reset_asks_and_previews…` (mục 5).
- `same()` thêm chuẩn hóa đường dẫn đã thoát `\\` trong JSON. Đây là lỗi có sẵn chỉ trên Windows: `GuardTests.test_guard_off_writes_exactly_like_before` và `MatrixTests.test_cli_approve…` đỏ ở nền trên Windows, cloud Linux xanh.

## Chạy test (chỉ test liên quan)
1. ĐỎ: `tests/test_v31_fix6_desk.py` trên nền 13eee058. Lần đầu dừng ở `-x` (thiếu `autopilot_state`). Lần hai: mọi test mục 1, 3–6 đỏ đúng lý do.
2. ĐỎ test rà quy ước 7 + kiểm phần đã sửa: 10 file, 232 xanh / 8 đỏ.
   - 6 đỏ là test mới (đúng lý do).
   - 2 đỏ là lỗi Windows có sẵn kể trên.
   - Thêm một lần chạy riêng 2 test để đọc lỗi.
3. XANH trước bàn giao: `test_v31_fix6_desk`, `test_v31_m48_desk_core`, `test_decisions`, `test_v31_m17_ops_notices`, `test_end_frames`, `test_quality_samples`, `test_image_pregen`, `test_autopilot`, `test_runner`, `test_video_gate`, `test_inbox_clean`, `test_stage_auto` → **342 passed**.
- Không chạy cả bộ.

## Rà quy ước 7
`py tools/related_areas.py core/stage_desk.py core/runner.py core/batch.py core/autopilot.py core/diag.py tests/…`:
- **Khu vực chứa file đổi:** plates3d, step2, step4, core_infra, autopilot, diag.
- **Khu vực gọi tới:** assets, lipsync, dashboard_ui, step1, budget, step3, step5, knowledge, devsys.
- **Test chậm ở bước gộp:** test_access, test_devsys(_v2), test_editor_*, test_hop_thu, test_rough_cut, test_ui_v2_acceptance.

Một agent đã rà. Đã sửa:
- **CAO:** end_frames / quality_samples đi vòng runner; `paid_gate` lỗi đọc → chỉ VÀNG; shot bắt buộc ngoài sân khấu bị cho qua.
- **VỪA:** autopilot không thấy giữ theo nhóm; 📥 thiếu mã `stage_desk_hold`.
- **THẤP:** ghi chú giới hạn N11 và `_close_reset`; `areas.json` thêm `tests/test_v31_fix6_desk.py` (plates3d + autopilot, không tăng version).

Ghi lý do, không sửa:
- **VỪA 5** (`paid_hold` mỗi job mỗi vòng chưa có cache): chỉ chạy khi EP đã đánh dấu. Cache theo thời gian làm trễ việc nhả / giữ sau khi EP duyệt (cờ / test hành vi S-C đỏ).
- **lipsync / scene_establish:** không theo shot hoặc là clip đã có; đã ghi ở docstring.
- **Đường tương đối `data/projects`** (THẤP 9): cùng rủi ro như mọi tệp dữ liệu khác. Dashboard và runner dùng cùng `data_dir`.

## Việc mở
- `_close_reset` chỉ chạy ở N6. Đạo diễn tự chốt và CLI `--crew-approve` chưa đóng dấu làm lại; lần EP duyệt sau vẫn so đúng với `marks_before`.
- Khóa S của N11 không phủ lúc render ở luồng `place_refs`. Máy ghi xen giữa lúc đó do `runner._stale_plates` bắt.
- Phần B (C-M83-TOOL) chưa làm.
