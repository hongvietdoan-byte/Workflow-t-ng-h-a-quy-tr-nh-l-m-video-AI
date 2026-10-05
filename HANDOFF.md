# HANDOFF S14.31 (nhánh worktree-agent-aa8a46c477535b594)
XONG: core/idea_buildable.py (kit dựng được, điểm then chốt, gate 0 USD, kiểm cảnh/điểm then chốt); idea_to_script.py nối vào
build_prompt/_ask/check_script (+blocked_scenes), TURN_USD 0.045, RUN_CAP_USD 0.30->0.40; step1_idea.py form điểm then chốt + nút trả
tiền ẩn khi gate chưa qua; eval tool nhận item["anchors"]; areas.json khai file mới (không tăng version).
DỞ / VIỆC MỞ: (1) data/idea_golden/ideas.json chưa có "anchors" -> chạy eval sẽ bị gate chặn (0 USD); cần điền anchors từng ý tưởng
trước khi ghi bản ghi mới (HỎI tiền ~0,75-1 USD). (2) Replay S11.2 cũ sẽ MISS (prompt đổi có chủ ý) -> cần bản ghi mới.
(3) Chưa kiểm trang phục trong kịch bản bằng code (chỉ đưa trang phục mặc định vào prompt). (4) Cờ idea_to_script vẫn TẮT.
BƯỚC KẾ: điền anchors golden -> người dùng duyệt tiền -> ghi bản ghi -> người dùng chấm lại; sau đó TODO.md S14.31.

## Rà lần 2 (đã sửa 8 điểm)
- _where: tiêu đề chỉ có thời gian = 'thiếu nơi quay' (chặn, báo rõ). UI: bỏ 'ui' trần (chỉ 'UI' viết hoa). Cụm cấm thu hẹp + KHÔNG tính dòng thoại (NAME: ...).
- Khớp nơi/nhân vật theo cả cụm (has_phrase), không còn chuỗi con hai chiều. kit() loại nơi có file 3D mất trên đĩa, ghi vào kit['excluded'] + nói trong prompt/gate.
- Gate cho dự án cũ chỉ tới ⚙ Thiết lập -> 'Ý tưởng mới'; check_script báo flag khi không có anchors. Hồ sơ chưa duyệt ghi rõ trong kit_block. Một danh sách nhân vật (gate kiểm cả inputs.characters); UI cảnh báo khi lựa chọn đã lưu không còn trong kit.
- HEURISTIC CÒN LẠI: regex giao diện/gameplay (nhay du, vong bo, minimap, bang xep hang, 'giao dien game'...) có thể sót hoặc chặn nhầm; không phân biệt 'nhảy dù' đời thường. Chưa kiểm trang phục trong kịch bản bằng code.
- RUN_CAP_USD 0,30 -> 0,40: ĐỔI NGOÀI YÊU CẦU (test trần cho một lượt không vừa với TURN_USD 0,045); cần người dùng duyệt.
