# 07 — DramaBox: "Doting Snake Lord" (kênh Drama Flicks, quảng bá app DramaBox)

- **URL**: https://www.youtube.com/watch?v=X5EJ9etPr2M
- **Thể loại**: AI short drama 9:16 huyền huyễn (rồng vàng / rồng đen, trứng rồng, "huyết thống"), lồng tiếng **tiếng Anh** + phụ đề Anh, gộp nhiều tập ~1–2 phút (có thẻ "TO BE CONTINUED" giữa các tập) — mục 1b.2 trong `MAU_S0_12.md`
- **Độ dài công bố**: 20:37 (1237.3s) · file tải 360×640 (9:16), 30 fps
- **Đoạn đã đo**: (1) 0:00–3:00 (mở đầu, 180.0s) · (2) yêu cầu 13:00–15:00 (file 130.0s; **hình chỉ bắt đầu ở giây 10.0 của file**, âm bắt đầu ở giây 0 — do yt-dlp cắt theo keyframe; mốc trong bảng là giây của file, mốc gốc ≈ 12:50 + t, sai số vài giây [suy luận])
- **Tổng đã đo**: ~300s hình / 1237s (~24%)
- **Đã tải**: `v07db_seg1_X5EJ9etPr2M.webm` (9.7 MB) + `v07db_seg2_X5EJ9etPr2M.webm` (7.2 MB) + 1 khúc quét thưa 9:00–20:37 (đã xoá ngay sau khi chọn đoạn) — **tất cả đã xoá sau khi viết xong file này**.

## Cách tìm đoạn "lật ngược"
Như video 04: tải khúc 9:00–20:37 (480p), `ffmpeg fps=1/20` + `tile` ra tờ ảnh thưa, đọc bằng mắt rồi tải lại đúng khúc 13:00–15:00 ở 720p-max.
Lượt trước không ghi lại lý do chọn cụ thể; nội dung đoạn đã đo cho thấy đây đúng là **một bước ngoặt nhiệm vụ**: nữ chính (rồng vàng) hứa với
cha sẽ "có thai trong ba ngày và sinh trứng vàng", bị con vẹt đồng hành cảnh báo "không tìm được bạn đời trong ba ngày thì chết", rồi quyết
định "mượn giống" con rồng đen hạng thấp nhất ở đáy hố rồng — và một ranh giới tập ("TO BE CONTINUED", 105.3–107.1s) nằm ngay trong đoạn.

## Phương pháp
Giống 04/05: điểm cắt `ffmpeg scene` (ngưỡng 0.25), tờ ảnh khung giữa shot, `ebur128` (LUFS/LRA) + `silencedetect` (−35 dB, ≥ 0.3s) +
RMS 1 mẫu/giây; chuyển động máy per-shot bằng OpenCV (`motion_cv2.py`, mô tả ở `05_rise_worlds2018.md`). **Mới ở lượt này — "nghe bằng số"
`tools/audio_listen.py`**: demucs tách lớp nhạc (trống + bass + khác) khỏi lớp giọng, mức nhạc từng giây (> −38 dBFS = rõ, −50…−38 = nhỏ dưới
thoại, < −50 = không nhạc), nhãn AudioSet (AST) mỗi 2s trên lớp nhạc, faster-whisper chép lời có mốc giây. Đã chạy: đoạn 1 giây 100–160;
đoạn 2 giây 0–90 của file (lớp âm thực có 80s, tương ứng giây file 10–90 — đã đối chiếu: quãng lặng 63.2–67.4s của bản tách khớp quãng
lặng 73.0–77.5s đo trên file gốc, lệch đúng 10s). Không báo cáo đỉnh (file Opus nén lại).

## Số đo
| Đoạn | Shot | Trung vị | Min–max | Shot/phút | Máy (OpenCV) |
|---|---|---|---|---|---|
| Mở đầu 0:00–3:00 | 57 | 2.50s | 0.63–12.4s | 19.0 | tĩnh 43%, **zoom/dolly in 29%**, tịnh tiến 21%, roll 5% |
| Lật ngược ~13:00 | 36 (120s có hình) | 3.68s | 0.4–15.8s | 18.0 | tĩnh 53%, tịnh tiến 19%, zoom in 11%, thiếu dữ liệu 17% |

- Âm thanh: LUFS **−13.0** / **−15.0**, LRA **14.1** / **11.8** LU; quãng lặng (< −35 dB) **17** / **12** lần.
- **Máy động hơn hẳn các AI short drama khác đã đo** (01, 04, 06 tĩnh 76–83%): ở đây chỉ 43–53% tĩnh, zoom/dolly in chiếm tới 29% đoạn mở đầu —
  gần với RISE (05, cinematic CGI: tĩnh 43%, zoom in 22%) hơn là với drama thoại. [suy luận] có thể do ảnh → video (image-to-video) với lệnh
  "đẩy máy chậm" mặc định hoặc cố ý cho cảnh thần thoại; không có bằng chứng về công cụ.

### Nghe bằng số (audio_listen)
- **Nhạc gần như luôn có**: 98% (đoạn 1, giây 100–160) và 84% (đoạn 2, giây file 10–90). Nhãn trên lớp nhạc: Music + nhiều **Explosion / Bang /
  Slam / Door / Whoosh** (tiếng "đập" hiệu ứng), đoạn 2 có **Timpani** (trống định âm) 0.05–0.38 liên tục từ giây ~40 đến ~88. Tempo đo 117.5 /
  89.1 BPM nhưng độ khớp giọng điệu thấp (0.41 / 0.36) → không tin phần giọng điệu.
- **Hiệu ứng "đập" trùng điểm cắt** (đoạn 1, cửa sổ 2s): Slam/Door 138–140s ↔ cắt 139.3; Explosion 140–142s ↔ cắt 139.9; Explosion 146–148s ↔ cắt
  145.9; Slam 148–150s ↔ cắt 148.2; Door/Slam 152–154s ↔ cắt 152.1 (5/6 cửa sổ có nhãn đập đều có cắt trong ±0.5s). Đoạn 2: Bang 14–16s ↔ cắt
  14.4; Bang 18–20s ↔ cắt 18.1. Độ tin: **có thể → khá** (nhãn AST điểm 0.1–0.4, mốc cửa sổ 2s nên chỉ khớp tới ±1s).
- **Tiếng tim đập** (Heart sounds 0.29–0.54) ở 156–160s đoạn 1 — ngay dưới câu lật bài "Surprise, sweetie. This is Grayson's baby too"
  (whisper 151.9–157.9s); đoạn 2 mở bằng tim đập 10–14s dưới câu cha "I can't protect you". Độ tin: **khá** (nhãn điểm cao, hai lần).
- **Tắt nhạc có chủ ý** (đoạn 2): (a) 33–40s nhạc < −50 dB trong khi thoại vẫn chạy ("…you'll only lay a black egg, who would want you") — nhạc trở
  lại ~40s kèm timpani, gần cắt 41.6 khi vẹt nói điều kiện sinh tử "không tìm bạn đời trong ba ngày thì chết"; (b) 73.0–77.5s **lặng hoàn toàn
  (RMS −113…−128 dB)** giữa shot giữ lâu 15.8s mắt đỏ rồng đen (64.5–80.3s), rồi nhãn **Roar 0.56 + Rumble** ở ~76–78s và nhạc vào lại.
- **Sau thẻ "TO BE CONTINUED" là quãng lặng dài**: đoạn 1 thẻ ở 50.6–52.4s → lặng 53.0–60.7s (3 quãng) dưới shot toàn cảnh lâu đài băng 12.4s;
  đoạn 2 thẻ ở 105.3–107.1s → lặng 107.1–115.1s dưới shot toàn cảnh đại sảnh 4.0s. [có thể] đây là chỗ nối tập của bản gộp (mỗi tập mở bằng
  toàn cảnh + lặng), không phải ý đồ kể chuyện trong một tập.
- Giới hạn: whisper chạy với `--lang zh` nên lời tiếng Anh của đoạn 2 bị **dịch lẫn sang tiếng Trung** — chỉ dùng để định mốc câu, nội dung câu
  đối chiếu bằng phụ đề Anh đọc được trên tờ ảnh.

## Bảng shot — đoạn 1 (0:00–3:00, 57 shot)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1–6 | 0.0–20.3 | insert/CU | ngang mắt, chính diện | zoom in×3, tịnh tiến×1, tĩnh×2 | nghi lễ ánh sáng vàng, trứng vàng, nữ váy vàng chạm tia sáng |
| 7–11 | 20.3–52.4 | CU/WS tối | ngang mắt; #8 sau lưng | tịnh tiến×1, zoom in×1, tĩnh×3 | "Veronica, today is the day of birth"; lâu đài tối; #11 thẻ TO BE CONTINUED |
| 12 | 52.4–64.8 | WS (toàn cảnh lâu đài băng) | cao, nhìn xuống | tịnh tiến | shot mở tập mới 12.4s; lặng 53.0–60.7s |
| 13–18 | 64.8–86.3 | CU/MS nhóm | ngang mắt | tịnh tiến×1, zoom in×1, tĩnh×4 | "Elena is having the baby"; "vàng xếp hạng huyết thống theo độ sáng" |
| 19–24 | 86.3–100.2 | insert trứng / CU | ngang mắt | **zoom in×4**, tịnh tiến×1, tĩnh×1 | trứng Elena vàng; #21 trứng đen; "What the hell" |
| 25–30 | 100.2–113.1 | CU (đàn ông giáp đen) | ngang mắt, #25 thấp | zoom in×3, tịnh tiến×1, tĩnh×2 | "Elena, you bitch! … the lowest trashiest black egg?" |
| 31–37 | 113.1–135.2 | CU đối đáp | ngang mắt | tịnh tiến×1, tĩnh×6 | "Our egg was gold a second ago" / "first-order gold dragon" |
| 38–42 | 135.2–145.9 | CU | ngang mắt | zoom in×2, roll×1, tịnh tiến×2 | "Veronica, you're my sister…"; "You slut!" — tiếng đập trùng cắt |
| 43–48 | 145.9–160.3 | insert trứng / CU | ngang mắt | zoom in×2, tịnh tiến×1, tĩnh×3 | "You laid a gold egg too!" → "This is Grayson's baby too"; tim đập 156–160s |
| 49–57 | 160.3–180.0 | CU → WS | ngang mắt | roll×2, zoom in×1, tịnh tiến×2, tĩnh×4 | đối chất; **#54–57 bốn shot 0.8–1.1s** dồn cuối đoạn (nữ chính ngã, kẻ phản bội đứng nhìn) |

## Bảng shot — đoạn 2 (≈13:00, 36 shot; hình từ giây 10.0)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1 | (10.0)–11.0 | MS qua vai cha | ngang mắt | tĩnh | "In the dragon world power is everything, I can't protect you"; tim đập |
| 2–6 | 11.0–26.8 | #2 ECU mắt vàng; MS/WS chính diện | ngang mắt | tịnh tiến×2, tĩnh×3 | "Don't worry, father… lay a gold dragon egg"; #5 chèn rồng đen 0.8s; tiếng đập ở cắt 14.4/18.1 |
| 7–15 | 26.8–64.1 | MS vẹt + nữ chính, CU vẹt | ngang mắt | tịnh tiến×2, zoom in×1 (#11 7.5s), tĩnh×6 | vẹt đồng hành: "you'll only lay a black egg"; nhạc tắt 33–40s; timpani vào ~40s; "the black dragon at the bottom of the dragon pit" |
| 16–17 | 64.1–80.3 | #16 insert lửa 0.4s; #17 ECU mắt đỏ rồng đen **15.8s** | chính diện | zoom in×1, tĩnh×1 | lặng hoàn toàn 73.0–77.5s → tiếng gầm ~76–78s |
| 18–26 | 80.3–105.3 | MS sau lưng / WS đại sảnh | ngang mắt, #22 cao | tịnh tiến×2, zoom in×1, thiếu dữ liệu×1, tĩnh×5 | "Desperate times call for desperate measures… borrow his seed" (82–90s); #20–22 ba shot 0.4–0.6s (vẹt tung cánh tia điện) |
| 27 | 105.3–107.1 | WS | — | tịnh tiến | thẻ TO BE CONTINUED; lặng 107.1–115.1s |
| 28–36 | 107.1–130.0 | WS đại sảnh → MS nữ + vẹt | ngang mắt | zoom in×1, thiếu dữ liệu×5, tĩnh×3 | tập mới: "Keep your voice down" / "He's the lowest order of Black Dragon" / "How could you possibly…" |

## Kỹ thuật đáng học
1. **Tiếng "đập" (slam / bang / whoosh) đặt đúng điểm cắt trong đoạn cãi vã** (đoạn 1, 138–154s; đoạn 2, 14.4s và 18.1s). Ý đồ **[có thể]**: biến
   mỗi nhát cắt thành một "cú đánh" để cãi vã bằng lời có lực như đánh nhau, giữ nhịp khi hình chủ yếu là CU tĩnh/zoom chậm. Độ tin: có thể → khá, 1 video.
2. **Tim đập dưới câu lật bài** (156–160s: "This is Grayson's baby too"; 10–14s đoạn 2). Ý đồ **[có thể]**: báo cho người xem "đây là khoảnh khắc
   quan trọng" bằng âm thanh cơ thể thay vì tăng nhạc. Độ tin: khá (2 lần trong cùng video, nhãn điểm cao).
3. **Tắt nhạc rồi giữ một shot rất dài trong im lặng trước tiếng gầm** (73.0–77.5s lặng, shot mắt rồng 15.8s ≈ 4× trung vị). Ý đồ **[có thể]**: tạo
   khoảng "nín thở" trước khi giới thiệu nhân vật nguy hiểm (rồng đen), để tiếng gầm có tương phản tối đa. Độ tin: có thể, 1 lần.
4. **Nhạc tắt dưới câu sỉ nhục, vào lại kèm timpani khi điều kiện sinh tử được nói ra** (33–40s → ~40s). Ý đồ **[đoán]**: để câu hạ nhục "trơ trọi",
   rồi dùng trống định âm đánh dấu chuyển từ "bị chê" sang "có hạn chót 3 ngày" (động cơ của phần sau). Mốc nhạc về (~40s) sớm hơn cắt 41.6s ~1.6s — không chắc là cắt theo nhạc.
5. **Máy đẩy chậm (zoom/dolly in) dày đặc, nhất là trên insert trứng và mặt phản ứng** (#19–24: 4/6 shot zoom in). Ý đồ **[có thể]**: dồn chú ý vào
   vật "bằng chứng" (trứng vàng / đen) — vật mang cả cốt truyện. [suy luận] với video AI, lệnh đẩy máy chậm dễ làm đẹp và ít lỗi hơn chuyển động phức tạp.

## Giới hạn / câu hỏi mở
- Chỉ ~24% phim; hai đoạn đều nằm trong bản gộp nhiều tập — nhịp và âm thanh ở chỗ nối tập có thể do khâu gộp của kênh đối tác, không phải của phim gốc.
- Nhãn AudioSet trên lớp nhạc tách bằng demucs: tiếng đập/hiệu ứng lọt vào lớp "nhạc" (drums/other), nên "nhạc 84–98%" là **nhạc + hiệu ứng**;
  không tách được hai thứ bằng công cụ hiện có. Chưa nghe bằng tai.
- Đoạn 2 chỉ phân tích âm tới giây file 90; 90–130s chỉ có số đo silencedetect/RMS.
- OpenCV không track được 5 shot cuối đoạn 2 (cảnh tối, hạt ánh sáng) — "thiếu dữ liệu" không có nghĩa là máy tĩnh.
- Không biết công cụ AI dùng (không ghi trong mô tả).

## Xoá dữ liệu
Đã xoá `v07db_seg1_X5EJ9etPr2M.webm`, `v07db_seg2_X5EJ9etPr2M.webm`, thư mục `v07db_seg*_frames/`, `v07db_seg*_listen/` (wav, stem demucs),
`v07db_seg*_sheet_*.jpg`, `v07db_seg*_spec_*.png` khỏi `scratchpad/s012` sau khi viết xong file này; chỉ giữ `*_result.json`, `*_listen_numbers.json` (mức nhạc / giọng, nhãn — đã bỏ lời chép), `*_table.md`, `*.py`.
