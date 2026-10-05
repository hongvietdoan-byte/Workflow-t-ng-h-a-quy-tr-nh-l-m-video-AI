# HANDOFF — S14.27 (nhánh `s14-27-devsys-answers`)

## Đã xong
- `devsys/answers.py`: lõi + CLI `py -m devsys.answers list [--pending] [--json] | add <mã> "…" [--choice] [--source chat|devsys] [--who] | applied <mã> "ghi chú"`.
  File `devsys/data/user_answers.json` của **bản chính** (tìm qua `.git` của worktree → `D:\AI-Video-Pipeline`); `DEVSYS_ANSWERS_FILE` đổi đường dẫn (test).
  Định dạng `devsys-answers/1`: `{format, updated, answers: {mã: {task_id, choice, text, source, who, at, status answered|applied, applied_note, applied_at, history[]}}}`.
  Ghi nguyên tử (mkstemp cùng thư mục + os.replace); file hỏng/sai định dạng → `AnswersError`, không ghi đè.
- `devsys/app.py` trang 📋: dưới mỗi việc ⏸ — khối "⏸ Đang chờ bạn" có form ngay tại chỗ; trong thân đợt có popover "✍ Trả lời"/"✏ Sửa trả lời".
  Trạng thái "✅ đã trả lời — chờ Claude áp dụng" / "✔ đã áp dụng (…)". File hỏng → st.error, ẩn ô. Thêm `_rel()` (relpath khác ổ đĩa không lỗi).
- Skill `.claude/skills/vong-lam-viec-theo-plan/SKILL.md`: mục 1 bước 3 đọc `--pending`; mục 5 ghi câu trả lời từ chat.
- `devsys/areas.json` khai test mới (không tăng version); `devsys/data/README.md` thêm dòng file trả lời.
- Test: `tests/test_devsys_answers.py` (17) + test_devsys*.py: 81 qua.

## Bước kế (phiên chính)
- Rà nhẹ/gộp; sau gộp `git pull` ở `D:\AI-Video-Pipeline` và khởi động lại web 8502 (Start-DevSystem.bat) để thấy ô trả lời.
- Đổi S14.27 → ✅ trong kế hoạch + TODO (nhánh này không sửa TODO).
