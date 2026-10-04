# HANDOFF — nhánh s14-b1b-voice-lipsync-autopilot (S14.3 B1b + S14.1 A1b)

Gốc: 7bca2b9 (Gộp S14.1 A1a). Không push, không merge main, không sửa TODO.md.

## Đã làm
1. Lipsync qua cổng tiền (A1b): `core/lipsync.py` `post_tick` dùng `spend_gate.spend(kind video, budget_stage videos, ledger_stage lipsync)`;
   model không có giá ở dự án khóa → từ chối TRƯỚC khi gửi (không còn dòng 'videos' chưa giá chặn cả khâu); dự án tạm dừng → `PipelinePaused`;
   `mark(running, sent_at)` ngay sau `submit`, trước dòng sổ; hạn chờ `RUNNING_LIMIT_S` (env `LIPSYNC_RUNNING_LIMIT_MIN`, mặc định 60) → failed + diag `lipsync_timeout`.
   Test: `tests/test_lipsync_gate.py` (mới, khai ở areas.json khu khớp môi); `test_trial_fixes` đổi tên provider khỏi `mock*` ở 1 test (cổng coi mock là miễn phí).
2. T7 `voice_check.redo`: bộ đếm `redos` riêng theo dòng (`MAX_REDOS = 2` theo luật 6, theo (văn bản, giọng) qua `redo_key`); dòng cũ chuyển
   `state="superseded"` (ẩn khỏi timeline: `voice._line_items` bỏ qua) tới khi bản mới xong — `settle_redos` (gọi ở redo, check_project,
   `voice.generate(settle=True)`) xóa bản cũ khi bản mới succeeded, trả bản cũ (+ `redo_error`) khi bản mới lỗi / bị từ chối / không gửi.
   Vượt trần → `refused` (tiếng Việt). Nút Bước 3 (`tts_redo_{pid}`, giữ khóa) qua `confirm_all` + "đã dùng X/Y lượt".
   Test: `tests/test_audio_g2.py::VoiceRedoTests` (3 test).
3. Autopilot: `_setcheck_block` dùng `spend_gate.reason` (trần thử + ngân sách dự án khóa) → bỏ khỏi PENDING_B của test quét.
   `tick` → `_tick`; mọi lần ghi trạng thái của tick qua `_tick_set` (UPDATE … WHERE autopilot_state='running' — stop()/reset() của người
   không bị ghi đè bởi _Wait/_Stop/lỗi/ghi chú tiến độ/DONE); `_still_running` trước `submit_pending` (ảnh, video), `lipsync.post_tick`,
   `delivery.deliver`. `PipelinePaused` bắt trong tick → ghi chú "Đang tạm dừng — …", trạng thái RUNNING.
   `_stop_if_claude_blocked` đọc `.code` (`llm_runner.FailText`/`fail_text`; producers: run_qc_batch, qc_video_batch, qc_scene, qc_agent,
   qc_team); CLI: `llm_runner.cli_error_code` cho mã `usage_limit`/`auth` ngay nơi sinh lỗi. Mã dừng: auth/config, usage_limit/rate_limit,
   out_of_credit, budget (MỚI: trước đây budget chỉ dừng nếu câu chứa "hết ngân sách claude").
   Test: `tests/test_autopilot.py::SafetyTests` (+7), `tests/test_v3.py` sửa 1 test sang FailText có mã.
