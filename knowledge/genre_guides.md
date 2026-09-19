# Knowledge pack — Hướng dẫn theo thể loại (v0.2, bản khởi đầu, cần chuyên gia/người duyệt xác nhận)

Mỗi thể loại gồm: **cảm giác cần có**, **bảng ánh sáng/màu**, **cỡ cảnh & góc máy hay dùng**, **từ khóa tiếng Anh cho image prompt**, **lỗi hay gặp**. Image prompt luôn viết tiếng Anh, cụ thể, không dùng tên IP/nhân vật nổi tiếng.

## 1. Hành động / rượt đuổi (action)
- **Cảm giác:** tốc độ, nguy hiểm, năng lượng liên tục.
- **Ánh sáng/màu:** tương phản cao, bóng đổ sắc, ánh sáng bên hoặc ngược sáng; palette cam–xanh (teal & orange) hoặc bụi xám ấm.
- **Cỡ cảnh/góc:** medium/wide có chuyển động, low angle cho nhân vật mạnh, dutch nhẹ cho hỗn loạn.
- **Từ khóa:** `dynamic pose, motion blur on background, dust and debris, strong rim light, low angle, sense of speed`.
- **Lỗi hay gặp:** tay/chân biến dạng khi vung vũ khí, nhân vật bị nhân đôi, vũ khí đổi hình → mô tả rõ vũ khí đang cầm ở tay nào.

## 2. Kinh dị / u ám (horror, dark)
- **Cảm giác:** bất an, thiếu thông tin, thứ gì đó đang tới.
- **Ánh sáng/màu:** low-key, nguồn sáng nhỏ (đèn pin, nến, trăng), xanh lạnh/xanh lục bệnh, đen sâu, sương.
- **Cỡ cảnh/góc:** wide để nhân vật nhỏ bé; static hoặc push-in chậm; góc thấp phía sau lưng nhân vật.
- **Từ khóa:** `low-key lighting, single practical light source, thick fog, deep shadows, cold desaturated palette, negative space`.
- **Lỗi hay gặp:** quá tối mất chi tiết, mặt méo → nêu rõ nguồn sáng chiếu vào mặt.

## 3. Drama / đối thoại
- **Cảm giác:** cảm xúc thật, gần gũi, nhịp chậm.
- **Ánh sáng/màu:** mềm, ánh sáng cửa sổ, màu ấm hoặc trung tính; tương phản vừa.
- **Cỡ cảnh/góc:** medium, over-the-shoulder, close-up cho cảm xúc; eye level.
- **Từ khóa:** `soft window light, shallow depth of field, natural skin tones, intimate framing, subtle expression`.
- **Lỗi hay gặp:** biểu cảm gượng, hai nhân vật giống nhau → mô tả khác biệt rõ (tóc, tuổi, trang phục).

## 4. Hùng tráng / trailer game (epic)
- **Cảm giác:** quy mô, khí thế, sự kiện lớn.
- **Ánh sáng/màu:** hoàng hôn/bình minh, tia sáng xuyên mây (god rays), vàng cam đối lập xanh lạnh; khói lửa.
- **Cỡ cảnh/góc:** extreme wide cho quy mô, low angle cho anh hùng, crane/orbit khi chuyển động.
- **Từ khóa:** `epic scale, volumetric god rays, low angle hero shot, banners in the wind, layered depth foreground midground background`.
- **Lỗi hay gặp:** đám đông bị hỏng, nhân vật chính lạc giữa nền → tách nhân vật bằng ánh sáng viền.

## 5. Khoa học viễn tưởng / cyberpunk
- **Cảm giác:** công nghệ, đô thị, cô độc hoặc áp lực.
- **Ánh sáng/màu:** neon tím–xanh–hồng, mưa, phản chiếu ướt, khói/hơi nước; tương phản cao.
- **Cỡ cảnh/góc:** wide đô thị, low angle từ đường phố, close-up chi tiết công nghệ.
- **Từ khóa:** `neon signs reflected on wet pavement, rain, volumetric haze, holographic ads, high contrast, cyan and magenta palette`.
- **Lỗi hay gặp:** chữ/biển hiệu bị vô nghĩa → tránh yêu cầu đọc được chữ; thêm "no readable text".

## 4b. Fantasy / phiêu lưu
- **Cảm giác:** kỳ diệu, cổ xưa, thiên nhiên lớn.
- **Ánh sáng/màu:** ánh trăng xanh, ánh sáng ma thuật (rune, phép), sương, lá cây; palette xanh lục–xanh dương–vàng phát sáng.
- **Từ khóa:** `ancient forest, glowing runes, mist between trees, magical particles, cinematic fantasy lighting`.

## 6. Võ thuật / cổ trang
- **Cảm giác:** nhịp, sự chính xác, thiên nhiên.
- **Ánh sáng/màu:** ánh nắng xuyên rừng tre, màu xanh lục–vàng, sương sáng sớm.
- **Từ khóa:** `bamboo forest, shafts of sunlight, flowing fabric, precise martial arts stance, mist`.

## Công thức image prompt (tham chiếu chung)
`[cỡ cảnh + góc máy], [chủ thể: mô tả nhân vật NGUYÊN VĂN từ Character Bible] [hành động cụ thể], [bối cảnh + thời gian], [ánh sáng + nguồn], [bảng màu + mood], [chi tiết chất lượng: cinematic, 35mm, shallow depth of field]`
- 25–70 từ, một cảnh một khoảnh khắc (một hành động).
- Không dùng: tên IP, tên người thật, "in the style of <tác giả còn sống>".
- Thêm ràng buộc an toàn khi cần: `no text, no watermark, no extra people`.
