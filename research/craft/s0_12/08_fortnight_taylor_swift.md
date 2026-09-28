# 08 — "Fortnight" (feat. Post Malone), MV chính thức của Taylor Swift

- **URL**: https://www.youtube.com/watch?v=q3zqJs7JUCQ (kênh chính chủ)
- **Thể loại**: MV ca nhạc có tường thuật (song-led), **đen trắng**, bối cảnh siêu thực (phòng bệnh trắng, văn phòng máy đánh chữ, đường giữa
  sa mạc, phòng thí nghiệm) — mục 4.3 trong `MAU_S0_12.md`
- **Độ dài công bố**: 4:09 · file tải 1280×720, 16:9
- **Đoạn đã đo**: 0:00–3:00 (180.0s; hình và âm bắt đầu cùng giây 0 — đã kiểm bằng `ffprobe`) · **~72% bài**
- **Đã tải**: `v08_seg1.webm` (11 MB) — **đã xoá sau khi viết file này**.

## Phương pháp
Như 06/07: điểm cắt `ffmpeg scene`, tờ ảnh khung giữa shot, `ebur128` + `silencedetect` (−35 dB, ≥ 0.3s), chuyển động máy per-shot bằng OpenCV
(`motion_cv2.py`), "nghe bằng số" `tools/audio_listen.py` 0–90s và 90–180s (`--lang en`). **Riêng video này**: hình đen trắng tương phản thấp nên
ngưỡng 0.25 bỏ sót 4 cắt (39.7, 89.7, 94.1, 179.7) — đã chạy lại ngưỡng 0.12 (32 cắt, khớp mắt) và 0.08 (thêm 3 "cắt" giả do giấy bay / chớp trắng).
Số shot dưới đây theo ngưỡng 0.12; chuyển động máy OpenCV đo theo ranh giới ngưỡng 0.25 (29 shot). Soi thêm 1 khung/giây ở 0–30s và 105–160s.
Mốc lời hát lấy từ faster-whisper trên lớp giọng — **chỉ dùng mốc giây, không chép lời** (bài hát có bản quyền; lời chép đã xoá).

## Số đo
| Đoạn | Shot | Trung vị | Min–max | Shot/phút | Máy (OpenCV, 29 shot) |
|---|---|---|---|---|---|
| 0:00–3:00 | 33 | 2.9s | 0.3–29.9s | 11.0 | tĩnh 59%, **zoom/dolly in 24%**, tịnh tiến 14%, roll 3% |

- Âm thanh: LUFS **−17.2**, LRA **3.3 LU** (rất hẹp — bản mix nhạc pop nén chặt, khác hẳn AI drama 11.8–14.1 LU); quãng lặng chỉ **2** (0–1.0s và 4.5–5.6s,
  cả hai trong thẻ tên phim).
- Nhịp cắt **chậm hơn mọi AI drama đã đo** (11 shot/phút so với 18–30) và phân bố lệch: 5 shot ≥ 10s (29.9s, 20.0s, 11.7s, 10.8s, 11.5s) chiếm 84s / 180s.

### Nghe bằng số (audio_listen)
- **Nhạc 99–100%** (0–90s / 90–180s). 0–4s trước nhạc: nhãn **Vehicle / Engine** trên lớp nhạc (tiếng nền kiểu máy móc dưới thẻ tên phim), nhạc lên dần
  từ −54 dB (giây 0) → −35 dB (giây 6) → −22 dB (giây 7–9) đúng lúc giọng hát vào (giây 6.0).
- Nhãn AST gần như chỉ "Music" 0.5–0.76 suốt 180s; điểm lẻ: Double bass / Bowed string 80–84s, Bicycle bell / Ding 94–96s và 164–166s, Slap/Whip 168–170s
  (tiếng hiệu ứng nhỏ trộn trong nhạc, điểm ≤ 0.12 — độ tin thấp).
- Tempo **95.7 BPM**, giọng điệu đoán B trưởng (độ khớp 0.75 — cao hơn hẳn các AI drama 0.36–0.41, vì đây là một bài hát liền mạch).
- **Không có lần tắt nhạc nào** trong 180s — khác 06/07. Biến đổi cảm xúc đi bằng lời hát + hình, không bằng im lặng.

### Phần lời hát ↔ hình (mốc whisper, không chép lời)
| Phần (mốc câu hát) | Hình | Cắt gần nhất |
|---|---|---|
| Thẻ tên phim 0–5s, chưa hát | thẻ chữ viền cổ điển, tiếng máy | chồng mờ ~5s |
| Đoạn 1 (6.0–45.7s, 5 câu) | 6–29.9s **một shot duy nhất**: từ CU mặt cô gái bị buộc trên giường, máy lùi / nâng dần thành toàn cảnh phòng bệnh trắng | câu 3 bắt đầu 28.5s ↔ cắt 29.9s (+1.4s) |
| Điệp khúc 1 (45.7–~65.7s) | shot 5: CU mặt 20.0s, máy đẩy vào (47.3–67.3s) | câu vào 45.7s ↔ cắt 47.3s (+1.6s) |
| Đoạn 2 (65.7–~90s) | văn phòng máy đánh chữ; người đàn ông xuất hiện 79.7s | câu vào 65.7s ↔ cắt 67.3s (+1.6s) |
| Câu chuyển (~90–114s) | cận phím / trang giấy: **dòng chữ đánh máy trên giấy trùng câu đang hát** (99.3–101.4s) | — |
| Điệp khúc 2 (~114–146s) | 109–113s **khói màu cam + xanh** (màu duy nhất trong MV đen trắng) bốc từ hai máy chữ gặp nhau → **chớp trắng 114s** → nhìn thẳng từ trên hai người nằm trên nền trắng → 119.8s đường giữa sa mạc, ôm nhau | chớp trắng trùng đầu điệp khúc (±1s, mốc whisper) |
| Hậu điệp khúc (~146–158s) | 139.5–145.9s bốn CU chính diện luân phiên nữ / nam nhìn thẳng máy (1.8–2.4s); 148.4s toàn cảnh giấy xoáy; 154.2s sang phòng thí nghiệm | 154.2s |

- Cắt **thường trễ đầu câu hát 1.4–1.6s** (3/4 chỗ đo được) chứ không trùng đầu câu — [có thể] để câu hát "vào" trên hình cũ rồi mới đổi hình. Chưa đo khớp
  phách (0.63s/phách ở 95.7 BPM) — mốc cửa sổ whisper không đủ mịn.

## Bảng shot (0:00–3:00, cụm theo cảnh)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1 | 0.0–29.9 | thẻ chữ → CU → WS | từ cao nghiêng, nhìn xuống | zoom/dolly **out** thấy bằng mắt (OpenCV xếp "zoom in" do trung vị cả shot gồm cả thẻ chữ) | thẻ tên 0–5s; giường bệnh; đoạn 1 lời hát |
| 2–4 | 29.9–47.3 | insert tay đưa thuốc; CU mặt; WS phòng | ngang mắt / cao | tịnh tiến×1, tĩnh×2 (+ cắt 39.7 ngưỡng thấp) | cô gái uống thuốc; căn phòng trắng rộng |
| 5 | 47.3–67.3 | CU mặt 20.0s | ngang mắt | zoom/dolly in | điệp khúc 1 trọn trong một shot |
| 6–10 | 67.3–96.4 | WS văn phòng → MS hai người ở máy chữ | ngang mắt, chính diện, đối xứng | tịnh tiến×1, tĩnh×3, zoom in×1 (84.7–96.4) | đoạn 2; nam xuất hiện 79.7s |
| 11–17 | 96.4–119.8 | insert trang giấy / phím; WS văn phòng; top-down | ngang / **nhìn thẳng từ trên** | tĩnh×5, zoom in×1 | chữ đánh máy trùng lời; khói màu; chớp trắng; vào điệp khúc 2 |
| 18–22 | 119.8–139.5 | WS đường sa mạc → MS ôm nhau → 2-shot | ngang mắt | tịnh tiến×2, tĩnh×1, **roll×1** (128.1–139.5, 11.4s) | điệp khúc 2 |
| 23–26 | 139.5–148.4 | CU chính diện luân phiên | ngang mắt, nhìn thẳng máy | zoom in×1, tĩnh×3 | giấy bay quanh mặt |
| 27 | 148.4–154.2 | WS giấy xoáy quanh hai người | ngang, xa | zoom in | kết khối điệp khúc |
| 28–33 | 154.2–180.0 | MS/WS phòng thí nghiệm, cô gái đội mũ điện cực | ngang mắt | zoom in×1 (154.2–165.7, 11.5s), tĩnh×4 | insert biểu đồ sóng 165.7s; hai nhà khoa học |

## Kỹ thuật đáng học
1. **Một shot dài trọn một đoạn lời** (6–29.9s: máy lùi dần từ mặt ra toàn phòng suốt 3 câu đầu; 47.3–67.3s: một CU 20s trọn điệp khúc 1). Ý đồ **[có thể]**:
   để giọng hát và gương mặt tự mang cảm xúc, tiết lộ không gian (bị buộc giữa phòng trắng) như một "câu trả lời" chậm cho câu hát mở đầu. Độ tin: có thể;
   quy ước MV (cắt ít khi lời kể quan trọng) — không áp thẳng cho drama thoại.
2. **Chuyển không gian bằng chuyển cảnh "phép thuật" đặt ở đầu điệp khúc** (109–120s: khói màu → chớp trắng 114s → top-down → sa mạc 119.8s). Ý đồ **[có thể]**:
   điệp khúc là lúc cảm xúc bùng — chuyển từ văn phòng khép kín sang không gian mở đúng nhịp đó. Độ tin: có thể (mốc điệp khúc lấy từ whisper, ±1s).
3. **Màu làm dấu hiệu duy nhất trong phim đen trắng** (khói cam + xanh 109–113s, hai màu từ hai máy chữ của hai người gặp nhau). Ý đồ **[đoán]**: đánh dấu
   khoảnh khắc hai nhân vật "kết nối". [suy luận] với video AI: làm được bằng hậu kỳ (giữ màu một vùng) dễ hơn bằng prompt.
4. **Chữ trong cảnh trùng lời đang hát** (trang giấy đánh máy 99.3–101.4s). Ý đồ **[có thể]**: nhân đôi lời hát bằng hình, đưa lời vào thế giới truyện.
   Chỉ hợp khi có lời / thoại — với pipeline: chữ phải do hậu kỳ chèn, model video vẽ chữ kém.
5. **Luân phiên CU chính diện nhìn thẳng máy** (139.5–145.9s, 4 shot 1.8–2.4s, giấy bay quanh). Ý đồ **[có thể]**: nói thẳng với người xem, dồn nhịp ở cuối
   điệp khúc sau các shot dài. Độ tin: có thể, 1 lần.

## Giới hạn / câu hỏi mở
- Chỉ 3 phút đầu (~72%); đoạn cuối bài (bridge / kết) chưa đo.
- Đây là MV **quay thật + kỹ xảo**, không phải video AI; nhịp theo bài hát — quy ước riêng của MV, không dùng làm chuẩn cho drama.
- Phân chia "đoạn / điệp khúc" dựa vào mốc câu của whisper (lời chép trên lớp giọng tách, có sai chữ) và việc câu lặp lại — độ tin "có thể", chưa nghe tai.
- OpenCV gộp cả thẻ chữ vào shot 1 nên nhãn "zoom in" sai chiều; mắt thấy máy lùi / nâng. Các nhãn khác chưa kiểm bằng mắt từng shot.

## Xoá dữ liệu
Đã xoá `v08_seg1.webm`, `v08_seg1_frames/`, `v08_seg1_sheet_01.jpg`, tờ 1 khung/giây `v08_shot1_1fps.jpg`, `v08_105_160.jpg`, thư mục `v08_a_listen/`,
`v08_b_listen/` (wav, stem demucs, lời chép) và log. Chỉ giữ `v08_seg1_result.json` và `v08_seg1{a,b}_listen_numbers.json` (không có lời chép).
