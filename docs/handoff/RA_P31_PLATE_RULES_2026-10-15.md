# Rà quy ước 7 — nhánh `claude/p31-plate-rules` (15/10, agent rà, chưa sửa)

Phiên sau: sửa hết các mục dưới (hoặc ghi lý do bỏ), chạy cả bộ test, rồi mới gộp main. Agent chạy 168 test liên quan: 2 FAIL (THẤP-1).

## CAO
1. **Ảnh toàn của shot không bao giờ gửi toàn vẫn giữ shot.** `core/location_pack.py` ~737 (WIDE_HOLDS). `place_refs.wide_for` (place_refs.py:244) không gửi toàn cho shot indoor; place_refs.py:175 không gửi cho máy locked. `plate_camera.wide_for` (:433) chép "locked"/"indoor"/"rig" sang máy toàn → máy toàn locked không dời → outside → shot bị giữ (chính phòng nhỏ #31). Sửa: chỉ WIDE_HOLDS khi shot thật sự sẽ gửi toàn.
2. **Ảnh toàn lỗi tạm không render lại nhưng sau 10 phút shot bị thả im lặng.** location_pack.py:599 `_failed(..., retry=kind=="shot")` → toàn không vào danh sách render lại; `_wide_record` retry=True → hết hạn wide_failed rỗng → shot đi KHÔNG có toàn; place_refs.missing (:177) báo thiếu mãi. Sửa: dòng 599 retry=True cho cả hai; `again` (~632) bỏ điều kiện kind=="shot".
3. **Sửa chỉ chạy khi ensure_plates chạy.** core/autopilot.py ~666 chỉ gọi ensure_plates khi index thiếu/lệch key → nền cache cũ #31 không qua FINISH_VERSION / camera_problem / _wide_record mới. Sửa: điều kiện gọi thêm finish_v != FINISH_VERSION hoặc camera_problem(rec).

## VỪA
4. forget_shot (location_pack.py:352) không xóa lỗi của ảnh toàn cho bản ghi giữ do toàn hỏng (~741 thiếu wide_key) → nút "↻ Render lại nền 3D" kẹt. Thêm wide_key.
5. Chữ/doc cũ sai: location_pack.py:581, :648 ("shot gửi không kèm ảnh toàn"), render_plates.py:685 ("WIDE never moved"), readiness.py:133, comment test_scene_establish.py:89.
6. Orbit tới ±120° không giới hạn: máy travel (TRAVEL_VIEW_MAX_DEG 60, memory "camera bám hướng chạy") và TPS bị xoay ngược; ứng viên orbit bỏ kiểm bg. Sửa: bỏ orbit cho travel/rig tps hoặc ≤ 60°, còn lại unplaceable.
7. lift_dark áp lên shadow.png với gain riêng → lệch sáng; nền indoor practical có thể cháy. Sửa: dùng chung gain hoặc không lift shadow; bỏ qua practical/indoor. "QUÁ TỐI" đang áp cả nền ban ngày (không được lift) → chỉ áp khi time != day.
8. Máy locked (stage_camera) bị coi outside → nền đã duyệt thành hỏng; cân nhắc chỉ warn.
9. _stage_hold chạy cho mọi dự án: cảnh hợp lệ có 2 chỗ đứng dừng một lần ở cổng plates — chấp nhận, ghi rõ.

## THẤP
1. tests/test_plate_depth_p24.py:42, :60 FAIL (MostlySkyPlateTests: ROOF_PLATE mean 31 nay "QUÁ TỐI") — test khẳng định hành vi cũ, cập nhật.
2. Cache key không lệch (key từ máy kế hoạch); horizon_y của plan vẫn theo ống cũ (nhẹ).
3. ambience.py không bị ảnh hưởng.
