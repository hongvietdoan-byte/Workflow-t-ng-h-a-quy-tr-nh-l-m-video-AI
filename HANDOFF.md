# HANDOFF — S14.3 B1a (vòng đời job trong runner)

Nhánh `s14-b1a-job-lifecycle` (worktree `.claude/worktrees/agent-a7291de6d6974f800`), gốc từ `7bca2b9` (Gộp S14.1 A1a).
Kế hoạch: `docs/KE_HOACH_NANG_CAP_DASHBOARD_2026-10-03.md` mục 3.2 (T2, T3, T9).

## Đã làm
- **T2** `core/runner.py`: 6 chỗ `p.start()` → `_Runner._running()` = `p.transition(job_id, RUNNING)` (không kiểm tạm dừng).
  - Sau `submit`: `UPDATE external_id` + stamp KHÔNG commit rồi `transition` commit cùng lúc (một giao dịch).
  - Nhánh lỗi (stale_input / missing_input / ProviderError): `transition(RUNNING)` rồi `fail` — không thêm `QUEUED→FAILED`.
  - Job bị `cancel_all_active` hủy trong lúc `submit` đang bay (`InvalidTransition`): commit `external_id`, ghi sổ chi,
    `provider.cancel` (lỗi → nêu trong diag), diag error `cancelled_in_flight`; vòng lặp đi tiếp, không ném lỗi ra ngoài.
  - Quy tắc: job `queued` đã có `external_id` → chỉ `transition(RUNNING)` + diag info `already_sent`, không gửi lại; đặt SAU `_wait`/`_blocked`.
  - Tạm dừng giữa lượt gửi: sau ít nhất 1 lần gửi, kiểm `paused` đầu mỗi vòng → dừng gửi tiếp (trước đây `start()` ném lỗi làm việc này).
  - `relink_failed` và follower nhóm multi-shot (`_finish_group`) cũng đi qua `_running` (không còn kẹt queued khi dự án tạm dừng).
- **T3** `core/runner.py`: `cancel_all(p, project_id, video=, image=, actor=)` (hàm module) + `_Runner.cancel_all` (bọc) + `cancel_note(report)`.
  `access.need_edit` trước; giữ `_turn(project_id, 'image_gen')` rồi `'video_gen'` (thứ tự cố định); dedupe theo (type, external_id);
  Deepix (`NO_CANCEL_API`) không gọi hủy, báo "ảnh đã gửi vẫn tính tiền"; lỗi hủy từng task → diag `cancel_failed` + nêu mã trong thông báo;
  runner `None` → đếm `no_provider`, thông báo "chưa hủy ở nhà cung cấp". Không hứa hoàn tiền.
  `dashboard/header.py`: hàm `cancel_everything(p, pid)`; nối vào 2 nút `btn_cancel` và luồng xóa dự án (`proj_del_<pid>`). Không đổi `key=`.
- **T9** `core/composite.py` `composite_video`: kiểm mã thoát writer/reader, BrokenPipe khi ghi, file đầu ra tồn tại & > 0 byte, độ dài
  (≥ 90 % − 0,1 s của min(số khung/fps, độ dài clip xanh)) → `CompositeError`; runner đã giữ clip gốc (os.replace chỉ sau khi trả về) + diag `plate_video`.

## Test (tests/test_job_lifecycle_b1a.py, mới; 0 USD, provider giả)
Đỏ trên code cũ → xanh: paused giữa submit (video + ảnh), hủy giữa submit, queued có external_id, relink_failed khi tạm dừng,
follower nhóm khi tạm dừng, 5 test cancel_all, 2 test UI (btn_cancel, proj_del), 4 test composite (writer≠0, reader≠0, thiếu file, runner giữ clip).
Xanh cả trước/sau (chốt hành vi): gửi lỗi vẫn queued→running→failed; composite chạy tốt vẫn trả về.

## Rủi ro cần rà
- `cancel_all` CHỜ khóa `_turn` (chặn): nếu luồng nền đang poll/tải lâu, nút Hủy trên dashboard đợi tới hết lượt đó.
- Quy tắc `already_sent` nằm sau `_blocked`: job queued có external_id mà `_blocked` trả lý do vẫn bị fail (theo đúng chỉ định kế hoạch).
- Kiểm độ dài T9 dùng `probe_duration` (ffmpeg -i); clip xanh không đọc được độ dài → so với số khung đã ghi.
- Không đụng spend_gate/lipsync/autopilot/voice/perf/syncso; `areas.json` không đổi (không có file mã mới).

## Kết quả test & thử thật
- 859 qua, 2 bỏ qua (59 file test liên quan: mọi file import core.runner + pipeline/access/spend_gate/composite/UI hủy-xóa/test_ui_v2_acceptance).
- **T9 chưa thử thật**: chạy composite_video với ffmpeg thật trên clip xanh 1 s (24 khung, 320x240) quá 7 phút chưa xong (ghép từng khung chậm) nên đã dừng — cần chạy thử 1 clip thật để xác nhận kiểm độ dài không chặn nhầm clip ghép tốt.
