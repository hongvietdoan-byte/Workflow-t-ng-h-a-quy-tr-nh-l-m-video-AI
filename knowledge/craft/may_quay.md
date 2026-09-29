# Máy quay — cỡ cảnh, độ dài giữ khung, ống kính, độ sâu trường ảnh, ánh sáng, mức "động" (S0.11 lượt 2, 2026-09-29)

> Đọc `README.md` trước (mã mẫu, cách ghi mốc, mã nguồn). Ý nghĩa do ngữ cảnh — mỗi mục liệt kê **nhiều** ý đồ đã thấy, không có nghĩa mặc định.
> Luật đang dùng của pipeline: `knowledge/roles/dp.md` Q1–Q3, Q8 (kho này là tư liệu, không thay các mục đó).

### Cận cảnh làm nền cho thoại (CU / MCU áp đảo)
- **Cách làm:** gần như toàn bộ cảnh đối thoại quay CU / MCU từng người, xen WS rất ít, cắt theo câu.
- **Có thể phục vụ:** giữ mắt người xem trên mặt người nói khi xem lướt điện thoại · kể twist bằng lời thay cho dựng lại sự kiện (rẻ khi làm AI)
  · nhưng cũng có kênh cùng thể loại dùng **hai người cùng khung** để giữ phản ứng của cả hai (xem ví dụ 06).
- **Khi hợp / khi không:** hợp khi truyện đi bằng thoại và định dạng dọc; không hợp khi quan hệ không gian (ai đứng đâu, ai tiến tới ai) là
  thông tin — khi đó cần MS / WS (dp.md Q9).
- **Ví dụ:** [01 0–180s] 107 shot gần như toàn CU, twist (bắt cóc → mẹ ruột → cô dâu thế thân) nằm hết trong cụm CU đối thoại, không quay
  cảnh bắt cóc · [04] máy tĩnh 76–83%, cảm xúc mang bằng thoại · phản ví dụ [06 32.6–36.5s] đối đáp 6 câu ~0,6 s/câu nằm trọn trong **một**
  shot hai người — nhịp hài ở thoại, hình giữ để thấy cả hai phản ứng.
- **Với video AI:** CU một người là shot ít lỗi nhất (1 mặt, ít chuyển động); shot hai người nói liên tục cần khớp môi nhóm (S4.2 `dialogue_take`).
- **Nguồn:** số đo S0.12 (01, 04, 06). **Độ tin:** khá (quan sát nhiều video; ý đồ "giữ mắt" là có thể).

### Giữ khung lâu trên một khoảnh khắc (shot dài gấp nhiều lần trung vị)
- **Cách làm:** một shot dài 4–40 s giữa nhịp cắt 1,5–4 s; máy thường đứng yên hoặc trôi rất chậm.
- **Có thể phục vụ:** (a) thiết lập / mở phim — cho người xem vào thế giới trước khi truyện chạy · (b) giữ **thời gian thực** của nỗi sợ /
  mất mát, không cắt vụn · (c) để diễn xuất không lời mang cảm xúc · (d) "nín thở" trước một cú nổ âm thanh · (e) "thở" giữa chuỗi cắt nhanh.
- **Khi hợp / khi không:** cần khung có đủ nội dung (diễn xuất, thông tin, hành động liền) để "nuôi" thời lượng; drama AI xem lướt chỉ kéo
  2–5× trung vị, phim ngắn quay thật kéo tới 10× — theo kênh / định dạng.
- **Ví dụ:** (a) [16 0–47s] mở bằng 25,1 s + 21,9 s người đi trong phố đêm · [25 0–24.2s] shot mở tĩnh ≈ 6× trung vị · [19] 55 s xe máy + chữ
  tên đoàn phim · [01 đ2 +0–9.7s] shot mở bữa tối ~5× trung vị. (b) [02 đ2 +21.9–80.3s] cận nòng súng 18,7 s rồi CU cậu bé sợ 39,7 s; [02 đ2
  +93.8–129.3s] chó chạy một mình 35,5 s. (c) [16] CU khóc 21,1 s, các CU im lặng 10–14 s. (d) [07 đ2 +64.5–80.3s] ECU mắt rồng 15,8 s, lặng
  73–77,5 s rồi tiếng gầm. (e) [03 143.5–165.4s] 21,9 s đánh liền giữa chuỗi shot ~1,8 s.
- **Với video AI:** clip dài dễ trôi nhân vật / tự chèn cảnh (dp.md Q5 job 196, 204, 205) → shot giữ lâu nên là máy tĩnh + ít động tác, hoặc
  ghép nhiều lần sinh cùng khung; ảnh tĩnh + zoom hậu kỳ là phương án rẻ cho shot "nhìn / chờ" (13).
- **Nguồn:** số đo S0.12 (mẫu hình 9 trong `TONG_HOP.md`, 10 video). **Độ tin:** khá.

### Ống kính rộng / dài (tiêu cự) và khoảng cách máy
- **Cách làm:** chọn tiêu cự + khoảng cách: ống rộng đặt gần phóng to tiền cảnh, giãn chiều sâu; ống dài đặt xa "nén" các lớp, tách chủ thể.
- **Có thể phục vụ (theo nguồn, chưa có mẫu đo):** ngợp / hùng / méo / hài với ống rộng gần; cô lập / rình rập / thân mật với ống dài — cùng
  hiệu ứng nhìn thấy, ý đồ do cảnh (dp.md Q2).
- **Khi hợp / khi không:** méo mặt là do **khoảng cách**, không do tiêu cự (Holben ASC [Q19]); nén chỉ lộ rõ khi khung có nhiều lớp chiều sâu.
- **Ví dụ:** chưa có mẫu S0.12 đo tiêu cự (không đo được từ video). Randy Thom [C2] nêu *The Conversation* dùng ống dài để biện minh cho âm
  thanh chủ quan — ví dụ nguồn, chưa có mốc giây.
- **Với video AI:** tả **hiệu ứng thấy được** ("background compressed close behind her", "wide lens close, foreground large") thay vì chỉ số
  mm; nền 3D thì máy ảo tự lùi / tiến theo mm (`plate_camera`).
- **Nguồn:** Holben "Understanding lens distortion" [Q19] (cao); [C2]. **Độ tin:** giả thuyết cho phần ý đồ (chưa có mẫu); cơ chế quang học: chắc.

### Độ sâu trường ảnh nông / sâu và đổi nét
- **Cách làm:** chọn lớp nét: nông (chủ thể nét, nền nhòe), sâu (mọi lớp nét), đổi nét trong shot (rack focus).
- **Có thể phục vụ:** tách chủ thể khỏi nền đông · giấu nền chưa hoàn chỉnh · dẫn mắt giữa hai lớp · nét sâu khi người xem **phải** thấy mối
  đe doạ ở hậu cảnh — không mặc định là ẩn dụ tâm lý.
- **Ví dụ:** chưa đo trong S0.12 (OpenCV không đo độ nét). [09 đ2 +71.5s] qua vai cậu bé nhìn đám mây khổng lồ — hai lớp cùng đọc được (quan
  sát tờ ảnh, chưa đo nét).
- **Với video AI:** nói lớp nào nét, lớp nào nhòe và vì sao; tránh "bokeh" chung (model vẽ đốm sáng trang trí) — dp.md Q2.
- **Nguồn:** dp.md Q2 [Q3][Q19]. **Độ tin:** giả thuyết (thiếu mẫu có mốc).

### Ánh sáng có nguồn / nguồn sáng duy nhất / màu tách thời điểm
- **Cách làm:** mọi ánh sáng có lý do trong cảnh (đèn, cửa, lửa); có khi chỉ **một** nguồn; màu tổng của khung đổi theo thời điểm / thực tại.
- **Có thể phục vụ:** chỉ cho người xem thấy cái nhân vật rọi tới (đèn pin) · báo "thoát ra / thắng" bằng một khung sáng cháy · tách giấc mơ
  với thực tại, ký ức với hiện tại, "phiên bản" này với phiên bản khác bằng tông màu.
- **Khi hợp / khi không:** tách bằng màu cần tương phản rõ và nhất quán suốt phim; một nguồn sáng làm tối gần hết khung — OpenCV / model khó đọc.
- **Ví dụ:** [18 đ2 +71–98s] đèn pin là nguồn duy nhất + chớp trắng cháy khung (#36–37) · [12 đ2 +80–94s] cửa lớn sáng cháy 14,1 s khi cha con bỏ
  đi · [11 0–27s → 28.4s] giấc mơ đêm xanh lạnh → phòng hồng ấm khi tỉnh · [23 đ1 148.9–180s] ký ức neon / tuyết trắng giữa phòng khám vàng
  nâu · [17 đ2 +79–99.7s ↔ +99.7s trở đi] khúc lam ↔ khúc lục tách vòng lặp · [08 109–113s] màu duy nhất (khói cam + xanh) trong MV đen trắng.
- **Với video AI:** tả nguồn sáng cụ thể (mẫu `lighting` của dp.md Q8); tách tông màu toàn đoạn làm ở hậu kỳ (E5) chắc hơn prompt từng shot;
  giữ màu một vùng (08) làm ở hậu kỳ.
- **Nguồn:** dp.md Q8 [Q27][Q28]; số đo / tờ ảnh S0.12. **Độ tin:** khá (tách tông màu: 11, 17, 23; nguồn sáng một nguồn: 1 mẫu — có thể).

### Mức "động" của máy — lựa chọn của kênh, đổi theo nhịp kịch
- **Cách làm:** tỉ lệ shot máy tĩnh / máy chuyển động trong một phim.
- **Có thể phục vụ:** máy tĩnh để thoại / diễn xuất mang cảm xúc · máy trôi chậm để "điện ảnh hóa" truyện nghiêm · máy cầm tay rung ở cao trào
  để phá vỡ sự ổn định đã dựng ở đoạn mở.
- **Khi hợp / khi không:** **không suy từ thể loại**: cùng AI drama thoại có kênh tĩnh 76–83% (04, 06, 10, 12) và kênh chỉ 37–47% (14); võ
  hiệp hùng vĩ tĩnh 90% (09). Trong một phim, mức động đổi theo nhịp: 17 tĩnh 62% ở đoạn mở → 17% ở cao trào (roll 21%).
- **Ví dụ:** [14] tĩnh 37–47%, shot 10–12,7 s máy trôi chậm, tông tối · [09 đ1] tĩnh 90% · [17] 62% → 17% · [19 đ2] tịnh tiến 43% khi đánh nhau.
- **Với video AI:** máy tĩnh ít lỗi nhận diện nhất (dp.md Q5: 19 clip duyệt; handheld job 198 nhận diện 0,20) — kênh AI tĩnh nhiều có thể một
  phần vì lý do này [suy luận]; 14 cho thấy máy trôi chậm vẫn làm được.
- **Nguồn:** OpenCV S0.12 (mẫu hình 3 `TONG_HOP.md`). **Độ tin:** khá (số đo nhiều video; giới hạn: OpenCV không đo shot < 0,4 s, cảnh tối).
