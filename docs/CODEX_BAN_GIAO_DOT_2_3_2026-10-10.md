# Bàn giao Codex — ĐỢT 2 và ĐỢT 3 (10/10/2026)

Đã làm theo thứ tự trên nhánh riêng; chưa gộp main. Không chạy API tốn tiền, Blender thật, sửa data/dashboard.env hoặc khởi động lại dịch vụ.

| Đợt · việc | Nhánh | Commit mã | Bằng chứng test |
|---|---|---|---|
| 2 · 1: hình nhân nằm | codex/d2-viec1-2-san-khau | 08d3e47 | 8 ca mới đỏ→xanh; nhóm hồi quy chung 172 passed |
| 2 · 2: tọa độ và sự thật block | codex/d2-viec1-2-san-khau | 38c4d49 | 3 ca mới đỏ→xanh; nhóm hồi quy chung 172 passed |
| 2 · 3: tấm duyệt và pack | codex/d2-viec3-tam-duyet | 163f378 | Đỏ trước triển khai; 71 passed; đã xem PNG mẫu |
| 2 · 4: mockup và nghiên cứu | codex/d2-viec4-mockup-video | fb51e24 | 4 ca mới đỏ→xanh; nhóm 8 passed; sau sửa trạng thái V3: 4 passed |
| 3 · 1: sổ kế hoạch | codex/d3-viec1-so-ke-hoach | de1dc4a | Đỏ→xanh; nhóm 68 passed, 2 deselected; riêng 6 ca mới passed; slow 2 passed |
| 3 · 2: việc đang chạy | codex/d3-viec2-dang-chay | ed0c445 | Đỏ→xanh; 66 passed, 2 deselected; slow 2 passed |
| 3 · 3: cổng A21 | codex/d3-viec3-cong-a21 | c6b867c | Đỏ→xanh; 69 passed, 2 deselected; riêng 7 ca mới passed; slow 2 passed |
| 3 · 4: mã quy trình | codex/d3-viec4-ma-quy-trinh | 4122f17 | Đỏ→xanh; 106 passed, 2 deselected; slow 2 passed; kiểm lại workflow 43 passed |

Các tổng test là nhóm liên quan từng nhánh, không phải cả bộ và không cộng thành tổng test duy nhất. Dùng Windows, PYTHONUTF8=1, py -m pytest -q -p no:cacheprovider. Kết quả chi tiết nằm trong CODEX_TASKS.md của từng nhánh.

## Khi tích hợp

1. Gộp cả nhánh cùng commit ghi kết quả, theo thứ tự bảng; nhánh đầu chứa hai việc. Không chỉ lấy commit mã rồi bỏ báo cáo.
2. CODEX_TASKS.md, devsys/app.py và areas.json có thể xung đột vì các nhánh độc lập từ main. Giữ đủ kết quả của mọi việc, cả các khối giao diện và danh sách file/test mới. Không dùng nguyên một phía để giải quyết toàn file.
3. Version areas.json chưa tăng ở từng nhánh; tăng một lần ở nhánh tích hợp theo quy ước dự án.
4. Chạy cả bộ Windows trước khi gộp main. Sau đó pull --ff-only ở D:\AI-Video-Pipeline, khởi động lại Dashboard/core và AI Dev System theo AGENTS.md; kiểm health hai cổng.

## Giới hạn còn mở

- Cần xác nhận hình nhân/khối bằng Blender thật; phép chiếu khối là lấy mẫu hình học, chưa thay thế kiểm ảnh render.
- Tấm duyệt hiện là sơ đồ trên xuống và schema pack thuần Python; 2–3 góc clay, nối Kho/Dashboard và ảnh tham chiếu để bên tích hợp làm tiếp. Quyết định mới vẫn bat:false.
- Mockup dùng dữ liệu giả. Nghiên cứu số lần bấm dựa code/AppTest; ngân sách chiều cao và mật độ là tính từ CSS, chưa đo pixel trình duyệt thật. Không coi đó là số đo cuộn thực tế.
- Điểm A21/lỗ hổng phản ánh bản thẩm định mới nhất đọc được; mục “đã sửa” chưa tự động xóa lỗ hổng trước lần thẩm định kế tiếp. Hai lần đầu thiếu điểm build hiện thiếu số đo.
- Tiến độ các kế hoạch ghi chú/phương pháp không có công thức phần trăm được để trống; lỗi đọc có lý do, không đổi thành 0%.
