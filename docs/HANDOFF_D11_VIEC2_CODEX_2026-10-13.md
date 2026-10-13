# Bàn giao Đ11v2 — 13/10/2026

- Nhánh `codex/d11-viec2-clay`, base `e513a567`; chưa commit/push. Không đổi main/live/env/dữ liệu thật/API.
- Code/test/registry xong bản làm; hai cờ OFF/OPT_IN_ONLY, areas version 68.
- Nhóm cuối **136 passed / 19,90 s**, `--tb=no`, UTF8; compileall/diffcheck sạch.
- RA: `docs/RA_D11_VIEC2_CODEX_2026-10-13.md`, hợp đồng caller và giới hạn đầy đủ.
- ON V3 cap3 (đầu +2 sửa) giữ feedback numeric camera, chỉ Nhánh C khi Kho không có model3d;
  OFF prompt byte-exact và v2 cũ. Render camera solved + props + người đứng đúng nhịp shot đầu.
- ROOT đã chốt vòng sửa gộp reviewer: kiểm người/vật mọi nhịp; PNG camera bền; clamp/legend nhãn.
- Vòng sửa gộp DONE: `blocking_from_plan` kiểm base/tất cả beat, vật overrides/hidden giữ plan;
  PNG camera sidecar bền Blender/fallback; topview clamp + clay legend đầy đủ ID, không chữ xuyên vật.
- CHUAN6: cùng lỗi lặp hai lần dừng/hỏi; lỗi thay đổi vẫn tối đa3calls. OFF hash vẫn xanh.
- Nhóm cuối vòng sửa **154 passed / 20,20 s** (worker136 + review + plate_camera_stage), compileall/diffcheck sạch.
  Đỏ 10/11 test mới; fixture V3 thiếu pid đã bổ sung số giả, không nới assert. Test caller thật có fake client/cap2/cap3.
- Root đọc diff vòng sửa, render lại ba PNG thật trên fixture (gồm sidecar `<stem>_camera.png`), xem nhãn/camera rồi mới commit/push.
- Giới hạn: kiểm tâm XY người trên sàn phẳng; z lệch sàn>5cm dừng hỏi; chưa toàn thân/tư thế/đứng trên bậc.
- Chưa claim nghiệm thu 12b.4 (7/9, ≤5%, duyệt một lần), ảnh Kho thật hay production.

## Chốt rà và QA của root
Root đã đọc diff vòng sửa, 3 nhóm finding và luật lỗi lặp đã đóng. Rà cuối phát hiện hướng sáng clay cố định140° khác topview; sửa cục bộ1dòng lấy huong_sang với chuyển hệ compass→Nishita. 4ca hướng chính ĐỎ→nhóm cuối158passed/19,53s (10file), --tb=no, UTF8; không nới test.
Blender Microsoft Store thật trên3fixture tạm (không Kho/dự án thật): indoor8,29s, outdoor7,41s, steps7,40s; mỗi tấm4góc, 0issue hình học, camera sidecar decode được sau return. Root đã xem3tấm cuối + camera PNG; nhãn không bị cắt/xuyên vật và legend đủID. 6PNG docs/images/d11/d11_v2_{indoor,outdoor,steps}{,_camera}.png. Cùng một người đứng, bậc chỉ là khối cao độ, không chứng minh đứng trên bậc/7trên9/chiếu≤5%/duyệt một lần.
Cờ OFF/OPT_IN, areas.version68 giữ; không API/dữ liệu thật/credentials/main/live/fullsuite. Ghi đúng phạm vi V3CLI/backend; Dashboard/autopilot adapter sẽ thuộc việc sau, không coi đã nối sản xuất.
