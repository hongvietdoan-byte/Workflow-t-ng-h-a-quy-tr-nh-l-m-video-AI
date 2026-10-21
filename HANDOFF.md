# HANDOFF — C-M71 (cloud-E nhánh phụ, nhánh cloud/v31-m71)

Việc: M7.1 Gói A sửa cờ (A1, A2, A3, A5; KHÔNG A4). Đề: docs/CLOUD_TASKS.md "#### C-M71".
- [x] A1 change_review fail-closed (quota → giữ; blocking không ném; vòng director_rewrite) — tests/test_change_review.py::M71FailClosed
- [x] A2 khai costs hero_takes + end_frames, scene_qc_claude, voice_check_redo (+ B5 audio_first, story_check); ước tính before_run
- [x] A3 director_rewrite_respect_lock (verified False, mặc định TẮT)
- [ ] A5 chat_prompts: pregen_check --payload nói D6; hết tiền → 1 diag, không đếm lượt
- [ ] Báo cáo docs/RA_CLOUD_M71_2026-10-21.md; xóa HANDOFF.md ở commit cuối
