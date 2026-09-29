# Phân tích mẫu prompt khớp môi tiếng Việt (người dùng gửi, 2026-09-29)

Nguồn: ảnh chụp giao diện ClipAI Agent → tab **Reference**, model **Seedance 2.5**, 27 s, âm thanh **On**, ×1, 720p, 9:16;
tài sản: **2 ảnh** (Kelly, Maxim — tờ nhân vật 3D) + **1 video** (Video1: cảnh quay thật một người đàn ông ngồi rửa bát — dùng làm
vũ đạo / vị trí / nhịp) + **1 audio** (Audio1: toàn bộ thoại tiếng Việt của cả cảnh). Nút "Generate Sample" **1,86 USD** (bản mẫu
480p/720p, xem S4.11). Prompt 3.673 / 5.000 ký tự.

## 1. Bố cục prompt (7 khối) — và pipeline đang làm thế nào

| # | Khối trong mẫu | Nội dung | Pipeline hiện tại (`core/seedance_refs.prompt`, `runner`) |
|---|---|---|---|
| 1 | Đầu | khổ 9:16, **độ dài khớp 1:1 với Video1 và Audio1, không kéo giãn thời gian**, phong cách | có "One clip with N shots…"; không nói gì về khớp độ dài với audio |
| 2 | REFERENCE ASSETS | **từng tài sản một vai trò**: Image1 = danh tính Kelly (tả đặc điểm nhận dạng: sẹo má phải, tóc nâu ngắn…), Image2 = Maxim, Video1 = vũ đạo / vị trí / cử chỉ / khung máy / nhịp hành động, Audio1 = thoại, nhịp nói, ngắt, **khớp âm vị → khẩu hình** | có vai trò ảnh (khung storyboard / danh tính); chưa có vai trò video tham chiếu và audio trong prompt |
| 3 | CHARACTERS & BLOCKING | mỗi người: nhãn C1/C2, vị trí trong khung (tiền cảnh trái / trung cảnh phải), tư thế, đạo cụ, tính cách, "khớp Image1" | có blocking trong shot; không gắn nhãn C1/C2 |
| 4 | AUDIO & LIP-SYNC DIRECTIVE | đồng bộ **khẩu hình, hàm, răng, âm vị** của C1 và C2 theo thoại tiếng Việt; phát âm đúng âm tiết, nguyên âm, phụ âm, cảm xúc; **miệng khép khi im lặng** | chỉ một câu "X says the line of the attached voice, lips in sync." |
| 5 | TIMELINE & CHOREOGRAPHY | mốc giây `[00:00 - 00:02]`… mỗi đoạn: hành động (theo Video1) + **"Dialogue (Tên / Lipsync @Audio1): câu nói"** + chỉ đạo mặt khi nói | 2.5 có mốc giây nguyên (S4.8); lời thoại KHÔNG nằm trong prompt video |
| 6 | Lip-sync theo đoạn | câu chỉ đạo diễn xuất mặt cho đoạn nói dài / lẩm bẩm ("continuous grumbling visemes… until end") | không có |
| 7 | CONTINUITY & AVOID | khớp ảnh; **tránh**: mặt anime / cel-shaded, mặt dán, mắt hoạt hình, chữ trên màn hình, phụ đề cháy, watermark, chữ Trung, **miệng đứng yên khi nói**, đổi trang phục | có câu khóa phong cách (S4.3), negative riêng; chưa có "no frozen mouth", "no burned-in subtitles" |

## 2. Các câu nói trong mẫu (ghi lại — nội dung tham khảo)
Mẫu gắn **mỗi câu thoại vào đúng một đoạn giây và đúng một người nói**, viết nguyên tiếng Việt trong prompt (dù phần còn lại tiếng Anh):

| Đoạn | Người nói | Câu nói (tiếng Việt, nguyên văn trong mẫu — tham khảo) | Chỉ đạo đi kèm |
|---|---|---|---|
| 00:00–00:02 | Kelly (C1) | "Anh rửa bát à, để em tráng bát cho." | đứng trái cầm bát, nói nhẹ nhàng |
| 00:02–00:05 | Maxim (C2) | "Phắn! Phắn lên phòng! Biến!" | ngừng rửa, ngẩng phắt lên, cau mày, mắt trợn, vẩy tay dính xà phòng; Kelly giật lùi |
| 00:05–00:06 | Kelly (C1) | "Thế em đi vào nấu cơm nhé." | ngập ngừng, lùi nửa bước, ôm bát trước ngực |
| 00:06–00:19 | Maxim (C2) | đoạn mắng dài ~13 s (mở đầu: "Nào! Đấy là việc của ai hả?…", kết: "…Đi lên nhà, bao giờ cơm chín tôi gọi!") | nhổm người khỏi ghế, chỉ ngón tay / miếng rửa bát vào Kelly; "cơ mặt biến dạng thật, hàm mở theo từng âm tiết giận dữ, KHÔNG méo kiểu 2D" |
| 00:19–00:27 | Maxim (C2) | câu lẩm bẩm cuối (có từ tục — chỉ ghi nhận, không dùng lại) | Kelly quay đi ra khỏi khung trái; Maxim ngồi xuống cọ bát, lắc đầu, lẩm bẩm; "khẩu hình lẩm bẩm liên tục tới hết" |

Nhận xét: đoạn Maxim 00:06–00:19 dài 13 s liền là một **một shot diễn liên tục** — đúng hướng S3.4 (đoạn diễn liên tục), không cắt 1–2 s.

## 3. Vì sao mẫu này khớp môi được (và pipeline hiện tại thì chưa)
1. **Một clip = cả cảnh thoại + một track giọng cả cảnh** (Audio1 27 s, hai người). Pipeline #8 khớp môi *từng shot*, mỗi shot một câu,
   clip 4 s tối thiểu → cắt ghép làm lệch khẩu hình; shot nhóm thì không có giọng.
2. **Câu thoại viết trong prompt, gắn mốc giây và tên người nói** → model biết *ai* mở miệng *lúc nào*. Pipeline chỉ gửi audio,
   không nói câu nào của ai ở giây nào → với hai người trong khung, model đoán người nói.
3. **Video tham chiếu cho vũ đạo** (Video1 quay thật) → cử chỉ, nhịp, khung máy có sẵn; model chỉ "thay người". Pipeline chưa dùng
   video tham chiếu ở đường Seedance nhóm (có bộ video trắng từ GLB tháp — S5.1 — dùng được cho bối cảnh).
4. **Chỉ đạo khẩu hình cụ thể**: hàm, răng, âm vị, miệng khép khi im, cấm miệng đứng yên.
5. **Phong cách "3D CGI tả thực, Unreal Engine 5, da tán xạ"** — lưu ý: pipeline hiện GỠ những chữ này ở dự án in-game (`looks.clean_prompt`,
   luật ff_gameplay_visual.md). Mặt tả thực có lẽ giúp khẩu hình rõ hơn nhưng kéo xa kiểu in-game FF → **cần bạn quyết** cho từng
   dự án (look "tả thực 3D" khác "in-game").
6. Seedance **2.5** (đọc mốc giây nguyên, nhận tiếng Việt — docs ClipAI 09/2026), bản mẫu 1,86 USD để thử trước.

## 4. Đề xuất đưa vào pipeline (liên quan S4.2 / S4.6)
- **Phương án (c) cho A/B khớp môi S4.6**: "cảnh thoại liền" — một clip Seedance 2.5 cho cả đoạn thoại (≤ 15 s/clip theo giới hạn model
  đang dùng; mẫu 27 s → kiểm lại giới hạn 2.5 trên API), audio = track giọng cả đoạn (đã có: TTS từng câu + `voice.place_on_timeline`
  ghép theo mốc), prompt theo 7 khối trên (code dựng từ bảng shot: người nói, câu, mốc giây, blocking), video tham chiếu tùy chọn.
  So với (a) mỗi shot một clip kèm giọng và (b) sync.so hậu kỳ.
- Chữ trong prompt: câu thoại giữ nguyên tiếng Việt; phần chỉ đạo tiếng Anh (như mẫu).
- Thêm vào AVOID: "no frozen mouth during speech", "no burned-in subtitles, no on-screen text".
- Chạy thử bằng **Generate Sample** (rẻ hơn) trước bản đầy đủ — S4.11.
