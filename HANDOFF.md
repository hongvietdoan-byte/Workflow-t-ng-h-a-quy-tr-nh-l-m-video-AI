# HANDOFF — C-M29 (V3.1 M2.9 lời dẫn ngoài khớp môi), nhánh cloud/v31-m29

## Đã xong
- Cờ `narration_offscreen`, `fit_durations_review` (core/features.py, verified False, TẮT; golden package_inputs 2 khối; areas.json flags).
- `lipsync.talking(data)` + `offscreen_on()` + `forget_skipped`; G53 seedance_refs, G16 claude_tasks._measure_clip, G17 quality_tier.hard_signs,
  G15 lipsync.mark(method="skip") + runner gọi forget_skipped (đơn shot + nhóm take). test_narration_regression: tham số cờ TẮT (21 xfail strict giữ)
  / BẬT (hết xfail). tests/test_v31_m29_narration.py (AST + forget_skipped).

- A11: end_frames.SKIP_TEXT + skill_objects.rising_names; runner nói đúng vật (bỏ "(ném keo)"/"tường" viết cứng), code diag giữ.

- A12: test ClaudeCliTests (tests/test_director_byd.py) — settle qua ClaudeCliClient (chữ + rào JSON) ĐÃ đọc được BYĐ (xanh ngay, không cần sửa code); nguyên nhân #33 chưa tái hiện = việc mở.
- G14: voice.plan_fit / apply_fit / fit_review_on (cờ fit_durations_review); fit_durations cờ BẬT chỉ áp mặc định (thoại trong khung);
  Bước 3 bảng duyệt ⏱ (_fit_review). tests/test_fit_durations_review.py; price scan thêm voice.apply_fit.

## Đang dở / bước kế

- related_areas + báo cáo docs/RA_CLOUD_M29_2026-10-21.md; xóa HANDOFF.md ở commit cuối.
