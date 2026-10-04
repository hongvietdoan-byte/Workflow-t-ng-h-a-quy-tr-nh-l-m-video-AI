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
4. Trần ngày (mục 3.1): `perf.sends_today` = dòng `usage_events` hôm nay (UTC), kind image/video, provider không `mock%`, mọi dự án/nút;
   `autopilot._daily_cap(p, ctx)` = sends_today + job đang `queued` của runner thật ≥ trần → dừng; `_create_job` kiểm + tạo job dưới
   `SPEND_LOCK` (commit trước khi chờ khóa — tránh khóa chết SQLite, đã gặp ở QueueTests). Chỉ đường autopilot; `AUTOPILOT_DAILY_JOBS=0` = tắt.
   `perf.jobs_today` giữ làm số phụ; `snapshot` thêm `sends_today`, cảnh báo dùng lượt gửi; sửa luôn so sánh giờ `usage_today`
   (trước so ISO 'T…+00:00' với 'YYYY-MM-DD HH:MM:SS' → dòng hôm nay bị loại). Nhãn: admin "Lượt gửi thật hôm nay" (2 chỗ + chú thích),
   header.py:548. `tests/test_dashboard.py:777` đổi nhãn theo. DailyCapTests: test cũ dùng provider không tên mock (nghĩa đổi: mock không tính) + 4 test mới.

## Rủi ro cần rà
- `superseded` là trạng thái mới trong manifest âm thanh: chỗ nào đếm dòng tts theo state có thể thấy dòng "biến mất" trong lúc chờ bản mới.
- `budget` code giờ dừng autopilot (trước chỉ khi câu chứa "hết ngân sách claude").
- Hạn chờ khớp môi 60 phút là ước lượng (chưa chạy sync.so thật).
