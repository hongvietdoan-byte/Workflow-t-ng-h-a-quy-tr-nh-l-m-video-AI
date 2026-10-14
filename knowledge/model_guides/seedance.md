# Viết prompt VIDEO Seedance (một trang — D6 "đường như chat")

Bạn viết MỘT prompt tiếng Anh cho Seedance từ: ảnh khung đầu đã duyệt (và khung cuối / ảnh tham chiếu nếu có — bạn đang nhìn thấy chúng),
ý đồ shot, mô tả của người dùng, và "bản code ghép" (dữ kiện).

1. **Bắt đầu từ đúng ảnh khung đầu**: ai đứng đâu, cỡ cảnh, nền — như trong ảnh. Không đổi bố cục, không đổi cỡ người, không thêm người.
2. **Kể chuyển động theo thứ tự thời gian**, động từ thì hiện tại: chủ thể làm gì → rồi gì → kết thúc ở trạng thái nào (đúng khung cuối /
   end_state nếu có). Một chuyển động máy rõ (static / slow push-in / follow…) hoặc nói máy đứng yên; không vừa đẩy vừa lùi.
3. **Không tả lại thứ ảnh đã cho** bằng chữ khác ảnh (màu áo, dáng vật, kiến trúc). Vật kỹ năng / hiệu ứng: theo dữ kiện (vd tường keo xuất
   hiện ngay, không "mọc", không "elevator / door").
4. **Giữ nguyên mã ảnh tham chiếu và khối nhóm shot** ("Image N is …", "Shot 1 / Shot 2 … (x s)", khối thoại) đúng số và thứ tự.
5. **Một đoạn liền mạch, không mâu thuẫn, không "Fix:"** — sửa thẳng vào câu tả. Mô tả của người dùng thắng ý đồ cũ.
6. Luật cứng giữ ý: look in-game (nếu có câu look), câu chỉ GỢI máu/xác, câu cấm dấu vẽ lên mặt, không tuổi dưới 18.
7. Ngắn hơn giới hạn ký tự được cho. Không chữ tiếng Việt (trừ khối thoại tiếng Việt có sẵn trong dữ kiện — giữ nguyên).
8. **Trái / phải** (thử D6 14/10: "núp bên TRÁI tường keo" ra bên phải ở cả hai bản): trái/phải trong ý đồ là của NHÂN VẬT. Máy sau lưng
   nhân vật → cùng phía khung ("on the frame-left side of the wall"); máy trước mặt → ngược phía khung. Viết rõ "frame-left /
   frame-right" theo ảnh khung đầu, không chỉ "left".
9. **Tư thế đúng chữ kịch bản** (đứng / ngồi / quỳ / nằm): "núp sau tường" khi kịch bản ghi đứng là ĐỨNG nép sát, không ngồi xổm.
10. **Tường keo** cong: hai đầu cong về phía người ném, mặt lồi về hướng địch; cao ~1,2 lần người đứng (~2 m), rộng ~4 m (3–4 lần vai). Mốc không có bộ phận ảnh không có (Tháp Đồng Hồ không có
   mặt đồng hồ → "the tower", không "clock tower").

## Chuyển động sống (thử D6 14/10: #29 Claude viết vs #28 code ghép — cách nghĩ, không phải luật)
Căn cứ của cả mục: MỘT cặp #28/#29, nhiều biến cùng đổi (ảnh khung đầu khác, chữ khác), chưa tách nguyên nhân — đọc như giả thuyết có lý.
11. **Kể cơ học của 1–2 bộ phận ở nhịp đỉnh, không chồng tính từ.** Model dựng chuyển động từ thứ thấy được ("right knee driving up,
    arms pumping opposite her legs, torso leaning forward"); tính từ ("full sprint, intense") có thể chỉ đổi nét mặt. Căn cứ: shot 1 chạy
    cầu thang flow 13,0 (#29) vs 5,8 (#28 nhãn rời "Acting — face: …; body: …") — 1 cặp, ảnh khung đầu cũng khác, chưa tách. Giả thuyết
    (chưa đo): nhiều điểm nhấn quá thì model có thể bỏ bớt — ưu tiên bộ phận tạo quãng đường.
12. **Máy nói CHIỀU so với nhân vật**, không chỉ "camera track": chạy về phía máy → "camera tracks backward, holding the same distance";
    máy sau lưng và người đi xa / về phía trước → "follows behind her". Lý do: "camera track" không nói máy lùi hay tiến, model phải tự
    đoán (1 cặp #28/#29, chưa tách khỏi khác biệt ảnh). Chỉ viết chiều khi ảnh khung đầu + ý đồ cho biết (mặt hướng máy, máy sau lưng);
    chạy ngang trái/phải, nhiều người mà không rõ ai chạy, hoặc không rõ → giữ chữ của bản ghép.
13. **Một mệnh đề động cơ + đích** ("sprinting to reach cover before she is spotted") cho model cường độ và nơi đến; trạng thái cuối nói
    chỗ đến + tư thế. Động cơ lấy từ `performance.motive` của ý đồ (dịch sang Anh), không tự bịa.
14. **Hướng đi phải khớp nền trong ảnh.** Đọc ảnh: trước mặt nhân vật theo hướng đi còn bao nhiêu đường, mặt đất lên hay xuống? Bậc thang
    đi lên XA máy thì "chạy lên về phía máy" là vô lý → model chạy tại chỗ / chạy xuống. Viết đúng cái ảnh cho phép (vd chạy trên sân phẳng
    về phía máy) và ghi điều trái ảnh vào "changes".
15. **Nhịp lắng (thở ra, ngồi xuống, núp) vẫn cần một thay đổi thấy được từ giây đầu tới giây cuối.** Shot 5 #29 (flow 1,1 < #28 2,9; 1 cặp):
    ảnh đầu đã ngồi sâu, prompt "lowers further … settled … holds" → gần đứng hình. Hỏi: giây cuối khác giây đầu ở đâu? Ảnh đã ở tư thế
    cuối → chọn chuyển động nhỏ mà thật (vai hạ theo hơi thở, đầu quay nhìn, tay chỉnh súng) + chuyển động nền; "holds" chỉ cho giây cuối.
    Shot 3 (cả hai bản "holds still, head leans out") cũng gần đứng hình (0,1–0,2): "holds still" cả shot = ảnh tĩnh.
