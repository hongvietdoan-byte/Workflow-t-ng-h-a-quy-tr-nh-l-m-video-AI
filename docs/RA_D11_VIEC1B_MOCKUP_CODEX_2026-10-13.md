# RÀ NHẸ Đ11 việc 1b mockup

Phạm vi 9c được duyệt 13/10; không API/backend/dữ liệu thật. Registry stage/segment/state + actors ID ổn định là nguồn geometry, shot cameras nằm trong registry.shots. `scenes.beats` là accessor trực tiếp states, không sync mirror mỗi render. Bản Director ban đầu chỉ dùng so sánh.

- Test đầu đỏ: browser thiếu registry/bảng chọn vật. Sau bổ sung: kiểm Chrome 1440/1280, edit state và undo đồng nhất registry; viewer orbit/pan/zoom độc lập máy, H không đổi SVG export, camera lens/FOV, target, keyframe/timeline/play, drag, diff setup, approved, layers, nhập phím, đề xuất cảnh sau.
- Đo thực bằng browser trên prototype c5544891 và mới, cùng fixture 3 shot: đổi lens hai shot chưa duyệt rồi xem máy. Baseline 5 thao tác, mới 5 (fill+change tính một thao tác). Chưa chứng minh giảm bấm; thêm diff đổi cách kiểm hơn là tuyên bố tiết kiệm.
- `related_areas.py`: chỉ dashboard_ui, không caller production; test chậm UI bắt buộc ở bước gộp. Assets/test đã khai areas, giữ version71.
- Tự rà 2b.5: không test nới assert; file URL tuyệt đối; browser context mới, chặn mọi request ngoài file; env test thay dict giả trước subprocess và tự teardown; không đọc API/data. Không hành vi autopilot/hàng loạt/cờ production nào thay.
- PNG cập nhật có chủ ý sau chạy script tay, pytest dùng tmp_path.

Giới hạn: projection SVG proxy, không Blender mesh/ray/LOD/collision/QC thật. Map và ảnh nguồn thiếu báo UNKNOWN; clay/stand_in preview_only, gửi thật tắt. Che/partial/lộ là fixture theo giây, không đo tia. Preset/JSON để sau; Director/solver/Kho/provider tắt. Keyframe chỉ kéo mốc mặc định, chưa curve/thêm/xóa. Orbit/pan là viewer local, chưa chống xuyên map. RAM mất khi refresh được ghi ngay header. Chưa chạy cả bộ/ca production, chưa gộp/push.

## Đối chiếu 18 mục đã duyệt
#1 cảnh/shot dựng sẵn; #2 preview nổi với thu/phóng và xuất SVG; #3 camera numeric/FOV/target; #4 chọn actor rồi xyz/facing/pose; #5 viewer/preset góc nhanh; #6 beat/pose proxy; #7 baseline so sánh, Director tắt; #8 registry chung; #9 provenance chiều cao không scale; #10 giếng/tường fixture (chưa chỉnh đạo cụ); #11 phát proxy; #13 bảng lớp gửi minh họa, gửi tắt; #14 phím an toàn; #15 viewer orbit/pan/zoom; #16 setup diff/approved; #17 kéo mốc keyframe chung timeline; #18 ba lớp có nhãn thiếu nguồn, chưa ánh sáng/render; #19 H/visibility fixture, ray unknown. Không coi đây là hoàn tất backend hay 18 tính năng production; điều khiển ánh sáng/nền/đạo cụ chi tiết chưa có. #12/#20 để sau đúng duyệt.
