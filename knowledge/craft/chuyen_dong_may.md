# Chuyển động máy (S0.11 lượt 2, 2026-09-29)

> Đọc `README.md` trước. Thuật ngữ + cách viết prompt từng chuyển động (pan ≠ truck, zoom ≠ dolly, arc ≠ orbit, roll ≠ dutch…) đã đối
> chiếu ở `research/craft/draft/chuyen_dong_may.md` (Runway [S1], Kling [S3], Luma [S4], StudioBinder [S6] — đọc trọn). Luật pipeline: dp.md Q5.
> Holben (ASC) [C1]: máy chuyển động để **nhấn kịch tính, thêm bí ẩn / hứng thú, hoặc kể truyện** — chọn công cụ theo ý đồ, ngân sách.
> **Giới hạn đo:** OpenCV của S0.12 **không tách được zoom với dolly** (đều là "đổi tỉ lệ") và không tách pan / truck / tilt / pedestal (đều là
> "tịnh tiến"); không đo shot < 0,4 s và cảnh tối. Số "zoom in" của 04–10 là "zoom in + zoom out" (lỗi đo đã sửa từ 11).

### Máy tĩnh (locked-off)
- **Cách làm:** máy không di chuyển; mọi chuyển động nằm ở nhân vật / môi trường.
- **Có thể phục vụ:** để diễn xuất / thoại mang cảm xúc · người xem tự quan sát, máy không "dẫn" · **để nhân vật tự đi vào khung** tạo câu hỏi
  "ai?" rồi trả lời trong cùng shot · làm nền để một chuyển động sau đó có lực.
- **Ví dụ:** [09 0–10s] khung núi trống 6 s → bàn tay kèm tiếng đập → mặt trồi lên, máy đứng yên (09 tĩnh 90%) · [25] tĩnh 61%, chuyển động nằm
  ở đoá hoa · [04, 06, 10, 12] tĩnh 76–83% dưới thoại.
- **Với video AI:** an toàn nhất cho nhận diện (dp.md Q5: 19 clip duyệt); viết khẳng định "locked camera, static shot" [S1]; clip tĩnh vẫn có
  thể tự chèn cảnh lạ đầu / cuối. "Khung trống rồi nhân vật vào" — [suy luận] prompt được, chưa thử.
- **Nguồn:** [C1], [S1]; số đo S0.12. **Độ tin:** khá.

### Đẩy vào chậm (push-in / dolly in / zoom in chậm)
- **Cách làm:** máy (hoặc tiêu cự) tiến dần về chủ thể trong shot.
- **Có thể phục vụ:** (a) dồn chú ý vào **vật mang truyện** (bằng chứng) · (b) kéo người xem vào đầu nhân vật lúc họ nhận ra / tỉnh ra · (c)
  "hạ nhiệt" kết phim bằng một shot dài chậm sau chuỗi cắt nhanh · (d) nhấn khoảnh khắc siêu nhiên bằng chuyển động rẻ nhất (zoom trên tranh)
  · Holben [C1]: "slow creep-in" lúc cảm xúc — nhưng tốc độ + chủ thể có thể biến nó thành xâm lấn / đe doạ.
- **Ví dụ:** (a) [07 86.3–100.2s, #19–24] 4/6 shot zoom in trên insert trứng vàng / đen và mặt phản ứng · (b) [11 24.6–33.5s] zoom in 5,1 s vào mặt vừa tỉnh
  mộng ("我做梦了") · [23 đ2] zoom / dolly in chậm ở 35% shot, shot 13–21 s lúc hát (ý đồ: đoán) · (c) [05 168.5–210.1s] đẩy chậm dài tới 16,2 s (#95) khi
  chuyển từ CGI sang game thủ thật · (d) [13 67.5–85.4s] 5 zoom in trên tranh tĩnh dồn vào chỗ "hệ thống".
- **Khi hợp / khi không:** cần một điểm đến rõ (mắt, vật); đẩy vào cùng lúc nhân vật bước tới → lỗi "đi tại chỗ" (dp.md Q5 job 206).
- **Với video AI:** "slow push-in" (Seedance), "dolly forward" (Kling); muốn không đổi phối cảnh thì tả "camera stays in place, lens zooms";
  với ảnh tĩnh làm zoom hậu kỳ (13) là rẻ nhất.
- **Nguồn:** [C1], [S1][S3]; mẫu 05, 07, 11, 13, 23. **Độ tin:** khá (5 mẫu, 4 ý đồ khác nhau).

### Lùi ra (pull-out / dolly out) để lộ không gian
- **Cách làm:** máy lùi dần, khung mở rộng.
- **Có thể phục vụ:** trả lời chậm câu "nhân vật đang ở đâu / bị gì" · buông, bỏ lại · kết cảnh.
- **Ví dụ:** [08 0–29.9s] máy lùi dần từ mặt ra toàn phòng trắng (bị buộc giữa phòng) suốt 3 câu hát đầu · [23 0–31.7s] zoom out trên cảnh ký
  giấy (OpenCV) · [18 đ2 +71–98s] zoom out trong đêm (OpenCV, thiếu dữ liệu cao).
- **Nguồn:** mẫu 08 (thấy bằng mắt), 18, 23 (chỉ OpenCV). **Độ tin:** có thể (1 mẫu chắc bằng mắt).

### Bám theo / tịnh tiến theo chủ thể (tracking, truck, follow)
- **Cách làm:** máy di chuyển theo người / vật đang chuyển động, giữ cỡ gần như không đổi.
- **Có thể phục vụ:** (a) cho thấy **trọn động tác thật** (võ thuật) thay vì cắt vụn · (b) đi cùng nhân vật để người xem "ở cạnh" · (c) máy trôi
  chậm cho truyện nghiêm "điện ảnh" hơn.
- **Ví dụ:** (a) [19 đ2 +45.3–94.3s] đánh nhau cỡ rộng, shot 2–7 s, tịnh tiến 43% · (c) [14] tịnh tiến 38–49%, shot 10–12,7 s · [11] tịnh tiến
  18–29% trong drama hài.
- **Với video AI:** nhân vật di chuyển thì để máy **bám theo** thay vì đẩy vào (dp.md Q5); track từng làm áo choàng đổi màu (job 197) — tổ hợp
  người động + máy động là khó cho nhất quán.
- **Nguồn:** [S1][S9][S10]; C3 (Schiff giữ shot để thấy diễn viên tự làm đòn); mẫu 11, 14, 19. **Độ tin:** khá.

### Máy cầm tay (handheld)
- **Cách làm:** máy rung nhẹ theo người quay.
- **Có thể phục vụ:** tức thời, kiểu tài liệu (Holben [C1]: *The Bourne Ultimatum*) · đặt người xem ngay sau lưng người sắp làm điều nguy hiểm ·
  phá vỡ sự ổn định đã dựng ở đoạn mở khi vào cao trào.
- **Ví dụ:** [18 đ2 +21–42s] theo sau lưng khi nhân vật lấy súng rồi vào vườn đêm (thiếu dữ liệu 32% + roll 11% — dấu hiệu máy rung trong tối)
  · [17 đ2 +99.7–143.1s] cao trào tĩnh 17%, roll 21%.
- **Với video AI:** rủi ro nhận diện cao nhất đã đo (job 198, nhận diện 0,20) → dành cho shot không cần mặt rõ; hoặc thêm rung ở hậu kỳ
  [suy luận, chưa thử].
- **Nguồn:** [C1], dp.md Q5; mẫu 17, 18. **Độ tin:** có thể → khá (2 phim quay thật; dấu hiệu gián tiếp qua OpenCV).

### Xoay trục ống kính (roll) trong shot
- **Cách làm:** khung xoay quanh trục ống kính trong lúc shot chạy.
- **Có thể phục vụ:** tăng cường độ thị giác ở chiến đấu / phép thuật · choáng váng, mất thăng bằng · khoảnh khắc "ký ức bị xoá".
- **Ví dụ:** [05 47.2–90.7s] roll + zoom-in ở chiến đấu tia tím / băng (roll 13% toàn phim) · [19 đ2 +45.3–94.3s] roll ×5 trong trận dao ·
  [23 đ2 +34.4–35.4s] roll trên shot "tế bào thần kinh loé sáng", nhạc −60 dB.
- **Với video AI:** Kling có trục "roll" riêng [S3]; pipeline chưa có giá trị `camera_move` roll (đề xuất ở draft mục 5).
- **Nguồn:** [S3][S4]; mẫu 05, 19, 23 (OpenCV). **Độ tin:** có thể (số đo, chưa soi 5–10 khung/giây từng shot).

### Cần cẩu / bay qua không gian (crane, boom, aerial)
- **Cách làm:** máy đổi độ cao (có thể đổi cả hướng) trong một đường liền.
- **Có thể phục vụ:** đi từ toàn cảnh xuống chi tiết then chốt (Holben [C1]: cú hạ cẩu của *Notorious* lộ chi tiết truyện) · nối hai không
  gian như một chuyển cảnh (xem `chuyen_canh.md`) · lập bản đồ nơi chốn từ trên cao.
- **Ví dụ:** [CM 2:20.6–2:21] máy bay lên xuyên đèn chùm rồi hạ xuống mặt bàn (10 khung/giây: liền, không cắt) — đổi sang thế giới siêu thực ·
  [09 #10 69.6–105s] flycam nhìn xuống túp lều (tĩnh).
- **Với video AI:** Seedance hiểu "the camera cranes up through…, then descends to…" (dp.md Q5, G-MV5); một chuyển động chính mỗi shot [Q8].
- **Nguồn:** [C1], dp.md Q12; CM. **Độ tin:** có thể (1 mẫu có chuyển động cẩu thật; 09 chỉ là góc cao tĩnh).

### Cú máy dài không cắt (long take)
- **Cách làm:** một shot dài, máy có thể đi qua nhiều vị trí, không cắt.
- **Có thể phục vụ:** giữ thời gian thực của căng thẳng · khoe một pha võ thuật liền mạch giữa chuỗi cắt nhanh · nhốt người xem cùng nhân vật
  trong một không gian.
- **Ví dụ:** [03 143.5–165.4s] 21,9 s đánh liền giữa cao trào (shot quanh đó ~1,8 s) · [17 8.6–96.3s] có thể một cảnh 87,7 s mở phim (ngưỡng
  0,10 vẫn không có cắt; **chưa xác minh** bằng 5 khung/giây) · [08 6–29.9s] một shot trọn 3 câu hát.
- **Với video AI:** clip sinh ngắn (vài giây tới ~15 s tùy model) → "cú máy dài" phải ghép nhiều lần sinh + nối bằng che máy (`chuyen_canh.md`);
  Holben [C1]: steadicam cho "walk-and-talk" và vũ đạo phức tạp.
- **Nguồn:** [C1]; mẫu 03, 08, 17. **Độ tin:** có thể.

### Vòng cung / quay quanh (arc / orbit)
- **Cách làm:** máy đi đường cong quanh chủ thể (arc không trọn vòng, orbit trọn vòng [S1]).
- **Có thể phục vụ (theo nguồn):** khoe / giới thiệu chủ thể · nhấn cao trào · mất phương hướng.
- **Ví dụ:** chưa đo được trong 21 mẫu (OpenCV không có nhãn vòng cung).
- **Với video AI:** rủi ro biến dạng cao (model phải bịa phía chưa thấy); ghi biên độ ("arcs 30° clockwise").
- **Nguồn:** [S1][S4][S5]. **Độ tin:** giả thuyết.

### Dolly zoom (Vertigo)
- **Cách làm:** dolly và zoom ngược chiều cùng lúc — chủ thể giữ cỡ, nền phồng / co.
- **Có thể phục vụ (theo nguồn):** trạng thái nội tâm, chợt nhận ra, mất phương hướng — Holben [C1] nêu *Vertigo* (Hitchcock), *Jaws* (Spielberg).
- **Ví dụ:** chưa có trong 21 mẫu. **Với video AI:** rủi ro cao; map `push_in`/`pull_out` + ghi ở `why` (dp.md Q5).
- **Nguồn:** [C1], [S8]. **Độ tin:** giả thuyết (nguồn chuyên gia, chưa có mẫu đo).

### Lia nhanh (whip pan)
- **Cách làm:** lia cực nhanh tới mức nhòe — gần như chuyển cảnh trong shot.
- **Có thể phục vụ (theo nguồn):** chuyển năng lượng cao giữa hai điểm nhìn · che điểm nối.
- **Ví dụ:** chưa thấy trong 21 mẫu (nhãn "Whip" trong âm thanh 09, 14 là **tiếng quất**, không phải whip pan). [CM 2:21] có vệt mờ zoom.
- **Nguồn:** [S1][S5]. **Độ tin:** giả thuyết.
