# HANDOFF — cloud (nhánh `claude/read-s14-45-cloud-tasks-ngb0q2`)

Credit: người dùng báo còn $96/100 (06/10, sau S14.45); trần cứng $90 đã dùng.

## Đã xong
- S14.45 (commit 31a7fe2, 1bf20d1): devsys/workflow.py + workflow_runs.jsonl + trang "Hiệu quả quy trình".
- S14.24 (chế độ bóng): core/lesson_judge.py (facts, build_prompt, normalize, verdict = 8 van + chủ đề đã bỏ, judge, judge_all,
  estimate, agreement, MockJudge), cờ `lesson_judge` TẮT, STAGE_SETTINGS/LLM_STAGE_TOKENS "lesson_judge", tests/test_lesson_judge.py.

## Đang dở / bước kế
- S14.24 giao diện: `lesson_judge_panel` trong tab Bài học (chỉ khi cờ bật; nút có giá, bảng kết quả bóng, độ đồng thuận) — test AppTest xanh; chưa nhìn trên Dashboard thật.
- Không sửa core/lessons.py (S14.46 đang làm ở máy chính): decide(reviewer=…), sync_knowledge một bản/key, DOC_TITLE — để Đợt bật tự duyệt.
