# HANDOFF — nhánh worktree-agent-ad0afa7fa7d78403d (14/10, #30 shot 1 / scene 302)

## Xong
- (b) Máy 3D đặt theo `camera_move` khi shot có đường A→B (sau cờ `travel_truth`, đang BẬT trên máy chính; tắt = như cũ):
  - `core/travel_truth.py`: `route()` (một nguồn A/B, dùng lại `_next_spot/_prev_spot`, `for_shot` cũng đi qua nó), `camera_mode()`
    (lead = camera_move `pull_out` / chữ máy lùi trong `shot`/`camera_setup` / chữ "toward camera", trừ orbit/crane/whip/pan/tilt;
    follow = chữ máy bám sau / `track` + sau lưng; cả hai → VÀNG, không đoán), `camera_route()`.
  - `core/plate_camera.py`: `travel_camera()` (máy TRÊN đường A→B: lead phía B nhìn về A, follow phía sau A nhìn về B; khoảng cách theo
    cỡ cảnh như `camera_for`; mặt đất dưới máy = nội suy z A/B, kẹp trong đoạn). `camera_for` thêm `behind=`, `rise_at=` (mặc định như cũ).
    `plan_cameras(travel_of=)`: shot đi đường riêng không gom chung camera_setup.
  - `core/location_pack.py` `plan()` + `_travel_checks()`: `plate_view` lệch máy-theo-đường > 60° → `needs` (chặn); không có đường /
    hai nghĩa → `travel_problem` (VÀNG, máy như cũ) — autopilot nói (`core/autopilot.py`), `tools/location_pack.py` in ra.
- (c) `travel_truth.for_shot` trả `needs` khi chữ ↔ máy render trái nhau chắc chắn; `plan()` gọi nó trên máy ĐÃ LẬP → index `needs` → ảnh chờ.
- (d) Câu hướng chạy dùng `label_en` / nhãn ASCII, không có thì "the foot / top of the stairs" ("bottom / top of the slope"); diag vẫn tiếng Việt.
- (e) Gốc: storyboard (`scene_storyboard.shared_references`) gom ảnh vật của MỌI shot trong cảnh; ảnh khóa vật = ảnh đầu của
  `prop_lock.usable_images` = Kho #367 `3.png` (sort −1, "triển khai có hình nộm so cỡ") → shot 1 nhận "Image 4 is the object Bom keo"
  + câu hình nộm. Sửa: `usable_images` bỏ ảnh có hình nộm (ảnh đó chỉ đi đường DEPLOYED `skill_objects.deployed_pictures`).

## Bằng chứng
- Test đỏ (code HEAD 2c605888, bản sao scratch): 9/9 FAIL `tests/test_travel_camera_p30.py`. Xanh: 382 passed (25 file liên quan, 1 lệnh; lần cuối sau khi siết regex lead/follow + test "pulls out her SKORP").
- CSDL thật #30 (chỉ đọc, `location_pack.plan`): cờ tắt máy shot 1 tại (-252.56, 143.73, 5.25) nhìn 288,2°; cờ bật (-252.64, 143.54, 5.61)
  nhìn 298° (đúng ngược hướng chạy 118°), mặt đất dưới máy cao +0,35 m; needs None; câu: "from the foot of the stairs (ground 3.9 m) to the
  top of the stairs (8.5 m) … KELLY moves TOWARD the camera", warn []. Shot 303–308: máy + khóa cache không đổi.
  Lưu ý: dữ liệu shot 1 đã sửa `plate_view` = away nên máy cũ đã gần đúng (lệch 10°); thay đổi chính = máy đúng trục đường chạy + nâng theo bậc.

## Dở / việc kế (phiên chính)
- Render lại nền 3D shot 1 #30 (khóa cache đổi → KLD-6 stale tự giữ ảnh + render lại, 0 USD) rồi `replay_payload --shot 1` kiểm gói.
- Chưa chạy agent rà khâu liên quan (CLAUDE.md quy ước 7) — phiên chính giao đề bài dưới đây.
- Còn mở: storyboard vẫn chia sẻ ảnh vật của shot khác (nay là 2.png "triển khai") cho shot 1 — đúng thiết kế "props stay shared" nhưng
  shot chỉ chạy vẫn nhận ảnh tường keo; cân nhắc lọc theo shot (`scene_storyboard.shared_references`).
- `travel_truth` chặn chỉ khi chênh cao ≥ 1,5 m (đường phẳng không kiểm mâu thuẫn — như cũ).

## related_areas (`py tools/related_areas.py core/travel_truth.py core/plate_camera.py core/location_pack.py core/prop_lock.py core/autopilot.py tools/location_pack.py`)
- Khu vực chứa: step2 (travel_truth), plates3d (location_pack, plate_camera, tools/location_pack), step1 (prop_lock), autopilot.
- Khu vực gọi tới: step4 (runner → location_pack/prop_lock/travel_truth; scene_establish → location_pack; skill_objects → prop_lock),
  core_infra (batch → autopilot; lineage → prop_lock; package_overrides → location_pack), assets (assets → prop_lock),
  dashboard_ui (archive, common, shell_parts, header, next_step), diag (capacity, limits_ui), budget (header).
- Dùng chung cờ: assets, core_infra, knowledge, lipsync, step3, step4. Test chậm ở bước gộp: test_access.py, test_ui_v2_acceptance.py.
- Điểm rà gợi ý: `lineage` (dấu vân ảnh khóa đổi khi Kho có ảnh hình nộm), `seedance_refs` (ảnh vật video), `stale_plates`/`package_overrides`
  (plan() nay gọi travel_truth mỗi shot khi cờ bật), `runner._travel_truth` (bỏ qua `needs` — chỉ index chặn).
