# 10 — DramaBox: "Your Dumped Housewife Is Your Boss" (kênh DramaTales, quảng bá app DramaBox)

- **URL**: https://www.youtube.com/watch?v=LMaaTmhvLuQ
- **Thể loại**: AI short drama 9:16 tổng tài / trả thù hiện đại (vợ bị bỏ → người thừa kế tập đoàn), lồng tiếng **tiếng Anh** + phụ đề Anh, gộp nhiều tập; góc
  trên phải có logo DramaBox, nhiều khung có dòng chữ vàng "Due to copyright restrictions, more episodes are available in the comment section" — mục 1b.1 trong `MAU_S0_12.md`
- **Độ dài công bố**: 2:16:11 · file tải 360×640, 9:16
- **Đoạn đã đo**:
  - (1) 0:00–3:00 (180.0s, hình và âm cùng từ giây 0);
  - (2) yêu cầu 25:30–27:30 — **hoá ra lặp lại y hệt đoạn 1** (xem dưới), chỉ dùng để kiểm lặp + lấy thêm số nghe cho đoạn 1;
  - (3) yêu cầu 9:30–11:30 — cảnh lật mặt ở tiệc sinh nhật; file 130.0s, **hình từ giây 9.85 của file** (mốc gốc ≈ 9:20 + t), mốc trong bảng là giây của file.
- **Tổng nội dung khác nhau đã đo**: ~300s / 8171s (~4%)
- **Đã tải**: `v10_seg1.webm` (5.6 MB), `v10_seg2.webm`, `v10_seg3.webm`, khúc quét 144p 10:00–50:00 (xoá ngay sau khi chọn đoạn) — **tất cả đã xoá sau khi viết file này**.

## Video gộp có lặp nội dung
Tờ quét 1 khung/20s (10:00–50:00, `tile=12x10`) cho thấy cùng các cảnh (bếp + điện thoại, phòng họp với người cha, tên "JULIAN THORNE", tiệc bánh kem) **xuất hiện
lại nhiều lần**. Đo trực tiếp: đoạn 2 (file từ ≈25:22.7) có **cùng điểm cắt với đoạn 1 lệch đúng 37.8s** (ví dụ cắt 13.2 / 15.1 / 15.4 của đoạn 2 = 51.0 / 52.9 / 53.3
của đoạn 1; cắt 83.7 = 121.5), và mức nhạc từng giây của hai bản khớp ±1s. Tức nội dung 0:44–3:00 được phát lại ở ≈25:30–27:40. [có thể] kênh gộp bằng cách lặp
tập; số phút "thật" của phim ít hơn 2:16 nhiều. Hệ quả cho cách chọn đoạn: **tờ quét thưa phải được đọc để loại cảnh lặp** trước khi coi là "đoạn giữa phim".

## Phương pháp
Như 07: `ffmpeg scene` 0.25, tờ ảnh khung giữa shot, `ebur128` + `silencedetect`, OpenCV `motion_cv2.py`, `tools/audio_listen.py --lang en`:
đoạn 1 giây 0–90; bản lặp (đoạn 2) giây 7–97 = **đoạn 1 giây 44.8–134.8** (đổi mốc +37.8s); đoạn 3 giây file 10–100 (bắt đầu đúng chỗ có hình).

## Số đo
| Đoạn | Shot | Trung vị | Min–max | Shot/phút | Máy (OpenCV) |
|---|---|---|---|---|---|
| Mở đầu 0:00–3:00 | 81 | **1.76s** | 0.33–7.07s | 27.0 | tĩnh 77%, tịnh tiến 11%, zoom in 6%, roll 4%, thiếu dữ liệu 2% |
| Tiệc sinh nhật ≈9:30–11:30 | 64 (120s có hình) | **1.42s** | 0.5–8.1s | 32.0 | tĩnh 83%, zoom in 5%, tịnh tiến 3%, roll 2%, thiếu dữ liệu 8% |

- Âm thanh: LUFS **−15.6** / **−14.4**, LRA **11.9** / **8.1 LU**; quãng lặng (< −35 dB, ≥ 0.3s) **44** / **15** (đoạn 3 bỏ 0–4.2s trước khi có hình → 14).
- Nhịp cắt nhanh nhất sau 01 (01: 1.4–2.0s); máy tĩnh 77–83% như 04 / 06 — **khác hẳn DramaBox 07** (tĩnh 43–53%, zoom in 29%): cùng app phát hành nhưng khác
  xưởng / thế giới truyện (07 huyền huyễn, 10 hiện đại).

### Nghe bằng số (audio_listen)
- **Nhạc ít và theo cảnh**: đoạn 1 giây 0–90 **32%**, giây 44.8–134.8 **14%**; đoạn 3 (tiệc) **76%**. Tempo đo 161.5 / 89.1 BPM, độ khớp giọng điệu 0.42–0.74 → không tin.
  Ngoài nhạc, lớp "nhạc" tách ra toàn tiếng hiệu ứng: Explosion / Rumble / Bang / Slam / Whoosh, tiếng tim đập, bíp điện thoại (DTMF 0.38), tiếng dao chặt ở bếp (0.5–0.87).
- **Đoạn 1**:
  - **0–14.2s (mở bằng cảnh tương lai — hai người phụ nữ đối đầu)**: nhạc lên từ −29 tới **−14.6 dB ở 8s**, Rumble 0.38 / Explosion 0.22 ở 8–10s ↔ cắt 8.0; tim đập 0.11 ở 6s.
  - **14.2–23.2s lặng hoàn toàn** (giọng −95…−110 dB, nhạc −86…−90 dB; silencedetect 14.2–23.2) — **bắt đầu đúng cắt 14.2** sang ảnh gia đình trên bàn bếp,
    rồi chị nấu ăn với **thẻ tên "LINDA HASTINGS"** (18.5–21.9s).
  - Cuộc gọi bắt cóc 21.9–39.8s: nhạc chỉ bật từng cú — 27s (−16.1 dB, Whoosh) dưới câu đòi người, 32s (−21.9) sau tiếng "Mommy!" (cắt 30.6), **36s Explosion 0.38 +
    nhạc −16.4 ↔ cắt 36.1 / 36.9** (màn hình "Unknown Caller" cuộc gọi kết thúc). Giữa các cú: nhạc < −60 dB.
  - 39.8–53.3s: gần như không nhạc; thở dốc / nấc (Gasp 0.52–0.62); **2 insert chớp trời 0.3s và 0.4s** (43.6, 52.9).
  - **"THREE YEARS LATER" 53.3s trong im lặng** (silencedetect 52.5–55.1). Cảnh giải cứu (61.4–80.0s, thẻ tên "JULIAN THORNE" 67.0s): nhạc chỉ −45…−47 dB 1–2 giây.
  - **Xe tới dinh thự 99.3s: nhạc −17.6 dB** (từ bản lặp), ngay trước đó tiếng "chụp ảnh" 0.9 (~98.8s); rồi **lặng tuyệt đối ~104.8–109.8s** (−109…−120 dB)
    dưới toàn cảnh dinh thự / hàng vệ sĩ. Phòng họp với người cha 121.5–180s: gần như không nhạc.
- **Đoạn 3 (tiệc sinh nhật, giây file)**:
  - 10–41s nhạc rõ; **Bang / Explosion 0.37 + nhạc −17.7 dB ở 26–28s ↔ cắt 27.5 / 28.6** (hợp đồng "HASTINGS GROUP" → đám khách há hốc).
  - **Nhạc tắt 42–57s** (< −60 dB) suốt màn đối đáp chính giữa Linda (chống nạng) và cô tình nhân; **nhạc về 58s ↔ cắt 57.9** (Nick: "I think I know how hard it was").
  - **68s: Bang 0.16 + nhạc −28 dB ↔ cắt 68.7** ("Is this a joke?"); **tim đập 0.17 / 0.34 ở 70s và 78s** dưới phản ứng của Nick / tình nhân.
  - Nhạc tắt 85–87s (tiếng "Plop" 0.76) ↔ cắt 85.4 / 86.9; về −25 dB ở 92s ↔ cắt 92.1 sang bánh kem sinh nhật (đổi tông).
  - silencedetect: lặng 108.7–114.8s (ngoài khúc audio_listen) dưới khách vỗ tay / cận nạng — chưa phân tích lớp.

## Bảng shot — đoạn 1 (0:00–3:00, 81 shot)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1–4 | 0.0–14.2 | CU hai phụ nữ | ngang mắt | tĩnh×4 | cảnh tương lai: đối đầu; nhạc lên + Rumble 8s |
| 5–6 | 14.2–21.9 | insert ảnh gia đình; MS nấu ăn | ngang | tịnh tiến×1, tĩnh×1 | **lặng hoàn toàn**; thẻ tên LINDA HASTINGS |
| 7–13 | 21.9–39.8 | insert điện thoại; MS / CU nghe máy | ngang | tĩnh×7 | cuộc gọi bắt cóc; nhạc bật từng cú 27 / 32 / 36s |
| 14–20 | 39.8–53.3 | insert tay; WS ngồi sàn; CU khóc; insert danh bạ | ngang; #15 cao | roll×1, tịnh tiến×1, tĩnh×3, thiếu dữ liệu×2 (chớp trời 0.3–0.4s) | gọi bố; gần như không nhạc |
| 21–24 | 53.3–61.4 | WS phòng giam (thẻ THREE YEARS LATER); CU; insert thỏ bông | cao nhìn xuống | tịnh tiến×1, zoom in×1, tĩnh×2 | im lặng dưới thẻ thời gian |
| 25–31 | 61.4–80.0 | CU nam ↔ CU nữ máu mặt; MS bế ra | ngang | roll×2, zoom in×2, tĩnh×3 | giải cứu; thẻ tên JULIAN THORNE |
| 32–39 | 80.0–99.3 | WS xe; CU trong xe; insert tay chìa ra | ngang | tịnh tiến×1, tĩnh×7 | "you walked away from your inheritance" |
| 40–48 | 99.3–121.5 | WS dinh thự + vệ sĩ; MS ôm cha | ngang / xa | tịnh tiến×3, zoom in×1, tĩnh×5 | nhạc lên 99.3s rồi lặng ~5s |
| 49–81 | 121.5–180.0 | insert hợp đồng chuyển cổ phần; CU ↔ CU cha / con 1–2.5s | ngang | zoom in×1, tịnh tiến×2, tĩnh×30 | "a position worth tens of billions"; gần như không nhạc |

## Bảng shot — đoạn 3 (tiệc sinh nhật ≈9:30, hình từ giây 9.85)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1–4 | (9.85)–17.1 | CU Linda; CU tình nhân; insert tay đeo nhẫn | ngang | tĩnh (#1 gộp đoạn đen) | khoe nhẫn |
| 5–11 | 17.1–28.6 | CU Nick "What?"; insert hợp đồng HASTINGS GROUP; CU | ngang | tĩnh×7 | nhạc rõ; Bang/Explosion ở cắt 27.5 / 28.6 |
| 12–14 | 28.6–42.1 | MS hai khách há hốc; CU tình nhân; CU Nick cầm giấy | ngang | tĩnh×3 | tình nhân kể "bao năm bên nhau" |
| 15–30 | 42.1–68.7 | shot / phản shot CU Linda (nạng) ↔ tình nhân ↔ Nick, 0.5–3.6s | ngang | zoom in×2, tĩnh×14 | **nhạc tắt 42–57s**, về ở cắt 57.9; "chữ ký của một giám đốc cấp thấp" |
| 31–41 | 68.7–89.7 | CU Nick "Is this a joke?"; CU tình nhân / Linda | ngang | tịnh tiến×1, zoom in×1, tĩnh×9 | Bang ở cắt 68.7; tim đập 70 / 78s; nhạc tắt 85–87s |
| 42–52 | 89.7–108.1 | CU con gái; insert bánh kem nến | ngang | tĩnh×11 | sinh nhật; nhạc về 92s |
| 53–65 | 108.1–130.0 | MS Nick + tình nhân + bánh; CU Linda; khách vỗ tay; **insert nạng bó bột** (115.0–116.2) | ngang | roll×1, tĩnh×7, thiếu dữ liệu×5 | lặng 108.7–114.8s; "Oh my God, Nick is so lucky" |

## Kỹ thuật đáng học
1. **Mở bằng cảnh tương lai có nhạc + tiếng ầm, rồi cắt thẳng vào im lặng hoàn toàn của "cuộc sống thường ngày"** (0–14.2s → 14.2–23.2s, lặng bắt đầu đúng
   điểm cắt). Ý đồ **[có thể]**: móc người xem bằng xung đột trước, rồi dùng tương phản âm thanh để báo "quay về lúc trước". Độ tin: khá (đo khớp tới 0.1s).
2. **Nhạc dùng như cú nhấn (sting), không làm nền, trong đoạn bi kịch** (cuộc gọi bắt cóc: 27 / 32 / 36s, mỗi cú 1–2s, còn lại < −60 dB; nhạc chỉ 14–32%). Ý đồ
   **[có thể]**: để tiếng thở, nấc, bíp điện thoại mang cảm xúc; nhạc chỉ chấm câu. Độ tin: có thể.
3. **Tắt nhạc dưới màn đối đáp then chốt, cho nhạc về ở cắt sang phản ứng** (đoạn 3: 42–57s tắt, về ở cắt 57.9; 85–87s tắt, về ở cắt 92.1 sang bánh kem).
   Ý đồ **[có thể]**: câu thoại lật thế cờ được nghe "trơ trọi". Độ tin: có thể — cùng chiều với 06 (tắt 84–89s) và 07 (tắt 33–40s).
4. **Tiếng đập + tim đập ở khoảnh khắc lộ bài** (Bang ở cắt 68.7 "Is this a joke?", tim đập 70s / 78s; Explosion ở cắt 36.1 khi cuộc gọi tắt). Ý đồ **[có thể]**:
   biến khoảnh khắc lời nói thành "cú đánh". Độ tin: có thể → khá — cùng kiểu với 07 (đập trùng cắt, tim đập dưới câu lật bài).
5. **Thẻ tên nhân vật trên hình** (LINDA HASTINGS 18.5s, JULIAN THORNE 67.0s) và **insert chớp trời 0.3–0.4s** giữa các CU khóc. Ý đồ **[có thể]**: giúp người xem
   lướt nắm ngay ai là ai; chớp trời là "dấu chấm than" rẻ, không cần diễn. [suy luận] với video AI: cả hai đều là tài sản dựng / hậu kỳ, không tốn lượt sinh video.

## Giới hạn / câu hỏi mở
- Bản gộp lặp tập: đoạn 2 trùng đoạn 1; tờ quét cho thấy còn lặp ở chỗ khác (phòng họp ~39:00). Chưa tìm được "giữa phim" thật; phần cuối phim chưa xem.
- Lớp "nhạc" của demucs lẫn hiệu ứng → "nhạc 76%" ở đoạn 3 là nhạc + hiệu ứng. Chưa nghe tai.
- Đoạn 3 giây file 100–130 và đoạn 1 giây 135–180 chỉ có số silencedetect / RMS.
- Không biết công cụ AI.

## Xoá dữ liệu
Đã xoá `v10_seg1.webm`, `v10_seg2.webm`, `v10_seg3.webm`, `v10_scan.mp4`, thư mục `v10_seg*_frames/`, `v10_*sheet*.jpg`, thư mục `v10_a_listen/`, `v10_b_listen/`,
`v10_c_listen/` (wav, stem, lời chép) và log. Chỉ giữ `v10_seg{1,2,3}_result.json`, `v10_seg1a/seg1b/seg3_listen_numbers.json` (không lời chép).
