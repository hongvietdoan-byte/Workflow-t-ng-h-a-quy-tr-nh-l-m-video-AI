# HANDOFF — tốc độ đọc giọng (14/10, #31 tập 2: lời dẫn 1,2)

Nhánh: worktree-agent-a01b0da03d90db683 (nền origin/claude/tap2-fixes @ 30182415). Chưa push.

## Xong
- `core/voice.py`: `SPEED_RANGE` 0,7–1,2, `clamp_speed` (rỗng/1,0 → không lưu; không phải số → bỏ + cảnh báo; ngoài khoảng → kẹp + cảnh báo),
  `profile_speed`, `set_profile` giữ `speed` riêng (không cần pitch), trả danh sách cảnh báo + ghi diag `warn` stage `voice` mã
  `voice_speed_clamped`. Hồ sơ KHÔNG có khóa `speed` → giữ tốc độ đã lưu (luật gắn giọng / Claude chọn giọng / lưu lại không làm mất);
  khóa `speed` = None/1,0 → xóa. Biến thể chỉ có speed không còn bị mất (trước chỉ giữ khi có pitch).
- `voice.line_params`: speed = pace câu (cờ voice_direction) × speed biến thể × speed hồ sơ, kẹp 0,7–1,2. Hồ sơ không speed → y hệt cũ.
- Khóa cache câu: mục âm thanh ghi `profile_speed`; `generate` coi câu CŨ khi tốc độ hồ sơ khác. `status()["speed_changed"]` chỉ hiển thị,
  không tính vào `missing` (autopilot không tự trả tiền đọc lại). Bước 3 hiện cảnh báo + nút 🎙 Tạo giọng đếm cả câu đổi tốc độ.
- `voice.preview(speed=)` + `voice_preview_row`: câu mẫu đọc ở tốc độ hồ sơ; mẫu khác tốc độ không bị hiện nhầm.
- Character Bible (`step1_characters.character_detail_panel`): ô "Tốc độ đọc" 0,7–1,2 bước 0,05 mặc định 1,0 → `saved_profile(speed=)`.
- LỜI DẪN: là một dòng `characters` như nhân vật khác (`voice.profiles` map theo tên IN HOA) → đặt tốc độ ở ô của LỜI DẪN.
- Test: `tests/test_voice_speed.py` (13 test, đỏ trên mã nền → xanh), khai ở `devsys/areas.json` khu step3.
  Chạy gộp 17 file: 314 passed.

## Dở / bước kế
- Rà khâu liên quan (CLAUDE.md quy ước 7) chưa giao agent riêng — phiên chính giao đề bài dưới cho agent rà trước khi gộp.
- Cần thử thật 1 câu TTS ở 1,2 (eleven_v3: playground nói speed không áp cho v3 — "chưa thử thật"); phiên chính hỏi giá người dùng.
- Rủi ro: autopilot gọi `voice.generate` khi CÓ câu khác thiếu → lúc đó câu đổi tốc độ cũng được đọc lại (giống hành vi đổi giọng hiện nay).
  Khớp môi (lipsync) dùng file câu cũ: đọc lại đổi độ dài → shot khớp môi cần làm lại như khi đổi giọng.

## `py tools/related_areas.py core/voice.py core/voice_casting.py dashboard/steps/step1_characters.py dashboard/steps/step3.py`
- Khu chứa: step3 (voice.py, voice_casting.py, step3.py); step1 (step1_characters.py).
- Khu gọi tới: step2 (animatic.py, runner.py), autopilot (autopilot.py), step4 (claude_tasks.py, runner.py), step5 (audio_lib.py → voice_casting;
  delivery.py, subtitles.py), lipsync (dialogue_take.py, lipsync.py), budget (project_budget.py), core_infra (runner.py),
  dashboard_ui (common.py, next_step.py).
- Dùng chung cờ: assets, autopilot, knowledge, plates3d, step2, step4, step5.
- Test chậm ở bước gộp: test_editor_apply, test_editor_review, test_rough_cut, test_ui_v2_acceptance.
