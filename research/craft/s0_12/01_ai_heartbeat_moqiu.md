# 01 — 《夫人又在掉馬甲了》 (AI心動劇場 | AI HeartBeat Drama)

- **URL**: https://www.youtube.com/watch?v=wPwzzQNtgr0
- **Thể loại**: AI short drama 9:16, 爽剧 (giải trí nhanh, plot twist liên tục), toàn tập gộp
- **Độ dài công bố**: 2:03:33 (7413.7s) · khung 360×640 (9:16), 30fps
- **Đoạn đã đo (LÀM LẠI bằng tải về + ffmpeg/ffprobe, thay cho lượt đo trong trình duyệt trước)**: (1) 0:00–3:00 (mở đầu, 180.0s) · (2) 1:14:08–1:15:08 (74:08–75:08, 68.0s — yt-dlp cắt hụt/dư nhẹ so với 60s xin do làm tròn theo keyframe)
- **Tổng đã đo**: 248s / 7413.7s (~3.3% video)
- **Đã tải**: `test_wPwzzQNtgr0.webm` (7.1 MB, 360×640, đoạn 1) + `v01_seg2_wPwzzQNtgr0.webm` (2.2 MB, đoạn 2) — **đã xoá cả hai + toàn bộ thư mục frame/sheet sau khi viết xong file này** (xem log lệnh cuối file).

## Phương pháp (v2 — tải về, đúng theo hướng dẫn phiên chính)
- Tải bằng `yt-dlp --download-sections`, `-f "bv*[height<=720]+ba/b[height<=720]"` (video gốc 360×640 nên tải nguyên, không giảm chất lượng).
- **Điểm cắt**: `ffmpeg -vf "scale=192:-2,select='gt(scene,0.28)',showinfo"` (ngưỡng 0.28, cao hơn mặc định 0.25 một chút để khớp số shot quan sát bằng mắt — không thấy cắt giả rõ rệt khi soát ảnh); gộp các cắt cách nhau < 0.3s.
- **Tờ ảnh**: 1 khung giữa mỗi shot, ghép 30 khung/tờ (`drawtext` mốc giờ, `fontfile=C:/Windows/Fonts/arial.ttf`) — đọc trực tiếp bằng mắt (Read ảnh), không cần lấy mẫu 1 khung/giây riêng vì mật độ cắt đã rất dày (~1.5s/shot).
- **Âm thanh**: `ebur128` (LUFS tích hợp, LRA, đỉnh thật), `silencedetect` (noise=-35dB, d=0.3s), RMS 1 mẫu/giây qua `astats+ametadata`. **Nghe bằng số** — không nghe được bằng tai (không có tai nghe/loa trong môi trường agent), chỉ đọc số đo + đối chiếu phụ đề song ngữ đã đọc được qua hình.
- **Chuyển động máy trong shot**: thử đo bằng khác biệt khung xám 64×36 ở 12fps (giống `scratchpad/ref/motion.py`) — kết quả **không đáng tin cho việc phân biệt "máy tĩnh/máy động"**: chỉ số này đổi mạnh theo diễn xuất (chớp mắt, cử động miệng khi nói) và phụ đề đổi từng khung, không tách được với chuyển động máy thật. Vì vậy **`camera_move` trong bảng dưới ghi "tĩnh (mặc định)"** cho phần lớn shot dựa trên quan sát tổng thể ở đợt trước (khung hình cố định giữa đầu và cuối mỗi khung mid-frame, không thấy dấu hiệu lệch góc/parallax giữa các insert liền kề) — **không xác minh được chuyển động thật bên trong từng shot bằng phương pháp này**, ghi rõ là giới hạn.

## Số đo (2 đoạn, 248s, 136 shot)
| Đoạn | Shot | Độ dài trung vị | Min–Max |
|---|---|---|---|
| Mở đầu 0:00–3:00 | 107 | 1.43s | 0.33–4.33s |
| Giữa phim 74:08–75:08 | 29 | 1.97s | 0.70–9.68s |

Nhịp cắt ~30–36 shot/phút — khớp số đo lần trước (đo trong trình duyệt, không tải) và khớp nghiên cứu DRAMA_DOC (33 shot/phút, median 1.86s) — **xác nhận lại bằng số đo chính xác hơn (ffmpeg thay vì canvas trình duyệt)**.

### Âm thanh — số đo
| Đoạn | LUFS tích hợp | LRA | Đỉnh thật | Số quãng lặng (≥0.3s) | % quãng lặng trùng 1 điểm cắt (±0.4s) |
|---|---|---|---|---|---|
| Mở đầu | **−11.2 LUFS** | 8.8 LU | **0.0 dBFS** (chạm trần, có vỡ nhẹ) | 46 | 28/46 = 61% |
| Giữa phim | −14.6 LUFS | 8.7 LU | −0.9 dBFS | 33 | 19/33 = 58% |

- **~60% các quãng lặng ngắn (thường 0.3–1.5s, giữa các câu thoại) trùng thời điểm với một điểm cắt shot (±0.4s)** — số đo khách quan xác nhận quan sát "cắt theo nhịp câu thoại" đã ghi ở đợt trước, nay có % cụ thể thay vì chỉ quan sát bằng mắt.
- **RMS (độ to) tụt rất sâu (< −40dB, có lúc tới −80/−95dB) ở nhiều mốc trong cả hai đoạn** (ví dụ 8–10s, 55–76s ở đoạn mở đầu; 0–5s, 24–39s ở đoạn giữa phim) — **[có thể]**: nhạc nền của video này không chạy liên tục xuyên suốt như MV tham khảo ClipAI đã phân tích trước (`docs/PHAN_TICH_CLIP_MAU_CLIPAI_2026-09-28.md`, nhạc không bao giờ tắt) mà **tắt hẳn giữa các câu thoại**, chỉ còn tiếng thoại (khi có) — **độ tin: có thể, dựa trên số đo RMS, chưa nghe được bằng tai để xác nhận có đúng là nhạc tắt hay chỉ là thoại nhỏ**. Cần người dùng nghe lại đoạn 8–10s và 55–76s để xác nhận.
- Đỉnh thật chạm 0.0 dBFS ở đoạn mở đầu — **có thể bị vỡ nhẹ trên loa điện thoại**, giống nhận xét đã ghi cho clip MV ClipAI (+0.7 dBFS).

## Bảng shot — đoạn 1 (0:00–3:00, 107 shot)
> Cỡ cảnh đọc trực tiếp từ tờ ảnh (4 tờ, 30 shot/tờ) — đáng tin. Góc máy: **eye-level xuyên suốt** cả 107 shot, không thấy góc thấp/cao/dutch rõ rệt nào trong các khung mid-frame đã xem. Máy: **tĩnh (mặc định, xem giới hạn phương pháp ở trên)**. Chuyển cảnh vào: **cut cứng cho gần như mọi shot** (không thấy fade/dissolve/wipe nào trong 107 shot).

| # | Vào–ra | Dài | Cỡ cảnh | Hành động / thoại |
|---|---|---|---|---|
| 1 | 0.0-1.4 | 1.4s | WS | toàn cảnh nhóm phù dâu/khách xếp hàng ngoài sân biệt thự |
| 2–3 | 1.4-7.2 | 3.1s, 2.7s | CU | xen kẽ CU nam (tay cầm áo) / CU nữ đọc sách nhỏ — thoại quà tặng |
| 4–6 | 7.2-10.0 | 1.7/0.8/0.3s | MCU/insert | áo dạ hội đỏ trên móc; nhóm tay bưng hộp quà |
| 7–13 | 10.0-20.1 | 0.3–3.1s | CU | đối thoại CU nam↔nữ xen insert hộp trang sức (vòng ngọc lục bảo, lắc tay) |
| 14–18 | 20.1-30.7 | 1.0–3.7s | CU | 'đổi đồ', 'cha đợi hơn 10 năm' |
| 19–30 | 30.7-56.0 | 0.8–4.3s | CU | hỏi–đáp liên tục, nhịp rất nhanh |
| 31–33 | 56.0-59.1 | 0.3–1.6s | CU/MS | nữ một mình ngoài sân — chuyển bối cảnh |
| 34 | 59.1-60.2 | 1.2s | insert | xe Bentley biển số cận — chuyển cảnh sang nhóm nhân vật mới |
| 35–36 | 60.2-63.5 | 1.9/1.4s | CU | nữ trang phục khác + nam đeo kính — nhân vật mới |
| 37–44 | 63.5-75.8 | 1.1–3.0s | CU | người phụ nữ lớn tuổi tự nhận là mẹ ("我是妈妈/I'm your mom"), đối thoại xúc động |
| 45–48 | 75.8-81.2 | 0.6–2.4s | CU | nam đeo kính (cha dượng) xen vào |
| 49–54 | 81.2-94.6 | 1.4–3.3s | CU | kể lại bị bắt cóc, cảnh sát giải cứu; cha dượng ra lệnh "theo tôi về" |
| 55–60 | 94.6-105.7 | 1.0–3.0s | CU | đối thoại căng thẳng về hôn nhân sắp đặt với nhà Chen |
| 61–66 | 105.7-114.9 | 0.6–3.5s | CU | chất vấn xuất thân trại mồ côi vs Li Le lớn lên trong nhung lụa |
| 67–72 | 114.9-122.1 | 0.8–1.9s | CU | tiếp tục so sánh hai chị em, ép gả |
| 73–78 | 122.1-131.6 | 1.0–2.4s | CU | "bán Xixi cho nhà Chen", mẹ phản đối yếu ớt |
| 79–84 | 131.6-142.1 | 1.1–2.5s | CU | nữ bị ngăn không cho rời đi, nam đeo kính can thiệp |
| 85–90 | 142.1-156.6 | 1.6–3.5s | CU/WS | tiếp tục thuyết phục, xen toàn cảnh nhóm dưới hàng cây |
| 91–96 | 156.6-164.1 | 0.5–1.7s | CU | hé lộ âm mưu — "mục tiêu là biến tôi thành cô dâu thế thân cho Li Le" |
| 97–102 | 164.1-173.0 | 0.8–3.0s | CU/WS | phản ứng các nhân vật + toàn cảnh nhóm rời đi |
| 103–107 | 173.0-180.0 | 0.8–2.4s | insert/CU | xe hơi rời khỏi, cận nam trong xe — "lần này tôi nhất định..." |

## Bảng shot — đoạn 2 (74:08–75:08, 29 shot)
> Nội dung khác hẳn với ghi chú "黎溪下降頭了" ở lượt đo trước bằng trình duyệt cho cùng mốc giây — **có thể do yt-dlp/YouTube tính mốc `*74:08-75:08` khác cách trình duyệt tính `currentTime` (ví dụ YouTube chèn quảng cáo làm lệch, hoặc chương trình cắt đoạn làm tròn theo GOP khác vị trí mong muốn)**. Ghi nhận sai lệch, không cố gán ghép hai lần đo; đoạn tải lần này (bữa tối gia đình căng thẳng) là nội dung xác thực tại vị trí tải được.

| # | Vào–ra | Dài | Cỡ cảnh | Hành động / thoại |
|---|---|---|---|---|
| 1 | 0.0-9.7 | 9.7s | CU | nữ trẻ "Cái gì vớ vẩn!" (phản ứng giận — shot dài bất thường, gần 5× trung vị) |
| 2–3 | 9.7-11.9 | 1.2/1.0s | CU/WS | nam trẻ tóc rối đáp trả; toàn cảnh bàn tiệc gia đình dài |
| 4–6 | 11.9-16.4 | 1.4/2.4/0.7s | CU | "ăn nhiều vào", "anh câm miệng" |
| 7–9 | 16.4-26.0 | 2.4–4.3s | CU | người đàn ông lớn tuổi mắng — "còn hơn cả lợn", phản ứng nữ |
| 10 | 26.0-27.4 | 1.4s | WS | toàn cảnh nội thất biệt thự (cầu thang kính) — chuyển không gian |
| 11–12 | 27.4-32.5 | 1.9/3.1s | CU | tiếp tục mắng, so sánh với "Li Xi" |
| 13–18 | 32.5-45.1 | 1.3–2.8s | CU/WS | nữ phản ứng; toàn cảnh nữ đứng cầu thang; nam ngồi sofa hỏi "Tiểu Xi… có ra ngoài không?" |
| 19–21 | 45.1-49.2 | 1.2–1.6s | CU/WS | nữ đeo dây chuyền; nam "tôi đưa cô ra cửa"; toàn cảnh cửa kính ngoài trời |
| 22–24 | 49.2-56.5 | 1.6–2.9s | CU | nữ áo trắng phản ứng liên tiếp (3 shot cận mặt gần giống nhau — có thể là 1 câu bị ngắt lời) |
| 25–27 | 56.5-61.8 | 0.8–2.9s | CU/WS | nam áo trắng; toàn cảnh nội thất hai người; cận màn hình điện thoại đang nhắn tin |
| 28–29 | 61.8-68.0 | 2.9/3.3s | CU | nam "lần này tôi nhất định..." — kết đoạn |

## Kỹ thuật đáng học
1. **Cắt gần như toàn cận/trung cận theo câu thoại (~60% quãng lặng trùng điểm cắt, đo được), nhịp rất nhanh (median 1.4–2.0s)** — xác nhận lại bằng số đo chính xác (không còn chỉ là quan sát bằng mắt qua trình duyệt). Ý đồ **[có thể]**: giữ người xem không rời mắt trong định dạng xem lướt trên điện thoại. Độ tin: **có thể → gần chắc** (đã có số đo lặp lại 2 đoạn khác nhau trong cùng video, cùng chiều với DRAMA_DOC).
2. **Nhạc nền có thể không chạy liên tục** (RMS tụt sâu < −40dB nhiều đoạn) — khác hẳn MV tham khảo ClipAI (nhạc không bao giờ tắt). Độ tin: **có thể**, dựa trên số đo RMS, **chưa nghe được bằng tai để xác nhận** — đây là phát hiện mới quan trọng cần người dùng nghe lại.
3. **Đỉnh âm chạm 0.0 dBFS** (đoạn mở đầu) — dấu hiệu kỹ thuật hậu kỳ chưa chặt limiter, có thể vỡ nhẹ trên loa nhỏ — giống nhận xét đã có ở clip MV ClipAI (+0.7 dBFS), cho thấy đây **có thể là vấn đề chung của khâu master âm thanh ở nhiều kênh AI drama, không riêng một kênh** — nhưng mới thấy ở 2 nguồn, cần thêm mẫu.
4. **Twist thả liên tục qua đối thoại ngắn** (bị bắt cóc → mẹ ruột lộ diện → âm mưu cô dâu thế thân, tất cả trong 180s đầu) — mỗi twist là 1 cụm shot CU đối thoại, không có cảnh minh hoạ riêng cho hành động (không quay cảnh bắt cóc thật). Độ tin: có thể — giảm chi phí sản xuất AI, giữ nhịp truyện dồn dập.
5. **Shot #1 của đoạn 2 dài bất thường (9.7s, gần 5× trung vị)** ngay đầu một cảnh mới (bữa tối) — có thể là shot "thiết lập" (thấy toàn cảnh bàn ăn + phản ứng đầu tiên) trước khi chuyển sang nhịp cắt nhanh — **[đoán]**, cần xem thêm ví dụ khác để xác nhận đây là quy luật "shot mở cảnh dài hơn" hay ngẫu nhiên.

## Nhạc nền — mục G (âm thanh) cập nhật
- **Không nghe được bằng tai** trong phiên này (môi trường agent không có audio output) — nhưng nay có **số đo LUFS/LRA/peak/RMS/silence khách quan** thay cho "không có gì".
- Diễn biến RMS gợi ý nhạc **gián đoạn theo câu thoại** thay vì liên tục — **cần người dùng nghe trực tiếp file gốc** (không còn trên máy vì đã xoá) hoặc mở lại link để xác nhận đây có đúng là nhạc tắt/bật hay chỉ là biến động của track thoại+nhạc trộn chung.
- Không đo được đường cong loudness dạng liên tục mượt (LUFS momentary M: không xuất ra được ở bản ffmpeg 9.0.1 cài trên máy — dùng RMS 1 mẫu/giây qua `astats` thay thế, đã ghi trong mục Phương pháp).

## Giới hạn / câu hỏi mở
- Vẫn chỉ đo 248s / 7413.7s (~3.3%) — không đủ để kết luận cấu trúc toàn phim.
- **Không xác minh được `camera_move` từng shot bằng máy** (xem mục Phương pháp) — nhãn "tĩnh (mặc định)" là suy đoán tổng thể, không phải đo từng shot.
- Đoạn 2 lần này (bữa tối gia đình) khác nội dung với lượt đo trình duyệt trước ở "cùng mốc giây" — chưa rõ nguyên nhân lệch, ghi nhận làm bài học cho cách chọn/kiểm mốc giây khi tải các video sau.
- Chưa xác định đúng vị trí cảnh "揭面" (lộ mặt) nêu trong tiêu đề gốc.
- LUFS/LRA/peak đo trên file WebM 360×640 đã nén lại qua yt-dlp (không phải luồng gốc YouTube phát), có thể lệch nhẹ so với bản gốc do nén lại — sai số ước tính nhỏ (< 1 LU) nhưng chưa kiểm chứng.

## Xoá dữ liệu
Đã xoá `test_wPwzzQNtgr0.webm`, `v01_seg2_wPwzzQNtgr0.webm`, các thư mục `v01_seg1_frames/`, `v01_seg2_frames/`, và các file `.jpg` tờ ảnh (`v01_seg*_sheet_*.jpg`) khỏi `scratchpad/s012` ngay sau khi ghi xong file phân tích này — chỉ giữ lại số đo (JSON) trong scratchpad để tham khảo nội bộ (không đưa vào repo).
