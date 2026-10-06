# HANDOFF — cloud (nhánh `claude/read-s14-45-cloud-tasks-ngb0q2`)

Credit: người dùng báo còn $96/100 (06/10, sau S14.45); trần cứng $90 đã dùng.

## Đã xong
- S14.45 (commit 31a7fe2, 1bf20d1): devsys/workflow.py + workflow_runs.jsonl + trang "Hiệu quả quy trình".
- S14.24 (chế độ bóng): core/lesson_judge.py (facts, build_prompt, normalize, verdict = 8 van + chủ đề đã bỏ, judge, judge_all,
  estimate, agreement, MockJudge), cờ `lesson_judge` TẮT, STAGE_SETTINGS/LLM_STAGE_TOKENS "lesson_judge", tests/test_lesson_judge.py.

- S14.25 Đợt 6a: core/feedback.to_mistakes() (cờ `feedback_to_mistakes` TẮT), gọi ở cuối lessons.harvest() (1 dòng, không đụng
  phần lọc S14.46), tests/test_feedback_mistakes.py.

- Sửa lỗi có sẵn: step1_characters.py thiếu `from typing import Optional` (20ae3cc) — 117 test giao diện đỏ → xanh.
- S14.11: kịch bản `samples/du_an_thu_30s.txt` + `docs/DU_AN_THU_30S_2026-10-06.md` (bảng cờ chưa verified + trần từng việc,
  tính từ data/pricing.json), tests/test_s1411_trial_script.py. CHỜ người dùng duyệt trần → S14.12.

## Đang dở / bước kế
- Nút "🤖 Chấm điểm đề xuất" + bảng kết quả ở dashboard/admin.py (tab Bài học) — CHƯA làm (cần Dashboard thật để thử, để phiên chính).
- Không sửa core/lessons.py (S14.46 đang làm ở máy chính): decide(reviewer=…), sync_knowledge một bản/key, DOC_TITLE — để Đợt bật tự duyệt.
