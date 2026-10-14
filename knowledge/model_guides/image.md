# Viết prompt ẢNH khung đầu (một trang — D6 "đường như chat")

Bạn viết MỘT prompt tiếng Anh cho model vẽ ảnh (GPT Image / Deepix), từ: các ẢNH sẽ gửi kèm (bạn đang nhìn thấy chúng), ý đồ shot của Đạo
diễn, mô tả của người dùng, và "bản code ghép" (dữ kiện).

1. **Ảnh là sự thật, chữ chỉ dẫn đường.** Nền / kiến trúc / bố cục → theo render 3D (ảnh tham chiếu nền). Mặt / tóc / trang phục → theo ảnh
   nhân vật. Đạo cụ / vật mốc → theo ảnh Kho của nó. Đừng tả lại khác ảnh (màu, dáng, cỡ). Chữ cũ trái ảnh → bỏ chữ, theo ảnh.
2. **Giữ nguyên mã đánh số ảnh** ("Image 1", "Images 2/3", "Image 4 is …") đúng số, đúng việc của ảnh đó. Không thêm số ảnh không có.
3. **Một khung hình, một khoảnh khắc**: ai ở đâu trong khung (frame-left / frame-right / foreground / background), cỡ cảnh, hướng máy, đang
   làm gì đúng giây đầu clip, nhìn đâu. Tên nhân vật và tên đạo cụ đúng như trong dữ kiện (vd SKORP, Bom keo) — không viết chung "gun".
4. **Một đoạn văn liền mạch, không mâu thuẫn**: gộp câu trùng, bỏ câu nói ngược nhau (giữ câu đúng với ảnh). Không viết danh sách luật, không
   viết "Fix:" — sửa thẳng vào câu tả.
5. **Mô tả của người dùng thắng ý đồ cũ** khi hai thứ khác nhau; mọi thứ người dùng không nhắc giữ như ảnh đã duyệt / dữ kiện.
6. **Luật cứng giữ nguyên ý**: không tuổi dưới 18; câu khóa nhân vật, câu "giữ đúng nền theo ảnh 1", câu chỉ GỢI máu/xác (nếu có trong dữ
   kiện) phải còn trong prompt (được viết gọn lại).
7. Không chữ tiếng Việt trong prompt. Không giải thích ngoài JSON.
8. **Trái / phải** (thử D6 14/10: "núp bên TRÁI tường keo" ra bên phải ở cả hai bản): trái/phải trong ý đồ là của NHÂN VẬT. Máy sau lưng
   nhân vật → cùng phía khung ("on the frame-left side of the wall"); máy trước mặt → ngược phía khung. Viết rõ "frame-left /
   frame-right" theo ảnh khung đầu, không chỉ "left".
9. **Tư thế đúng chữ kịch bản** (đứng / ngồi / quỳ / nằm): "núp sau tường" khi kịch bản ghi đứng là ĐỨNG nép sát, không ngồi xổm.
10. **Tường keo** cong: hai đầu cong về phía người ném, mặt lồi về hướng địch; cao ~1,2 lần người đứng (~2 m), rộng ~4 m (3–4 lần vai). Mốc không có bộ phận ảnh không có (Tháp Đồng Hồ không có
   mặt đồng hồ → "the tower", không "clock tower").

## Khung đầu của shot DI CHUYỂN (thử D6 14/10 #28/#29 shot 1 — cách nghĩ)
11. **Khung đầu = điểm XUẤT PHÁT của đường đi, có quãng trống theo hướng đi.** Nhân vật sắp đi A→B phải đứng ở đầu đường; phía trước theo
    hướng đi (về phía máy / sang mép khung) là mặt đất trống, đúng chiều dốc. Căn cứ (1 cặp #28/#29, chữ prompt video cũng khác — chưa
    tách, đọc như lý lẽ có căn cứ chứ không phải số đo nhân quả): cùng cỡ người (đo 3D ~56 % khung), #28 vẽ Kelly đã
    đứng TRÊN bậc thang (bậc đi lên xa máy) → "chạy về phía máy" thành chạy tại chỗ (flow 5,8); #29 vẽ ở chân cầu thang, trước mặt là
    sân phẳng trống → chạy thật (13,0). Viết rõ "at the start of her path, open ground ahead of her toward the camera".
12. **Cỡ người đo trên sân khấu 3D thắng chữ "small in the distance"** — đừng viết cả hai (mâu thuẫn). Quãng để chạy tạo bằng CHỖ đứng trên
    đường và khoảng trống trước mặt, không bằng thu nhỏ người.
