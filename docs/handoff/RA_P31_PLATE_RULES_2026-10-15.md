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

## Kết quả sửa (phiên p31-plate-fix, 15/10) — test: tests/test_plate_rules_fix_1510.py + tests/test_plate_rules_1510.py (đỏ trên code nhánh, xanh sau sửa)
- **CAO-1 ĐÃ SỬA**: `location_pack.wide_sent(camera)` (không `locked`, không `indoor`) — ảnh toàn hỏng chỉ giữ shot thật sự gửi ảnh toàn; shot trong nhà / máy khóa giữ `wide_failed` như ghi chú. Kèm lỗi gốc phát hiện khi sửa: `sp["indoor"]` của chỗ đứng **chưa từng** vào camera gửi Blender (plan) → luật "máy trong nhà không trần = ngoài phòng" + exposure phòng không bao giờ chạy trên dây chuyền; nay `plan()` chép `indoor` vào camera (đổi cache key shot trong nhà).
- **CAO-2 ĐÃ SỬA**: ảnh toàn lỗi tạm vào danh sách render lại theo giờ như shot (`_failed(retry=True)`, `again` cho cả ảnh toàn); chữ lỗi nói "GIỮ CHỜ tới khi có ảnh toàn".
- **CAO-3 ĐÃ SỬA**: `location_pack.refresh_due()` (index có finish_v cũ ở nền hoặc ảnh toàn, hoặc camera_problem) → autopilot gọi ensure_plates dù key khớp; ảnh toàn ghi `finish_v` vào index. KHÔNG nâng `SCRIPT_VERSION` (đã thử v4-2 rồi bỏ — rà lần 2 CAO-1: mọi ảnh đã duyệt thành "vẽ trên nền cũ", autopilot giữ clip). Nền cache đặt máy theo luật cũ: render lại bằng `py tools/location_pack.py render --project N --fresh-shot IDX` (Blender, 0 USD); shot trong nhà / chạy theo đường có key mới nên tự render lại.
- **VỪA-4 ĐÚNG SẴN**: bản ghi giữ do ảnh toàn có `wide_key` qua `**extra` — test `test_retry_button_forgets_the_wide_of_a_shot_held_by_it` xanh cả trên code nhánh; giữ test làm khóa.
- **VỪA-5 ĐÃ SỬA**: docstring ensure_plates, chữ lỗi ảnh toàn, docstring render_plates.clearance, readiness (shot trong nhà = ok không góc rộng; wide_failed = "ảnh shot chờ góc rộng"), comment test_scene_establish (đó là ảnh thiết lập cảnh học việc — làm rõ, không sai).
- **VỪA-6 ĐÃ SỬA**: ORBIT_STEPS_DEG ≤ 60° (= TRAVEL_VIEW_MAX_DEG); không tự xoay cho máy travel (camera mang `travel`) / rig tps / wide / locked → unplaceable (shot chờ, có lý do); ứng viên xoay đo lại nền (tường cao/thấp); ảnh toàn xoay THEO máy shot (`follow` + `turn_deg`, không vào cache key). Hệ quả: góc phòng #31 shot 2 cần xoay > 60° → "không còn chỗ / ngoài phòng" → đổi chỗ đứng / plate_view ở dữ liệu.
- **VỪA-7 ĐÃ SỬA**: shadow.png dùng chung gain của plate (`finish_plate(lift=)`), nền có đèn practical không nâng, "QUÁ TỐI" chỉ khi `time != day` (rec["time"]); FINISH_VERSION 3.
- **VỪA-8 ĐÃ SỬA**: máy Sân khấu 3D khóa nằm ngoài phòng → chỉ cảnh báo (không `outside`, không hỏng nền đã duyệt).
- **VỪA-9 CHẤP NHẬN**: `_stage_hold` chạy mọi dự án — cảnh hợp lệ có 2 chỗ đứng dừng một lần ở cổng 'plates' (hash theo dòng báo, bấm Tiếp tục là qua), đúng ý người dùng "mỗi cảnh một sân khấu chung".
- **THẤP-1 ĐÃ SỬA**: test_plate_depth_p24 — nền mái cũ (31/255) nay "QUÁ TỐI" là đúng; kiểm phẳng riêng bằng dark_check=False / time=day.
- **THẤP-2 BỎ**: horizon_y trong plan theo ống cũ khi máy mở ống — chỉ ảnh hưởng chữ bố cục, reframe đã tính horizon riêng; để khi nối sân khấu 3D v2.
- **THẤP-3**: không cần làm.

## Rà quy ước 7 lần 2 (agent, sau bản sửa) — 2 CAO / 4 VỪA / 7 THẤP; test: `AgentReviewTests` trong tests/test_plate_rules_fix_1510.py
- **CAO-1 ĐÃ SỬA**: bỏ nâng SCRIPT_VERSION (xem CAO-3 trên); câu `old_plate_images` nói "nền 3D của shot đã đổi (chỗ đứng / hướng máy / ánh sáng / luật đặt máy…)" thay vì chỉ "chỗ đứng / hướng máy".
- **CAO-2 ĐÃ SỬA**: `location_pack.effective_camera()` — `camera_plan` trong index = máy Blender thật dùng (vị trí/hướng/ống sau khi kéo vào, xoay); máy kế hoạch giữ ở `camera_planned`. geometry_sentence / light_words / plate_anchor / travel_truth đọc máy thật.
- **VỪA-3 ĐÃ SỬA**: `dark_judged()` — đêm có đèn practical không bị "QUÁ TỐI" (không nâng sáng nên không phán).
- **VỪA-4 ĐÃ SỬA**: ảnh toàn chỉ "QUÁ TỐI" (máy không lỗi) vẫn gửi kèm `wide_note` + diag cảnh báo, không giữ shot vô hạn.
- **VỪA-5 CHƯA KIỂM THẬT — giao phiên máy chính**: `indoor` lần đầu tới Blender (exposure +1,5 + đèn fill) — render thử #31 phòng 2 cửa ngày + đêm (0 USD) và xem ảnh trước khi gen; chưa có kiểm "quá sáng".
- **VỪA-6 ĐÃ SỬA**: hoàn thiện lại lỗi → bản ghi failed có lý do (nút Render lại), không ném lỗi mỗi nhịp; ảnh toàn tương tự → wide_failed.
- **THẤP-7 ĐÃ SỬA**: `place_refs.missing` không đòi ảnh toàn của shot trong nhà (wide_sent). Ảnh toàn trong nhà vẫn render cùng lượt (không đổi luồng render).
- **THẤP-8 BỎ**: máy locked trả "ok" ở nhánh `stage_locked` phía trên — không rơi vào câu "shot trong nhà".
- **THẤP-9 ĐÃ SỬA**: tools/location_pack.py preview mang `indoor` như dây chuyền (travel không áp cho preview).
- **THẤP-10 ĐÃ SỬA**: shot render trong lượt này ghi góc xoay (0 = không xoay) → ảnh toàn không lấy góc cũ từ cache. Key ảnh toàn không gồm góc xoay — chấp nhận (hiếm, dùng --fresh-shot).
- **THẤP-11 HẾT** (không còn nâng SCRIPT_VERSION).
- **THẤP-12 GHI NHẬN**: xoay ≤ 60° chưa kiểm trục 180° với shot liền kề — để khi nối sân khấu 3D v2 (một cảnh một sân khấu).
