# 09 — 《大師兄》 (phim ngắn AI võ hiệp, kênh 柯克明 Ke Ke Ming)

- **URL**: https://www.youtube.com/watch?v=wW5CYqCvWzI
- **Thể loại**: phim ngắn AI (không phải drama gộp tập) võ hiệp / wuxia, 16:9, thoại tiếng Trung + phụ đề Trung; mô tả kênh ghi làm toàn bộ bằng AI,
  **không ghi tên công cụ** — mục 6.1 trong `MAU_S0_12.md`
- **Độ dài công bố**: 13:25 · file tải 1280×720
- **Đoạn đã đo**: (1) 0:00–3:00 (180.0s, hình và âm cùng từ giây 0) · (2) yêu cầu 8:50–10:20 — file 100.0s, **hình chỉ bắt đầu ở giây 9.9 của file**, âm từ giây 0
  (yt-dlp cắt theo keyframe) → mốc gốc ≈ 8:40 + t; mốc trong bảng là giây của file
- **Tổng đã đo**: ~270s hình / 805s (~34%)
- **Đã tải**: `v09_seg1.webm` (11.6 MB), `v09_seg2.webm`, khúc quét 360p 3:00–13:25 (xoá ngay sau khi chọn đoạn) — **tất cả đã xoá sau khi viết file này**.

## Cách tìm đoạn cao trào hành động
Khúc 3:00–13:25 ở 360p, `ffmpeg fps=1/10` + `tile=8x8` ra 1 tờ 62 khung. Phim **không có một trường đoạn đánh nhau dài** như phim hành động quay thật: phần lớn là
cậu bé và "đại sư huynh" nói chuyện ở túp lều trên núi tuyết. Khung "hành động" duy nhất là **hồi tưởng bên hồ mùa thu** (luyện kiếm, người luyện chém mặt nước)
và các khung **đám mây khổng lồ** (~9:50 và ~11:50). Chọn 8:50–10:20 phủ trọn hồi tưởng + đám mây đầu tiên.

## Phương pháp
Như 07: `ffmpeg scene` 0.25 (kiểm lại ở 0.12), tờ ảnh khung giữa shot + tờ 1 khung/2s (đoạn 1) và 1 khung/giây (đoạn 2), `ebur128` + `silencedetect`, OpenCV
`motion_cv2.py`, `tools/audio_listen.py --lang zh` trên đoạn 1 giây 0–90 và đoạn 2 giây file 10–100 (bắt đầu đúng chỗ có hình, nên mốc listen + 10 = giây file).
Ngưỡng 0.12 ở đoạn 1 thêm một chùm 8 "cắt" trong 124.9–126.0s — là chớp sáng khi cửa lều mở, không phải cắt; nên giữ số shot theo ngưỡng 0.25.

## Số đo
| Đoạn | Shot | Trung vị | Min–max | Shot/phút | Máy (OpenCV) |
|---|---|---|---|---|---|
| Mở đầu 0:00–3:00 | 29 | **4.66s** | 1.33–19.0s | 9.7 | **tĩnh 90%**, tịnh tiến 7%, zoom in 3% |
| Hồi tưởng + đám mây (≈8:50–10:20) | 23 (90s có hình; ngưỡng 0.12: 31) | 3.37s | 0.9–8.6s | 15.3 | tĩnh 65%, zoom in 9%, tịnh tiến 9%, thiếu dữ liệu 13% (cả shot đen đầu file) |

- Âm thanh: LUFS **−17.6** / **−19.5**, LRA **12.7** / **7.4 LU**; **0 quãng lặng** (< −35 dB) ở cả hai đoạn.
- **Nhịp cắt chậm nhất trong các video AI đã đo** (trung vị 4.66s so với 1.4–3.7s ở 01, 04, 06, 07) — gần phim ngắn TOMORROW (02, 3.7s mở đầu) hơn AI drama.
- Máy tĩnh 90% ở đoạn 1 dù bối cảnh là núi non hùng vĩ — **ngược** quan sát "thế giới thần thoại → máy động" của 07; ở đây sự hùng vĩ đến từ **cỡ cảnh** (toàn cảnh
  cực rộng, người nhỏ xíu) chứ không từ chuyển động máy.

### Nghe bằng số (audio_listen)
- **Nhạc 100%** cả hai đoạn, không lần nào tắt. Tempo 99.4 BPM (đoạn 1) / 129.2 (đoạn 2); giọng điệu đoán D thứ, độ khớp **0.82 / 0.74** (cao — nhạc nền
  có giai điệu rõ, khác AI drama 0.35–0.41).
- **Đoạn 1 gần như không có lời thoại trong 2:38 đầu**: whisper không ra câu nào ở 0–90s; lớp giọng (−15…−22 dBFS ở 10–22s, 27–30s, 55–58s, 64–73s) là **tiếng thở,
  gắng sức** khi leo núi (nhãn Snort / Gasp / Sigh 2–4s). Phụ đề (thoại) chỉ xuất hiện từ ~2:38 trên tờ ảnh.
- Mức nhạc đoạn 1 theo hình (listen = giây file):
  - 0–29s nhạc nhỏ −38…−46 dB dưới tiếng gió / thở; **6s nhãn Whip 0.72** trùng lúc bàn tay đập lên mép đá (khung 6s).
  - **30s nhạc lên −26.5 → −22 dB, trùng cắt 30.1** sang toàn cảnh cực rộng vách đá, cậu bé nhỏ như một chấm.
  - 38–42s sáo (Flute 0.13, 0.07).
  - **58s nhạc lên −20.7 dB, trùng chữ tên phim 《大師兄》 hiện ra (58–68s)** trên toàn cảnh vách tuyết.
  - 73s lên −19.3 dB ↔ cắt 74.2 (cây thông + biển mây).
- Đoạn 2 (giây file):
  - Nhạc rõ −24…−37 dB suốt, **thoại gần liên tục** (44 câu whisper trong 90s, dùng làm mốc — không chép lời) chạy **xuyên qua hồi tưởng** (giọng kể của sư huynh).
  - **32–34s nhạc lên −26.4 → −22.9 dB + nhãn Smash/Crash** trùng nhát kiếm chém mặt nước (khung 32s).
  - **44–46s giọng tắt (−72 dB) nhưng nhạc vẫn chạy** — đúng chỗ ECU hai mắt người bị đánh bại (44–46s).
  - **71s nhạc lên −23.4 dB ↔ cắt 71.5** sang shot qua vai cậu bé nhìn đám mây khổng lồ.
  - Từ ~84s nhãn **Explosion / Eruption 0.13–0.40** kéo dài tới hết khúc đo (98s) — một lớp ầm ì trầm dưới thoại sau khi thấy đám mây. Độ tin: có thể (nhãn trên lớp
    nhạc tách, có thể là tiếng trống trầm của nhạc chứ không phải hiệu ứng nổ).

## Bảng shot — đoạn 1 (0:00–3:00, 29 shot)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1 | 0.0–19.0 | WS núi → CU mặt | ngang mép đá | tĩnh | khung trống 6s → tay bám mép đá (tiếng đập) → mặt cậu bé trồi lên 10s; thở gấp |
| 2–4 | 19.0–51.5 | MS bên hông → **EWS vách đá** → WS sống núi | ngang / xa | tĩnh×3 | leo vách với gùi; 30.1s nhạc lên cùng toàn cảnh cực rộng |
| 5 | 51.5–69.6 | EWS vách tuyết 18.1s | xa, ngang | tĩnh | cậu bé leo nhỏ xíu; chữ tên phim 58–68s + nhạc lên |
| 6–10 | 69.6–105.0 | MS trên biển mây; WS cây thông; WS nhìn từ trên xuống túp lều | ngang; #10 cao (flycam) | tĩnh×5 | chưa có thoại; sáo |
| 11–15 | 105.0–124.9 | CU chỉnh khăn; insert chân / khúc gỗ; CU nhìn lên | ngang; #13 thấp nhìn lên mặt | tịnh tiến×1, tĩnh×4 | tới lều |
| 16–21 | 124.9–147.8 | trong lều tối; MS ở cửa; **CU mặt ↔ insert vách đá có vết khắc** | ngang | tịnh tiến×1, zoom in×1, tĩnh×4 | cắt đi lại mặt cậu bé và vết khắc đếm ngày trên đá |
| 22–29 | 147.8–180.0 | WS lều; OTS cậu bé nhìn bóng người xa trên núi; CU | ngang | tĩnh×8 | sư huynh xuất hiện; thoại bắt đầu ~158s |

## Bảng shot — đoạn 2 (≈8:50–10:20, hình từ giây 9.9)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1 | (9.9)–16.1 | CU cậu bé | ngang | (gộp đoạn đen) | nghe kể, rưng rưng |
| 2–3 | 16.1–27.8 | OTS → sư huynh cầm hũ; insert túi táo đỏ | ngang | tĩnh×2 | thoại liên tục |
| 4–9 | 27.8–48.4 | **hồi tưởng hồ mùa thu**: WS người luyện kiếm, insert **chém mặt nước**, ECU mắt, insert tay / cánh tay | ngang; ECU sát | zoom in×1, tịnh tiến×1, tĩnh×4 (ngưỡng 0.12: 12 shot, trung vị ~1.5s) | giọng kể chạy xuyên; nhạc lên + Smash 32–34s; giọng tắt 44–46s dưới ECU mắt |
| 10–13 | 48.4–71.5 | MCU sư huynh; insert bàn tay mở → nắm lại trên nền núi | ngang | tĩnh×4 | về hiện tại; giơ nắm tay |
| 14–16 | 71.5–80.8 | **OTS cậu bé → đám mây khổng lồ**; CU nghiêng sư huynh; CU cậu bé | ngang | tĩnh×3 | nhạc lên ở cắt 71.5 |
| 17–23 | 80.8–100.0 | CU ↔ CU đối đáp; WS sư huynh trên biển mây | ngang | tịnh tiến×1, tĩnh×3, thiếu dữ liệu×3 | cậu bé cười 94–96s; lớp ầm ì "Explosion" 84–98s |

## Kỹ thuật đáng học
1. **Mở phim 2:38 không một câu thoại** — kể bằng hình (leo vách, túp lều, vết khắc đếm ngày), tiếng thở và nhạc (0–158s). Ý đồ **[có thể]**: cho người xem sống cùng
   sự cô độc / gian khổ của cậu bé trước khi nghe ai nói gì. Độ tin: khá (đo được: whisper không ra câu, lớp giọng chỉ là thở). Khác hẳn AI drama (thoại từ giây 1).
2. **Lộ nhân vật bằng cách để họ đi vào khung tĩnh** (shot 1: khung núi trống 6s → bàn tay kèm tiếng đập → mặt trồi lên 10s). Ý đồ **[có thể]**: câu hỏi "ai đang
   ở đây?" rồi trả lời trong cùng shot, không cần cắt. Với video AI: prompt được dạng "khung trống, rồi tay xuất hiện ở mép dưới" — [suy luận] cần thử.
3. **Nhạc lên đúng shot "lộ quy mô" và chữ tên phim** (30.1s toàn cảnh vách đá; 58s tên phim). Ý đồ **[có thể]**: nhạc đánh dấu cấu trúc (hết mở màn → vào truyện)
   thay cho lời. Độ tin: có thể (mức nhạc đo được, trùng cắt ±0.5s ở 3 chỗ).
4. **Hành động kể bằng hồi tưởng ngắn dưới giọng kể liên tục** (27.8–48.4s: ~12 shot trung vị ~1.5s, gấp đôi nhịp quanh đó), rồi **để giọng tắt 2s trên ECU mắt**
   (44–46s) trong khi nhạc vẫn chạy. Ý đồ **[có thể]**: hành động là minh hoạ cho lời kể; khoảng lặng lời trên ECU làm nổi "cú sốc" của người thua. Độ tin: có thể, 1 lần.
5. **Cho thấy sức mạnh qua hậu quả, không qua đòn đánh** (71.5s: đám mây khổng lồ nhìn qua vai cậu bé, rồi lớp ầm ì dưới thoại). Ý đồ **[đoán]**: tránh dựng
   trường đoạn giao đấu (khó và dễ lỗi với AI), thay bằng một hình ảnh quy mô lớn + phản ứng nhân vật. [suy luận] hợp với giới hạn model video về đánh nhau nhiều người.

## Giới hạn / câu hỏi mở
- Chưa thấy trường đoạn đánh nhau "thật" nào trong 3:00–13:25 qua tờ 1 khung/10s — có thể phim cố ý không có; các khung đám mây ở ~11:50 chưa đo.
- Chép lời whisper chỉ dùng lấy mốc câu; nội dung câu chưa đối chiếu với phụ đề (chữ nhỏ trên tờ ảnh).
- "Explosion" 84–98s có thể là trống trầm — chưa nghe tai. OpenCV không đo được 3 shot cuối đoạn 2 (nền mây trắng ít điểm bám).
- Công cụ AI: không biết (mô tả không ghi).

## Xoá dữ liệu
Đã xoá `v09_seg1.webm`, `v09_seg2.webm`, `v09_scan.mp4`, thư mục `v09_seg*_frames/`, `v09_*sheet*.jpg`, `v09_seg1_half.jpg`, `v09_seg2_1fps.jpg`, thư mục
`v09_a_listen/`, `v09_b_listen/` (wav, stem, lời chép) và log. Chỉ giữ `v09_seg{1,2}_result.json`, `v09_seg{1,2}_listen_numbers.json` (không lời chép).
