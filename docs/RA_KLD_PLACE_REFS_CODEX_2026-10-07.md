# Rà sửa nền video Khủng Long Đỏ — Codex 07/10/2026

Phạm vi: mục 1 của bàn giao Khủng Long Đỏ #22 trong TODO; bổ sung render địa điểm cho đường Seedance chỉ ảnh tham chiếu. Worktree `D:\AI-Video-Pipeline\.codex-wt\kld-place-refs`, gốc `e3d76f5` từ `origin/main` sau fetch.

## Lỗi và thay đổi

- Trước sửa: `VideoRunner._reference_pictures` chỉ gửi storyboard + mặt/trang phục. `place_render_refs` chỉ phục vụ gen ảnh, video không nhận render 3D.
- Sau sửa: thêm render cuối danh sách, giữ số ảnh mặt/trang phục; prompt chỉ rõ Image N quyết định kiến trúc của Shot tương ứng. File render dùng chung chỉ gửi một lần; render khác góc giữ ánh xạ riêng.
- Cùng hàm `seedance_refs.place_pictures` dùng cho prompt, danh sách gửi và kiểm tra trước gửi. Cả đường ảnh đánh dấu và Subject Library đều nhận render.
- Thiếu render của nơi có mô hình 3D hoặc quá 9 ảnh: chặn trước provider, nêu cách khắc phục; không tự bỏ trang phục, không tự gọi Blender hay API.
- Cờ tắt giữ prompt/danh sách như cũ. Không đổi widget, không có RENAMED; không thêm file mã; `devsys/areas.json` tăng 25 → 26 một lần.

## Bằng chứng

- Đỏ trước: 2 test `test_place_render_reaches_video_and_its_image_number_matches_prompt`, `test_place_render_cannot_silently_drop_outfits_or_overflow_provider_limit` đều đỏ (render không được gửi, vượt ảnh không bị chặn).
- Xanh sau: nhóm `test_seedance_refs`, `test_place_refs`, `test_trial_fixes`, `test_skill_route`, `test_group_test`: **97 qua, 2 bỏ qua**, 11,56 giây. Thêm kiểm tra render bị thiếu và đánh số nhiều góc ở đường hosted.
- Cả bộ Windows: `PYTHONUTF8=1 py -m pytest -q -p no:cacheprovider`: **2796 qua, 4 bỏ qua, 66 subtest qua**, 843,46 giây (14 phút 03 giây), 10 cảnh báo Pillow cũ, không lỗi. Log tại `%TEMP%\kld-place-full.log`.
- Kiểm tra dữ liệu thật **chỉ đọc**, sao SQLite vào RAM để helper không ghi diagnostics vào CSDL thật: shot 6 (scene 253) có 4 ảnh, render Image 4; shot 7–9 (254–256) mỗi shot có **6 ảnh**, render **Image 6**, giữ đủ mặt và OUTFIT của Maxim/Kelly. Render thực ghi spot `nha_lon_dong`; cả ba dùng chung cache `98ae410409fd641bbed0/plate.png`.
- Kiểm này chạy với thư mục hiện hành máy chính vì ảnh OUTFIT trong dữ liệu hiện tại dùng đường dẫn tương đối. Đọc từ worktree thiếu các file thật; không coi kết quả đó là đầu vào của Dashboard.

## Tự rà mục 2b.5 — lượt 1

Không nới test; không đổi cờ mặc định; không đụng key widget; không đọc nhãn thành nội dung; không thêm truy cập mạng. Dùng data_dir của runner để lấy index, không hard-code dự án #22. Giữ luồng skill riêng và first-frame. Chặn quá ảnh có thông báo rõ cho luồng hàng loạt/tự động, không cắt danh sách âm thầm. Chưa sửa dữ liệu thật hoặc gọi trả phí.

## Rà kỹ lượt 2 — đường gửi và tiền

Đọc lại diff từ góc độ thứ tự gọi: `_submit_pending` → `_blocked` → `_ref_lint` chạy trước `_submit_kwargs`, Subject Library và `provider.submit`. Job đã có external_id vẫn lấy kết quả đã trả tiền theo cơ chế hiện hành, không gửi lại. Đối chiếu số slot ở cả ba chỗ; sửa chênh lệch cũ giữa số frame có file và số shot dự kiến. Kiểm lại danh sách trang phục thực của dự án từ máy chính. Không phát hiện lỗi còn chặn gộp trong phạm vi diff; cả bộ Windows xanh.

## Giới hạn và bàn giao

Chưa có bằng chứng video thật giữ nền tốt hơn: cần gen và xem chuyển động sau khi triển khai. Nhóm nhiều shot vượt 9 ảnh phải tách; không tự đổi bố cục phim. Độ dài prompt vẫn được lint theo model.

Mục 2 có lệch bàn giao: `seedance_sample_mode`/`submit_final_from_sample` đã bị gỡ S14.9, test hiện tại yêu cầu chúng không tồn tại. **Người dùng 07/10 đã chọn khôi phục B và so đủ A+/B**. Làm ở worktree kế tiếp sau khi gộp sửa nền, test đỏ→xanh + cả bộ; kết quả thử riêng, không tự thay clip đã duyệt của phim. Dashboard đang bị quyền trình duyệt đã lưu chặn `http://localhost:8501`; người dùng đang mở lại quyền. Chưa có API trả phí nào trong phiên này.

Chuẩn bị A+ miễn phí: Real-ESRGAN bản Windows 20220424 từ release chính thức `xinntao/Real-ESRGAN` v0.2.5.0, lưu ở `D:\AI-Video-Tools\realesrgan-20220424`. SHA256 ZIP: `ABC02804E17982A3BE33675E4D471E91EA374E65B70167ABC09E31ACB412802D`. Chạy mẫu kèm gói `input.jpg` 220×220 → `verification-x4.png` 880×880 thành công với model `realesrgan-x4plus`; nhận GPU GTX 1070 Ti. Chưa upscale clip dự án, chưa đánh giá độ nét mặt Kelly.
