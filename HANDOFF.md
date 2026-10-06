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

- Test test_users: đọc query_params cả dạng chuỗi (Streamlit 1.65) lẫn danh sách (123c19f).
- S14.29 (người dùng mở lại 06/10): mã thiết bị khi IP không có PTR — core/machine_auth (identify, DEV-<băm>, chỉ lưu băm, khớp băm),
  2 cột machine_approvals.kind/device_hash (V2_COLUMNS), cookie do dashboard/common.ensure_device_cookie đặt + tải lại 1 lần;
  tests/test_s1429_device_code.py; THỬ THẬT bằng Chromium trong cloud (DASHBOARD_LAN=1, IP 192.0.2.2 không PTR): cookie 43 ký tự,
  không lên URL, máy đầu DEV-AD1E83 tự duyệt, trình duyệt thứ hai DEV-C5DA3E chờ duyệt. CHƯA thử trong mạng công ty (dải 10.7.168.x).

## Đang dở / bước kế
- S14.24 giao diện: `lesson_judge_panel` trong tab Bài học (chỉ khi cờ bật; nút có giá, bảng kết quả bóng, độ đồng thuận) — test AppTest xanh; chưa nhìn trên Dashboard thật.
- Không sửa core/lessons.py (S14.46 đang làm ở máy chính): decide(reviewer=…), sync_knowledge một bản/key, DOC_TITLE — để Đợt bật tự duyệt.
