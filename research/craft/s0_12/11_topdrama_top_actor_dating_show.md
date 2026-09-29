# 11 — 月光爽劇社 TopDrama: "The Top Actor Joined a Dating Show Just for Her…" (bản gốc 十八線女星…)

- **URL**: https://www.youtube.com/watch?v=cNX5tisG3dk
- **Thể loại**: AI short drama 9:16 **hiện đại, hài lãng mạn** (nữ minh tinh hạng 18 × ảnh đế "oan gia" tham gia show hẹn hò livestream), gộp nhiều tập;
  **thoại tiếng Trung** + phụ đề Trung / Anh (tiêu đề kênh ghi "bản lồng tiếng Anh" nhưng âm thanh đo được là tiếng Trung). Kênh tự nhận chuyên AI 真人
  **cổ trang**, nhưng phim này là **hiện đại** — mục 1.3 trong `MAU_S0_12.md`
- **Độ dài công bố**: 1:44:46 · file tải 360×640, 9:16
- **Đoạn đã đo**:
  - (1) 0:00–3:00 (180.0s, hình và âm cùng từ giây 0, không có khung đen đầu);
  - (2) yêu cầu 19:30–22:00 (cao trào "nhà ma" trong show + ranh giới tập) — file **160.0s** (dài hơn yêu cầu 10s: yt-dlp cắt theo keyframe). Đối chiếu tờ quét
    (thẻ "未完待续" ở 21:30 ↔ shot 46 của file ở 146.4–153.9s) thì file bắt đầu khoảng **18:56–19:20** gốc — **chưa chốt được**, mốc trong bảng là giây của file.
- **Tổng đã đo**: ~340s / 6286s (~5%)
- **Đã tải**: `v11_seg1.webm`, `v11_seg2.webm`, khúc quét 144p 5:00–65:00 (1 khung/30s, xoá ngay sau khi chọn đoạn) — **tất cả đã xoá sau khi viết file này**.

## Cách chọn đoạn / kiểm lặp
Tờ quét 120 khung (5:00–65:00): thẻ **"未完待续" (còn tiếp)** thấy ở 21:30 và 42:00; không thấy cụm cảnh nào lặp lại (khác 10) — mỗi khung quét là cảnh / trang phục
khác nhau. Chọn 19:30–22:00 vì có khung "đầu ma mắt đỏ" (20:00) ngay trước thẻ còn tiếp → đoạn "cao trào + móc tập sau".

## Phương pháp
Như 10 (`ffmpeg scene` 0.25, tờ khung giữa shot, `ebur128` + `silencedetect`, OpenCV), **có sửa `motion_cv2.py` → `motion_cv2b.py`**: bản cũ luôn gắn nhãn
"zoom/dolly **in**" cho mọi shot đổi tỉ lệ (lấy trị tuyệt đối trước khi xét chiều) — bản mới xét `scale > 1` → in, `< 1` → out. `tools/audio_listen.py --lang zh`
đoạn 1 giây 0–90, đoạn 2 giây file 10–100.

## Số đo
| Đoạn | Shot | Trung vị | Min–max | Shot/phút | Máy (OpenCV) |
|---|---|---|---|---|---|
| Mở đầu 0:00–3:00 | 83 | **2.00s** | 0.3–5.93s | 27.7 | tĩnh 61%, tịnh tiến 29%, zoom in 5%, zoom out 1%, roll 1%, thiếu dữ liệu 2% |
| Nhà ma + ranh giới tập (file 160s) | 50 | **2.13s** | 0.63–14.2s | 18.8 | tĩnh 64%, tịnh tiến 18%, zoom in 8%, roll 4%, thiếu dữ liệu 6% |

- Âm thanh: LUFS **−14.3** / **−14.3**, LRA **11.2** / **14.4 LU**; quãng lặng (< −35 dB, ≥ 0.3s) **10** / **10**.
- **Độ dài tập đo được**: thẻ "未完待续" chồng lên shot cuối tập ở 79.4s và 158.8s (đoạn 1), 60.8s và 146.4s (đoạn 2) → **một tập ≈ 79–86s**.

### Nghe bằng số (audio_listen)
- **Nhạc gần như liên tục**: đoạn 1 **98%** (tempo đo 123 BPM, độ khớp giọng điệu 0.89), đoạn 2 **97%** (136 BPM). Nhãn nhạc cụ: đoạn 1 **marimba / xylophone**
  (0.10–0.25 ở 42–46s, 86s), maraca; đoạn 2 **accordion 0.29–0.52 (24–28s), harmonica 0.14–0.24 (18–20s)**, violin 0.14 — màu nhạc "hài", kể cả trong cảnh nhà ma.
- **Đoạn 1**:
  - 0–27s (giấc mơ, đêm, tông xanh lạnh, cầu hôn): nhạc rõ −31.8 dB, to lên −26.3 ở 15s.
  - **Cắt 28.4s sang cảnh tỉnh dậy (tông hồng ấm): lặng 28.6–29.3s** (silencedetect) + nhạc xuống "nền dưới thoại" −42 dB ở 28s; câu "我做梦了" 27.1–28.2s.
  - Nhạc to lên 37s (−30.8), 43s (−22.1) quanh câu "chắc là mơ thôi", 67s (−23.2, Rumble 0.38 ở 66s) ↔ cụm cắt 64.0–69.4s khi thấy "hot search".
  - Ranh giới tập 79.4s: **nhạc không dừng** (−36 dB), có Door / Slam 0.20 ở 82s ↔ cắt 81.7 (tập mới mở).
- **Đoạn 2 (giây file)**:
  - Nhạc to lên 34s (−17.8 dB) dưới câu "có người đang khóc", 52s (−20.3) dưới "hắn khoác da người"; tiếng gà / "Fowl" 0.37–0.42 ở 48–52s và huýt sáo 0.50 ở 58s.
  - **Explosion 0.30 ở 66s ↔ cắt 66.6** (giữa cụm ECU mở tập: cổ, mắt, **đầu lâu**, môi — 63.1–67.7s).
  - **Màn cãi nhau "anh cười tôi / không có"** (70–100s, shot/phản shot 0.6–2.1s): nhạc tụt −48 dB ở 70s (lặng 71.3–72.3), −51 ở 82s, **−46 / −54 ở 90–92s**
    (lặng 90.7–91.6 và 92.4–92.9) dưới câu chốt "我在嘲笑你" (89.5–91.5s), **nhạc về −33 dB ở 94s ↔ cắt 93.4**.

## Bảng shot — đoạn 1 (0:00–3:00, 83 shot)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1–12 | 0.0–24.6 | CU / MCU hai người; #7 WS tối | ngang; #7 cao | tịnh tiến×3, zoom in×1, tĩnh×8 | **giấc mơ** đêm xanh lạnh: nam cầu hôn; nhạc rõ |
| 13–16 | 24.6–33.5 | CU nữ trên giường hồng | ngang | tịnh tiến×3, zoom in×1 (#16 5.1s) | tỉnh dậy "我做梦了"; **lặng 28.6–29.3 ↔ cắt 28.4** |
| 17–21 | 33.5–44.8 | ECU mắt / tay; insert chăn; WS phòng | ngang | tịnh tiến×1, tĩnh×4 | độc thoại "là anti-fan của anh ta mà mơ thế này" |
| 22–38 | 44.8–79.4 | MS / CU nữ ↔ **insert màn hình điện thoại** (6/17 shot) | ngang | tịnh tiến×6, tĩnh×11 | gọi bạn, lên "hot search" ảnh hai người; nhạc to lên 67s |
| 39 | 79.4–81.7 | MS hai người (ảnh "hot search") + thẻ **未完待续** | ngang | tịnh tiến | hết tập 1 |
| 40–62 | 81.7–141.9 | WS nằm giường; CU nữ ↔ CU người quản lý ở văn phòng (cắt xen hai nơi qua điện thoại) | ngang | tịnh tiến×2, zoom in×1, tĩnh×20 | cuộc gọi dài; lặng ngắn 125.6–131.6 |
| 63–72 | 141.9–152.6 | **insert** lọ sao giấy, điện thoại, sao giấy có chữ — 0.3–0.9s | cao nhìn xuống | tịnh tiến×4, zoom out×1, tĩnh×3, thiếu dữ liệu×2 | lộ "thư tình" giấu trong sao giấy |
| 73–75 | 152.6–161.1 | WS biệt thự; MS nữ quát ở cửa + **未完待续** | ngang | tịnh tiến×1, tĩnh×2 | hết tập 2 |
| 76–83 | 161.1–180.0 | CU nam "chào buổi sáng"; MS hai người trên giường | ngang | zoom in×1, tịnh tiến×4, tĩnh×3 | tập 3 mở; lặng ngắn 163.5–177.7 (5 quãng) |

## Bảng shot — đoạn 2 (giây file; nhà ma trong show)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1–3 | 0.0–24.1 | MS nữ sườn xám **khung livestream có bình luận chạy**; WS phòng | ngang | tĩnh×3 (8.4 / 9.2 / 6.5s) | khán giả trong truyện bình luận; accordion / harmonica |
| 4–11 | 24.1–60.8 | ECU mắt; WS đi; **MS 14.2s** (#6); insert tay cầm liềm; CU sợ | ngang | zoom in×3, roll×1 (#10), tịnh tiến×1, tĩnh×3 | giọng "叮咚" kể chuyện ma; nhạc to lên 34 / 52s |
| 12 | 60.8–63.1 | WS phòng + **未完待续** | ngang | tịnh tiến | hết tập |
| 13–16 | 63.1–67.7 | **ECU** cổ nam, mắt nữ, **đầu lâu**, môi — 0.7–1.5s | ngang | tĩnh×4 | mở tập mới; **Explosion ở cắt 66.6** |
| 17–35 | 67.7–118.2 | MS hai người trong phòng tối (nữ bám nam); shot / phản shot CU 0.6–2.1s | ngang | tịnh tiến×4, roll×1, tĩnh×14 | cãi yêu "anh cười tôi"; **nhạc tụt + lặng 90.7–92.9, về ở cắt 93.4** |
| 36–45 | 116.1–144.1 | WS phòng bí mật; insert chìa khoá (#39); ECU nam | ngang | tịnh tiến×3, zoom in×1 (#45), tĩnh×6 | thông báo "ba cặp tìm được chìa" |
| 46 | 146.4–153.9 | MS hai người trước gương + **未完待续** (7.5s) | ngang | tịnh tiến | hết tập |
| 47–50 | 153.9–160.0 | ECU mắt; WS nhân viên hét chạy; CU nam | ngang | thiếu dữ liệu×3 | tập mới: "黎酒 chạy mất rồi" |

## Kỹ thuật đáng học
1. **Mở bằng "giấc mơ lãng mạn" rồi lật thành hài bằng tương phản màu + một nhịp lặng** (0–27s đêm xanh lạnh, cắt 28.4s sang phòng hồng ấm; lặng 28.6–29.3s;
   zoom in 5.1s vào mặt vừa tỉnh; câu "我做梦了"). Ý đồ **[có thể]**: móc bằng khoảnh khắc người xem mong chờ (cầu hôn), rồi rút lại để đặt giọng hài + mâu thuẫn
   "anti-fan". Độ tin: khá (đo khớp 0.2s). Cùng họ với 10 (mở bằng cảnh tương lai rồi cắt vào lặng).
2. **Tập ≈ 80s, kết bằng thẻ "未完待续" chồng lên một shot giữ 2.3–7.5s; nhạc không ngắt qua ranh giới tập** (79.4 / 158.8 / 60.8 / 146.4s). Ý đồ **[có thể]**: cấu
   trúc cho nền tảng dọc trả theo tập — mỗi tập có một "móc" riêng (ảnh hot search, người quát ở cửa, cặp đôi trước gương). Độ tin: chắc về số đo, có thể về ý đồ.
3. **Mở tập bằng cụm ECU chi tiết 0.7–1.5s + âm nhấn** (đoạn 2: 63.1–67.7s cổ / mắt / đầu lâu / môi, Explosion ở cắt 66.6; 153.9s ECU mắt). Ý đồ **[có thể]**: nhắc
   lại không khí trong 5 giây cho người xem vào giữa chừng. Độ tin: có thể (2 lần trong 1 video; đoạn 1 không có).
4. **Nhạc hài liên tục (marimba / accordion / harmonica) cả trong cảnh "kinh dị", tụt xuống lặng đúng câu chốt của màn cãi yêu, về ở cắt sang phản ứng**
   (90–92s → 93.4s). Ý đồ **[có thể]**: giữ giọng hài, và cho câu chốt "trơ" ra như một cú punchline. Độ tin: có thể — cùng hình dạng với mẫu hình 5 (06, 07, 10),
   nhưng ở đây trong **hài**, không phải lật mặt.
5. **Khung livestream có bình luận chạy ngay trong hình** (đoạn 2 #1–2 giữ 8.4 / 9.2s; tờ quét thấy ở 11:30, 18:00, 30:00, 38:00, 47:00…) và **insert màn hình điện
   thoại** mang tin (6/17 shot ở 44.8–79.4s). Ý đồ **[có thể]**: "đám đông trong truyện" phản ứng thay người xem; shot giữ lâu để kịp đọc. [suy luận] với AI: lớp
   chữ / giao diện dựng ở hậu kỳ, không cần model sinh.
6. **Cụm insert rất ngắn để lộ bí mật** (141.9–152.6s: 10 shot 0.3–0.9s lọ sao giấy → chữ viết trên sao) giữa nhịp ~2s. Ý đồ **[có thể]**: nhịp "khám phá" nhanh dần
   trước thẻ còn tiếp. Độ tin: có thể — thêm một ví dụ cho mẫu hình 2 (cụm shot ngắn), nhưng ở đây là **vật**, không phải hành động.

## Giới hạn / câu hỏi mở
- Mốc gốc của đoạn 2 lệch chưa rõ (18:56–19:20 + t). Chưa xem phần giữa / cuối phim (chỉ quét tới 65:00).
- Nhãn "Fowl / Moo / Fart" của AST trên lớp nhạc là nhạc cụ hoặc hiệu ứng hài bị gán nhầm — không suy luận.
- Không biết công cụ AI (kênh không ghi).

## Xoá dữ liệu
Đã xoá `v11_seg1.webm`, `v11_seg2.webm`, tờ quét, thư mục `v11_seg*_frames/`, `v11_*sheet*.jpg`, `v11_*_all_*.jpg`, thư mục `v11_seg1_L0/`, `v11_seg2_L10/` (wav, stem,
lời chép) và log. Chỉ giữ `v11_seg{1,2}_result.json`, `v11_seg1_L0_numbers.json`, `v11_seg2_L10_numbers.json` (không lời chép).
