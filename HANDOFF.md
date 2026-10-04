# HANDOFF — S14.17 Đạo diễn viết lại prompt shot trước mỗi lần gen lại

Nhánh `s14-17-director-rewrite` (từ `43788fa`). Không sửa TODO.md, chưa push, chưa merge.

## Đã làm
- `core/prompt_rewrite.py` (mới): `before_retry` (móc của pipeline/regen) → `rewrite_for_retry` gọi Claude khâu `director_rewrite`
  (prompt hệ thống `prompts/26_director_rewrite.md`, JSON `new_prompt/changed/why`), ảnh lỗi (ảnh: result_path; clip: 3 khung qua
  `video_analysis.extract_frames`). Code kiểm sau Claude: `no_minor_age`, `looks.clean_prompt`, không trùng prompt cũ, không thêm nhân vật
  ngoài `characters` của shot. Lưu bảng `prompt_versions` (original/manual/director_rewrite/revert), `revert()`, `live_versions()`,
  `word_diff()`.
- Nối vào: `Pipeline.reject` (thêm `qc=` tùy chọn; QC chạm AUTO_REGEN_LIMIT → không gọi), `reopen_approved`, `regen.regenerate_video`
  (khi có `fix`), `qc_scene.apply` truyền root_cause/problem/fix. Thành công → retry_reason = `pipeline.REWRITE_NOTE` "(vN): ghi chú";
  `runner.model_fix` và `_combine_fix` bỏ qua tiền tố này (không còn "Fix:"). Lỗi bất kỳ → giữ "Fix: …" + diag warn
  `director_rewrite_fallback` (stage image/video).
- Cờ `director_rewrite` (verified False, tắt mặc định); `STAGE_SETTINGS` max_tokens 6000; `cost.LLM_STAGE_TOKENS`; dòng ngân sách
  `claude_director` (tiền tố "director"); `MockLlm` trả lời prompt mới; `delete_project` xóa `prompt_versions`.
- UI v2: `dashboard/design/screens/prompt_versions_ui.py` — mục gập "✏ Prompt đã sửa (vN)" trên thẻ ảnh Storyboard + thẻ clip Video,
  so sánh bôi đỏ/xanh, danh sách thay đổi, nút `pvrevert_<kind>_<scene_id>` "↩ Dùng lại prompt cũ". Khóa widget cũ giữ nguyên.

## Sửa theo phiên rà độc lập (05/10)
1. Claude được gọi khi job CÒN SỐNG (`propose_rewrite`, không ghi DB); `Plan.apply()` ghi prompt ngay trước khi chèn job mới — `reject`,
   `reopen_approved`, `regenerate_video` kiểm quyền/reviewable trước, rồi rewrite, rồi REJECTED. Prompt bị sửa tay trong lúc chờ → giữ bản người.
2. `Pipeline.has_pending_take(scene, kind)`; vòng làm lại bản cũ (`autopilot._images_phase`/`_videos_phase`, `batch.queue_images`/`queue_videos`)
   bỏ qua cảnh đã có job cùng loại queued/running/retryable.
3. Khâu `director_rewrite`: `timeout` 90 s, `retries` 1 (STAGE_SETTINGS mới hỗ trợ 2 khóa này; Claude CLI lấy min); hết giờ → "Fix:" + diag.
   Spinner `prompt_versions_ui.spin()` bọc các nút có thể gọi Đạo diễn (step2, step4, storyboard_cards); nút gen lại clip vì "cũ" không có câu sửa → không bọc.
- (a) "↩ Dùng lại prompt cũ": cảnh báo tốn tiền + ô xác nhận `pvrevack_<kind>_<scene_id>`. (b) `cost.rewrite_estimate` cộng vào
  `estimate_run` (key `rewrite`, max theo số lần gen) và `project_budget.remaining["claude_director"]`. (c) `apply_qc(qc=None)` tự dựng
  root_cause (tiêu chí thấp)/problem/fix cho QC ảnh + QC clip. (d) thư mục tạm khung clip xóa sau lời gọi.

## Test
- `tests/test_prompt_rewrite.py` (31: + ReviewFixes, ReviewMinor, chờ ngắn), `tests/test_ui_prompt_versions.py` (4: + SpinnerScan).

## Còn mở / rủi ro
- Chưa chạy thật Claude (cờ verified False). Nút chờ tối đa ~3 phút khi Claude chậm (90 s × 2).
- "Dùng lại prompt cũ" khi không có lần gen đang chờ vẫn có thể làm bản đã duyệt bị coi là cũ → đã cảnh báo + xác nhận, không chặn.
- `p.retry(by_user=True, fix=…)` (job lỗi + câu sửa) chưa gọi rewrite — ngoài phạm vi S14.17.