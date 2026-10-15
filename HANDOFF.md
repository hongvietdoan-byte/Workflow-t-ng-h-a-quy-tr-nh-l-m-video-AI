# HANDOFF — Phòng 2 cánh cửa (tập 2 #31, cảnh 1 + 5) — 15/10

Nhánh: worktree-agent-a070165b71313189d. 0 USD (Blender trên máy, không Meshy/API).

## Đã làm
- `tools/build_room_2_doors.py`: phòng procedural 5 × 4,5 × 2,6 m (giấy dán tường lục giác xám-xanh tile theo mét, nẹp trắng ngà,
  sàn gỗ tối + thảm, dây cờ đỏ–xanh, kệ sách + TV CRT, 4 bóng bay, sofa, đèn bàn chụp vải ấm cạnh cửa 1; trần tối).
  Cửa 1 tường TÂY (trái) y 3,3–4,2; cửa 2 tường BẮC (sau, lệch phải) x 2,5–3,4; cao 2,05; cánh panel 6 ô + tay nắm đồng + 3 bản lề.
  Gốc object `cua_1` / `cua_2` = trục bản lề thật (xoay Z là mở), mở ra hành lang (không quét vào phòng).
  Sau lối: hành lang tối (cửa 2 có dây đèn màu nhỏ như key visual); sau cửa 1 ở B/C: ánh tím–đỏ loang (vật liệu phát sáng).
- 3 trạng thái = 3 file .glb CÙNG hệ tọa độ, CÙNG SPOTS (pipeline không có cơ chế biến thể mô hình theo cảnh — `profile.model3d`
  chỉ có 1 `path`): `phong_2_cua_A_dong.glb` (mặc định, cảnh 1), `_B_cua1_mo.glb` (cửa 1 mở 45°, đầu cảnh 5), `_C_ca_hai_mo.glb`
  (cửa 1 45° + cửa 2 80°, cuối cảnh 5). Cần phiên chính quyết: đăng ký 3 mục Kho riêng, hay đổi `path` theo cảnh.
- `tools/preview_room_2_doors.py <ra>`: dựng (Blender Store qua plates3d, giữ khóa lượt) + render 9:16 bằng ĐÚNG render_plates.py
  (đêm, indoor của chỗ đứng, + đèn POINT ấm tại đèn bàn như practical_lights) + finish_plate + ảnh tổng hợp.
- `tests/test_build_room_2_doors.py` (cửa trong tường, chỗ đứng trong phòng/không trong đồ, POV và Kelly WS thấy cả 2 cửa,
  cánh mở ra hành lang, 3 trạng thái). Khai trong devsys/areas.json (khu step1, cạnh build_kitchen; không tăng version).

## Đăng ký Kho (CHƯA làm — không ghi CSDL chính)
`location_pack.set_model3d(conn, <id>, path=<A.glb>, spots=SPOTS (+ "indoor": INDOOR mỗi chỗ), default_spot="goc_nhin_kelly_2_cua",
notes=NOTES)` — SPOTS/INDOOR/NOTES/DEFAULT_SPOT lấy từ tools/build_room_2_doors.py. Copy .glb vào data/models3d/phong_2_cua/.

## Lưu ý
- Spot `kelly_giua_phong`: chỉ cỡ WS (ống 24 mm theo plate_camera) mới thấy cả 2 cửa sau lưng Kelly; MS/MLS thấy 1 cửa + góc phòng.
- `goc_nhin_kelly_2_cua` là POV: máy ở 'at' cao 1,55 m nhìn 'view', ống 20 mm (camera_for đặt máy TRƯỚC mặt nhân vật — POV cần
  cách đặt máy riêng của pipeline).
- Đèn trong .glb bị render_plates bỏ → ấm của đèn bàn phải đến từ practical_lights (lamp warm, phía trái/sau) của shot.
- Ảnh: renders/phong_2_cua/tong_hop.png (commit); ảnh lẻ + .glb không commit (dựng lại: `py tools/preview_room_2_doors.py renders/phong_2_cua`).
