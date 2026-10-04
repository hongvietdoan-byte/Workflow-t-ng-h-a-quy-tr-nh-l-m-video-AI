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

## Sửa sau rà soát (04/10)
- Test quét: lời gửi phải nằm TRONG thân khối `with spend_gate.spend(...)` (nút ast.With); bỏ quy tắc cùng hàm/cùng class (chỉ
  danh sách trắng theo tên hàm); test tự kiểm `test_the_rule_catches_a_send_outside_the_with_block`.
- experiments ghi sổ `ledger_stage="kling_multishot"`; `budget.check_image(count>1)` báo "N ảnh ≈ $…".

## CẢNH BÁO cho A1b
- `core/lipsync.py` `post_tick` (~241-257) chỉ kiểm `check_video`. Khi `SYNC_MODEL` không có giá (vd. lipsync-2), một lượt gửi ở
  dự án khóa ghi dòng 'videos' CHƯA CÓ GIÁ → `project_budget.check` (T6) chặn CẢ khâu video của dự án. A1b phải đưa lipsync qua
  `spend_gate.spend` (giá None → từ chối TRƯỚC khi gửi, không ghi dòng không giá).

## Còn lại (ngoài phạm vi A1a — danh sách CHỜ CHUYỂN trong test quét)
- lipsync `post_tick` (A1b), autopilot `_setcheck_block` (A1b), runner `_Runner._submit_pending` (giữ mẫu cũ, danh sách trắng),
  storyboard_frames `run` (submit_storyboard_frame), previz `_deepix_cutout`.
- Trần job/ngày theo lượt gửi (perf.py) — nhánh khác.

## Bước kế
- Người điều phối rà + gộp; chạy cả bộ test sau gộp.
