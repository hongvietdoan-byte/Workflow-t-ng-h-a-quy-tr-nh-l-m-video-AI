# Ca vàng Đ10.6 (cờ ambient_motion) — Nền sống nhẹ, kể cả máy tĩnh

Nguồn: người dùng xem nháp v3 #24 shot 9 ngày 11/10/2026 thấy cảnh đơ. Ca dưới đây tái dựng từ mô tả, không đọc dữ liệu sản xuất.
Máy tĩnh ở sân giếng, ban đêm, trời lặng có sương: nhân vật giữ tư thế, sương lan chậm phía sau; không tự tạo gió mạnh.
Trong nhà: chỉ cho đèn/lửa chập chờn nếu đã có vật đó; không đưa mây vào nhà. Thiếu bối cảnh/thời tiết/giờ phải bổ sung, không bịa.

Cờ ambient_motion mặc định TẮT. ON thêm luật cho Director/DP và bước motion, truyền BYĐ/location/weather/time vào bước motion.
Director ghi nền vào action để đường dịch trung thành sang motion_en.action kế thừa; không sửa dịch hay đường gửi video.
Cần prompt_formula ON để kiểm khi lưu: thiếu chuyển động nền → VÀNG, không chặn gen. Regex nhận chủ thể nền + động từ; chỉ danh từ,
phủ định hoặc nền đứng yên không đủ. Đây là kiểm chữ, không chứng minh video có chuyển động hoặc chuyển động hợp cảnh.
Chưa gọi Claude/video thật. Chưa bật cờ. Chất lượng chọn nền và lý do phải đo qua thử thật được người dùng duyệt tiền.
