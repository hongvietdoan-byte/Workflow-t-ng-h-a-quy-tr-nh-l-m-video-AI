# Khôi phục B và phép so A+/B — Codex 07/10/2026

Người dùng 07/10 chọn khôi phục B, so đủ A+/B sau khi phát hiện luồng đã bị gỡ S14.9. Worktree `D:\AI-Video-Pipeline\.codex-wt\kld-quality` từ origin/main `22f16b7`, làm sau sửa nền `c8f7a69`.

## Thay đổi

- Khôi phục `seedance_sample_mode` (chưa verified), `submit(draft=True)` chỉ Seedance 2.5, ép 480p; final gửi draft_task ở 1080p. Clip thường giữ body, không khóa draft.
- Hộp thử riêng ở tab Video, chọn shot và xác nhận phí từng bước. Chỉ thử 4 giây, 9:16, shot không thoại/không video ref; mục tiêu #22: shot 6 Kelly (scene 253).
- A 720p **0,9245 USD**, B mẫu 480p **0,4112**, final 1080p **2,0801**; tổng **3,4158**, trần cặp **4 USD**. A+ phóng AI cục bộ sau khi lấy A, 0 USD API.
- Kết quả ở `data/projects/<id>/experiments/quality_samples.json` + `quality_<scene>_<kind>.mp4`; không thay jobs/clip v2. Không tự gửi final, không tự gen cả phim.
- Giữ ảnh/motion, look/negative và PLACE của v2; khóa fingerprint prompt/negative/thời lượng/tỉ lệ/cách gửi + byte ảnh. A và mẫu B cùng đầu vào. Final dùng draft đã lưu.
- Final chỉ gửi khi mẫu tải thành công và metadata xác nhận draft 4 giây còn hạn; thiếu/sai/hết hạn → chưa trả tiền.
- Mọi send qua spend_gate + sổ chi `quality_sample`, RLock; paused/out-of-credit dừng. JSON nguyên tử ghi trước POST, task lưu trước polling. Bấm lại không POST lần hai; file hỏng không coi là rỗng.
- Mạng lỗi chưa biết có task chưa: giữ uncertain, không tự thử lại; ledger tạm tính ước lượng, UI yêu cầu đối chiếu task. Không coi chi phí có thể phát sinh là 0.
- Đổi test đã-gỡ theo chốt người dùng, giữ kiểm tra 4 cờ còn bị gỡ; bỏ B khỏi retired topics. Không sửa/xóa bài học thật hoặc phục hồi dòng CSDL đã nghỉ.
- Không đổi key cũ, không RENAMED. Key mới quality_scene/go/refresh. Khai module/test/cờ vào areas.json; version 26 → 27 một lần.

## Bằng chứng

- Đỏ: 3 test adapter lỗi TypeError/thiếu method; 7 test phép so thiếu module. Xanh: **44 qua**, 4,66 giây, gồm adapter, tiền, dữ liệu, retired topics, AppTest.
- AppTest cô lập: hiện ước tính A/B mẫu; final chỉ xuất hiện sau mẫu thành công; không chạm UI thật/API.
- Kiểm #22 chỉ đọc, SQLite sao RAM: scene 253 → 4 giây, reference-only, **4 ảnh**, prompt **1651 ký tự**; hash `3edbfaa338a5691f99eac6e01a86a697b7577a3be20cc30638e5e82efcf651d7`; danh sách có shot 6. Cwd máy chính để đọc đúng ảnh OUTFIT tương đối. Không POST/ghi CSDL thật.
- Cả bộ Windows xanh: `PYTHONUTF8=1 py -m pytest -q -p no:cacheprovider`: **2808 qua, 4 bỏ qua, 66 subtest qua**, 10 cảnh báo Pillow cũ, **869,52 giây (14 phút 29 giây)**. Log `%TEMP%\kld-quality-full.log`.

- Phóng AI cục bộ đã kiểm trên khung Kelly v2 tại 1,5 giây: 720×1280 → Real-ESRGAN x4 → 1440×2560; không gọi API, không thay clip/data. Ảnh đối chiếu `D:\AI-Video-Output\2026-10-07_du-an-22\kiem_thu_phong_AI\kiem_thu_mat_Kelly.png`. Đây chỉ là kiểm công cụ trên v2, chưa phải mẫu A+/B mới.

## Rà hai lượt

Lượt 1 theo skill 2b.5: không nới test, đổi kỳ vọng có chốt người dùng; cờ off và normal body được khóa. UI chỉ đọc ước tính, không paid call khi vẽ. Không đổi verified. data_dir truyền từ C.DATA, thiếu đầu vào báo rõ, JSON sai giữ nguyên. Không sửa sandbox, không bỏ dấu để so, không đọc nhãn thành prompt.

Lượt 2: access → feature → trần → trạng thái cũ → metadata/hash → spend_gate → JSON trước POST → POST → task → ledger. Kiểm RLock lồng, bấm lại, mạng lỗi, paused, hết hạn. Bắt/sửa: thiếu look/negative v2; lọc shot thoại/video ref tránh thiếu giá; candidates cần data_dir thật; hash phải có negative; giữ phí chưa xác định. Không migration hay tự gen lại.

## Còn mở

Chưa API trả phí, chưa có A+/B thật. Quyền site đã lưu vẫn chặn localhost:8501 dù người dùng mở tab/yêu cầu tiếp tục. Không dùng đường vòng. Người dùng cần Settings → Browser → bỏ localhost khỏi Blocked sites. Sau đó backup → bật cờ UI → chọn shot 6 → gửi A/mẫu B → lấy kết quả → final B → phóng A 1440×2560 → cắt cận mặt cùng giây → người dùng chọn trước cả phim. Chưa kết luận final giữ chuyển động/độ nét tốt hơn.
