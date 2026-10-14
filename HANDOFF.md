# HANDOFF — nhịp nhanh, ít khoảng lặng (người dùng 14/10, thử cho tập 2 #31)

Nhánh: `worktree-agent-aab8abc49ae455096` (nền `origin/claude/tap2-fixes` 30182415). Chưa push. 0 USD (không gọi API).

## Đã làm
1. **Thiết lập dự án** `projects.pacing` (cột mới `core/db.py` V2_COLUMNS; NULL/'normal' = y cũ, 'fast'); `set_project_field` cho phép
   `pacing`. Chọn ở Bước 1 · 📐 Định dạng: radio "⏱ Nhịp phim" (`dashboard/steps/step1_prep.py` `pacing_control`). KHÔNG kế thừa: không có
   trong `project_defaults.INHERIT` (ghi chú tại đó) → dự án mới về Bình thường. Nhân bản dự án (`compare.clone_project`) chép mọi cột nên
   bản sao giữ 'fast' — cố ý (nhân bản = cùng điểm xuất phát), báo nếu muốn khác.
2. **Prompt**: tri thức `knowledge/craft/nhip_nhanh.md` (mục `## Đạo diễn`, `## Biên kịch`, viết thành cách nghĩ có lý do + căn cứ Kelly /
   SHORT_FORM / editing.md). `pacing.director_block` chèn vào `build_director_bundle` (sau khối thời lượng), `build_intent_bundle` (Tầng A),
   `dp_common` (Tầng B); `idea_to_script.build_prompt` thêm `screenwriter_block`. normal → "" (lọc bởi `if x`) → prompt y hệt (test
   so NULL == 'normal' và fast = normal + đúng một khối). Thiếu mục trong tệp tri thức khi fast → ValueError (không im lặng).
3. **Kiểm sau Đạo diễn** `pacing.check_plan` (0 USD): mỗi cảnh, giây đọc lời = âm tiết ÷ (`dialogue.RATE` 3,5 × tốc độ giọng) — tốc độ đọc
   mềm `profile.speed`, rồi `variant.speed`, mặc định 1,0 — so tổng `duration_s`; không lời > 1 s hoặc shot dài hơn lời > 1 s → diag VÀNG
   `pacing_gap` có số liệu. Gọi ở `llm_runner._pacing_check` sau `run_director` (một lượt + hai tầng) và `run_director_scene` (cả nhánh
   replan hai tầng). Lỗi đo → diag `pacing_check_error`, không làm hỏng kế hoạch đã trả tiền. Không chặn gen.
4. **Khâu dựng** (khâu thật = `delivery.render` → `voice.place_on_timeline`; `tools/experiments/p27_final_mix.py` là script riêng #27, KHÔNG sửa):
   - `pacing.tighten`: shot có lời TTS mà sau câu cuối (LEAD + câu + GAP) còn lặng > 0,5 s → cắt đuôi còn 0,5 s (≥ 1,0 s), qua `edits["fit"]`
     → `_fit_edits` (bản sao, clip gốc giữ). Bỏ qua: shot không lời (nhịp hình của Đạo diễn), shot khớp môi, shot người dùng tự sửa
     (fit/head/cut). diag info `pacing_tail_cut` + manifest `pacing_fast`.
   - `pacing.line_start` trong `place_on_timeline` và `timeline_extras`: câu đầu của shot vào ngay sau câu trước + 0,2 s (≤ 0,25 s), gối
     qua cú cắt tối đa 0,5 s; câu đầu phim, shot khớp môi giữ y cũ. Áp cho MỌI câu TTS (lời dẫn và thoại), không riêng nhãn LỜI DẪN.

## Test
`tests/test_pacing_fast.py` (11 test): đỏ trước (bản HEAD gốc: lỗi thu thập — chưa có `core.pacing`) → xanh. Lần chạy 1: 506 pass + 1 đỏ
(test tự đếm sai âm tiết "Bốn đối thủ ập tới từ bốn phía" = 8, không phải 7 — sửa số mong đợi, không nới); lần 2: 84 pass
(pacing + animatic + two_pass + subtitles + project_defaults + editor_cuts). Lần 1 gồm cả editor_apply / rough_cut (test chậm), c5_*, lipsync,
director_*, idea_to_script, s1443_screenwriter, change_review, voice_casting, tap2.

## Chưa làm / rủi ro
- **Chưa thử thật** (CHUAN luật 8): chưa dựng lại #31 ở chế độ fast — phải bật 'fast' trên #31, chạy lại Đạo diễn (tốn tiền, người quyết)
  hoặc chỉ ghép lại (0 USD) để nghe phần dựng.
- Animatic (`core/animatic.voice_extras`) vẫn đặt lời kiểu cũ (LEAD đầu mỗi shot, giây của Đạo diễn) — bản xem trước, chưa theo fast.
- `lipsync.line_offsets` / dialogue_take giữ giây cố định — đúng ý (khớp môi không được dời).
- Gối tiếng 0,5 s trước cú cắt ở MỌI shot có lời có thể nghe dồn; nếu người dùng muốn câu luôn bắt đầu SAU cú cắt thì hạ `FAST_J_MAX` về 0
  (khi đó khoảng giữa hai câu qua cú cắt = lặng đuôi ≤ 0,5 s + LEAD, > 0,25 s).
- `voice.set_profile` hiện chưa lưu `speed` gốc (nhánh khác đang thêm) — `voice_speed` đọc mềm, chưa có thì 1,0 (ước tính dài hơn thật).
- Chưa có agent rà khâu liên quan (quy ước 7) — đề bài dưới đây giao phiên chính.

## py tools/related_areas.py (file đổi)
core/pacing.py core/prompts.py core/voice.py core/delivery.py core/llm_runner.py core/idea_to_script.py core/db.py core/pipeline.py
core/project_defaults.py dashboard/steps/step1_prep.py
- Khu vực chứa: step1 (idea_to_script, llm_runner, pacing, prompts, step1_prep), step5 (delivery, pacing), step3 (llm_runner,
  project_defaults, voice), core_infra (db, pipeline).
- Khu vực gọi tới: assets, step4 (claude_tasks, compare), knowledge, step2 (animatic, autoqc, costume), dashboard_ui, autopilot, lipsync
  (dialogue_take, lipsync), budget (cost, project_budget, project_reserve), plates3d (camera_plan, director_blockout).
- Test chậm bắt buộc ở bước gộp: test_editor_apply, test_editor_review, test_rough_cut, test_ui_v2_acceptance.
- `devsys/areas.json`: thêm `core/pacing.py` vào step1 + step5 (không tăng version).
