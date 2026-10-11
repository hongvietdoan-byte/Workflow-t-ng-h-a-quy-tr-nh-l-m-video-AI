# Rà ĐỢT 6 việc 2 — công cụ nhịp ref

Nhánh `codex/d6-viec2-ref-beats` · nền `858804f` · code `4a0c638`.

- `tools/ref_beats.py <video>`: JPG 2 fps có mốc giờ + mẫu `.beats.json` cạnh nguồn theo `ref_beats_path`; mẫu phải được người xem điền trước `--check`. Không tự phân tích nội dung bằng AI.
- Cờ `ref_beats_tool` mặc định TẮT; main và generate từ chối trước đọc nguồn/ffmpeg/ghi. Bật thử CLI bằng `$env:FEATURE_REF_BEATS_TOOL='1'` (preset/settings nếu có ưu tiên hơn env). Không sửa settings thật, không nối vào pipeline.
- Lệnh sử dụng khi bật: `py tools/ref_beats.py "D:/thu_muc_tam/ref.mp4"`; điền mẫu rồi `py tools/ref_beats.py "D:/thu_muc_tam/ref.mp4" --check`. Tạo lại cả cặp cần `--force`.
- Schema khớp core: nhip gồm ten/tu_s/den_s/mo_ta/tu_khoa/bien_do; biên độ toan_than/nua_tren/mat, chi_tiet là object list. Từ khóa/mô tả không rỗng, thời gian finite/thứ tự/bounds, tên không trùng.
- Rà độc lập tìm 4 P2: enum không khớp, huge integer OverflowError, ảnh portrait gây JPG/RAM quá lớn, extract thiếu timeout/cap khung. Đã sửa gom một vòng. Root đọc lại phần sửa theo skill 2b.5.
- Trần: 300 giây, 600 khung, frame ≤240×240, sheet ≤40 triệu pixel / cạnh 65500; đo timeout 30s, extract 60s và một khung dư để phát hiện metadata sai. Vượt báo rõ, không cắt im lặng.
- URL bị từ chối; ffmpeg chỉ cho protocol file. Đây là giới hạn protocol, không phải sandbox OS. Không gọi API/Blender.
- Extract/compose xong mới publish. Không force dùng hardlink không overwrite; force backup rồi publish; lỗi thông thường rollback cặp. Không hứa transaction bền vững qua mất điện/crash giữa hai file; đây là tool thủ công, cần kiểm cặp nếu bị ngắt giữa publish.
- Đỏ đầu ImportError; hồi quy rà **9 failed / 17 passed → xanh**. Lệnh cuối `PYTHONUTF8=1 py -m pytest -q -p no:cacheprovider tests/test_ref_beats_tool.py tests/test_p24_lessons_1110.py` → **62 passed / 1,31s**, gồm portrait ffmpeg thật/TMP, CWD khác, schema, OFF, thư mục đầu ra, rollback, timeout/khung dư giữ cặp cũ. `git diff --check` xanh.
- Module mới khai areas, giữ version 48. Related areas mới có features: không thay caller nào, chỉ thêm flag, các consumer flags hiện hữu giữ nguyên; bên Claude chạy cả bộ Windows trước gộp (test chậm bắt buộc ở bước tích hợp do features dùng chung).
- Chưa thử ref sản xuất, chưa chạy cả bộ hoặc gộp main. Không đổi TODO/PLAN/dashboard/runner/lock_exceptions/data, không restart máy chính.
