# HANDOFF — nhánh s14-a1a-spend-gate (S14.1 phần A1a)

## Đã xong
- T6: `project_budget.check(usd=None)` từ chối khi dự án khóa (chỉ vào ⚙ → 💵 Tiền → 💲 Bảng giá); `unpriced_by_stage` — dòng sổ
  không giá (sau mốc reset) làm khâu đó bị từ chối, không còn = 0 im lặng; runner truyền `None` khi không có giá (ảnh + video).
- `core/spend_gate.py`: `spend(...)` giữ `SPEND_LOCK`, kiểm tạm dừng → `slot.over`/`slot.paused`, `check_image(count=)` /
  `check_video` / `check_audio`, `project_budget.check(budget_stage, giá|None)`; `slot.send` (out_of_credit → `budget.halt`),
  `slot.record` (ghi sổ ngay, nhãn `ledger_stage`), lượt gửi quên ghi được ghi khi ra khỏi khối; `SpendRefused(ValueError)`.
- Chuyển sang cổng: costume (trước bỏ qua mọi cổng), experiments, scene_establish, end_frames.
- `budget.check_image` thêm tham số `count=1` (bộ 2 ảnh kiểm trọn trước khi gửi ảnh đầu).
- Test: `tests/test_spend_gate.py` (đỏ→xanh), `tests/test_project_budget.py::UnknownPriceTests`, `tests/test_spend_gate_scan.py`.
- `devsys/areas.json` khu vực budget: thêm `core/spend_gate.py` + 2 file test (không tăng version).

## Còn lại (ngoài phạm vi A1a — danh sách CHỜ CHUYỂN trong test quét)
- lipsync `post_tick` (A1b), autopilot `_setcheck_block` (A1b), runner `_Runner._submit_pending` (giữ mẫu cũ, danh sách trắng),
  storyboard_frames `run` (submit_storyboard_frame), previz `_deepix_cutout`.
- Trần job/ngày theo lượt gửi (perf.py) — nhánh khác.

## Bước kế
- Người điều phối rà + gộp; chạy cả bộ test sau gộp.
