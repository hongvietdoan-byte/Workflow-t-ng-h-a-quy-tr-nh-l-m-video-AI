# HANDOFF — nhánh s14-b1b-voice-lipsync-autopilot (S14.3 B1b + S14.1 A1b)

Gốc: 7bca2b9 (Gộp S14.1 A1a). Không push, không merge main, không sửa TODO.md.

## Đã làm
1. Lipsync qua cổng tiền (A1b): `core/lipsync.py` `post_tick` dùng `spend_gate.spend(kind video, budget_stage videos, ledger_stage lipsync)`;
   model không có giá ở dự án khóa → từ chối TRƯỚC khi gửi (không còn dòng 'videos' chưa giá chặn cả khâu); dự án tạm dừng → `PipelinePaused`;
   `mark(running, sent_at)` ngay sau `submit`, trước dòng sổ; hạn chờ `RUNNING_LIMIT_S` (env `LIPSYNC_RUNNING_LIMIT_MIN`, mặc định 60) → failed + diag `lipsync_timeout`.
   Test: `tests/test_lipsync_gate.py` (mới, khai ở areas.json khu khớp môi); `test_trial_fixes` đổi tên provider khỏi `mock*` ở 1 test (cổng coi mock là miễn phí).
