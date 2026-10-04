# HANDOFF — nhánh s14-a1a-spend-gate (S14.1 phần A1a)

## Đã xong
- T6: `project_budget.check(usd=None)` từ chối khi dự án khóa; `unpriced_by_stage` (dòng sổ không giá không còn = 0 im lặng);
  runner truyền `None` khi không có giá (ảnh + video). Test: `tests/test_project_budget.py::UnknownPriceTests`.

## Đang dở
- `core/spend_gate.py` + chuyển costume / experiments / scene_establish / end_frames; test quét.

## Bước kế
- Viết test đỏ cho costume + end_frames, rồi cổng.
