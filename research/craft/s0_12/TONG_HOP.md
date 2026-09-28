# S0.12 — Tổng hợp quan sát nhiều phim (cập nhật sau 7 video, đã tải + đo bằng ffmpeg / OpenCV / audio_listen)

> 7 video đã phân tích: 01 AI心動劇場 (AI drama 9:16), 02 TOMORROW / Omeleto (phim ngắn CGI 3D), 03 WARLIKE / BIGFILMS (hành động),
> 04 《我的婆婆是軟柿子》 (AI drama 9:16), 05 RISE Worlds 2018 (cinematic game CGI), 06 《逃不出大哥手掌心》 (AI drama BL 16:9),
> 07 DramaBox "Doting Snake Lord" (AI drama huyền huyễn 9:16, lồng tiếng Anh). Theo `knowledge/craft/PHUONG_PHAP_PHAN_TICH.md` mục 1–2:
> chỉ quan sát thấy ở **≥ 2 video** mới ghi là "mẫu hình bước đầu" (kèm điều kiện, độ tin); quan sát 1 video ở nguyên trong file riêng.

## Phương pháp đã đổi qua các lượt (2026-09-29)
- Lượt 1 → 2: bỏ đo trong trình duyệt, **tải đoạn về máy** (yt-dlp, xoá ngay sau phân tích, không vào repo) — điểm cắt `ffmpeg scene`, LUFS / LRA /
  quãng lặng `ebur128` + `silencedetect`. Video 01, 02 đã làm lại toàn bộ.
- Lượt 3: **chuyển động máy per-shot bằng OpenCV** (04–07), **tờ ảnh thưa 1 khung/20s** để tìm đoạn lật ngược trong video gộp dài (04, 06, 07).
- Lượt 3b: **"nghe bằng số" `tools/audio_listen.py`** (demucs tách nhạc / giọng, mức nhạc từng giây, nhãn AudioSet, whisper có mốc) — dùng cho 06, 07.
  Lưu ý kỹ thuật: khi file tải có hình bắt đầu muộn hơn âm (yt-dlp cắt theo keyframe), mốc của bản tách lệch đúng bằng độ trễ đó (06 đoạn 2:
  +4.5s, 07 đoạn 2: +10s) — phải đối chiếu một mốc thoại/quãng lặng trước khi ghép với điểm cắt.
- Bỏ báo cáo đỉnh âm (true peak): file Opus nén lại có thể vượt đỉnh gốc 1–3 dB — chỉ LUFS / LRA / quãng lặng là đáng tin.

## Bảng số chung
| Video | Loại | Trung vị shot (đoạn 1 / 2) | Máy tĩnh (OpenCV) | LUFS | Quãng lặng |
|---|---|---|---|---|---|
| 01 | AI drama 9:16 | 1.4–2.0s | (chưa đo OpenCV; mắt: gần như tĩnh) | −11.2 / −14.6 | 46 / 33 |
| 02 | phim ngắn CGI | 3.7s mở → < 1s cụm bạo lực | — | — | 11 / 3 |
| 03 | hành động | 4.72s mở/kết, 1.84s đánh nhau | — | — | 1 (toàn phim) |
| 04 | AI drama 9:16 | 2.04 / 2.15s | 76% / 83% | −13.4 / −13.5 | 3 / 2 |
| 05 | cinematic CGI | 1.19s (toàn phim) | 43% (zoom in 22%, roll 13%) | −16.5 | 7 |
| 06 | AI drama 16:9 | 2.60 / 2.97s | 77% / 79% | −19.0 / −19.2 | 0 / 2 |
| 07 | AI drama 9:16 (DramaBox) | 2.50 / 3.68s | 43% / 53% (zoom in 29% / 11%) | −13.0 / −15.0 | 17 / 12 |

## Mẫu hình bước đầu (≥ 2 video)

### 1. Nhịp cắt: ổn định ở AI drama thoại, đổi mạnh ở phim kể bằng hình / hành động
- AI drama (01, 04, 06; 07 ít hơn): trung vị gần như giữ nguyên giữa đoạn mở đầu và đoạn lật ngược cách nhau 13–74 phút (01: 1.4–2.0s; 04: 2.04 / 2.15s;
  06: 2.60 / 2.97s; 07: 2.50 / 3.68s). Phim ngắn / hành động (02, 03): trung vị đổi 2–4× giữa đoạn thiết lập và đoạn cao trào.
- **Mẫu hình [có thể → khá, 4 AI drama cùng chiều]**: khi thoại là phương tiện chính, nhịp cắt giữ trong một dải hẹp suốt phim; cảm xúc đổi bằng thoại / nhạc
  hơn là bằng tốc độ cắt. **Điều kiện**: dải này **khác nhau theo kênh** (01 nhanh nhất ~30 shot/phút; 06, 07 chỉ ~18–20 shot/phút) — không có một con số
  chung cho "AI drama". Giả thuyết cũ "trần nhịp ~1.8–2.0s mà nhiều thể loại hội tụ" không còn đứng: 06 / 07 chậm hơn hẳn.

### 2. Cụm shot rất ngắn (≤ 0.6s) cho một khoảnh khắc hành động giữa nhịp 2–4s
- 02: cụm bạo lực < 1s; 06: 4 shot 0.33s + 1 shot 0.5s khi chạy khỏi nhà (62.4–64.3s đoạn 2); 07: 3 shot 0.4–0.6s khi vẹt tung cánh tia điện (89.3–90.9s
  đoạn 2) và 4 shot 0.8–1.1s dồn cuối đoạn 1 (176.2–180s).
- **Mẫu hình [có thể, 3 video]**: một hành động ngắn (chạy, đánh, phép thuật) được nén thành cụm 3–5 shot rất ngắn rồi trả về nhịp thường. Điều kiện: cụm dài
  ≤ 2s, xuất hiện ở chỗ ít / không thoại. Với video AI: cần sinh nhiều clip ngắn hoặc cắt một clip dài thành nhiều mảnh.

### 3. Máy tĩnh áp đảo ở drama thoại hiện đại; đẩy máy (zoom / dolly in) dày ở cảnh thần thoại / CGI
- Tĩnh 76–83%: 04 (drama thập niên 80), 06 (drama học đường) — cả hai là bối cảnh đời thường.
- Tĩnh chỉ 43–53%, zoom / dolly in 11–29%: 07 (rồng, trứng thần), 05 (cinematic game).
- **Mẫu hình [có thể, 2 + 2 video]**: mức "động" của máy đi theo **thế giới truyện** (đời thường ↔ thần thoại / hoành tráng) hơn là theo "AI hay không". Ở 07,
  zoom in dồn vào insert vật "bằng chứng" (trứng) và mặt phản ứng. Điều kiện: OpenCV còn nhạy với rung / zoom rất chậm; các shot < 0.4s không đo được.

### 4. Nhạc nền gần như liên tục ở AI drama — **sửa kết luận cũ**
- Đo bằng audio_listen: 06 có nhạc 92–100% thời gian đã đo, 07 có 84–98%. Kết luận trước đây (từ RMS ở 01 và từ đọc phổ bằng mắt ở 04) rằng "AI drama thoại nhiều
  ít / không có nhạc, nhạc tắt giữa các câu" **không đúng với 06, 07** — đọc phổ bằng mắt không thấy được nhạc nhỏ nằm dưới thoại. 01 và 04 cần đo lại bằng
  audio_listen trước khi giữ kết luận cũ (xem Tồn đọng).
- Số quãng lặng không theo thể loại mà theo kênh: 01 46 / 33, 07 17 / 12, 04 3 / 2, 06 0 / 2 — cùng là AI drama.
- **Mẫu hình [có thể → khá, 2 video đo trực tiếp]**: nhạc là lớp nền liên tục, hạ xuống dưới thoại khi cần (06 đoạn 2: −36…−52 dB dưới câu của hai người đàn ông);
  "im lặng" là **ngoại lệ có chủ đích**, xem mục 5.

### 5. Tắt nhạc ngắn 4–8s để đánh dấu một nhịp quan trọng, nhạc về ở (gần) một điểm cắt
- 06 đoạn 2: tắt 84–89s khi thấy lưng đầy vết thương / "你怎么来了", nhạc về **đúng cắt 90.0s**. 07 đoạn 2: tắt 33–40s dưới câu sỉ nhục, về ~40s với timpani
  (cắt ở 41.6s); lặng hoàn toàn 73.0–77.5s trong shot mắt rồng giữ 15.8s, rồi tiếng gầm.
- **Mẫu hình [có thể, 2 video, 3 lần]**: im lặng ngắn đặt ngay trước / dưới khoảnh khắc sốc hoặc lộ tin, rồi âm thanh trở lại mang tông mới (dịu ở 06, căng ở 07).
  Điều kiện: nền phải có nhạc liên tục trước đó thì chỗ tắt mới "nghe" được; không dùng khi cả đoạn vốn ít nhạc.

### 6. Shot mở cảnh / mở tập dài gấp nhiều lần trung vị
- 01: shot đầu cảnh bữa tối 9.7s (~5× trung vị). 06: shot mở đoạn 2 ở nhà ≥ 6.2s (bị cắt đầu file; tổng 10.65s). 07: sau thẻ "TO BE CONTINUED" là toàn cảnh
  12.4s (đoạn 1) và 4.0s (đoạn 2), kèm quãng lặng 7–8s.
- **Mẫu hình [có thể, 3 video]**: shot đầu một cảnh / tập được giữ lâu (thường là toàn cảnh hoặc một người trong không gian) trước khi vào nhịp cắt thoại. Điều kiện:
  ở video gộp tập (07), phần lặng + toàn cảnh có thể do khâu gộp của kênh, không hẳn là ý đồ trong phim.

### 7. Âm thanh liên tục ở phim kể bằng hình / hành động (giữ từ lượt trước)
- 02 (11 / 3 quãng lặng), 03 (1 quãng lặng trong 240.9s), 05 (7, dồn ở cuối) — nhạc / SFX chạy gần như không ngắt. [khá, 3 video]. Nay 06 / 07 cho thấy AI drama
  **cũng** có nhạc gần liên tục, nên khác biệt thật giữa hai nhóm nằm ở **chỗ và cách ngắt** (mục 5), không ở "có / không có nhạc".

### Không dùng được làm mẫu hình: đỉnh âm ≥ 0 dBFS
Đỉnh đo trên file Opus / WebM tải về (01: 0.0, 02: +3.4, 03: +1.8 dBFS) có thể do giải mã nén lại — bỏ, không suy luận.

## Quan sát chỉ 1 video (chưa đủ điều kiện)
- 07: tiếng "đập" (slam / bang / whoosh) trùng điểm cắt trong đoạn cãi vã; tiếng tim đập dưới câu lật bài (2 lần trong cùng video).
- 06: đổi nhạc cụ theo nhịp kịch trong một đoạn (guitar → nền → cello / bass → violin → lặng → piano); phần hài giữ nguyên một bản nhạc vui 125s kể cả lúc "bị điện giật".
- 06: đối đáp nhanh 6 câu trong một shot hai người (không cắt theo câu) — ngược "1 câu ≈ 1 shot" của 01.
- 04: vật thể (hộp thư, máy cát-xét) làm phương tiện kể lại quá khứ thay vì hồi tưởng bằng hình.
- 02: hai biến cố lớn cách nhau ~10 phút → không chọn đoạn cao trào theo % thời lượng (nay dùng tờ ảnh thưa).

## Giới hạn chung
- Chưa nghe bằng tai; audio_listen là "nghe bằng số": lớp "nhạc" của demucs lẫn cả hiệu ứng (trống + bass + khác), tên nhạc cụ AST điểm thấp (0.03–0.2) → chỉ ở mức "có thể".
- Mỗi video gộp dài chỉ đo 4–26% thời lượng (01: 3.3%, 04: 4.2%, 06: ~26%, 07: ~24%).
- OpenCV không đo được shot < 0.4s và cảnh tối nhiều hạt sáng.

## Tồn đọng
- **Fortnight** (MV, `MAU_S0_12.md`) — chưa phân tích.
- **《大师兄》** — chưa phân tích.
- **2 mẫu DramaBox còn lại** (mục 1b): "Your Dumped Housewife Is Your Boss" (LMaaTmhvLuQ) và "My Dirty Secret With The Wrong Stepbrother" (fmvJdZkrB2k, cần xác nhận khung 9:16).
- Đo lại **01 và 04 bằng audio_listen** (tải lại 60–90s mỗi đoạn) để kiểm kết luận cũ về nhạc — mục 4 đang mâu thuẫn với chúng.
- Phần chưa "nghe bằng số": 06 đoạn 1 giây 125–180; 07 đoạn 2 giây 90–130.
- Người dùng nghe trực tiếp để xác nhận: 06 đoạn 2 (84–90s tắt nhạc; cello từ ~41s), 07 đoạn 2 (73–78s lặng rồi gầm).

## Đã xoá dữ liệu tải về
Media, khung hình, tờ ảnh, phổ, wav và thư mục tách âm của cả 7 video đã xoá khỏi `scratchpad/s012` sau khi viết file phân tích tương ứng — chỉ giữ JSON số đo,
bảng `*_table.md` và script `*.py` để đối chiếu mà không cần tải lại.
