# Dựng (S0.11 lượt 2, 2026-09-29)

> Đọc `README.md` trước. Luật pipeline: `knowledge/editor/editing.md` E1, E4, E7, E9; Đạo diễn Đ2. Nhịp cắt đo bằng `ffmpeg scene` (ngưỡng
> 0,10–0,28 tùy tương phản; cảnh tối / đơn sắc bỏ sót cắt, chớp sáng bắt nhầm).

### Thứ tự ưu tiên khi chọn điểm cắt (Murch — Rule of Six)
- **Cách làm:** cảm xúc > câu chuyện > nhịp > hướng mắt người xem > mặt phẳng 2D / trục > liền mạch không gian 3D; cảm xúc nặng hơn mọi thứ
  khác cộng lại; phải hy sinh thì bỏ **từ dưới lên** (liền mạch 3D trước, rồi trục 180°, rồi nhịp). Murch tự nói (C4, 2020): ông **không kéo
  từng khung** để tìm điểm ra — chạy shot ở tốc độ thật, dừng khi thấy "đúng nhất", làm lại lần hai và phải dừng trúng cùng khung.
- **Có thể phục vụ:** giải tranh chấp giữa nhiều điểm cắt đều "đúng kỹ thuật" · chọn giữa hai bản sinh của cùng một shot (bản đúng cảm xúc /
  nhịp hơn bản "đẹp").
- **Khi hợp / khi không:** thứ tự này là cho khi **có mâu thuẫn**; pipeline còn đặt "nghe rõ thoại, đọc được chữ" lên trên (editing.md tầng 4).
- **Ví dụ:** [06 32.6–36.5s] đối đáp 6 câu hài không cắt theo từng câu — giữ hai phản ứng (cảm xúc / nhịp hài) thay vì quy ước "1 câu 1 shot"
  của [01] (~60% quãng lặng giữa câu trùng một điểm cắt ±0,4 s).
- **Với video AI:** áp dụng ở khâu dựng / chọn bản; không cần ở lúc sinh.
- **Nguồn:** Murch [C4] (đọc trọn); [E1]. **Độ tin:** chắc (nguồn chuyên gia); ví dụ minh hoạ: có thể.

### Nhịp cắt đi theo kịch — hoặc giữ đều theo kênh
- **Cách làm:** độ dài shot đổi theo đoạn (thiết lập chậm → cao trào nhanh → kết chậm), hoặc giữ gần như hằng số suốt phim.
- **Có thể phục vụ:** đổi nhịp để cao trào "vỡ vụn" và kết được "thở" · giữ đều để người xem lướt không bị hụt nhịp (drama thoại).
- **Khi hợp / khi không:** AI drama thoại (10 video) giữ trung vị giữa hai đoạn lệch ≤ 1,2 s; phim ngắn / hành động đổi 2–4×. Tốc độ **theo
  kênh**: AI drama nhanh 27–33 shot/phút (01, 10, 11, 15) hoặc vừa 16–25 (06, 07, 12, 13, 14); "video AI" không kéo theo "cắt nhanh" (09: 4,66 s).
- **Ví dụ:** [17] 2,96 s → 0,75 s (50 shot ≤ 0,5 s trong 76 s đấu súng) · [02] 3,7 s mở → cụm bạo lực 120.8–163.4 s có shot 0,37–1,0 s · [05 168.5–210.1s] sau
  trung vị 1,19 s kết bằng shot 16,2 s · [11] 2,00 / 2,13 s · [15] 1,79 / 1,85 s.
- **Với video AI:** độ dài từng shot lên kế hoạch **trước** khi sinh (tránh sinh lại); editing.md E1 "nhịp đổi theo cụm" [E4].
- **Nguồn:** số đo S0.12 (mẫu hình 1); Cutting và cộng sự (2010) [E4]. **Độ tin:** chắc (số đo 17 video, cùng chiều).

### Cụm shot rất ngắn cho một khoảnh khắc giữa nhịp chậm hơn
- **Cách làm:** 4–50 shot dài ≈ ½–⅓ nhịp quanh đó, gom thành một "cú".
- **Có thể phục vụ:** (a) hành động / bạo lực · (b) nén một quãng đường thành một nhịp gấp · (c) **khám phá một vật** (bí mật lộ ra dần) · (d)
  ký ức loé lên · (e) hành động làm minh hoạ cho lời kể.
- **Ví dụ:** (a) [02 120.8–163.4s] · [17 đ2 +99.7–143.1s] 48 shot 0,3–1,1 s · (b) [06 đ2 +62.4–64.3s] 4 shot 0,33 s + 1 shot 0,5 s thành cú "chạy"
  1,9 s · (c) [11 141.9–152.6s] 10 insert 0,3–0,9 s lọ sao giấy → chữ trên sao · (d) [23 đ1] ký ức 0,6–1,1 s giữa shot 12–25 s · (e) [09 27.8–48.4s]
  ~12 shot ~1,5 s dưới giọng kể.
- **Với video AI:** shot rất ngắn giấu lỗi động tác; nhưng mỗi shot vẫn là một lần sinh (clip tối thiểu) → gom nhiều shot một lần sinh (Q9 H5).
- **Nguồn:** mẫu hình 2 `TONG_HOP.md` (7 video). **Độ tin:** khá.

### Tiết chế cắt trong pha hành động — hoặc cắt vụn có chủ đích
- **Cách làm:** giữ shot đủ dài để thấy trọn đòn / trọn không gian, chỉ cắt nhanh ở đoạn nối; hoặc ngược lại cắt vụn khi muốn hỗn loạn.
- **Có thể phục vụ:** khoe vũ đạo thật và cho người xem **cảm lực đòn** · cho thấy chính diễn viên làm đòn · (ngược lại) truyền mất kiểm soát,
  nghịch lý vỡ vụn.
- **Khi hợp / khi không:** Schiff [C3]: mỗi lần cắt mắt và não cần thời gian định hướng lại — hỏi mỗi nhát cắt có cần không; cảnh chật (xe
  buýt trong *Nobody*) vẫn giữ shot để thấy Odenkirk tự đánh. Chỉ giữ lâu khi động tác **đáng xem trọn**.
- **Ví dụ:** [19 đ2 +45.3–94.3s] cỡ rộng, shot 2–7 s, máy đi theo (trung vị 2,52 s, đổi ×1,9) · [03 143.5–165.4s] 21,9 s đánh liền giữa shot ~1,8 s ·
  ngược lại [17 đ2] 0,75 s cắt vụn.
- **Với video AI:** động tác AI dễ lỗi → [suy luận] thường phải ngắn hơn phim thật; muốn giữ lâu thì quay thử rẻ trước (dp.md Q12).
- **Nguồn:** Schiff [C3] (đọc trọn); mẫu 03, 17, 19. **Độ tin:** khá.

### Cắt xen (cross-cutting) — nghe lén, người xem biết trước
- **Cách làm:** xen hai mạch: người nghe ↔ người nói ở chỗ khác; hoặc cảnh A ↔ cảnh B diễn ra cùng lúc.
- **Có thể phục vụ:** người xem nhận tin **cùng lúc** với nhân vật (phản ứng là điểm nhấn) · người xem biết **trước** nhân vật (dramatic irony) —
  biến màn sỉ nhục thành chờ cú "vả mặt".
- **Ví dụ:** [06 đ2 +30.4–59.5s] 4 CU cậu nghe lén xen 6 shot hai người nói; nhạc to lên ở CU phản ứng #12 (41,8 s), không ở câu thoại · [12
  86.6–149.1s] giữa màn sỉ nhục ở tiệc cưới, cắt sang vườn: "người làm vườn" là cha tỷ phú; cắt đúng tiếng gọi "老爷" (85,9 s).
- **Nguồn:** mẫu 06, 12. **Độ tin:** có thể (2 mẫu, 2 ý đồ khác nhau — mỗi ý đồ mới 1 lần).

### Cắt theo câu / cảnh hay theo phách (MV và phim có nhạc)
- **Cách làm:** điểm cắt bám câu hát / câu thoại / đổi cảnh, hoặc bám phách nhạc.
- **Có thể phục vụ:** theo câu / cảnh: hình kể theo lời, tránh máy móc · theo phách: đồng bộ, "đóng đinh" (vũ đạo, cao trào).
- **Khi hợp / khi không:** **"MV = cắt theo beat" không đúng mọi MV** — hai MV kể chuyện đo được không bám phách; MV cũng giữ một shot trọn
  đoạn lời. Là lựa chọn phong cách, trộn được.
- **Ví dụ:** [22 đ1 44–180s] trúng phách 27% = đúng mức ngẫu nhiên 27% · [23 đ1] 39% so với ngẫu nhiên 31% · [08 6–29.9s] một shot trọn 3 câu đầu;
  [08 47.3–67.3s] một CU 20 s trọn điệp khúc 1; [08] cắt trễ đầu câu hát 1,4–1,6 s.
- **Với video AI:** lập bảng câu hát / phách trước khi sinh để mỗi clip đúng độ dài (`music_timing`). **Mâu thuẫn cần duyệt:** editing.md E4
  mô tả cắt theo ô nhịp / phách như cách chính — nên ghi thêm "hoặc theo câu / cảnh".
- **Nguồn:** `cong_cu/beat_align.py` (librosa — có thể lệch pha, cần nghe tai); [E31] (thấp–tb). **Độ tin:** khá (2 MV đo, cùng chiều).

### Mở bằng cảnh tương lai / giấc mơ rồi quay về
- **Cách làm:** 14–27 s đầu là cảnh cao trào (hoặc giấc mơ) của sau này; cắt về "trước đó"; khi truyện đuổi kịp có thể phát lại đúng các khung.
- **Có thể phục vụ:** móc người xem trong 15–30 s đầu · người xem biết điều nhân vật chưa biết · đặt kỳ vọng rồi lật (lãng mạn → hài).
- **Ví dụ:** [10 0–14.2s] đối đầu → cắt vào im lặng · [15 0–18s] nụ hôn crush + bạn thân (Explosion, tim đập) → quay về; phát lại 99.6–155.2 s ·
  [11 0–27s] giấc mơ cầu hôn → tỉnh dậy 28,4 s · biến thể rời rạc không lời: [18 0–13.4s] 6 khung "báo trước" rồi mới vào tên phim.
- **Nguồn:** mẫu hình 11 `TONG_HOP.md`. **Độ tin:** khá (4 mẫu; 3 là AI drama kênh quảng bá).

### Lớp chữ / giao diện / thẻ tên trong hình mang truyện
- **Cách làm:** thẻ tên + quan hệ khi nhân vật mới vào; bình luận livestream / HUD "hệ thống"; đạo cụ có chữ (điện thoại, hợp đồng, giấy viết
  tay); chữ trùng lời hát.
- **Có thể phục vụ:** giới thiệu nhiều nhân vật cùng lúc không cần câu thoại giới thiệu · "đám đông trong truyện" phản ứng thay người xem · bằng
  chứng người xem phải đọc · giải thích luật chơi · khả năng tiếp cận (chữ theo tay đánh vần).
- **Khi hợp / khi không:** giữ đủ lâu để đọc (1,5–9 s); tránh vùng giao diện app (safe_zones.md).
- **Ví dụ:** thẻ tên [10 18.5s, 67.0s], [12 đ1] 6 thẻ trong 90 s, [15 ~0–40s] · giao diện [11 đ2 #1–2] khung livestream giữ 8,4 / 9,2 s, [13 67s,
  đ2 +113.9s] HUD "1/3 → 2/3" · đạo cụ [14 56.5s] xét nghiệm ADN, [17 đ2 ~161s] giấy "Don't PANIC" · [16 đ2 +129.6–147.3s] "YOU'LL BE OK" hiện theo tay ·
  [08 99.3–101.4s] trang đánh máy trùng lời.
- **Với video AI:** làm ở hậu kỳ / ghép (model vẽ chữ kém) — không tốn lượt sinh video.
- **Nguồn:** mẫu hình 12, 14 `TONG_HOP.md`. **Độ tin:** chắc (≥ 8 video).

### Ranh giới tập trong video gộp
- **Cách làm:** mỗi tập 80–130 s kết bằng một "móc" (ảnh, người quát ở cửa, cú ngã) + thẻ "未完待续 / TO BE CONTINUED" hoặc bộ đếm.
- **Có thể phục vụ:** cấu trúc cho nền tảng trả theo tập; mở tập sau bằng cụm ECU + âm nhấn để người vào giữa chừng bắt kịp.
- **Ví dụ:** [11 79.4s, 158.8s] thẻ chồng lên shot giữ 2,3–7,5 s, nhạc **không** ngắt · [11 đ2 +63.1–67.7s] cụm ECU mở tập + Explosion ở cắt 66,6 ·
  [12 104.5s; đ2 +112.2–130.6s] thẻ hết tập; tập sau kết bằng cú ngã / hậu quả · [13] HUD khép mỗi "ca" · [07 50.6–52.4s] thẻ + lặng 7–8 s (khác: có lặng).
- **Nguồn:** mẫu hình 13 `TONG_HOP.md`. **Độ tin:** khá (hình thức đo được; ý đồ: có thể).

### Đoạn kể không lời / montage trên nhạc
- **Cách làm:** một đoạn dài chỉ có hình + nhạc / tiếng thở, không thoại.
- **Có thể phục vụ:** cho người xem sống cùng hoàn cảnh trước khi nghe ai nói · giới thiệu thế giới (công việc, nơi chốn) · kể trọn truyện bằng
  biểu cảm (hoạt hình).
- **Ví dụ:** [09 0–158s] 2:38 đầu không thoại (leo vách, túp lều, vết khắc đếm ngày) · [18 18–93s] montage vườn táo trên nhạc phẳng · [25] 1 câu
  thoại trong 183 s.
- **Với video AI:** tránh bài toán khớp môi; đòi hỏi hình kể được — động cơ + chuỗi hành động rõ trong motion prompt (dp.md Q12).
- **Nguồn:** mẫu 09, 18, 25. **Độ tin:** khá (3 mẫu).
