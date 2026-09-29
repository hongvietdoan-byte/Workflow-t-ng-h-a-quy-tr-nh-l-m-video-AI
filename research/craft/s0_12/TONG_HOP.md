# S0.12 — Tổng hợp quan sát nhiều phim (cập nhật 2026-09-29 tối: **27 video viết file** — 20, 21, 22, 24, 26, 27, 28 mới; hết phần đo dở)

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
| 20 | hành động quay thật (hẻm Sài Gòn, tiếng Việt) | (đoạn 1 thiếu cắt — cú máy mở **78.9s**) / **1.87s** | 38% / 23% (**roll 14%**) | −21.8 / **−11.6** | 23 / 14 | 89% nhỏ −50 → lên / 97% |
| 21 | hành động samurai + VFX, rất tối | **2.70 / 2.45s** (ngưỡng 0.10; 0.15 bỏ sót nửa) | 25% / 28% | −23.3 / −20.5 | 14 / **0** | 97% / 100% |
| 22 | MV rap kể chuyện | **1.46** / 2.23s | 42% / 20% (zoom 46%) | **−10.9 / −10.8** (LRA 7.5 / 3.0) | 12 / 2 | bài vào ~44s; **cắt không bám phách** |
| 24 | **MV làm bằng Kling AI** | **1.28s** (trọn MV, max 5.8s) | 32% (thiếu dữ liệu 19%) | −16.1 | 0 | hát vào ~36s; **không bám phách** |
| 26 | phim ngắn CGI 3D (360p) | 2.29 / 2.38s | **72%** / 60% | −24.9 / −20.2 | 29 / 14 | giấc mơ rõ ↔ đời thường nhỏ |
| 27 | phim ngắn CGI game, không thoại | 3.48 / 3.81s | **88%** / 53% | **−25.7 / −11.4** (LRA 15 / 25) | 16 / 8 | 71% nhỏ / 100%, vọt −13 dB ở hồi ức |
| 28 | **phim ngắn AI** sử thi | 2.56 / 3.04s (max 6.6s đoạn 1) | **80% / 75%** | −16.8 / −12.3 | 9 / **0** | 96% / 100% + lời kể |

> Số 19–28 do phiên 29/09 đo (ngưỡng cắt **0.15**; 20, 21 kiểm thêm 0.10). 20–28 viết file tối 29/09 (phiên check-current-task-progress).

## Mẫu hình bước đầu (≥ 2 video)

### 1. Nhịp cắt: ổn định ở AI drama thoại, đổi mạnh ở phim kể bằng hình / hành động [khá → chắc]
- AI drama (01, 04, 06, 07, 10, 11, 12, 13, 14, 15): trung vị giữa hai đoạn đổi ≤ 1.2s (vd 11: 2.00 / 2.13; 13: 2.20 / 2.06; 15: 1.79 / 1.85). **10/10 cùng chiều.**
- Phim ngắn / hành động (02, 03, 09, **17**): đổi 2–4× giữa thiết lập và cao trào — 17: 2.96s → **0.75s**, 50 shot ≤ 0.5s trong 76s đấu súng.
- **Điều kiện**: dải nhịp của AI drama **khác nhau theo kênh**: nhanh 27–33 shot/phút (01, 10, 11 đoạn 1, 15), vừa 16–25 (06, 07, 12, 13, 14). Phim ngắn quay thật
  mở rất chậm (16: 8 shot/phút; 17 có một cảnh 87.7s). "Video AI" không kéo theo "cắt nhanh" (09).
- **Hành động (19, 20, 21 — thêm 29/09)**: 19 chỉ đổi ×1.9 (4.87 → 2.52s), đánh bằng cỡ rộng + máy đi theo để khoe vũ đạo thật; 20 từ cú máy mở 78.9s xuống **1.87s**
  trong hẻm hẹp (máy cầm tay, roll 14%); 21 (ngưỡng 0.10) 2.70 → 2.45s. → "hành động = cắt vụn" **không đúng mọi phim**: tuỳ động tác thật có đáng xem trọn không
  và không gian có cho cỡ rộng không.
- **Video AI (24, 28)**: không shot nào > 6s (24: max 5.8s, 40.6 shot/phút; 28: max 6.6s) — mỗi lần gen 5–10s bị cắt lấy phần tốt [khá, 2 video].

### 2. Cụm shot ngắn cho một khoảnh khắc giữa nhịp chậm hơn [khá, 6 video]
- 02, 06, 07, 09 (như trước); **11**: 10 insert 0.3–0.9s lộ "sao giấy có chữ" (141.9–152.6s) giữa nhịp ~2s; **17**: 48 shot 0.3–1.1s khi các phiên bản rút súng.
- Điều kiện: ngắn tương đối (≈ ½–⅓ nhịp quanh đó); phục vụ **hành động** (02, 06, 07, 09, 17) **hoặc khám phá một vật** (11).
- Thêm 29/09: **23** ký ức thành cụm 0.6–1.1s, màu khác hẳn, giữa shot dài 12–25s (biến thể "ký ức"); **24** cắt vụn **cùng một take** 7 × 0.3s (nhấn nhịp không cần
  gen thêm); **26** 8 shot cùng khung đổi tư thế trong 8s + dấu "EXILE" (nén thời gian, hài) → **9 video**.

### 3. Mức "động" của máy: theo kênh / phong cách, không theo thể loại [khá — thêm phản ví dụ]
- Tĩnh 76–83%: 04, 06, 10, 12 (drama "vả mặt" / đời thường). Tĩnh 37–47%: **14** (drama trọng sinh, tông tối, máy trôi chậm ở shot 10–12.7s), 05, 07.
- **14 là phản ví dụ** cho "drama thoại = máy tĩnh": cùng thể loại thoại hiện đại nhưng tịnh tiến 38–49%. 09 (võ hiệp hùng vĩ) tĩnh 90%.
- Phim quay thật ở cao trào: 17 tĩnh 17%, roll 21% (máy cầm tay) — ở đoạn mở 62%.
- **Mẫu hình**: mức động là **lựa chọn phong cách của kênh / người làm** và **đổi theo nhịp kịch** (17), không suy ra từ thể loại. Điều kiện: OpenCV không đo được
  shot < 0.4s, cảnh tối; với tranh động (13) "zoom" là chuyển động hậu kỳ trên ảnh tĩnh.
- Thêm 29/09: CGI **27** tĩnh 88% (rừng yên) → 53% (hồi ức chiến tranh), **26** 72 / 60%; AI **28** 80 / 75%; nhưng AI **24** (MV) chỉ 32% (zoom 24%) → "video AI =
  máy tĩnh" cũng không phải luật; hành động quay thật **20** roll 14%, **19** tịnh tiến 43%.

### 4. Nhạc nền: hai kiểu, theo kênh và theo cảnh [khá, 14 video đo trực tiếp]
- Kiểu A — **nền liên tục**: 04, 06, 07, 09, 08, **11 (97–98%, marimba / accordion hài), 12 (100%, 0 quãng lặng), 13 (100%, phẳng ±3 dB), 16 (nền −44…−48 dB)**.
- Kiểu B — **thưa, bật tắt theo câu / dùng như cú nhấn**: 01 (20%), 10 bi kịch (14–32%), **14 (56–69%, tiếng động thay nhạc), 15 (57–69%, 57–68 quãng lặng / 3 phút)**.
- Một phim đổi kiểu theo cảnh: 10 (bi kịch ↔ tiệc), **17 (đoạn mở thưa 48 quãng lặng ↔ cao trào 100% nhạc, 1 quãng lặng)**.
- **Mẫu hình**: không có luật "AI drama = có / không có nhạc". Kênh chọn kiểu; phim ngắn quay thật dùng độ dày âm thanh như một đường cong kịch (17).
- **Bài học đo [chắc]**: phải tách lớp (demucs); lớp "nhạc" lẫn tiếng động (14: phần lớn là tiếng đập, tát, quất).

### 5. Tắt nhạc ngắn dưới câu / khoảnh khắc then chốt, nhạc về ở (gần) một điểm cắt [khá, 10 video, 13+ lần]
- 06 (84–89s → cắt 90.0), 07 (33–40s), 10 (42–57s → cắt 57.9; 85–87s), **11** (câu chốt cãi yêu 90–92s → nhạc về ở cắt 93.4 — trong **hài**),
  **12** (lặng 79.1–80.6 ↔ cắt 80.2 rồi nhạc trồi −11 dB), **15** (nhạc tắt dưới câu nội tâm then chốt 36–42s, 47–53s; dưới "It was a mistake" 60–70s),
  **16** (lặng 60.8–67.5s → nhạc −16 dB khi xe buýt tới).
- Điều kiện: dùng được cả cho lật mặt (06, 07, 10, 12), punchline hài (11), thú nhận (15), kết nhiệm vụ (16) — **ý nghĩa do ngữ cảnh**; chỉ "nghe" được khi trước đó có nhạc.
- Thêm 29/09: **nghỉ giữa trận** ở phim hành động — **19** (nhạc tụt + gong + lặng 17s trên CU ↔ CU), **20** (nhạc −63 dB + lặng ~20s + CU hai phía, rồi CU đối thủ
  5–7s) — hai phim khác đoàn, cùng cấu trúc; **23** (nhạc −60 dB đúng shot ký ức bị xoá, về **dần** 12s, không đúng điểm cắt); **27** (lặng 5.8s ngay sau loạt bắn).
- **Ngược lại**: 28 để nhạc liên tục (0 quãng lặng) dưới lời kể ở cao trào — lời kể là điểm nhấn, nhạc là nền. 21 trận 160s không quãng lặng.

### 6. Âm nhấn (đập / nổ / tim đập / nhạc trồi) trùng điểm cắt [khá, 8 video]
- 04, 07, 09, 10 (như trước); **11** Explosion ở cắt 66.6 (đầu lâu); **12** Clang / Whoosh ở cắt 80.2, tim đập 84s; **14** Slap ở cắt 37.9, Explosion 0.59 ở cắt 28.2;
  **15** Explosion 0.81 cảnh mở, tim đập 10s, Ding + Whoosh ở insert hồi ức.
- Tim đập dưới câu lật bài / thú nhận: 07, 10, 12, 15 → **[khá, 4 video]**. Điều kiện: nhãn AST cửa sổ 2s → khớp ±1s.

### 7. Nhạc vào / trồi lên ở shot "mở không gian" hoặc lúc nhân vật "thoát ra" [khá, 7 video — 1 phản ví dụ]
- 04, 08, 09, 10 (như trước); **12**: shot cửa lớn sáng cháy 14.1s khi cha con bỏ đi, nhạc −11 dB; **16**: nhạc −16 dB khi xe buýt tới; đoạn mở 16 nhạc lên dần
  −49 → −20 dB dưới shot đi bộ dài.
- Điều kiện: MV (08) theo cấu trúc bài hát; ở drama thường đi **sau một nhịp lặng** (12, 16).
- Thêm 29/09: **20** nhạc −50 → −21 dB (54–88s) đúng lúc tài xế dắt xe ra khỏi hẻm, chạy ra phố. **Phản ví dụ 25**: nhạc lên đỉnh ngay TRƯỚC khi thoát ra rồi tụt
  gần câm (−67 dB) khi khu vườn mở ra — cùng loại khoảnh khắc, cách làm ngược → "một cách làm", không phải quy luật.

### 8. Im lặng ở chỗ chuyển thời gian / thực tại [khá, 8 video]
- 01, 07, 10 (như trước); **11**: lặng 28.6–29.3s đúng cắt 28.4 từ giấc mơ sang tỉnh dậy; **14**: lặng 115.4–117.2 và 123.8–125.6s quanh cảnh trọng sinh.
- Thêm 29/09: **26** tỉnh mơ = 1s đen + nhạc đổi hẳn sang tiếng mưa (89.7s); **28** tắt nhạc 4s + timpani ở chỗ chuyển chiến trường → cung điện (80–84s);
  **21** nhạc tụt −60 ở chỗ đen trước đoạn chữ giới thiệu thế giới (18s).
- Điều kiện: ở video gộp (07) có thể do khâu gộp.

### 9. Shot mở cảnh / mở phim dài gấp nhiều lần trung vị [khá → chắc, 12 video]
- 01, 06, 07, 08, 09 (như trước); **12** shot 1 đoạn 2 7.2s; **16** shot mở 25.1s + 21.9s (người đi trong phố đêm); **17** cảnh mở 87.7s (có thể một cảnh dài).
- Điều kiện: phim ngắn quay thật kéo dài nhất (16, 17); AI drama chỉ 2–5× trung vị.
- Thêm 29/09: **19** (xe máy + chữ tên đoàn 55s), **25** (24.2s tĩnh ≈ 6× trung vị), **20** (**một cú máy liền ~75s** ở đầu hẻm — nghề xe ôm đêm trước khi bạo lực nổ ra),
  **27** (WS rừng máy lướt 17s sau logo). Video AI 24, 28 **không** có (max < 7s).

### 10. Âm thanh liên tục ở phim kể bằng hình / hành động / MV [khá, 5 video] — **kèm ngoại lệ**
- 02, 03, 05, 08, 09 (như trước). **Ngoại lệ**: phim ngắn quay thật 16, 17 có **nhiều** quãng lặng ở đoạn mở (6 / 48) — "liên tục" đúng với hành động / MV, không
  đúng mọi phim ngắn. 17 chuyển sang liên tục ở cao trào.
- Thêm 29/09: **21** trận 160s 0 quãng lặng; **22** MV LRA 3.0; **24** MV AI 0 quãng lặng; **28** đoạn cao trào 0 quãng lặng. Ngoại lệ tiếp: 19, 20 có nghỉ giữa trận (mẫu hình 5).

### 11. Mở bằng cảnh tương lai (flash-forward) rồi quay về — **mới, 2 video** [khá]
- 10: 0–14.2s đối đầu → cắt vào im lặng của "cuộc sống thường ngày". **15**: 0–18s nụ hôn của crush và bạn thân (Explosion, tim đập) → quay về trước; khi truyện đuổi
  kịp, **phát lại đúng các khung đó** (99.6–155.2s). Biến thể: **11** mở bằng giấc mơ (0–27s) rồi tỉnh dậy.
- Điều kiện: cả 3 là AI drama kênh quảng bá / gộp tập; móc người xem trong 15–30s đầu.
- Thêm 29/09: **26** (CGI) mở bằng **giấc mơ du hành vũ trụ 0–89.7s** rồi tỉnh dậy vào chuỗi buổi sáng **lặp lại đúng các shot cũ** → biến thể "giấc mơ" có 11, 26.

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

### 16. Đoạn thiết lập không nhạc / nhạc rất nhỏ rồi mới vào nhạc — **mới 29/09, 7 video** [khá]
- 09 (2:38 đầu không thoại, nhạc nhỏ), 18 (16s), 23 (52s), **20** (nhạc −50 dB tới ~50s dưới cú máy mở), **22** (~40s hành lang tối + gõ cửa + huýt sáo, bài vào ~44s),
  **24** (tiếng tàu + sóng, giọng hát vào ~36s), **27** (23s chỉ tiếng rừng).
- Điều kiện: phim ngắn / MV có thời lượng ≥ 2:30; video 30–60s mạng xã hội thì móc 3s đầu quan trọng hơn — [suy luận] rút lại còn vài giây tiếng môi trường.

### 17. MV: điểm cắt không bám phách — **mới 29/09, 3 MV** [khá]
- 22 (Not Like Us): bài hát 44–180s trúng phách 27% = ngẫu nhiên 27%; cuối MV 22% / 27%. 23: 39% / 31% (đoạn 1). **24** (MV Kling AI, 40.6 shot/phút): 33% / 36%.
- Cắt theo **câu / đổi bối cảnh**; căn cứ sửa `knowledge/editor/editing.md` E4 (2026-09-29). Điều kiện: librosa có thể lệch pha — cần nghe tai.
  22 đoạn mở chưa vào bài (0–40s) lại trúng 44% / 27% — cắt theo tiếng gõ cửa?

### 18. Hồi ức / ký ức đánh dấu bằng màu khác hẳn + đổi âm — **mới 29/09, 2 video** [khá]
- **23**: ký ức thành cụm 0.6–1.1s màu khác, nhạc −60 dB khi ký ức bị xoá. **27**: hồi ức chiến tranh khung đỏ cam, nhạc vọt −13 dB, zoom in dài; về hiện tại bằng
  **CU mắt đổi màu** xanh → đỏ.
- Liên hệ #8 (lỗi "hồi tưởng không có dấu hiệu"): hai cách làm cụ thể, người xem hiểu ngay không cần chữ.

### 19. Kể không lời (hành động + âm thanh) — **mới 29/09, 5 video** [khá]
- 09 (2:38 đầu), 18 (montage), 25 (1 câu / 183s), **26** (CGI, chỉ tiếng động + nhạc), **27** (0 câu thoại trong 340s đo).
- Điều kiện: phim CGI / game và phim ngắn quay thật; truyện đơn giản, một nhân vật chính. [suy luận] với pipeline: tránh được bài toán khớp môi (cùng mẫu hình 15).

### Không dùng được làm mẫu hình: đỉnh âm ≥ 0 dBFS
Đỉnh đo trên file Opus / WebM tải về có thể do giải mã nén lại — bỏ, không suy luận.

## Quan sát chỉ 1 video (chưa đủ điều kiện)
- 28: kể sử thi bằng chuỗi "tableau" tĩnh (hàng quân, thú cưỡi, chân dung) thay vì đánh nhau liên tục — [suy luận] né điểm yếu AI; kết bằng zoom vào khung trắng 19s.
- 27: dải động rất rộng (LUFS −25.7 → −11.4, LRA 25.4) — phim game dám để đoạn yên rất nhỏ.
- 26: tiếng beep báo thức mở cả hai buổi sáng — lặp âm để nhận ra vòng lặp.
- 24: chuyển thế giới qua một vật trong khung (biển quảng cáo sóng → nước tràn sân ga; pha lê nổ → khung trắng → đời thường); khép vòng về sân ga.
- 22: nhiều "thế giới" hình tách hẳn (phòng trắng mù, nền xanh phẳng, phố thật, bãi container) cắt qua lại suốt bài; kết bằng lặng 10s sau khi bài hết.
- 21: giới thiệu thế giới bằng **chữ chạy trên tranh nền ~40s** dưới tiếng ầm trầm, sau đoạn mở nhanh 15s; tiếng kim loại (Clang / Ding) làm nhịp trận kiếm.
- 20: đánh trong hẻm hẹp bằng máy cầm tay (roll 14%, 1.87s) — khác 19 (cỡ rộng, máy đi theo) cùng thể loại; chữ tên đoàn phim chạy trên cảnh chạy xe.
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
- MV có 08, 22, 23, 24 viết file. **Phim ngắn tối (20, 21)**: ngưỡng 0.15 bỏ sót nửa số cắt (21: 29 → 52 ở 0.10); 20 có 46.9s gồm ≥ 6 cảnh mà cả 0.10 không bắt
  (chuyển cảnh hoà / tối) — đếm shot đoạn 1 của 20 **không dùng được**.
- **Lỗi đo mới (29/09 tối) — tải theo đoạn bị cụt tiếng**: `yt-dlp --download-sections` cho ra file có **tiếng ngắn hơn hình** ở 3/18 đoạn: 22 đoạn 2 (97s/184s),
  24 (107s/164s), 27 đoạn 2 (156s/160s). LUFS / quãng lặng / nhạc của các đoạn này sai ở phần cuối. Đã sửa bằng cách tải trọn bản 360p (client `android`,
  định dạng 18) và ghép tiếng đủ vào hình 720p (`*_segNf.mkv`). **Từ nay phải kiểm độ dài tiếng = độ dài hình trước khi đo.** Các đoạn 11–18 đã xoá media nên
  không kiểm lại được — mọi "quãng lặng kéo tới hết đoạn" ở đó cần coi chừng (chưa thấy kết luận nào dựa vào chỗ đó).
- **Phép đo mới — điểm cắt so với phách** (`cong_cu/beat_align.py`, librosa): 22 (Not Like Us) đoạn bài hát 44–180s: trúng phách 27% = đúng mức ngẫu nhiên 27%;
  23 đoạn 1: 39% so với 31% ngẫu nhiên. **Hai MV kể chuyện đều cắt không bám phách** [khá, 2 video] — ngược dự đoán "MV cắt theo beat" trong MAU_S0_12.
  Điều kiện: librosa có thể dò lệch pha; cần nghe tai một đoạn để chắc.
- Crunch (26): YouTube báo "not available" với client mặc định; tải được bằng `--extractor-args youtube:player_client=android -f 18` (360p).

## Ghi chú thêm cho các mẫu hình
Đã gộp vào các mẫu hình 1, 2, 3, 5, 7, 8, 9, 10, 11 và mẫu hình mới 16–19 (2026-09-29 tối).

## Bàn giao (29/09 tối) — ĐÃ XONG
- Phiên check-current-task-progress (29/09 tối) viết đủ **20, 21, 22, 24, 26, 27, 28** từ số đo hàng đợi (xong 19:35) + tờ ảnh: 20, 21 đo lại điểm cắt ở ngưỡng
  0.10; 24 đo lại độ to + phách trên `v24_seg1f` (tiếng đủ); 22 thêm phách đoạn 2. Số đo chép vào `so_do/` (bỏ lời chép, bỏ đường dẫn tờ ảnh); bảng số + mẫu hình
  đã gộp (mẫu hình mới 16–19).
- **Media ĐÃ XOÁ (người dùng xoá 2026-09-29 tối, đã kiểm hai thư mục không còn)** — trước đó ở:
  - media ~2.3 GB ở `C:\Users\hongviet.doan\AppData\Local\Temp\claude\D--AI-Video-Pipeline--claude-worktrees-nice-bhabha-e53229\3c4c4228-e947-4768-809f-dd34138821d5\scratchpad\s012\`
    (`bash clean.sh vNN` cho 16–28 + xoá `v2x_full.*`, `*_segNf.mkv`; hoặc xoá cả thư mục `s012`);
  - scratchpad phiên trước `...worktrees-danh-gia-devsys-2026-491348\819f89c0-...\scratchpad\s012\` (~0.25 GB webm 19–28).
- Bộ công cụ ở `research/craft/s0_12/cong_cu/` (`pipe.py` dùng biến môi trường `REPO`, mặc định `D:/AI-Video-Pipeline`).
- Việc tiếp đáng làm (miễn phí): đo khớp môi của 24 (MV Kling có hát) bằng `core/clip_measure.lip_sync`; đo 28 đoạn 3:00–8:00 (AI làm cảnh đánh nhau thế nào).

## Tồn đọng (ngoài bàn giao)
- 15: tìm đoạn cao trào thật (video gộp lặp / không theo thứ tự).
- 17: xem ≥ 5 khung/giây shot 8.6–96.3s để chắc là một cảnh; nghe tai lớp tích tắc.
- 10: tìm đoạn giữa phim không lặp và phần kết.
- Đo lại nhạc đoạn 2 của 01 và 04; các phần chưa "nghe bằng số" của 06, 07, 08, 09, 10.
- Người dùng nghe trực tiếp để xác nhận: 06 (84–90s), 07 (73–78s), 10 (14.2–23.2s; 42–57s đoạn 3), 09 (0–30s), 01 (0–90s), **11 (28.4s tỉnh mộng; 90–93s
  đoạn 2)**, **12 (79–86s đoạn 2)**, **17 (tiếng tích tắc 0–90s)**, **23 (đoạn 2 giây 28–46: nhạc tụt khi ký ức bị xoá; cắt có bám phách không)**,
  **25 (116–131s: nhạc tắt khi ra tới vườn)**, **20 (đoạn 2 giây 96–118: nghỉ giữa trận)**, **22 / 24 (vài điểm cắt: có bám phách không)**,
  **27 (đoạn 2 giây 58–90: hồi ức; 114–121 lặng)**.

## Đã xoá dữ liệu tải về
01–15: media, khung hình, tờ ảnh, phổ, wav và thư mục tách âm đã xoá sau khi viết file. 16–28: **đã xoá** (người dùng xoá 2026-09-29 tối; số đo ở `so_do/`).
Số đo JSON (không lời chép, đã bỏ đường dẫn tờ ảnh) của **19–28** nằm ở `so_do/` (20, 21 thêm điểm cắt ngưỡng 0.10 `*_t010.txt`); của 01–18 chỉ còn trong
scratchpad phiên trước.
