# HANDOFF — C-M29 (V3.1 M2.9 lời dẫn ngoài khớp môi), nhánh cloud/v31-m29

## Đã xong
- Cờ `narration_offscreen`, `fit_durations_review` (core/features.py, verified False, TẮT; golden package_inputs 2 khối; areas.json flags).
- `lipsync.talking(data)` + `offscreen_on()` + `forget_skipped`; G53 seedance_refs, G16 claude_tasks._measure_clip, G17 quality_tier.hard_signs,
  G15 lipsync.mark(method="skip") + runner gọi forget_skipped (đơn shot + nhóm take). test_narration_regression: tham số cờ TẮT (21 xfail strict giữ)
  / BẬT (hết xfail). tests/test_v31_m29_narration.py (AST + forget_skipped).

## Đang dở / bước kế
- G14 `voice.plan_fit` / `apply_fit` (cờ fit_durations_review) + nút ⏱ duyệt.
- A11 thông điệp end_frames theo lý do (bỏ "ném keo" viết cứng). A12 kiểm director_byd.settle với ClaudeCliClient.
- related_areas + báo cáo docs/RA_CLOUD_M29_2026-10-21.md; xóa HANDOFF.md ở commit cuối.
