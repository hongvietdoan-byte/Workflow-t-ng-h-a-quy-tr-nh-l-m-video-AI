# Rà nhẹ Đ13 việc 3 — mockup Tiểu Nhị / pet

- Nhánh `codex/d13-viec3-mockup-pet`, base `1cb845b2`, giữ areas.version 72.
- Phạm vi: hai mockup HTML + test hiện có, không backend/phiếu thật/API.
- ĐỎ: browser chạy JS thật phát hiện quay 1.2 sau 1.3 còn được gen và dáng thường còn 3 phiếu (cả 1440/1280); 1 fail + 2 pass / 10,61s.
- XANH: `py -m pytest -q -p no:cacheprovider --tb=no tests/test_mockup_tieu_nhi_d7.py tests/test_mockup_video_3cot.py`: 7 pass / 9,75s.
- Set lưu đầy đủ snapshot fields + draftPackage; chặn tại preview và gen. Chỉ nhớ trong phiên mockup.
- Pet chuyển dáng ẩn/khôi phục ticketList, nút chỉ mô phỏng mở Dashboard.
- Kiểm browser: sửa ngay hai lỗi gói, duyệt dữ liệu trước duyệt tiền riêng, gen một lần, quay đầu vào cũ bị chặn, khoảng cách âm không hợp lệ, câu báo admin đúng, pet không nút Duyệt.
- 1440/1280: 0 lỗi JS/console, 0 overflow ngang, chặn request ngoài file. PNG từng lượt ở tmp_path, không ghi đè ảnh tài liệu.
- Browser test gắn slow vì đo >=8s; dùng bundled Node/Playwright + Chrome headless new context, env tiến trình whitelist không kế thừa khóa.
- `related_areas.py`: dashboard_ui; không caller module/cờ dùng chung. Test slow bắt buộc khi gộp: ui_v2_acceptance.
- Tự rà 2b.5: không nới assert cũ; ROOT tuyệt đối; không tự động/batch/default backend; không so chữ bỏ dấu; không gọi mạng/tiền; không đổi nhãn thành nội dung.
- Chưa chạy cả bộ Windows/chưa thử sản xuất. Root đọc diff/test/ảnh trước push.
