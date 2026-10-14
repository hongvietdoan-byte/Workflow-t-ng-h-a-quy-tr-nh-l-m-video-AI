# Rà và sửa gộp Đ11 việc 1b mockup — 13/10/2026

Phạm vi người dùng duyệt: 18 dòng mục 9/9c `THIET_KE_BAN_DUNG_3D_D11.md`; #12 preset và #20 JSON để sau. Chỉ HTML/JS/test/PNG offline, không backend, API, dữ liệu thật hoặc editor 2D riêng. Registry stage/segment/state/setup/shot là nguồn đang chỉnh; `scenes.beats` accessor vào states. Snapshot stage chỉ là revision giữ geometry của approved, không phải bản sao editor độc lập.

## Một vòng sửa sau rà độc lập

1. P2 drag: bỏ deltaXY/34; client→SVG bằng inverse CTM và inverse yaw/pitch/zoom của viewer. World axis lock/snap áp sau inverse. Actor/camera kéo về mốc đang chọn; nét hướng mặt không chặn chọn.
2. P2 keyframe: giới hạn từng mốc bởi hàng xóm và khoảng cách 0,1 s; luôn start < peak < end, tránh chia 0.
3. P2 timeline: Director/camera/export dùng chung sampler state theo giây; pose đổi ở mốc, máy nội suy theo start/end đã kéo. Nhãn chuyển động/cỡ cảnh/góc là yêu cầu solver, chưa xây đường mới.
4. P2 diff: giữ shot_id/setup_id/point, revision và snapshot nguồn; đổi shot/setup/point hoặc sửa đầu vào hủy pending. Confirm chặn revision cũ; setup diff liệt kê trước/sau từng shot, approved chỉ VÀNG. Undo phục hồi states/shot/setup/stage/snapshot cùng nhau.
5. P2 target: actor_id resolve trên state đang sample, hướng pinhole bám mắt fixture; nhập yaw/pitch quay về manual. Numeric endpoint đưa thời gian về đúng mốc đang chỉnh.

## Đối chiếu 18 dòng bản gọn đã duyệt

| Dòng | Hiện có và giới hạn |
|---|---|
| #1 | Fixture Director dựng sẵn ba shot, không dựng cảnh trống |
| #2 | Preview máy nổi thu/phóng, cùng shot/khung/safe area, hướng/mm; xuất SVG projection `preview_only` |
| #3 | Chọn nền fixture/phông xanh, source_asset_id; map/panorama thật thiếu UNKNOWN, không tải panorama |
| #4 | Giờ/thời tiết nguồn + azimuth nâng cao; nét hướng/overlay minh họa, không đo/render ánh sáng |
| #5 | Hai setup có camera khác nhau + ba shot độc lập; setup→shot có danh sách/diff |
| #6 | XYZ/yaw/pitch/mm↔FOV/sensor/aspect, target actor_id; cỡ cảnh/góc là yêu cầu solver, roll nâng cao chưa hỗ trợ có lý do |
| #7 | Chép hướng viewer/dán máy/về snapshot Director fixture đều diff/xác nhận; giữ actor/state/approved; solver chưa nối tắt |
| #8 | Hai cast actor_id cố định, nguồn chiều cao fixture; XYZ/hướng mặt; không scale người |
| #9 | Đứng/bò/lùi theo đầu/đỉnh/cuối BYĐ; pose proxy chưa đo cơ thể thật |
| #10 | Chọn đạo cụ object_id fixture, chỉnh XY/rộng/sâu/cao qua registry.stage.objects + provenance; stand_in chỉ viewer, không xuất/gửi; không ghi Kho |
| #11 | Một nút phát proxy dùng cùng timeline #17 |
| #13 | Bảng lớp/source gửi; thiếu map/source UNKNOWN, provider/Director/Kho thật tắt |
| #14 | V/R/F/T/Q/Esc/Undo/←→, bảng chọn vật/máy; S chỉ kích thước, Del cảnh báo; bỏ qua phím trong input |
| #15 | Viewer yaw/pitch/pan ngang/zoom độc lập máy, T/Q/F, nhớ theo scene; SVG world projection fixture, chưa chống xuyên map |
| #16 | Registry setup + danh sách shot, diff/revision/undo; approved giữ snapshot, không trần 10 hardcode; chưa đo danh sách lớn |
| #17 | Mốc BYĐ mặc định kéo theo giây, monotonic, cùng sampler; thêm/xóa/curve/K để sau |
| #18 | Clay/map/source với nhãn nguồn/preview_only; render/map/Blender/LOD/ray thật chưa nối |
| #19 | hidden/partial/visible theo giây là fixture, ray/QC UNKNOWN; H chỉ viewer, không xuất; adapter prompt/ref thật để sau |

Sửa stage dùng chung chỉ tác động shot chưa duyệt; approved resolve stage snapshot revision đã giữ. Đây là fence fixture cục bộ, không thay thế revision/ACL/change_review production. RAM mất khi refresh ghi ngay header. Chưa chạy ca production.

## Bằng chứng

- Đỏ trước: thêm các hồi quy browser bắt lỗi đã rà và điều khiển thiếu; `test_mockup_ban_dung_d11.py`: **1 failed, 1 passed / 9,03 s** trên bản trước sửa.
- Xanh cuối: **3 passed / 50,00 s**, hai ca môi trường giả thiếu/có credential giả + test nơi ghi ảnh. Môi trường subprocess thay dict trước runtime/imports; không in/so credential; pytest monkeypatch tự teardown. HTML chỉ registry/model fixture; context Chrome mới, mọi request ngoài file bị chặn, không dùng profile người dùng.
- Browser: actor/camera drag 16 tổ hợp yaw0/90 × pitch30/90 × zoom0,7/1,4; world-axis-lock; numeric camera endpoint có hiệu ứng; keyframe monotonic/sampler; target ở tâm pinhole; pending ID/revision; approved shot/SVG bất biến khi stage đổi; props/undo; baseline/diff/undo.
- QA Chrome 1440/1280 hai góc: **console0 / overflow0**. Bốn PNG `docs/images/d11/ban_dung_*.png` recapture có chủ ý sau xanh; pytest luôn ảnh thư mục tạm.
- Baseline c5544891 và bản mới cùng fixture đổi lens hai shot + xem máy: **5/5 thao tác**, chưa chứng minh giảm bấm, không gán tiết kiệm giả.
- related_areas: chỉ dashboard_ui, không caller production; **test chậm UI bắt buộc ở bước gộp**. File đã khai areas, giữ version71. Không chạy cả bộ, không gộp/push/main.
