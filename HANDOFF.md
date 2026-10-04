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

## Test
- `tests/test_prompt_rewrite.py` (20), `tests/test_ui_prompt_versions.py` (2).

## Còn mở / rủi ro
- Chưa chạy thật Claude (cờ verified False). Gọi Claude đồng bộ trong nút Loại/Vẽ lại (chờ vài giây).
- Đổi `image_prompt` / `motion_prompt` làm lineage coi bản DUYỆT cũ hơn của cùng shot là "cũ" (hiếm: chỉ khi còn bản duyệt cũ hơn bản vừa loại).
- `p.retry(by_user=True, fix=…)` (job lỗi + câu sửa) chưa gọi rewrite — ngoài phạm vi S14.17.
