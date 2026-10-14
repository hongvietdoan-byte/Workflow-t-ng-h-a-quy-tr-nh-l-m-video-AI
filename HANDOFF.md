# HANDOFF — nhánh `claude/tap2-b-planview-framing` (14/10)

## Việc 1 — diag `plate_view_fix` báo nhầm 'đổi' với shot người khóa tay (ĐÃ SỬA)
- `core/llm_io.py`: thêm `_locked_plate_views()` (đọc `_user_locked` chứa `plate_view` trên các dòng shot hiện có, khóa theo
  (cảnh kịch bản, số shot) — đúng khóa `store_plan` dùng để giữ giá trị người). `_plate_view_fix()`: shot đã khóa → kế hoạch mang
  giá trị khóa (= CSDL sau lưu, `_plate_view_diag` đọc cùng giá trị), không gọi `fix_reverse_landmark`, không ghi diag 'đổi'; nếu
  hình học vẫn sai (nhìn thẳng mặt + 'landmark') → diag VÀNG "người đã khóa hướng nền X, code thấy nên là 'away' — giữ theo người".
- Test: `tests/test_plate_view_fix_locked.py` (4 test; 2 đỏ trước sửa → xanh). Khai trong `devsys/areas.json` (step1, không tăng version).
- Việc mở: đường chia shot lại từ một cảnh (`shots.replace_from`, gọi từ `core/llm_runner.py:881`, `core/director_two_pass.py:697`)
  KHÔNG chạy `_plate_view_fix` / `_plate_view_diag` — sửa hình học landmark chỉ có ở `store_scene_analysis` (chưa sửa, ngoài phạm vi).

## Việc 2 — Seedance lùi máy / vẽ lại bố cục: CHỈ PHÂN TÍCH, KHÔNG thêm lớp phòng (không đủ bằng chứng)
Dữ liệu (đọc CSDL, job 926–935, #28/#29, tất cả seedance-2.5): 6/10 clip `framing_hold` ĐỎ (926, 927, 929, 930, 931, 935).
- Theo kế hoạch máy: static 0/2 đỏ (928, 933 — prompt đã có "camera static" do code viết); track 3/4, orbit 1/2, pan 2/2 đỏ.
  → Câu giữ khung cho shot máy tĩnh sẽ KHÔNG chặn được clip đỏ nào (shot tĩnh vốn không đỏ).
- 5/6 lỗi là "khung 0 khác hẳn ảnh đầu": mọi gói gửi dùng `reference_only` — ảnh khung đầu chỉ là "Image 1 storyboard" chứ không ghim
  khung đầu thật; 4/10 là clip gộp 2 shot (shot 2 bắt đầu sau cắt cứng, model tự vẽ). Ảnh PLACE render được ghi "decides architecture
  over storyboard" — giả thuyết (chưa kiểm): model lấy luôn khung/cỡ của render nền → vẽ lại / lùi máy.
- 926/931 (track, Kelly chạy về phía máy, "camera keeps the same distance") nền ×0,77/0,80: máy lùi theo người là ĐÚNG kế hoạch →
  nhiều khả năng framing_guard báo nhầm (bước zoom không miễn khi `camera_move` là track/follow; chỉ `_end_drift` miễn).
- 930/935 (pan, MCU) nền ×0,79/0,62: lùi máy thật; pan chỉ quay, không đổi tỉ lệ. Một shot (A/B) — quá ít để thành luật.
Đề xuất: (1) thử A/B gửi ảnh duyệt làm first_frame thật (không reference_only) cho shot đơn; (2) framing_guard miễn bước zoom-out khi kế
hoạch là track/follow mà người đi về phía máy; (3) pan/tilt: câu code "camera stays in place and only turns, same distance and lens"
(chuyen_dong_may.md đã gợi "camera stays in place") — chỉ làm sau khi có thêm mẫu.
