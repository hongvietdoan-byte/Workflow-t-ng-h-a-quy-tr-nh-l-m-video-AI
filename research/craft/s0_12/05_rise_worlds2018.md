# 05 — RISE (ft. The Glitch Mob, Mako, The Word Alive) — Worlds 2018 Cinematic (League of Legends)

- **URL**: https://www.youtube.com/watch?v=fB8TyLTD7EE
- **Thể loại**: CGI cinematic game chính thức (Riot Games) — kết hợp nhiều nhân vật League of Legends, có đoạn người thật (game thủ xem) ở cuối
- **Độ dài**: 3:30 (210.1s) · khung 1280×720 (16:9)
- **Đoạn đã đo**: TOÀN BỘ (210.1s, ≤4 phút nên đo hết)
- **Đã tải**: `v05_full_fB8TyLTD7EE.webm` (11.8 MB) — **đã xoá cùng frame/sheet/spectrogram sau khi viết xong file này**.

## Phương pháp (cải tiến lượt 3)
- Cùng pipeline cắt/tờ ảnh/LUFS-LRA-quãng lặng như trước, **bỏ báo cáo đỉnh (true peak)** theo ghi chú phiên chính (đo trên WebM/Opus tải về không tin được, giải mã tổn hao có thể vượt đỉnh gốc).
- **Chuyển động máy per-shot bằng OpenCV** (`goodFeaturesToTrack` + `calcOpticalFlowPyrLK` + `estimateAffinePartial2D` RANSAC), lấy mẫu cặp khung cách ~0.2s trong mỗi shot, che dải dưới khung trước khi tính đặc trưng. Phân tách: tịnh tiến lớn → "pan/truck/tilt/pedestal" (không tách được hướng nếu không có thị sai rõ); đổi tỉ lệ → "zoom/dolly in/out"; xoay trục ống kính → "roll"; dưới ngưỡng cả 3 → "tĩnh". Ngưỡng: tịnh tiến > 1.0%/cặp khung, đổi tỉ lệ > 1%, xoay > 0.5°.
- **Phổ âm thanh** (`showspectrumpic`, 3 khúc 60s) — đọc trực tiếp bằng mắt để "nghe bằng mắt": tìm vệt hoà âm ngang bền vững (nhạc có giai điệu/hợp âm) vs kết cấu vạch dọc dày đặc (thoại/tiếng động liên tục).

## Số đo
- 100 shot, độ dài trung vị **1.19s** (rất nhanh — nhanh nhất trong các video đã đo), min 0.33s, max 16.25s (shot #95, cảnh mây/pháo đài cuối).
- Âm thanh: LUFS tích hợp **−16.5**, LRA **7.0 LU**. 7 quãng lặng, chủ yếu dồn ở cuối phim (198–207s, đoạn "mắt game thủ") — chỉ 1/7 trùng điểm cắt.
- **Chuyển động máy per-shot (OpenCV, 100 shot)**: tĩnh 43%, zoom/dolly in **22%**, roll **13%**, pan/truck/tilt/pedestal 12%, không đủ dữ liệu (shot quá ngắn <0.4s để track) 10%.
  - **Đây là video có tỉ lệ zoom/dolly-in và roll cao nhất trong các video đã đo** (video 01/04 gần như chỉ có tĩnh + tịnh tiến nhẹ, không có zoom/roll đáng kể) — khớp trực giác: cinematic game CGI dùng đẩy máy (dolly/zoom in) để nhấn khoảnh khắc và roll cho hiệu ứng choáng ngợp/chuyển cảnh, trong khi drama thoại (01, 04) gần như chỉ tĩnh.

### Đọc phổ âm thanh (spectrogram, 3 khúc 60s)
- **Khúc 1 (0–60s)**: 0–5s yên tĩnh hơn hẳn (mở đầu bí ẩn — khớp shot #1–9 cận tay/vũ khí); **~6–7s có một điểm vào rất mạnh, phổ rộng đột ngột** (dải sáng lan tới tần số cao) — khớp đúng lúc nhạc/hiệu ứng "vào" mạnh sau mở đầu tĩnh lặng. Độ tin: **khá** (thấy rõ bằng mắt, đối chiếu đúng cấu trúc "mở bí ẩn → bùng nổ" điển hình của trailer).
- **Khúc 3 (120–180s)**: thấy **rõ các vệt ngang xếp tầng ổn định** ở dải 700–3000Hz (khác hẳn kết cấu "vạch dọc dày đặc không có vệt ngang" của các video thoại 01/04) — đây là dấu hiệu điển hình của **nhạc có hoà âm/giai điệu bền vững** (dây, kèn, hoặc pad tổng hợp) chạy dưới hiệu ứng. Cũng thấy các vạch dọc sáng lặp gần như đều đặn (~mỗi 1.5–2s) — có thể là nhịp trống/tiếng đập của track hành động. **Độ tin: khá** — mẫu hình rõ ràng, khác biệt rõ rệt so với các video thoại-chủ-đạo đã xem.
- **Khúc 2 (60–120s)**: năng lượng dải trầm rất mạnh và liên tục (đúng đoạn chiến đấu băng/lửa #43–66) — ít thấy vệt ngang rõ hơn khúc 3, có thể do mix hành động dày (SFX nổ, va chạm) che mất hoà âm nhạc nền. Độ tin: vừa.
- **Kết luận nhạc nền [có thể → khá]**: RISE có nhạc nền chạy liên tục xuyên suốt với hoà âm rõ (khớp việc bài hát chủ đề "RISE" của The Glitch Mob/Mako/The Word Alive là chính bài hát của video), khác hẳn kết cấu "gần như chỉ thoại" của video 01/04. Đây là bằng chứng **thị giác trực tiếp** (đọc phổ) đầu tiên trong dự án xác nhận có nhạc, mạnh hơn nhiều so với phép đo RMS/silence gián tiếp.

## Bảng shot (toàn bộ 100 shot — xem chi tiết đầy đủ vào/ra/dài/cỡ cảnh/máy đo OpenCV/hành động)
Đã tạo trong quá trình phân tích (giữ trong `scratchpad/s012/v05_full_table.md` trước khi xoá theo quy tắc — tóm tắt theo cụm cảnh dưới đây, mỗi shot vẫn có số thứ tự/mốc/cỡ cảnh/góc riêng trong dữ liệu đo gốc):

| # | Vào–ra | Cỡ cảnh chủ đạo | Máy chủ đạo (đo OpenCV) | Nội dung |
|---|---|---|---|---|
| 1–9 | 0.0–11.8 | CU/insert | tĩnh + vài zoom-in/roll ngắn | Mở đầu bí ẩn: cận tay/vũ khí, lông vũ đen, lau sậy khô |
| 10–18 | 11.8–20.1 | CU/insert | tĩnh | Nhân vật đội mũ trùm giữa lau sậy; cận quạ đen |
| 19–30 | 20.1–47.2 | WS | tịnh tiến + zoom-in xen kẽ | Nhân vật nhỏ giữa núi tuyết/sa mạc rộng lớn — thiết lập quy mô |
| 31–39 | 47.2–70.2 | CU/insert | roll + zoom-in + tịnh tiến | Chiến đấu tia sáng tím, nhân vật tóc tím, sấm sét |
| 40–48 | 70.2–90.7 | insert/CU/WS | roll + tịnh tiến | Tia sét bùng nổ toàn khung; chiến đấu băng giá |
| 49–66 | 90.7–138.9 | CU/insert/WS | zoom-in nhiều nhất đoạn này | Thế giới lửa đỏ — quái vật, nhiều nhân vật chiến đấu, thành trì cháy |
| 67–78 | 138.9–154.1 | insert/CU | tĩnh + zoom-in + roll | Biểu tượng/huy hiệu, kiếm, hiệu ứng phép thuật bùng nổ (cao trào thị giác) |
| 79–90 | 154.1–168.5 | WS/insert/CU | tịnh tiến + roll | Toàn cảnh mây, ánh sáng vàng, tia lửa/nổ |
| **91–100** | **168.5–210.1** | **insert/CU/WS** | **zoom-in (đẩy máy chậm dài, tới 16.2s)** | **CHUYỂN SANG NGƯỜI THẬT**: cận mặt game thủ đeo kính xem màn hình, hai cột trụ đá trong mây, kết bằng cận mắt người xem phản chiếu ánh sáng |

## Kỹ thuật đáng học
1. **Nhịp cắt cực nhanh (median 1.19s) đi kèm chuyển động máy phong phú (zoom-in 22%, roll 13%)** — khác các video thoại đã xem (chủ yếu tĩnh). Ý đồ **[có thể]**: cinematic trailer dùng cả tốc độ cắt VÀ chuyển động máy để tạo cường độ thị giác tối đa, không chỉ dựa vào tốc độ cắt như drama thoại. Độ tin: có thể, khớp trực giác về thể loại trailer game.
2. **Chuyển từ CGI sang người thật ở đoạn cuối (shot #91–100), dùng đẩy máy chậm dài (16.2s ở #95)** — ngược hẳn nhịp cắt nhanh trước đó — kỹ thuật "hạ nhiệt bằng shot dài" trước khi kết, tương tự nguyên tắc "shot dài ở khoảnh khắc cảm xúc" đã thấy ở video 02/03. Đây là **quan sát trùng với video 02 và 03** (nhịp chậm hẳn ở đoạn cảm xúc/kết) — đủ điều kiện đưa vào `TONG_HOP.md`.
3. **Cấu trúc "người chơi tưởng tượng trận chiến"**: mở bằng CGI hoành tráng, kết lộ ra một game thủ thật đang xem/tưởng tượng — kỹ thuật kể chuyện đặc trưng của cinematic game (kết nối người chơi thật với thế giới ảo). Độ tin: quan sát 1 mẫu, đặc trưng thể loại cinematic game nói chung (kiến thức nền, không phải suy luận từ video này).
4. **Bằng chứng thị giác (phổ âm thanh) đầu tiên xác nhận nhạc chạy liên tục có hoà âm rõ** — khác hẳn RMS/silence gián tiếp đã dùng trước đây; phương pháp `showspectrumpic` đọc bằng mắt hiệu quả hơn hẳn phép đo số (RMS/LUFS) cho câu hỏi "có nhạc hay không".

## Giới hạn / câu hỏi mở
- Không xác định được chính xác từng vị trí "nhạc vào/ra/đổi" theo giây — chỉ đọc được xu hướng theo khúc 60s; cần spectrogram khúc nhỏ hơn (10-20s) quanh các điểm nghi ngờ để chính xác hơn nếu cần mốc giây chi tiết.
- `pan/truck/tilt/pedestal` vẫn không tách được hướng cụ thể — cần xem lại bằng mắt qua tờ ảnh mid-frame để đoán hướng khi cần (không làm ở đây do giới hạn thời gian).
- Không xác định được tên chính xác từng vị tướng League of Legends xuất hiện (không phải trọng tâm phân tích kỹ thuật quay/dựng).

## Xoá dữ liệu
Đã xoá `v05_full_fB8TyLTD7EE.webm`, thư mục `v05_full_frames/`, `v05_full_sheet_*.jpg`, `v05_full_spec_*.png` khỏi `scratchpad/s012` sau khi viết xong file này — chỉ giữ JSON số đo + bảng shot đầy đủ dạng `.md` nội bộ.
