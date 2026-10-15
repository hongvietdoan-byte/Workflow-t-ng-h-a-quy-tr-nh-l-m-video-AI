# HANDOFF — giây đọc theo (giọng, tốc độ) + BREATH + lưới an toàn sau TTS (15/10, #31)

Nhánh: `worktree-agent-afae68763012abf21` (đã merge `claude/p31-truoc-buoc1`). 0 USD — không gọi TTS/Claude/API. Không sửa TODO.md, không push,
không ghi CSDL chính (đo bằng `?mode=ro` + đọc `data/projects/*/audio_assets/assets.json` ở máy chính).

## 1. Số đo thật (86 câu TTS, ≥ 3 âm tiết, đếm âm tiết = `pacing.syllables`)
Âm tiết/giây theo độ dài FILE (khâu dựng đặt cả file). Tốc độ gửi = pace của delivery (slow 0,9 / fast 1,1, cờ voice_direction) × profile_speed
(chưa câu nào có profile_speed ≠ 1).

| giọng (model) | tốc độ | n | p50 | p10 |
|---|---|---|---|---|
| 72 "voice boy ingame VN" (eleven_v3, LỜI DẪN #27) | 0,9 / 1,0 / 1,1 | 3 / 11 / 2 | 4,19 / 4,35 / 3,85 | — |
| 72 gộp | | 16 | 4,24 | 3,62 |
| 70 KELLY (eleven_v3) | 0,9 / 1,0 | 7 / 3 | 2,84 / 4,10 | gộp 1,65 |
| 69 KENTA (eleven_v3) | 0,9 / 1,1 | 5 / 2 | 3,40 / 4,01 | gộp 3,17 |
| 30020 / 30007 / 30003 (multilingual_v2) | 1,0 | 18 / 15 / 6 | 2,96 / 2,75 / 2,55 | 2,33 / 2,32 / 2,26 |
| tất cả | | 86 | 2,98 | 2,33 |

- **eleven_v3 có theo speed không?** Không thấy: giọng 72 ở 1,1 còn CHẬM hơn 1,0 (3,85 vs 4,35); KELLY 0,9 chậm hơn nhưng các câu đó có
  pause/tag cảm xúc (nhiễu). Không có mẫu nào ở 1,2. Trang thử ElevenLabs cũng ghi speed không áp cho v3. → `speed_follows.eleven_v3 = false`,
  hệ số tốc độ = 1,0 (ước như cũ). **Đề xuất lượt TTS thử (người dùng duyệt tiền riêng):** giọng 72, cùng 5 câu lời dẫn #31, đọc ở 1,0 và
  1,2 (10 lượt TTS) → `py tools/measure_speech_rate.py --write data/speech_rates.json`; nếu 1,2 ngắn hơn rõ thì đặt `speed_follows.eleven_v3 = true`.
- Công thức cũ (÷ 3,5 + 0,5) ước THIẾU > 0,5 s ở 15/86 câu (giọng chậm: multilingual_v2, KELLY có pause).
- Biên an toàn: dùng **p10 âm tiết/giây** (= p90 giây/âm tiết). (p90 âm tiết/giây như đề bài gợi ý sẽ ước NGẮN hơn audio.) Và chỉ dùng khi chậm
  hơn RATE (min(RATE, p10), n ≥ 8) → bảng giọng chỉ làm ước tính dài ra. Giọng 72 p10 3,62 > 3,5 → không đổi.

## 2. Sửa
- `core/dialogue.py`: MỘT chỗ ước giây — `line_seconds(said, voice)`, `voice_rate`, `speed_factor`, `speech_ctx(conn, pid)`, `voice_of`,
  `needed_seconds(rows, ctx, gap)`, `scene_seconds(rows, ctx)`; bảng `data/speech_rates.json`.
- Dùng ở: prompts.duration_block / intent_frame_block / build_motion_bundle (dialogue_min_sec), director_report.report (ctx mới, Bước 1 truyền),
  shot_normalize.normalize/_fit_speech (ctx; llm_io._normalized + director_two_pass.check_scene truyền), pacing.check_plan, dialogue.check, video_pregen.
- Tốc độ: hồ sơ giọng (riêng × biến thể) → chưa có Bible: `projects.narration_speed` (cột mới V2_COLUMNS, ô "🎙 Tốc độ đọc lời dẫn" cạnh
  "⏱ Nhịp phim", mặc định trống = 1,0); `voice.set_profile` mang giá trị vào hồ sơ người dẫn (speaker_lint.is_narrator) khi hồ sơ chưa có speed.
- BREATH: một BREATH mỗi LƯỢT LỜI (câu liền nhau cùng người nói) + khoảng thật giữa câu (trong shot `LINE_GAP` = voice.GAP 0,15 — khâu dựng
  đặt câu trong một clip với GAP kể cả nhịp nhanh; tổng cảnh: nhịp nhanh 0,2 = pacing.FAST_LINE_GAP).
- Số đếm đọc thành chữ (2025 = 7 âm tiết; trước = 1) — ước dài ra ở câu có số.

## 3. Prompt Đạo diễn (normal, không đặt tốc độ) — thay đổi so với trước
Chỉ phần BREATH: dòng "Shot có thoại ... + 0.5 giây cho câu của nó" thêm "(nhiều câu trong một shot: + 0.15 giây giữa hai câu)"; dòng Tầng A
"(mỗi câu một hơi, ≈ ...)" → "(≈ số âm tiết ÷ 3.5; + 0.5 s mỗi lượt lời, + 0.15 s giữa hai câu liền nhau của cùng người nói)"; số giây cảnh có
câu liền nhau cùng người nói giảm. Hai ngoại lệ ngoài BREATH: câu có chữ số (đếm như đọc) và dự án ĐÃ có Bible với giọng đo chậm hơn 3,5 (giọng 70).
Nhịp nhanh: 0,2 thay 0,15 trong dòng Tầng A (test_pacing_fast cập nhật đúng chỗ này).

## 4. Lưới an toàn sau TTS — lỗ tìm thấy + sửa
1. Kling multishot gửi giây shot theo `duration_s` của Đạo diễn, bỏ qua giây đã kéo theo giọng thật (fit_durations) → shot ngắn hơn câu.
   Sửa: `runner._billed_seconds` = max(giây Đạo diễn, giây motion đã kéo) ở 3 chỗ (multi_prompt, sent, tổng clip).
2. Giọng thật dài hơn clip dài nhất của model: fit_durations kẹp im lặng. Sửa: `voice.over_model_max` + autopilot diag ĐỎ + chờ
   (`voice_over_max`; "Tiếp tục" = chấp nhận).
3. video_pregen (cờ video_pregen) chỉ so ước tính khi không gửi kèm audio. Sửa: có giọng thật → so độ dài thật (đầu clip + câu) → ĐỎ nếu dài hơn.
Còn lại (chưa sửa, ghi rủi ro): nhóm Seedance tham chiếu kẹp 15 s (`seedance_refs.seconds`) khi tổng giây shot đã kéo > 15; Kling multishot
tổng > 15 sau khi kéo → nhà cung cấp có thể từ chối (lỗi hiện rõ, không cắt im lặng). Nhóm do `seedance_refs.groups`/`shots.multishot_groups`
vẫn chia theo giây Đạo diễn.

## 5. #31 (8 cảnh, lời dẫn tách 28 câu, nhịp nhanh, chưa Bible)
Tổng giây nói ước: trước 131,8 s → sau 126,4 s (−5,4 s, toàn bộ do BREATH; +0,9 s cảnh 8 vì số đọc thành chữ). Giọng 72 thật đọc trung vị 4,24
âm tiết/s → audio thật ~98 s (p10: ~115 s): phần "dư ~20 s" là do 3,5 âm tiết/s chậm hơn giọng 72, KHÔNG do tốc độ 1,2. Rút tiếp chỉ an toàn khi
đo audio thật trước gen video (audio_first: TTS lời dẫn trước, shot theo giây thật).

## Test
Đỏ trước (code cũ, WIP tạm rồi khôi phục): 17 failed + 5 errors ở test_speech_time + test_video_pregen::Duration (giọng thật) + test_pacing_fast
(tốc độ). Xanh sau: lần 1 1164 passed/1 failed (test_pacing_fast "fast chỉ thêm block" — cập nhật cho khoảng 0,2), lần 2 115 passed.
Test đổi kỳ vọng: test_pacing_fast `speech_s` 1,9 → 2,3 (giả thuyết cũ v3 theo 1,2; nay đo là không) — trường hợp model theo speed có test mới.

## related_areas (py tools/related_areas.py <file đổi>)
Khu vực chứa file đổi: step1, step5 (pacing), step3 (voice), step4 (runner, video_pregen), step2 (runner), core_infra (db, pipeline, runner), autopilot.
Gọi tới module đổi: assets (dialogue/prompts/runner), lipsync (dialogue_take/lipsync → voice/dialogue), dashboard_ui (common → autopilot/db/
dialogue/llm_io), knowledge (prompts), plates3d (llm_io), budget (cost/project_budget → voice/pipeline/llm_io), diag (capacity/inbox → autopilot/runner).
Cờ dùng chung: assets, knowledge, lipsync, plates3d. Test chậm bắt buộc ở bước gộp: test_access, test_editor_apply, test_editor_review,
test_rough_cut, test_ui_v2_acceptance. → Cần agent rà (quy ước 7) trước khi gộp main.

## Tự kiểm
- Test nới để che lỗi: 2 test cũ đổi kỳ vọng, cả hai đúng hành vi mới có chủ đích (ghi ở trên), không nới chung.
- Bật mặc định đổi hành vi người không dùng: BREATH/khoảng giữa câu + đếm số áp cho mọi dự án (chủ đích); autopilot dừng mới khi giọng thật
  dài hơn clip tối đa model (trước: cắt im lặng); multishot gửi giây đã kéo (có thể đắt hơn vài giây).
- Đường dẫn tương đối: `data/speech_rates.json` theo `__file__`. Lời gọi tốn tiền: không.
