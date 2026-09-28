# S0.12 — Tổng hợp quan sát nhiều phim (cập nhật sau 10 video, đã tải + đo bằng ffmpeg / OpenCV / audio_listen)

> 10 video đã phân tích: 01 AI心動劇場 (AI drama 9:16), 02 TOMORROW / Omeleto (phim ngắn CGI 3D), 03 WARLIKE / BIGFILMS (hành động),
> 04 《我的婆婆是軟柿子》 (AI drama 9:16), 05 RISE Worlds 2018 (cinematic game CGI), 06 《逃不出大哥手掌心》 (AI drama BL 16:9),
> 07 DramaBox "Doting Snake Lord" (AI drama huyền huyễn 9:16, lồng tiếng Anh), 08 "Fortnight" (MV Taylor Swift, quay thật đen trắng),
> 09 《大師兄》 (phim ngắn AI võ hiệp 16:9), 10 DramaBox "Your Dumped Housewife Is Your Boss" (AI drama hiện đại 9:16, lồng tiếng Anh).
> Theo `knowledge/craft/PHUONG_PHAP_PHAN_TICH.md` mục 1–2: chỉ quan sát thấy ở **≥ 2 video** mới ghi là "mẫu hình bước đầu" (kèm điều kiện, độ tin);
> quan sát 1 video ở nguyên trong file riêng.

## Phương pháp đã đổi qua các lượt (2026-09-29)
- Lượt 1 → 2: bỏ đo trong trình duyệt, **tải đoạn về máy** (yt-dlp, xoá ngay sau phân tích, không vào repo) — điểm cắt `ffmpeg scene`, LUFS / LRA /
  quãng lặng `ebur128` + `silencedetect`. Video 01, 02 đã làm lại toàn bộ.
- Lượt 3: **chuyển động máy per-shot bằng OpenCV** (04–10), **tờ ảnh thưa 1 khung/10–20s** để tìm đoạn lật ngược / cao trào (04, 06, 07, 09, 10).
- Lượt 3b: **"nghe bằng số" `tools/audio_listen.py`** (demucs tách nhạc / giọng, mức nhạc từng giây, nhãn AudioSet, whisper có mốc) — dùng cho 06–10 và
  **đo lại nhạc 01, 04** (0:00–1:30). Lưu ý kỹ thuật: khi file tải có hình bắt đầu muộn hơn âm (yt-dlp cắt theo keyframe: 06 +4.5s, 07 +10s, 09 +9.9s,
  10 +7.3s / +9.85s), chạy audio_listen với `--start` = giây có hình, hoặc đối chiếu một mốc thoại / quãng lặng trước khi ghép với điểm cắt.
- Lượt 4: **hình đen trắng tương phản thấp** (08) — ngưỡng cắt 0.25 bỏ sót cắt, phải kiểm lại ở 0.12; ngưỡng 0.12 lại bắt nhầm chớp sáng (09) → luôn soát bằng mắt.
- Lượt 4: **video gộp có thể lặp tập** (10: 0:44–3:00 phát lại ở ≈25:30) — kiểm bằng so điểm cắt lệch một hằng số trước khi coi là đoạn mới.
- Bỏ báo cáo đỉnh âm (true peak): file Opus nén lại có thể vượt đỉnh gốc 1–3 dB — chỉ LUFS / LRA / quãng lặng là đáng tin.
- Bài hát có bản quyền (08): whisper chỉ để lấy mốc câu, không chép / lưu lời.

## Bảng số chung
| Video | Loại | Trung vị shot (đoạn 1 / 2) | Máy tĩnh (OpenCV) | LUFS | Quãng lặng | Nhạc (audio_listen) |
|---|---|---|---|---|---|---|
| 01 | AI drama 9:16 | 1.4–2.0s | (chưa đo OpenCV; mắt: gần như tĩnh) | −11.2 / −14.6 | 46 / 33 | **20%** (0–90s, đo lại) |
| 02 | phim ngắn CGI | 3.7s mở → < 1s cụm bạo lực | — | — | 11 / 3 | — |
| 03 | hành động | 4.72s mở/kết, 1.84s đánh nhau | — | — | 1 (toàn phim) | — |
| 04 | AI drama 9:16 | 2.04 / 2.15s | 76% / 83% | −13.4 / −13.5 | 3 / 2 | **98%** (0–90s, đo lại) |
| 05 | cinematic CGI | 1.19s (toàn phim) | 43% (zoom in 22%, roll 13%) | −16.5 | 7 | — |
| 06 | AI drama 16:9 | 2.60 / 2.97s | 77% / 79% | −19.0 / −19.2 | 0 / 2 | 92–100% |
| 07 | AI drama 9:16 (DramaBox) | 2.50 / 3.68s | 43% / 53% (zoom in 29% / 11%) | −13.0 / −15.0 | 17 / 12 | 84–98% |
| 08 | MV quay thật, đen trắng | 2.9s (5 shot ≥ 10s) | 59% (zoom in 24%) | −17.2 (LRA 3.3) | 2 | 99–100% |
| 09 | phim ngắn AI võ hiệp 16:9 | **4.66** / 3.37s | **90%** / 65% | −17.6 / −19.5 | 0 / 0 | 100% / 100% |
| 10 | AI drama 9:16 (DramaBox) | 1.76 / 1.42s | 77% / 83% | −15.6 / −14.4 | 44 / 15 | **14–32%** (bi kịch) / 76% (tiệc) |

## Mẫu hình bước đầu (≥ 2 video)

### 1. Nhịp cắt: ổn định ở AI drama thoại, đổi mạnh ở phim kể bằng hình / hành động
- AI drama (01, 04, 06, 07, 10): trung vị gần như giữ nguyên giữa đoạn mở đầu và đoạn lật ngược (01: 1.4–2.0s; 04: 2.04 / 2.15s; 06: 2.60 / 2.97s;
  07: 2.50 / 3.68s; 10: 1.76 / 1.42s). Phim ngắn / hành động (02, 03) và phim ngắn AI 09 (4.66s mở → cụm hồi tưởng đánh kiếm ~1.5s): đổi 2–4× giữa thiết lập và cao trào.
- **Mẫu hình [khá, 5 AI drama cùng chiều]**: khi thoại là phương tiện chính, nhịp cắt giữ trong một dải hẹp suốt phim; cảm xúc đổi bằng thoại / nhạc / hiệu ứng
  hơn là bằng tốc độ cắt. **Điều kiện**: dải này **khác nhau theo kênh** (01, 10 nhanh ~27–32 shot/phút; 06, 07 ~18–20 shot/phút) — không có một con số chung.
- **Mới**: phim ngắn AI **không phải drama** (09) cắt chậm nhất trong mọi video AI (trung vị 4.66s, 9.7 shot/phút) — "video AI" không kéo theo "cắt nhanh";
  nhịp theo thể loại / người làm. MV (08) chậm (11 shot/phút) và rất lệch: vài shot ≥ 10s trọn một đoạn lời.

### 2. Cụm shot ngắn cho một khoảnh khắc hành động giữa nhịp chậm hơn
- 02: cụm bạo lực < 1s; 06: 4 shot 0.33s + 1 shot 0.5s (62.4–64.3s đoạn 2); 07: 3 shot 0.4–0.6s (89.3–90.9s đoạn 2) và 4 shot 0.8–1.1s (176.2–180s đoạn 1);
  09: hồi tưởng chém kiếm ~12 shot trung vị ~1.5s trong 20s (27.8–48.4s đoạn 2) giữa nhịp 3.4–4.7s.
- **Mẫu hình [có thể, 4 video]**: một hành động ngắn (chạy, đánh, phép thuật, đường kiếm) được nén thành cụm shot ngắn hơn hẳn nhịp quanh đó rồi trả về nhịp thường.
  Điều kiện: độ ngắn tương đối (≈ ½–⅓ trung vị quanh đó), không phải một con số tuyệt đối; xuất hiện ở chỗ ít thoại **hoặc** dưới giọng kể (09).

### 3. Mức "động" của máy: theo kênh / người làm, không theo "thế giới truyện" một cách nhất quán — **sửa mẫu hình cũ**
- Tĩnh 76–83%: 04, 06, 10 (drama đời thường / hiện đại). Tĩnh 43–53%, zoom / dolly in 11–29%: 07 (thần thoại), 05 (cinematic game).
- **Phản ví dụ mới**: 09 là thế giới võ hiệp núi non hùng vĩ nhưng **tĩnh 90%** — sự hùng vĩ đến từ **cỡ cảnh** (toàn cảnh cực rộng, người nhỏ như chấm) chứ không
  từ chuyển động máy. 07 và 10 cùng app DramaBox nhưng 43–53% ↔ 77–83% tĩnh.
- **Mẫu hình [có thể]**: drama đời thường thoại nhiều → máy tĩnh áp đảo (3 video). Còn phim "hoành tráng" thì hai cách đều gặp: máy đẩy chậm (05, 07) **hoặc** máy
  tĩnh + toàn cảnh cực rộng (09). Điều kiện: OpenCV nhạy với rung / zoom rất chậm; không đo được shot < 0.4s và cảnh tối / trời mây ít điểm bám.

### 4. Nhạc nền ở AI drama: **hai kiểu, theo kênh và theo cảnh** — sửa lần hai
- Đo lại 01 và 04 bằng audio_listen (trước đây kết luận từ RMS / đọc phổ bằng mắt):
  - **04 có nhạc 98%** — kết luận cũ "không có nhạc rõ" **sai**: nhạc nhỏ −36…−42 dBFS nằm dưới thoại, mắt không thấy trên phổ.
  - **01 có nhạc chỉ 20%** — kết luận cũ "nhạc gián đoạn" **đúng**: lớp tách ra chủ yếu là tiếng môi trường (chim, côn trùng, tiếng vải).
- Kiểu A — **nền liên tục**, hạ dưới thoại, trồi lên ở điểm nhấn: 04 (98%), 06 (92–100%), 07 (84–98%); cũng là cách của phim ngắn AI 09 (100%) và MV 08 (99–100%).
- Kiểu B — **thưa, dùng như cú nhấn (sting)**, còn lại là thoại + tiếng thở / môi trường: 01 (20%), 10 ở cảnh bi kịch (14–32%). Nhưng **cùng video 10**, cảnh tiệc
  lật mặt có nhạc 76% → kiểu nhạc đổi **theo cảnh** trong một phim, không chỉ theo kênh.
- **Mẫu hình [khá, 7 video đo trực tiếp]**: không có luật "AI drama = có / không có nhạc". Cả hai kiểu đều gặp; một phim có thể đổi kiểu theo cảnh.
- **Bài học đo [chắc]**: phải tách lớp (demucs) mới biết có nhạc hay không; RMS tổng và đọc phổ bằng mắt cho kết luận sai ở 04.

### 5. Tắt nhạc ngắn dưới câu / khoảnh khắc then chốt, nhạc về ở (gần) một điểm cắt
- 06 đoạn 2: tắt 84–89s ("你怎么来了"), nhạc về **đúng cắt 90.0s**. 07 đoạn 2: tắt 33–40s dưới câu sỉ nhục, về ~40s (cắt 41.6); lặng 73.0–77.5s rồi tiếng gầm.
  10 đoạn 3: **tắt 42–57s** suốt màn đối đáp chính, về **ở cắt 57.9s**; tắt 85–87s, về ở cắt 92.1s sang bánh kem.
- Biến thể ngược ở 09: **giọng tắt 44–46s nhưng nhạc vẫn chạy**, dưới ECU mắt người thua trận.
- **Mẫu hình [có thể → khá, 3 video, 5 lần]**: im lặng (nhạc) ngắn 4–15s đặt dưới lời lật thế / lộ tin, rồi âm thanh trở lại ở điểm cắt sang phản ứng, thường đổi tông.
  Điều kiện: chỉ "nghe" được khi trước đó có nhạc nền (kiểu A, hoặc cảnh có nhạc của kiểu B).

### 6. Âm nhấn (tiếng đập / nổ / tim đập / nhạc trồi) trùng điểm cắt — **mới, nâng từ quan sát 1 video**
- 07: slam / bang / explosion trùng cắt trong cãi vã (5/6 cửa sổ, ±1s); tim đập dưới câu lật bài (2 lần).
- 10: Explosion + nhạc ở cắt 36.1 (cuộc gọi bắt cóc kết thúc); Bang/Explosion ở cắt 27.5 / 28.6 (hợp đồng lộ tên); Bang ở cắt 68.7 ("Is this a joke?") rồi
  **tim đập** 70s / 78s; Rumble ở cắt 8.0 cảnh mở.
- 04: nhạc trồi 5–20 dB ở cắt 9.2, 50.6, 73.0 / 74.2 (Whoosh) — chuyển bối cảnh / chỗ thoại ngừng. 09: Smash + nhạc lên ở nhát kiếm chém nước (32–34s đoạn 2).
- **Mẫu hình [có thể → khá, 4 video]**: điểm cắt quan trọng (lộ tin, chuyển bối cảnh, cú hành động) được "đóng dấu" bằng một âm ngắn; tim đập dùng dưới câu lật bài
  (07, 10). Điều kiện: nhãn AST cửa sổ 2s → khớp ±1s; lớp "nhạc" demucs lẫn hiệu ứng nên không tách được "nhạc trồi" với "tiếng nổ".

### 7. Nhạc vào / trồi lên ở shot "mở không gian" hoặc tên phim — **mới**
- 09: nhạc lên ở cắt 30.1 (toàn cảnh cực rộng vách đá), 58s (chữ tên phim), cắt 71.5 (đám mây khổng lồ). 10: nhạc −17.6 dB ở cắt 99.3 (xe tới dinh thự).
  08 (MV): chớp trắng chuyển sang sa mạc đúng đầu điệp khúc 2 (~114s). 04: nhạc trồi ở cắt 9.2 (sổ tay → sân làng).
- **Mẫu hình [có thể, 4 video]**: khi hình "mở ra" (không gian mới, quy mô lớn, tên phim), âm nhạc lớn lên cùng lúc (±0.5s ở 09, 10, 04). Điều kiện: 08 là MV — điểm
  mở nằm theo cấu trúc bài hát, không theo truyện.

### 8. Im lặng hoàn toàn ở chỗ chuyển thời gian / bối cảnh — **mới**
- 01: 7.8–11.3s (chèn vật, không thoại) và ~55–67s (đổi bối cảnh, xe Bentley). 07: 7–8s lặng sau thẻ "TO BE CONTINUED" (2 lần). 10: **14.2–23.2s bắt đầu đúng cắt
  14.2** (từ cảnh tương lai về "cuộc sống thường ngày" + thẻ tên), 52.5–55.1s dưới thẻ "THREE YEARS LATER", ~104.8–109.8s dưới toàn cảnh dinh thự.
- **Mẫu hình [có thể, 3 video]**: một khoảng lặng 3–9s làm "dấu xuống dòng" khi truyện nhảy thời gian / chỗ / tập. Điều kiện: ở video gộp tập (07) có thể do khâu
  gộp; ở 01 nền vốn ít nhạc nên "lặng" chỉ là không thoại.

### 9. Shot mở cảnh / mở phim dài gấp nhiều lần trung vị
- 01: shot đầu cảnh bữa tối 9.7s (~5× trung vị). 06: shot mở đoạn 2 ≥ 6.2s. 07: toàn cảnh 12.4s / 4.0s sau thẻ "TO BE CONTINUED". **08: shot mở 29.9s**
  (thẻ tên + máy lùi dần trọn đoạn lời 1). **09: shot mở 19.0s** (khung núi trống → tay → mặt) và shot tên phim 18.1s.
- **Mẫu hình [khá, 5 video]**: shot đầu một cảnh / phim được giữ lâu (toàn cảnh, hoặc một người trong không gian, thường có máy di chuyển chậm / nhân vật đi vào
  khung) trước khi vào nhịp cắt chính. Điều kiện: ở video gộp tập, một phần có thể do khâu gộp của kênh.

### 10. Âm thanh liên tục ở phim kể bằng hình / hành động / MV
- 02 (11 / 3 quãng lặng), 03 (1 trong 240.9s), 05 (7, dồn ở cuối), **08 (2, chỉ trong thẻ tên), 09 (0 / 0)** — nhạc / SFX chạy không ngắt. [khá, 5 video].
  Khác biệt thật với AI drama nằm ở **chỗ và cách ngắt** (mục 5, 8), không ở "có / không có nhạc".

### Không dùng được làm mẫu hình: đỉnh âm ≥ 0 dBFS
Đỉnh đo trên file Opus / WebM tải về (01: 0.0, 02: +3.4, 03: +1.8 dBFS) có thể do giải mã nén lại — bỏ, không suy luận.

## Quan sát chỉ 1 video (chưa đủ điều kiện)
- 10: mở bằng **cảnh tương lai** (flash-forward) 0–14.2s; thẻ tên nhân vật trên hình; insert chớp trời 0.3–0.4s giữa các CU khóc.
- 09: **2:38 đầu không có câu thoại** (kể bằng hình, tiếng thở, nhạc); lộ nhân vật bằng cách để họ đi vào khung tĩnh; cho thấy sức mạnh qua **hậu quả** (đám mây) thay vì đòn đánh.
- 08: **màu duy nhất** (khói cam + xanh) trong MV đen trắng; chữ đánh máy trùng câu đang hát; cắt thường trễ đầu câu hát 1.4–1.6s; luân phiên CU nhìn thẳng máy.
- 06: đổi nhạc cụ theo nhịp kịch trong một đoạn; phần hài giữ nguyên một bản nhạc vui 125s; đối đáp 6 câu trong một shot hai người.
- 04: vật thể (hộp thư, cát-xét) làm phương tiện kể lại quá khứ.
- 02: hai biến cố lớn cách nhau ~10 phút → không chọn đoạn cao trào theo % thời lượng.

## Giới hạn chung
- Chưa nghe bằng tai; audio_listen là "nghe bằng số": lớp "nhạc" của demucs lẫn cả hiệu ứng, tên nhạc cụ AST điểm thấp (0.03–0.3) → chỉ ở mức "có thể".
- Mỗi video gộp dài chỉ đo 3–26% thời lượng (01: 3.3%, 04: 4.2%, 06: ~26%, 07: ~24%, 10: ~4% nội dung khác nhau); 08 ~72%, 09 ~34%.
- OpenCV không đo được shot < 0.4s, cảnh tối nhiều hạt sáng, nền mây trắng; nhãn có thể sai chiều khi shot gộp cả thẻ chữ (08 shot 1).
- Chỉ 1 MV (08) — mọi nhận xét về MV đều ở mức 1 mẫu.

## Tồn đọng
- **DramaBox còn 1 mẫu**: "My Dirty Secret With The Wrong Stepbrother" (fmvJdZkrB2k, cần xác nhận khung 9:16).
- **10**: tìm một đoạn giữa phim **không lặp** (tờ quét 10:00–50:00 cho thấy nhiều cảnh lặp) và phần kết.
- Đo lại nhạc bằng audio_listen **đoạn 2** của 01 (74:08–75:08) và 04 (43:30–45:40, cát-xét phát nhạc hay giọng?) — lượt này chỉ đo lại 0:00–1:30.
- Phần chưa "nghe bằng số": 06 đoạn 1 giây 125–180; 07 đoạn 2 giây 90–130; 09 đoạn 1 giây 90–180; 10 đoạn 1 giây 135–180, đoạn 3 giây file 100–130;
  08 phút 3:00–4:09 (bridge / kết).
- 09: các khung đám mây ~11:50 chưa đo; kiểm "Explosion" 84–98s đoạn 2 là hiệu ứng hay trống trầm.
- Người dùng nghe trực tiếp để xác nhận: 06 đoạn 2 (84–90s tắt nhạc), 07 đoạn 2 (73–78s lặng rồi gầm), **10 (14.2–23.2s lặng sau cảnh mở; 42–57s đoạn 3 tắt nhạc)**,
  **09 (0–30s: nhạc nhỏ + tiếng thở; 30s nhạc lên)**, **01 (0–90s: xác nhận gần như không có nhạc)**.

## Đã xoá dữ liệu tải về
Media, khung hình, tờ ảnh, phổ, wav và thư mục tách âm của cả 10 video (và bản tải lại 01, 04) đã xoá khỏi `scratchpad/s012` sau khi viết file phân tích tương ứng —
chỉ giữ JSON số đo (`*_result.json`, `*_listen_numbers.json` đã bỏ lời chép), bảng `*_table.md` và script `*.py` để đối chiếu mà không cần tải lại.
