# Checklist rà motion prompt trước khi gen video
Nguồn: seedance25-prompt-optimization skill (STAGE 15 Final QC) + slide ClipAI "Prompt khó khóa được cảnh quay phức tạp" / "Mô tả rõ cảnh quay bạn muốn" (thư mục Tài nguyên tham khảo). Dùng cho nút "🔍 Rà motion prompt" và cho Claude khi tự viết motion prompt.

## 1. Ý đồ
Giữ đúng câu chuyện, tông, kết của cảnh; thoại quan trọng còn nguyên.
## 2. Nhất quán thực thể
Danh tính từng người rõ; mỗi ảnh tham chiếu có vai trò rõ (@Hình = diện mạo, @Video = chỉ chuyển động/nhịp, không lấy diện mạo); không thể nhầm/đổi người.
## 3. Blocking
Vị trí làm được; hướng nhìn hợp lý; đường di chuyển liền mạch; không "dịch chuyển tức thời" không giải thích.
## 4. Đạo cụ
Ai cầm gì rõ ràng; trao tay được viết ra; liên tục với cảnh trước.
## 5. Máy quay
Chuyển động hiểu được về mặt vật lý; khung hình phục vụ hành động chính; máy không mâu thuẫn blocking.
## 6. Thời gian
Thứ tự sự kiện rõ; mốc giây gắn với nhịp có ý nghĩa; cảnh không bị nhồi quá nhiều việc.
## 7. Ngôn ngữ
Mỗi hành động có chủ ngữ rõ; cảm xúc trừu tượng được đỡ bằng hành vi nhìn thấy được; bỏ chữ thừa; tính từ không thay cho chỉ dẫn vật lý.
## 8. Model đọc được không (Seedance)
Model biết ai làm gì, ở đâu, theo thứ tự nào, ảnh tham chiếu nào đóng vai trò gì.

## 4 kiểm tra mơ hồ BẮT BUỘC cho cảnh `complex` (slide ClipAI)
Một câu tự nhiên như "người khổng lồ đứng phía sau người nhỏ, máy từ từ tiến vào và đi nửa vòng, đến giây thứ 3 người nhỏ ngẩng đầu" vẫn bắt model tự suy luận:
- **Tỉ lệ (scale):** chiều cao, khoảng cách, vật mốc so sánh phải ghi rõ, nếu không tỉ lệ trôi khi máy di chuyển.
- **Vị trí (position):** "phía sau" chưa nói khoảng cách, hướng, ai che ai.
- **Đường đi máy (camera):** "tiến chậm và vòng nửa vòng" chưa nói điểm đầu, tốc độ, độ cao, điểm kết thúc.
- **Thời điểm hành động (timing):** "ngẩng đầu ở giây thứ 3" chưa nói lúc bắt đầu, kéo dài bao lâu, tư thế kết thúc.
Chữ vẫn không khóa được quan hệ không gian → dựng trước (previz 2D / bàn đạo diễn 3D / Blender blockout) và gửi kèm làm tham chiếu.

## Không làm
Không dán danh sách negative chung chung vào mọi prompt — chỉ cấm những rủi ro có thật của cảnh. Không bịa thêm thoại, không thêm hành động không liên quan.
