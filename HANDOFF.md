# HANDOFF S14.31 (nhánh worktree-agent-aa8a46c477535b594)
XONG: core/idea_buildable.py (kit dựng được, điểm then chốt, gate 0 USD, kiểm cảnh/điểm then chốt); idea_to_script.py nối vào
build_prompt/_ask/check_script (+blocked_scenes), TURN_USD 0.045, RUN_CAP_USD 0.30->0.40; step1_idea.py form điểm then chốt + nút trả
tiền ẩn khi gate chưa qua; eval tool nhận item["anchors"]; areas.json khai file mới (không tăng version).
DỞ / VIỆC MỞ: (1) data/idea_golden/ideas.json chưa có "anchors" -> chạy eval sẽ bị gate chặn (0 USD); cần điền anchors từng ý tưởng
trước khi ghi bản ghi mới (HỎI tiền ~0,75-1 USD). (2) Replay S11.2 cũ sẽ MISS (prompt đổi có chủ ý) -> cần bản ghi mới.
(3) Chưa kiểm trang phục trong kịch bản bằng code (chỉ đưa trang phục mặc định vào prompt). (4) Cờ idea_to_script vẫn TẮT.
BƯỚC KẾ: điền anchors golden -> người dùng duyệt tiền -> ghi bản ghi -> người dùng chấm lại; sau đó TODO.md S14.31.
