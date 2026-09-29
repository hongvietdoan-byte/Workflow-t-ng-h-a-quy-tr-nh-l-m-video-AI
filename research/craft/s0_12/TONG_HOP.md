# S0.12 — Tổng hợp quan sát nhiều phim (cập nhật sau 20 video viết file — 18, 19, 23, 25 mới; 7 video đang đo dở, xem "Bàn giao")

> 17 video đã phân tích: 01 AI心動劇場 (AI drama 9:16), 02 TOMORROW / Omeleto (phim ngắn CGI 3D), 03 WARLIKE / BIGFILMS (hành động),
> 04 《我的婆婆是軟柿子》 (AI drama 9:16), 05 RISE Worlds 2018 (cinematic game CGI), 06 《逃不出大哥手掌心》 (AI drama BL 16:9),
> 07 DramaBox "Doting Snake Lord" (AI drama huyền huyễn 9:16, lồng tiếng Anh), 08 "Fortnight" (MV Taylor Swift, quay thật đen trắng),
> 09 《大師兄》 (phim ngắn AI võ hiệp 16:9), 10 DramaBox "Your Dumped Housewife Is Your Boss" (AI drama hiện đại 9:16, lồng tiếng Anh),
> **11** TopDrama "Top Actor… Dating Show" (AI drama hài lãng mạn 9:16), **12** Knight Drama 《剛離婚，首富老爸找上門》 (AI drama "vả mặt" 9:16),
> **13** 《天命神算》 (AI 漫剧 tranh động 16:9), **14** SuperDrama (AI drama trọng sinh 9:16), **15** DramaBox "Wrong Stepbrother" (AI drama 9:16 tiếng Anh),
> **16** FEELING THROUGH / Omeleto (phim ngắn quay thật), **17** STALLED / Omeleto (phim ngắn quay thật, hài sci-fi).
> Theo `knowledge/craft/PHUONG_PHAP_PHAN_TICH.md` mục 1–2: chỉ quan sát thấy ở **≥ 2 video** mới ghi là "mẫu hình bước đầu" (kèm điều kiện, độ tin);
> quan sát 1 video ở nguyên trong file riêng.

## Phương pháp đã đổi qua các lượt (2026-09-29)
- Lượt 1 → 2: bỏ đo trong trình duyệt, **tải đoạn về máy** (yt-dlp, xoá ngay sau phân tích, không vào repo) — điểm cắt `ffmpeg scene`, LUFS / LRA /
  quãng lặng `ebur128` + `silencedetect`. Video 01, 02 đã làm lại toàn bộ.
- Lượt 3: **chuyển động máy per-shot bằng OpenCV** (04–17), **tờ ảnh thưa 1 khung/10–30s** để tìm đoạn lật ngược / cao trào.
- Lượt 3b: **"nghe bằng số" `tools/audio_listen.py`** (demucs tách nhạc / giọng, mức nhạc từng giây, nhãn AudioSet, whisper có mốc) — 06–17 và đo lại 01, 04.
  Khi file tải có hình bắt đầu muộn / sớm hơn yêu cầu (yt-dlp cắt theo keyframe: file đoạn 2 thường dài 160s cho yêu cầu 150s), mốc gốc chỉ **ước tính**.
- Lượt 4: **hình tối / đơn sắc / tương phản thấp** (08, 16, 17) — ngưỡng cắt 0.25 bỏ sót cắt; kiểm lại ở 0.10–0.12; ngưỡng thấp lại bắt nhầm chớp sáng (09, 17).
- Lượt 4: **video gộp có thể lặp tập** (10, 15) — kiểm bằng so điểm cắt **hoặc so chuỗi câu whisper** lệch một hằng số (15: lệch 17.7–17.8s ổn định).
- **Lượt 5 — sửa lỗi đo**: `motion_cv2.py` luôn gắn nhãn "zoom/dolly **in**" cho mọi shot đổi tỉ lệ (lấy trị tuyệt đối trước khi xét chiều). Từ 11 dùng
  `motion_cv2b.py` (`scale > 1` → in, `< 1` → out). **Số "zoom in" của 04–10 thực ra là "zoom in + zoom out"**; tỉ lệ tĩnh / động không đổi.
- Bỏ báo cáo đỉnh âm (true peak): file Opus nén lại có thể vượt đỉnh gốc 1–3 dB — chỉ LUFS / LRA / quãng lặng là đáng tin.
- Bài hát có bản quyền (08, 16): whisper chỉ để lấy mốc câu, không chép / lưu lời.

## Bảng số chung
| Video | Loại | Trung vị shot (đoạn 1 / 2) | Máy tĩnh (OpenCV) | LUFS | Quãng lặng | Nhạc (audio_listen) |
|---|---|---|---|---|---|---|
| 01 | AI drama 9:16 | 1.4–2.0s | (mắt: gần như tĩnh) | −11.2 / −14.6 | 46 / 33 | **20%** (0–90s) |
| 02 | phim ngắn CGI | 3.7s mở → < 1s cụm bạo lực | — | — | 11 / 3 | — |
| 03 | hành động | 4.72s mở/kết, 1.84s đánh nhau | — | — | 1 (toàn phim) | — |
| 04 | AI drama 9:16 | 2.04 / 2.15s | 76% / 83% | −13.4 / −13.5 | 3 / 2 | **98%** |
| 05 | cinematic CGI | 1.19s (toàn phim) | 43% | −16.5 | 7 | — |
| 06 | AI drama 16:9 | 2.60 / 2.97s | 77% / 79% | −19.0 / −19.2 | 0 / 2 | 92–100% |
| 07 | AI drama 9:16 (DramaBox) | 2.50 / 3.68s | 43% / 53% | −13.0 / −15.0 | 17 / 12 | 84–98% |
| 08 | MV quay thật, đen trắng | 2.9s | 59% | −17.2 | 2 | 99–100% |
| 09 | phim ngắn AI võ hiệp 16:9 | **4.66** / 3.37s | **90%** / 65% | −17.6 / −19.5 | 0 / 0 | 100% / 100% |
| 10 | AI drama 9:16 (DramaBox) | 1.76 / 1.42s | 77% / 83% | −15.6 / −14.4 | 44 / 15 | 14–32% / 76% |
| 11 | AI drama 9:16 hài lãng mạn | 2.00 / 2.13s | 61% / 64% | −14.3 / −14.3 | 10 / 10 | 98% / 97% |
| 12 | AI drama 9:16 "vả mặt" | 2.07 / 2.76s | 83% / 69% | **−10.3** / −11.5 | **0** / 4 | 100% / 99% |
| 13 | AI 漫剧 tranh động 16:9 | 2.20 / 2.06s | 76% / 65% (zoom trên tranh 19% / 13%) | −13.4 / −11.2 | 0 / 0 | 100% phẳng ±3 dB |
| 14 | AI drama 9:16 trọng sinh | 2.83 / 3.20s | **47% / 37%** | −9.8 / −12.1 | 18 / 25 | 56% / 69% |
| 15 | AI drama 9:16 (DramaBox, tiếng Anh) | **1.79** / 1.85s | 57% / 74% | −14.0 / −13.9 | **57 / 68** | 69% / 57% |
| 16 | phim ngắn quay thật (đêm) | 5.03 / 2.91s (ngưỡng 0.10) | 62% / 55% | **−24.9 / −22.5** | 6 / 31 | 96% / 94% (nền −44…−48) |
| 17 | phim ngắn quay thật (hài sci-fi) | 2.96s (1 cảnh 87.7s) / **0.75s** | 62% / **17%** | −23.3 / −20.9 | 48 / **1** | 69% / 100% |
| 18 | phim ngắn quay thật (đêm vườn táo) | 2.52s / 4.74↔1.12s (dải ngưỡng) | 49% / 23% | −24.0 / −23.1 | 47 / 22 | 86% / nhạc lên đều |
| 19 | hành động võ thuật quay thật | 4.87 / **2.52s** | 41% / 20% (**tịnh tiến 43%**) | −19.4 / −21.5 | 25 / 13 | 100% / 99% |
| 23 | MV kể chuyện quay thật | 3.40 / 5.42s | 57% / 35% | −10.7 / −10.6 | 0 / 1 | nền −38 → bài hát từ 52s |
| 25 | phim ngắn CGI không lời | 3.96s (trọn phim) | 61% | **−27.9** | 46 | 94% / 53% (nhỏ) |

> Số 19, 23, 25 do phiên 29/09 tối đo (ngưỡng cắt **0.15**); đang dở: 20–22, 24, 26–28 (xem "Bàn giao").

## Mẫu hình bước đầu (≥ 2 video)

### 1. Nhịp cắt: ổn định ở AI drama thoại, đổi mạnh ở phim kể bằng hình / hành động [khá → chắc]
- AI drama (01, 04, 06, 07, 10, 11, 12, 13, 14, 15): trung vị giữa hai đoạn đổi ≤ 1.2s (vd 11: 2.00 / 2.13; 13: 2.20 / 2.06; 15: 1.79 / 1.85). **10/10 cùng chiều.**
- Phim ngắn / hành động (02, 03, 09, **17**): đổi 2–4× giữa thiết lập và cao trào — 17: 2.96s → **0.75s**, 50 shot ≤ 0.5s trong 76s đấu súng.
- **Điều kiện**: dải nhịp của AI drama **khác nhau theo kênh**: nhanh 27–33 shot/phút (01, 10, 11 đoạn 1, 15), vừa 16–25 (06, 07, 12, 13, 14). Phim ngắn quay thật
  mở rất chậm (16: 8 shot/phút; 17 có một cảnh 87.7s). "Video AI" không kéo theo "cắt nhanh" (09).

### 2. Cụm shot ngắn cho một khoảnh khắc giữa nhịp chậm hơn [khá, 6 video]
- 02, 06, 07, 09 (như trước); **11**: 10 insert 0.3–0.9s lộ "sao giấy có chữ" (141.9–152.6s) giữa nhịp ~2s; **17**: 48 shot 0.3–1.1s khi các phiên bản rút súng.
- Điều kiện: ngắn tương đối (≈ ½–⅓ nhịp quanh đó); phục vụ **hành động** (02, 06, 07, 09, 17) **hoặc khám phá một vật** (11).

### 3. Mức "động" của máy: theo kênh / phong cách, không theo thể loại [khá — thêm phản ví dụ]
- Tĩnh 76–83%: 04, 06, 10, 12 (drama "vả mặt" / đời thường). Tĩnh 37–47%: **14** (drama trọng sinh, tông tối, máy trôi chậm ở shot 10–12.7s), 05, 07.
- **14 là phản ví dụ** cho "drama thoại = máy tĩnh": cùng thể loại thoại hiện đại nhưng tịnh tiến 38–49%. 09 (võ hiệp hùng vĩ) tĩnh 90%.
- Phim quay thật ở cao trào: 17 tĩnh 17%, roll 21% (máy cầm tay) — ở đoạn mở 62%.
- **Mẫu hình**: mức động là **lựa chọn phong cách của kênh / người làm** và **đổi theo nhịp kịch** (17), không suy ra từ thể loại. Điều kiện: OpenCV không đo được
  shot < 0.4s, cảnh tối; với tranh động (13) "zoom" là chuyển động hậu kỳ trên ảnh tĩnh.

### 4. Nhạc nền: hai kiểu, theo kênh và theo cảnh [khá, 14 video đo trực tiếp]
- Kiểu A — **nền liên tục**: 04, 06, 07, 09, 08, **11 (97–98%, marimba / accordion hài), 12 (100%, 0 quãng lặng), 13 (100%, phẳng ±3 dB), 16 (nền −44…−48 dB)**.
- Kiểu B — **thưa, bật tắt theo câu / dùng như cú nhấn**: 01 (20%), 10 bi kịch (14–32%), **14 (56–69%, tiếng động thay nhạc), 15 (57–69%, 57–68 quãng lặng / 3 phút)**.
- Một phim đổi kiểu theo cảnh: 10 (bi kịch ↔ tiệc), **17 (đoạn mở thưa 48 quãng lặng ↔ cao trào 100% nhạc, 1 quãng lặng)**.
- **Mẫu hình**: không có luật "AI drama = có / không có nhạc". Kênh chọn kiểu; phim ngắn quay thật dùng độ dày âm thanh như một đường cong kịch (17).
- **Bài học đo [chắc]**: phải tách lớp (demucs); lớp "nhạc" lẫn tiếng động (14: phần lớn là tiếng đập, tát, quất).

### 5. Tắt nhạc ngắn dưới câu / khoảnh khắc then chốt, nhạc về ở (gần) một điểm cắt [khá, 6 video, 9+ lần]
- 06 (84–89s → cắt 90.0), 07 (33–40s), 10 (42–57s → cắt 57.9; 85–87s), **11** (câu chốt cãi yêu 90–92s → nhạc về ở cắt 93.4 — trong **hài**),
  **12** (lặng 79.1–80.6 ↔ cắt 80.2 rồi nhạc trồi −11 dB), **15** (nhạc tắt dưới câu nội tâm then chốt 36–42s, 47–53s; dưới "It was a mistake" 60–70s),
  **16** (lặng 60.8–67.5s → nhạc −16 dB khi xe buýt tới).
- Điều kiện: dùng được cả cho lật mặt (06, 07, 10, 12), punchline hài (11), thú nhận (15), kết nhiệm vụ (16) — **ý nghĩa do ngữ cảnh**; chỉ "nghe" được khi trước đó có nhạc.

### 6. Âm nhấn (đập / nổ / tim đập / nhạc trồi) trùng điểm cắt [khá, 8 video]
- 04, 07, 09, 10 (như trước); **11** Explosion ở cắt 66.6 (đầu lâu); **12** Clang / Whoosh ở cắt 80.2, tim đập 84s; **14** Slap ở cắt 37.9, Explosion 0.59 ở cắt 28.2;
  **15** Explosion 0.81 cảnh mở, tim đập 10s, Ding + Whoosh ở insert hồi ức.
- Tim đập dưới câu lật bài / thú nhận: 07, 10, 12, 15 → **[khá, 4 video]**. Điều kiện: nhãn AST cửa sổ 2s → khớp ±1s.

### 7. Nhạc vào / trồi lên ở shot "mở không gian" hoặc lúc nhân vật "thoát ra" [khá, 6 video]
- 04, 08, 09, 10 (như trước); **12**: shot cửa lớn sáng cháy 14.1s khi cha con bỏ đi, nhạc −11 dB; **16**: nhạc −16 dB khi xe buýt tới; đoạn mở 16 nhạc lên dần
  −49 → −20 dB dưới shot đi bộ dài.
- Điều kiện: MV (08) theo cấu trúc bài hát; ở drama thường đi **sau một nhịp lặng** (12, 16).

### 8. Im lặng ở chỗ chuyển thời gian / thực tại [khá, 5 video]
- 01, 07, 10 (như trước); **11**: lặng 28.6–29.3s đúng cắt 28.4 từ giấc mơ sang tỉnh dậy; **14**: lặng 115.4–117.2 và 123.8–125.6s quanh cảnh trọng sinh.
- Điều kiện: ở video gộp (07) có thể do khâu gộp.

### 9. Shot mở cảnh / mở phim dài gấp nhiều lần trung vị [khá, 8 video]
- 01, 06, 07, 08, 09 (như trước); **12** shot 1 đoạn 2 7.2s; **16** shot mở 25.1s + 21.9s (người đi trong phố đêm); **17** cảnh mở 87.7s (có thể một cảnh dài).
- Điều kiện: phim ngắn quay thật kéo dài nhất (16, 17); AI drama chỉ 2–5× trung vị.

### 10. Âm thanh liên tục ở phim kể bằng hình / hành động / MV [khá, 5 video] — **kèm ngoại lệ**
- 02, 03, 05, 08, 09 (như trước). **Ngoại lệ**: phim ngắn quay thật 16, 17 có **nhiều** quãng lặng ở đoạn mở (6 / 48) — "liên tục" đúng với hành động / MV, không
  đúng mọi phim ngắn. 17 chuyển sang liên tục ở cao trào.

### 11. Mở bằng cảnh tương lai (flash-forward) rồi quay về — **mới, 2 video** [khá]
- 10: 0–14.2s đối đầu → cắt vào im lặng của "cuộc sống thường ngày". **15**: 0–18s nụ hôn của crush và bạn thân (Explosion, tim đập) → quay về trước; khi truyện đuổi
  kịp, **phát lại đúng các khung đó** (99.6–155.2s). Biến thể: **11** mở bằng giấc mơ (0–27s) rồi tỉnh dậy.
- Điều kiện: cả 3 là AI drama kênh quảng bá / gộp tập; móc người xem trong 15–30s đầu.

### 12. Thẻ tên nhân vật trên hình — **mới, 3 video** [chắc]
- 10 (LINDA HASTINGS, JULIAN THORNE), **12** (6 thẻ dọc tên + quan hệ trong 90s), **15** (Jessica — "Haley's best friend", Haley Burns, Derek Treves).
- Điều kiện: dùng khi một cảnh có nhiều nhân vật mới cùng lúc (tiệc cưới, tiệc sinh nhật); thay câu thoại giới thiệu.

### 13. Ranh giới tập hiện rõ trong video gộp — **mới, 3 video** [khá]
- **11**: thẻ "未完待续" chồng lên shot cuối, tập ≈ 79–86s, nhạc **không** ngắt qua ranh giới. **12**: "未完待续" ở 104.5s và 130.6s; kết tập bằng cú ngã / hậu quả.
  **13**: HUD đếm "有效算卦次数 1/3 → 2/3" khép mỗi "ca". 07: thẻ "TO BE CONTINUED" + lặng 7–8s (khác: có lặng). 14: không thấy thẻ trong 120 khung quét.
- Điều kiện: mỗi tập / ca có một móc riêng; thẻ là hậu kỳ.

### 14. Lớp chữ / giao diện trong hình mang truyện — **mới, 6 video** [khá]
- Giao diện: **11** bình luận livestream chạy trên hình (shot giữ 8–9s để đọc), **13** HUD "hệ thống" + đồ hoạ trên mặt (mạch xanh, dấu X đỏ), **16** bong bóng tin nhắn
  nổi trên cảnh phố và chữ "YOU'LL BE OK" hiện theo tay đánh vần.
- Đạo cụ có chữ: **10, 14** insert điện thoại / hợp đồng / xét nghiệm ADN / báo cáo thuốc; **17** giấy viết tay "Don't PANIC", mũi tên trên tường; **16** sổ tay.
- Điều kiện: chữ phải giữ đủ lâu để đọc (1.5–9s). [suy luận] với video AI: phần lớn làm ở hậu kỳ / ghép, không cần model sinh chữ.

### 15. Giọng nội tâm / giọng kể trên CU không mở miệng — **mới, 2 video** [có thể]
- **14**: giọng kể "40 năm hôn nhân" trên cảnh đám tang (0–28.7s); **15**: nội tâm "crush… best friend" (14.3–57s), "who is he?" (đoạn 3).
- Điều kiện: AI drama; [suy luận] tránh bài toán khớp môi và cho người xem vào đầu nhân vật.

### Không dùng được làm mẫu hình: đỉnh âm ≥ 0 dBFS
Đỉnh đo trên file Opus / WebM tải về có thể do giải mã nén lại — bỏ, không suy luận.

## Quan sát chỉ 1 video (chưa đủ điều kiện)
- 17: **một cảnh dài 87.7s** mở phim (ngưỡng 0.10 vẫn không có cắt); motif tiếng **tích tắc / bánh răng** (nhãn AST 0.13–0.36) dưới cảnh mở; góc thấp + súng chĩa thẳng
  ống kính ở cao trào; tông lam ↔ lục tách "phiên bản".
- 16: CU im lặng giữ 10–21s; chữ "YOU'LL BE OK" hiện theo tay đánh vần (chữ phục vụ khả năng tiếp cận); LUFS −25 / LRA 26 LU (dải động rộng nhất).
- 15: insert hồi ức 1–2 shot có Ding + Whoosh chen giữa cảnh hiện tại.
- 14: lặng 8.0s dưới cảnh chờ tin nhắn; chuyển trọng sinh bằng insert lịch.
- 13: một "ca" = ~1.5–2 phút với cấu trúc lặp (toàn cảnh → ECU chẩn đoán → insert bằng chứng → phản ứng → HUD); nhạc phẳng ±3 dB — đối cực của 12.
- 12: cắt xen để người xem biết trước (dramatic irony: "người làm vườn" là cha tỷ phú); nhạc dây kéo lên dưới chuỗi sỉ nhục; LUFS −10.3, 0 quãng lặng.
- 11: nhạc hài (marimba / accordion) cả trong cảnh "nhà ma"; mở tập bằng cụm ECU 0.7–1.5s + âm nhấn.
- 10: insert chớp trời 0.3–0.4s giữa các CU khóc.
- 09: 2:38 đầu không thoại; lộ nhân vật bằng cách để họ đi vào khung tĩnh; sức mạnh qua **hậu quả** (đám mây).
- 08: màu duy nhất trong MV đen trắng; chữ đánh máy trùng câu hát; cắt trễ đầu câu hát 1.4–1.6s.
- 06: đổi nhạc cụ theo nhịp kịch; đối đáp 6 câu trong một shot hai người.
- 04: vật thể (hộp thư, cát-xét) làm phương tiện kể lại quá khứ.
- 02: hai biến cố lớn cách nhau ~10 phút → không chọn đoạn cao trào theo % thời lượng.

## Giới hạn chung
- Chưa nghe bằng tai; audio_listen là "nghe bằng số": lớp "nhạc" lẫn hiệu ứng, nhãn AST điểm thấp → chỉ ở mức "có thể".
- Video gộp dài chỉ đo 3–10% thời lượng; 10 và 15 **lặp nội dung** nên "đoạn giữa phim" có thể là bản lặp.
- Mốc gốc của đoạn 2 (11–19) chỉ ước tính ±10–30s (keyframe). Cách đo chính xác (mới): tải trọn bản 360p rồi tương quan chéo tiếng (`cong_cu/fix_audio.py`)
  — 22 đoạn 2 bắt đầu 2:54.9, 27 đoạn 2 bắt đầu 4:13.8.
- OpenCV không đo được shot < 0.4s, cảnh tối; ngưỡng cắt phải chỉnh theo độ tương phản (16, 17).
- MV mới có 08, 23 viết file (22 và 24 đang đo).
- **Lỗi đo mới (29/09 tối) — tải theo đoạn bị cụt tiếng**: `yt-dlp --download-sections` cho ra file có **tiếng ngắn hơn hình** ở 3/18 đoạn: 22 đoạn 2 (97s/184s),
  24 (107s/164s), 27 đoạn 2 (156s/160s). LUFS / quãng lặng / nhạc của các đoạn này sai ở phần cuối. Đã sửa bằng cách tải trọn bản 360p (client `android`,
  định dạng 18) và ghép tiếng đủ vào hình 720p (`*_segNf.mkv`). **Từ nay phải kiểm độ dài tiếng = độ dài hình trước khi đo.** Các đoạn 11–18 đã xoá media nên
  không kiểm lại được — mọi "quãng lặng kéo tới hết đoạn" ở đó cần coi chừng (chưa thấy kết luận nào dựa vào chỗ đó).
- **Phép đo mới — điểm cắt so với phách** (`cong_cu/beat_align.py`, librosa): 22 (Not Like Us) đoạn bài hát 44–180s: trúng phách 27% = đúng mức ngẫu nhiên 27%;
  23 đoạn 1: 39% so với 31% ngẫu nhiên. **Hai MV kể chuyện đều cắt không bám phách** [khá, 2 video] — ngược dự đoán "MV cắt theo beat" trong MAU_S0_12.
  Điều kiện: librosa có thể dò lệch pha; cần nghe tai một đoạn để chắc.
- Crunch (26): YouTube báo "not available" với client mặc định; tải được bằng `--extractor-args youtube:player_client=android -f 18` (360p).

## Ghi chú thêm cho các mẫu hình (từ 19, 23, 25 — chưa gộp vào bảng mẫu hình phía trên)
- **Mẫu hình 1 (nhịp cắt)**: 19 hành động võ thuật chỉ đổi ×1.9 (4.87 → 2.52s), đánh nhau bằng cỡ rộng + máy đi theo (tịnh tiến 43%) để khoe vũ đạo thật —
  khác 17 (×3.9, cắt vụn). → "hành động = cắt vụn" không đúng mọi phim; tuỳ động tác thật có đáng xem trọn không.
- **Mẫu hình 2 (cụm shot ngắn)**: 23 — ký ức hiện thành cụm 0.6–1.1s, màu khác hẳn, giữa các shot dài 12–25s (thêm 1 video, biến thể "ký ức").
- **Mẫu hình 5 (tắt nhạc dưới khoảnh khắc then chốt)**: thêm 19 (nghỉ giữa trận: nhạc tụt + gong + lặng 17s trên CU ↔ CU) và 23 (nhạc −60 dB đúng shot ký ức bị
  xoá, về **dần** 12s, không đúng điểm cắt) → 8 video.
- **Mẫu hình 7 (nhạc trồi ở shot mở không gian)**: **phản ví dụ 25** — nhạc lên đỉnh ngay TRƯỚC khi thoát ra rồi tụt gần câm (−67 dB) khi khu vườn mở ra.
  Cùng loại khoảnh khắc, cách làm ngược → giữ là "một cách làm", không phải quy luật.
- **Mẫu hình 9 (shot mở dài)**: thêm 19 (xe máy + chữ tên 55s), 25 (24.2s tĩnh ≈ 6× trung vị).
- **Đoạn thiết lập không nhạc / nhạc nhỏ rồi mới vào bài** (18: 16s, 23: 52s, 09): đủ 3 video → ứng viên mẫu hình mới.
- **Kể không lời**: 25 (1 câu / 183s), 09, 18 (montage) — thêm vào nhóm kể bằng hình.

## Bàn giao (phiên 29/09 tối tạm dừng theo yêu cầu người dùng — phiên khác làm tiếp)
- **Đã viết file**: 18 (cả 2 đoạn — dòng Tồn đọng cũ ghi "chưa viết" là sai), **19, 23, 25**.
- **Nơi làm việc + media** (chưa xoá, ~0,4 GB):
  `C:\Users\hongviet.doan\AppData\Local\Temp\claude\D--AI-Video-Pipeline--claude-worktrees-nice-bhabha-e53229\3c4c4228-e947-4768-809f-dd34138821d5\scratchpad\s012\`.
  Bộ công cụ đã chép vào repo `research/craft/s0_12/cong_cu/` (`pipe.py` dùng biến môi trường `REPO`, mặc định `D:/AI-Video-Pipeline`). Hàng đợi đo
  (`q.sh qA.txt / qB.txt / qC.txt`, `THR=0.15`) có thể vẫn chạy nền sau khi phiên dừng — kết quả: `vNN_*_proc.log` (chỉ ghi khi xong mỗi đoạn), `*_result.json`,
  `*_L*_numbers.json`.
- **Trạng thái từng video**:
  - 20 NIGHT SHIFT (đoạn 2 = 3:30–6:00), 21 Kodama (đoạn 2 = 9:50–12:20), 27 The Last Bastion (đoạn 2 = 4:13.8–6:53.8, dùng `v27_seg2f`), 28 RESET (đoạn 2 =
    8:10–10:40): đang / đã đo trong hàng đợi — **chưa viết file**. 28 đoạn 1 đã đo (64 shot, trung vị 2.56s, tĩnh 80%, LUFS −16.8; `so_do/v28_seg1_*`).
  - 22 Not Like Us: đoạn 1 đo xong (93 shot, trung vị 1.46s, 31 shot/phút, LUFS −10.9, nhạc 79%, bài hát vào ~44s; cắt không bám phách) — đoạn 2 đo lại bằng
    `v22_seg2f` (tiếng đủ). **Chưa viết file.**
  - 24 New Born — LUNA (MV làm bằng Kling AI): 111 shot / 164s, trung vị **1.28s**, 40.6 shot/phút, OpenCV thiếu dữ liệu 19% — số âm thanh cũ **sai** (tiếng cụt
    107s); đo lại `v24_seg1f` (0–90 trong qC) + còn phải `py pipe.py listen v24_seg1f en 90 164 song`. **Chưa viết file.**
  - 26 Crunch (CGI, 360p): đoạn 1 đo xong (64 shot, trung vị 2.29s, tĩnh 72%, LUFS −24.9; mở bằng **giấc mơ du hành vũ trụ 0–89.7s rồi tỉnh dậy** vào chuỗi ngày
    lặp lại — cùng họ mẫu hình 11, biến thể "mở bằng giấc mơ" như 11); đang nghe 90–180s (`v26_L90.log`); đoạn 2 = 4:40–7:10 (cắt từ `v26_full.mp4`).
    **Chưa viết file.**
- **Việc còn lại sau khi viết đủ 20–22, 24, 26–28**: cập nhật bảng số + gộp mục "Ghi chú thêm" vào các mẫu hình; `bash clean.sh vNN` cho 19–28 (và xoá
  `v2x_full.*`, `*_segNf.mkv`); nhờ người dùng xoá tay media cũ ở scratchpad phiên trước
  (`...worktrees-danh-gia-devsys-2026-491348\819f89c0-...\scratchpad\s012\` — ~0,25 GB webm 19–28; lệnh xoá tự động bị chặn).

## Tồn đọng (ngoài bàn giao)
- 15: tìm đoạn cao trào thật (video gộp lặp / không theo thứ tự).
- 17: xem ≥ 5 khung/giây shot 8.6–96.3s để chắc là một cảnh; nghe tai lớp tích tắc.
- 10: tìm đoạn giữa phim không lặp và phần kết.
- Đo lại nhạc đoạn 2 của 01 và 04; các phần chưa "nghe bằng số" của 06, 07, 08, 09, 10.
- Người dùng nghe trực tiếp để xác nhận: 06 (84–90s), 07 (73–78s), 10 (14.2–23.2s; 42–57s đoạn 3), 09 (0–30s), 01 (0–90s), **11 (28.4s tỉnh mộng; 90–93s
  đoạn 2)**, **12 (79–86s đoạn 2)**, **17 (tiếng tích tắc 0–90s)**, **23 (đoạn 2 giây 28–46: nhạc tụt khi ký ức bị xoá; cắt có bám phách không)**,
  **25 (116–131s: nhạc tắt khi ra tới vườn)**.

## Đã xoá dữ liệu tải về
01–15: media, khung hình, tờ ảnh, phổ, wav và thư mục tách âm đã xoá sau khi viết file. 16–28: **chưa xoá** (xem Bàn giao).
Số đo JSON (không lời chép, đã bỏ đường dẫn tờ ảnh) của 19, 22 (đoạn 1), 23, 24 (hình), 25, 26 (đoạn 1), 28 (đoạn 1) nằm ở `so_do/`; của 01–18 chỉ còn trong
scratchpad phiên trước.
