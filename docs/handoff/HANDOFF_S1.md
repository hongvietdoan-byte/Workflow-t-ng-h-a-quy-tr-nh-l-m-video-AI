# HANDOFF — phiên S1 (vòng đời job + bậc chất lượng), 13/10

Nguồn: `docs/handoff/DANH_SACH_SUA_CHUOI_2026-10-13.md` (S1: C1+U1, C2, C3, C7+U2, V6, U4, U5).

## Đã xong (test đỏ trên mã HEAD ee2e45c7 → xanh)
- **C1+U1** `core/quality_tier.py`: `outdated_final()` — bản cao ĐÃ DUYỆT không tính khi nháp gốc cũ hơn nháp người duyệt mới nhất, hoặc
  take đang dùng (`takes.used`, trạng thái dùng được) là nháp mới hơn. Dùng trong `state()` + `final_source_problem()` → shot về
  `draft_ok` (nút ⬆), `request_final` gắn nháp mới, `draft_scenes` tính shot là nháp (`_DRAFT` / cảnh báo bản giao). Bản cao cũ giữ nguyên.
  Test: `SupersededFinalTests::test_newer_approved_draft_reopens_final_after_old_final_approved`, `…test_used_draft_take_newer_than_the_approved_final_marks_the_shot_draft`.
- **C2** `core/autopilot.py` `_approve_unflagged` bỏ nháp 2 bậc; `_drafts_waiting` + `_Wait("drafts", …)` (nhãn PHASE_LABELS);
  phòng thủ `Pipeline.approve`: máy (≠ user) duyệt nháp 2 bậc → False, job về pending_review, diag `draft_needs_person`;
  `core/qc_scene.py` chữ kết quả "chờ người duyệt (nháp)". Test: `ChainFixS1Tests::test_video_phase_never_approves_draft_as_ai`.
- **C3** `core/pipeline.py` `FINAL_HOLD = "final_hold"`; runner (`VideoRunner._hold_prefix` → `quality_tier.hold_prefix`) fail bản cao chờ
  người bằng `final_hold:` (chỉ giữ `stale_input` khi đầu vào của nháp đã duyệt thật sự đổi); `quality_tier.final_hold_note` nhận cả
  ghi chú cũ `stale_input: bản cao bị chặn: cần xác nhận…`; `batch.input_failures`/`provider_failures` bỏ qua; `Pipeline.retry` từ chối
  gửi lại y nguyên; thẻ Bước 4 ghi "⏸ Bản cao chờ bạn xác nhận…". Test: `test_requeue_input_failures_skips_final_needing_confirm`,
  `test_old_stale_input_note_of_a_final_needing_confirm_is_not_requeued`, `test_a_final_of_a_changed_draft_input_stays_stale_input`.
- **C7+U2** `core/runner.held_reason()` (WAIT_REASONS, rồi diag `HOLD_CODES` gần nhất) → caption "⏸ …" trên thẻ Bước 4 khi `queued`;
  `core/inbox.py` `_video_waits`: clip bị giữ (video_pregen_hold / final_wait — Tổ rà soát đã có dòng riêng), "Bản cao chờ bạn xác nhận"
  (không còn tính vào "Lỗi gen"), "N nháp đã duyệt chờ gen bản cao". Test: `test_queued_video_shows_wait_reason`,
  `test_inbox_lists_drafts_waiting_for_final_and_held_clips`.
- **V6** `Pipeline.apply_qc`: bản cao (final, hoặc direct có draft_job_id) dưới ngưỡng → `_hold` (needs_review), không autofix/không
  reject/không job con; ghi "nháp #N đã có cùng lỗi (…)" / "nháp #N không có lỗi này…: bản cao lệch nháp?" / "chưa có điểm QC để so".
  Test: `test_final_below_threshold_never_autofixes`, `test_final_far_below_the_floor_is_not_rejected_either`;
  `tests/test_qc_draft_context.py` cập nhật: test cũ khẳng định final auto_fix → tách `test_direct_keeps_the_old_automatic_redo` +
  `test_final_is_never_auto_fixed` (đổi hành vi có chủ đích theo V6, không nới).
- **U4** dòng kế hoạch model trên thẻ → "🎛 Lần gen tới: …"; dòng meta clip → "clip hiện tại: <model>" (`video_ui.meta_line(current=)`).
  Pill "Cao luôn ✓": `card_block` luôn vẽ STATE_PILL; trên bản sao không hiện vì U5 (đo không được → state `final_review`) — U5 sửa gốc.
  Test: `test_card_meta_line_says_the_current_clip_model`.
- **U5** `core/final_cut.measured_size` + `quality_tier.draft_seconds`: đường tương đối theo cwd trước rồi gốc repo.
  Test: `test_measured_size_tries_the_working_folder_first`.

Chạy: 23 file test liên quan — 448 passed, 2 skipped (không chạy cả bộ).

## Việc mở / cần người quyết
- **Bước 3 nhãn model (U4)** "Kling 3.0 Omni · pro" vs thẻ Bước 4: `dashboard/steps/step3.py` thuộc vùng S4 — chưa đổi; nên ghi "lần gen tới" ở đó.
- **QC cảnh (`core/qc_scene.py` verdict "fix")** vẫn `p.reject(ai_agent)` cả bản cao → tạo job con final (cùng gốc V6 ở đường khác). Chưa sửa
  (ngoài phạm vi 539-546; nên chặn trong `Pipeline.reject` khi tier final + ai_agent, cần rà kỹ vì nhiều đường gọi reject).
- `_approve_held` (người bấm "Tiếp tục" ở chờ "clips") vẫn duyệt mọi clip chờ — kể cả nháp — với tư cách `user` (hành vi cũ "người đã xem").
- Rủi ro nhỏ C1: người đã CHỌN tay bản cao cũ (takes.choose) rồi duyệt nháp mới hơn → shot về `draft_ok` và bản dựng gắn `_DRAFT` dù clip
  đang dùng là bản cao cũ (chỉ cảnh báo, không chặn).
- `held_reason` khi runner khởi động lại đọc diag gần nhất (ghi "(lần giữ gần nhất)") — có thể đã hết giữ mà job còn chờ lượt.

## Bước kế
- Phiên chính gộp nhánh, chạy cả bộ test một lần ở bước gộp (S3 sau S1 vì cùng `core/runner.py`).

## Vòng sửa sau rà (13/10, `docs/handoff/RA_S1_S2_2026-10-13.md` mục 10–14)
- **10** `core/autopilot.py` `_approve_held`: "Tiếp tục" ở chờ "clips" bỏ qua job `quality_tier='draft'` khi cờ two_tier_quality bật
  (nháp chỉ người ✔ trên thẻ). Test `ReviewRoundS1Tests::test_continue_after_clips_wait_never_approves_a_draft`.
- **11** `_drafts_waiting`: tính theo shot, chỉ shot có `quality_tier.state()=='draft_review'` (nháp cũ còn succeeded sau nháp mới đã
  duyệt không giữ chạy mãi). Test `…test_drafts_waiting_ignores_an_old_draft_after_a_newer_approved_one`.
- **12** `Pipeline.reject`: máy (ai_agent) loại bản cao từ nháp (`_final_from_draft`) + respawn → `_hold_final` (pending_review,
  escalated, ghi lý do), không job con. `qc_scene.apply` ghi "giữ cho người (không tự gen lại…)". Người loại vẫn sinh job con.
  Test `…test_scene_qc_fix_on_a_final_holds_instead_of_a_paid_child`, `…test_a_person_rejecting_a_final_still_gets_a_new_take`;
  `RetryCapTests::test_final_is_redone_at_most_once` → `test_final_is_never_redone_by_the_machine_only_by_the_person` (đổi có chủ đích).
- **13** chỉ kiểm: `VideoRunner._hold_prefix` trả `final_hold` chỉ khi lý do bắt đầu "bản cao bị chặn" → ĐỎ V4 (S2) trên bản cao vẫn ra
  `stale_input`. Hết khi S2 bỏ ĐỎ V4 (mục 1); nếu S2 giữ ĐỎ thì phải sửa ở đây.
- **14** `core/pipeline.py`: FINAL_HOLD dời xuống sau docstring của MISSING_INPUT.
- Chạy: 1059 passed, 4 skipped (các file khu vực liên quan + test chậm của related_areas).
