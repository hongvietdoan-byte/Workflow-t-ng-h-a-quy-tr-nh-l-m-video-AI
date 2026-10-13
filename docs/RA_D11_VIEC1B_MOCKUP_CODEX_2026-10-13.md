# RÀ NHẸ Đ11 việc 1b mockup

Phạm vi 9c được duyệt 13/10; không API/backend/dữ liệu thật. Registry stage/segment/state + actors ID ổn định là nguồn geometry, shot cameras nằm trong registry.shots. `scenes.beats` là accessor trực tiếp states, không sync mirror mỗi render. Bản Director ban đầu chỉ dùng so sánh.

- Test đầu đỏ: browser thiếu registry/bảng chọn vật. Sau bổ sung: kiểm Chrome 1440/1280, edit state và undo đồng nhất registry; viewer orbit/pan/zoom độc lập máy, H không đổi SVG export, camera lens/FOV, target, keyframe/timeline/play, drag, diff setup, approved, layers, nhập phím, đề xuất cảnh sau.
- Đo thực bằng browser trên prototype c5544891 và mới, cùng fixture 3 shot: đổi lens hai shot chưa duyệt rồi xem máy. Baseline 5 thao tác, mới 5 (fill+change tính một thao tác). Chưa chứng minh giảm bấm; thêm diff đổi cách kiểm hơn là tuyên bố tiết kiệm.
- `related_areas.py`: chỉ dashboard_ui, không caller production; test chậm UI bắt buộc ở bước gộp. Assets/test đã khai areas, giữ version71.
- Tự rà 2b.5: không test nới assert; file URL tuyệt đối; browser context mới, chặn mọi request ngoài file; env test thay dict giả trước subprocess và tự teardown; không đọc API/data. Không hành vi autopilot/hàng loạt/cờ production nào thay.
- PNG cập nhật có chủ ý sau chạy script tay, pytest dùng tmp_path.

Giới hạn: projection SVG proxy, không Blender mesh/ray/LOD/collision/QC thật. Map và ảnh nguồn thiếu báo UNKNOWN; clay/stand_in preview_only, gửi thật tắt. Che/partial/lộ là fixture theo giây, không đo tia. Preset/JSON để sau; Director/solver/Kho/provider tắt. Keyframe chỉ kéo mốc mặc định, chưa curve/thêm/xóa. Orbit/pan là viewer local, chưa chống xuyên map. RAM mất khi refresh được ghi ngay header. Chưa chạy cả bộ/ca production, chưa gộp/push.

## Đối chiếu đúng bảng mục 9

Các dòng #3 (nền/map/phông xanh), #4 (ánh sáng), #10 (vật thể Kho/stand_in): mockup hiện chỉ nhãn nguồn UNKNOWN và giếng/tường fixture có provenance; CHƯA có điều khiển phông xanh, ánh sáng, đạo cụ chi tiết. Đây là phần còn thiếu, không coi việc1b hoàn tất đủ18mục.

#5 nhiều camera: 2 setup + 3 shot camera riêng; #6 numeric: xyz/yaw/pitch/lens/FOV sensor/aspect/target; #8 actor: 2 actor_id/chiều cao nguồn/không scale; #9 pose: đứng/bò/lùi 3beats; #11 hoạt ảnh: phát proxy cùng timeline; #13 gói gửi: bảng lớp/source, nút provider tắt; #14 phím: V/R/F/T/Q/Esc/Undo/arrows và Sreadonly/Del disabled; #15 viewer: orbit/pan/zoom độc lập shot; #16 setup: diff trước áp, approved VÀNG; #17 keyframe: kéo mốc mặc định; #18 map/clay: lớp proxy/source UNKNOWN và nhãn preview_only; #19 H/visibility: fixturehidden/partial/visible theo giây, H không export. #12/#20 để sau đúng duyệt.

Preview panel đã chuyển overlay nổi trên viewer, tự ẩn khi ở góc camera để tránh hai khung camera trùng. #1/#2/#7 cần root đối chiếu lại bảng gốc trong vòng sửa mới nếu còn yêu cầu chưa thể hiện; không tuyên bố hoàn tất18mục. Test cuối sau floating 2passed13.17s, QA1440/1280 console0/overflow0. Không tự triển khai backend.
