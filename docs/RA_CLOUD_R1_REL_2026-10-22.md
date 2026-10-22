# C-R1-REL — R1-SIDE hiểu "bên phải CỦA X" (cloud-E, 22/10)

Nhánh `cloud/v31-r1-rel`. 0 USD, chỉ đọc, không đổi cờ; positions không vào gen/QC.

## Đã làm
- `core/world_map._side_claims` (một bộ đọc chung cho REVIEW M3.3 + R1): chữ tương đối "right of X", "bên phải (của) X" KHÔNG còn bị gán
  thành bên KHUNG của ai ("of the frame", "bên phải khung", "phía phải của khung" vẫn là bên khung); thêm "khung trái/phải".
- `core/position_invariants`: R1-SIDE tách hai loại.
  (a) tuyệt đối: như cũ (góc chủ thể so tâm khung, CENTRE_DEG 8°), phát hiện ghi `kind=tuyet_doi` + `angle_deg`.
  (b) tương đối (`relative_claims`: "A … to the right of B", "A … on B's left", "A … bên phải (của) B", "A đứng bên trái B"):
  map 3D/2D → so góc A với góc B theo máy shot (Δ dương = A phải hơn); map tương đối → quan hệ `trai_cua`.
  `|Δ| < REL_MIN_DEG = 5°` → KHÔNG RÕ + số đo (angle_deg, other_angle_deg, delta_deg). Thiếu chủ thể / toạ độ / quan hệ → KHÔNG RÕ + lý do.
  Bộ phận cơ thể ("Kelly's right shoulder"), đại từ ("her left") → không phải quan hệ (giữ như cũ).

## Test (đỏ trước → xanh sau)
`tests/test_v31_3d_goc_b.py` thêm 8 test (+24 biến thể seed): 34 đỏ trước sửa → xanh. Đúng chiều không báo / ngược chiều báo VÀNG cho cả
EN + VI, cả hai phía; ngưỡng 5° → KHÔNG RÕ; map tương đối dùng quan hệ; mọi chỗ đặt cảnh (seed). Test cũ giữ nguyên (body parts,
where-clause, "Kelly stands frame-right" vẫn báo), `test_map_positions_are_not_fed_into_gen_or_qc` xanh.
Chạy: test_v31_3d_goc_b, _goc_a, _dp8_world_map, _dp11_position_sentence, test_stage_facts → 295 passed.

## Kết luận shot 34 (#31, fixture thật)
Đo theo máy shot: Kelly −37.2°, Yêu nữ −20.6°, Xúc tu đỏ −16.6°, Sứ giả bóng đêm −22.9° — cả bốn nửa TRÁI khung; ba địch phải hơn Kelly
14–21° (> 5°). Câu thật ("turning her head toward frame-right where three enemies stand", blocking "far frame-right corner") là bên KHUNG
tuyệt đối, KHÔNG phải quan hệ tương đối → chữ "frame-right" VẪN mâu thuẫn map. Khi chủ thể là tên trên map (vd "Yêu nữ … far frame-right
corner") R1-SIDE vẫn báo VÀNG (có test). Câu thật dùng cụm "three enemies" không phải tên trên map nên (như sau 85189242) không gán được ai
→ không báo; đây là chỗ còn mở (cụm nhóm người chưa nối với thực thể map). Sửa chữ đúng: "to Kelly's right" / "bên phải Kelly" → nay qua
kiểm tương đối, không báo.

## Tồn đọng
- Cụm nhóm ("three enemies", "the enemies") chưa nối tới thực thể map → chữ bên khung của nhóm chưa được kiểm (đề xuất việc sau).

## Sửa sau rà quy ước 7 (4 mục VỪA)
1. "of X" chỉ là tương đối khi X là tên trên map (`world_map.rel_names`, một danh sách cho cả hai loại); X = center/centre/middle/camera/
   composition/viewer/lens/frame… → bên khung (VÀNG nếu ngược); X lạ → KHÔNG RÕ «X không phải tên trên map» (hết im lặng).
2. Tiếng Việt: "của màn hình / khuôn hình / ảnh / khung (hình)" = bên khung; "A đứng bên phải B" xét theo mọi tên trên map, không chỉ `placed`.
3. `world_map.relations_at`: valid_from/valid_to không phải số → chỉ khớp khi bằng shot, không TypeError; position_sentence dùng chung.
4. Máy thiếu / cờ stage_camera tắt → MỘT KHÔNG RÕ «máy shot chưa có», không đổ lỗi thiếu toạ độ thực thể; thực thể sau lưng máy nói đúng.
Test: +11 ca (10 đỏ trên d9d22d6c → xanh); bộ liên quan 305 passed.
Còn mở (THẤP): world_map.review (M3.3, chưa có chỗ gọi thật) chưa gọi kiểm tương đối; nhãn "bên KHUNG" kind=tuyet_doi vẫn dùng cho
map tương đối (placed suy từ trai_cua); "looks/turns to the right of X" vẫn đọc như chỗ đứng.
