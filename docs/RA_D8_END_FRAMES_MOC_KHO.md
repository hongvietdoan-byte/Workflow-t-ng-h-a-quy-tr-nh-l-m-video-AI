# Rà Đ8 việc 2 — ảnh mốc Kho của khung cuối

Ngày 11/10/2026; chỉ đọc code và chạy hồi quy bằng CSDL/ảnh tạm. **Chưa thử thật**, không đọc `data/`, không gọi API/Blender. Không sửa `core/end_frames.py` vì #24 đang dùng.

## Đường chọn hiện tại

- `end_frames.tick`: ảnh đầu `images/job_<start_job_id>.png` là ref đầu, role `previous_scene`; nối `assets.scene_references(..., limit=MAX_REFERENCES-1)` từ dữ liệu shot hiện tại, sau đó thêm ảnh kỹ năng cuối nếu có và lọc `runner.sendable_references`. Thiếu/không gửi được ảnh đầu → failed + diag, không gửi.
- `assets.scene_references`: ảnh nhân vật đúng look + OUTFIT đúng chủ thể; bối cảnh được chọn bằng `location_plate` rồi mới `location_landmark`. WS/EWS dùng ảnh `eye_level`/`low_angle`/`high_angle` trong Kho; MS/CU dùng `detail` (hoặc `low_angle`); ECU không nền. `landmark_off_frame` giữ mốc ngoài khung không được gửi. Vì `location_landmark` từ chối shot rộng, có ảnh `detail` cũng không đổi lựa chọn của WS.
- **Không thể kết luận luôn gửi nền 3D:** `tick` không gọi `place_refs.swap_in` hay `location_pack.ensure_plates`; nguồn thực là ảnh trong `asset_images` được chọn như trên. Nó có thể là ảnh rộng/render đã đăng ký trong Kho; code không chứng minh nguồn pixel của ca #24. Nền 3D đúng máy/nhịp cuối không được dựng tại đây. Không có dữ liệu thật để xác nhận ảnh/job #24 cụ thể.
- `prompt_for` gọi builder ảnh đầu với `camera_end=True`, nhưng vẫn nói SAME camera/framing/place/light. Đây là điểm cần rà thêm với máy di chuyển; không sửa trong đợt này. Nhãn Blocking at the end không chứng minh blocking đã chuyển sang nhịp cuối.

## Lỗi và đề xuất sau #24

Ảnh đầu đã giữ bố cục; gửi thêm nền rộng có góc riêng có thể kéo máy ra khỏi ảnh đầu. Khung cuối nên giữ ảnh đầu + bộ nhân vật đúng look + ảnh mốc Kho chỉ tả hình dạng/vật liệu/màu, không bắt chước góc/ánh sáng. Không dùng ảnh nội thất làm mốc ngoài trời (luật đang có trong `assets.location_landmark`).

Sau #24, thêm chính sách ref riêng cho khung cuối sau cờ TẮT: thay **slot nền rộng** bằng `detail` Kho hợp lệ, kể cả WS khi mốc hiện diện; giữ guard mốc ngoài khung/ECU và đúng bối cảnh. Không đổi `assets.location_plate` toàn cục. Nếu thiếu mốc, báo VÀNG có lý do; không tự chọn nền khác góc. Kiểm đủ slot/đọc được ảnh trước đánh số và giữ nguyên sổ chi + `sent_refs`/`sent_package` + `start_job_id`/`usable_path`. Duyệt một ảnh thật trước bật/autopilot.

Hồi quy đặt sẵn: `tests/test_d8_technical.py::test_end_frame_wide_reference_must_choose_landmark`, `xfail(strict=True)` với lý do đợi #24. Dựng ảnh đầu và CSDL tạm bằng fixture end_frames hiện hữu, hai ảnh Kho khác role WS/detail; chạy `end_frames.tick` bằng MockImageProvider và kiểm **gói thực gửi** phải chứa detail, không chứa ảnh rộng. Hiện chưa đạt; sửa xong phải bỏ xfail và thêm guard mốc ngoài khung, thiếu mốc, OUTFIT/đúng look, máy cuối, giới hạn ref. Đây là test luồng, không xác nhận chất lượng thật.

## Phạm vi nối layout_drift cùng đợt

`tools/stage_grid.py:v3_main` gọi `review_stage_round` sau ghi `blocking.json` và trước giải/render. Cả `change_review` và `layout_drift_review` phải ON; baseline từ `--hand`, project từ `inputs.pid`, approved image từ jobs, nhịp/máy từ `shot_specs.json`/`v2.json` baseline. Thiếu đầu vào sinh VÀNG; không dùng lượt sửa gần nhất thay bản đã duyệt. Finding nguồn `layout_drift` vào Tổ rà soát và hộp việc hiện hữu, không bị `refresh_code` tự đóng; hoàn tác bố cục đóng finding cũ.

Đây là producer sân khấu **v3**, chưa bao phủ Dashboard, ghi tay tệp, v2 thuần hoặc `tools/experiments/stage_v2_p24/apply_v4.py`. Trigger `scenes.data` chỉ bắt thay đổi CSDL, không thấy tệp sân khấu; `blocking` trong shot là chữ, không giả thành cấu trúc sân khấu. Sau #24 cần nối API tại các đường ghi chính thức, lưu baseline bất biến gắn job ảnh duyệt, và rà việc mốc/nhịp mới. Chưa gọi API này từ các luồng ấy.

`change_review.blocking` hiện giữ job khi pending event hoặc finding ĐỎ; finding layout_drift chỉ VÀNG theo L13, không tạo event pending/lời gọi Claude, không tự chặn hay tự duyệt. Cờ OFF không đọc baseline/approved qua hook, prompt OUTFIT OFF giống cũ từng byte.
