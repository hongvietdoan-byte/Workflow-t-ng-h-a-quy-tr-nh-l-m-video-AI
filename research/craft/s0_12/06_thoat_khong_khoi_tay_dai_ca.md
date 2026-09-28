# 06 — 《逃不出大哥手掌心》(他和他放映室)

- **URL**: https://www.youtube.com/watch?v=TB9erIvAiko
- **Thể loại**: AI short drama BL hiện đại (kênh một người viết/dựng, theo `MAU_S0_12.md` mục 1.5), tiền đề "xuyên sách / thức tỉnh": nhân vật tóc vàng
  biết trước anh trai kế (tóc đen) sẽ yêu "thụ chính" rồi bị "công chính" giết, còn mình phải chết theo; cứ chống lại anh là **bị điện giật**.
  [suy luận] hình do AI sinh (da mặt mịn đồng nhất, tia điện xanh vẽ bằng hiệu ứng) — kênh không ghi công cụ.
- **Độ dài công bố**: 19:39 · file tải **1280×720 (16:9)**, 30 fps — khung ngang, khác các AI short drama 9:16 còn lại
- **Đoạn đã đo**: (1) 0:00–3:00 (mở đầu, 180.0s) · (2) yêu cầu 16:40–18:40 (file 130.0s; **hình bắt đầu ở giây 4.48 của file**, âm ở giây 0 —
  yt-dlp cắt theo keyframe; mốc trong bảng là giây của file, mốc gốc ≈ 16:35.5 + t, sai số vài giây [suy luận])
- **Tổng đã đo**: ~305s / 1179s (~26%)
- **Đã tải**: `v06_seg1_TB9erIvAiko.webm` (12.7 MB) + `v06_seg2_TB9erIvAiko.webm` (7.6 MB) + 1 khúc quét thưa 12:00–19:39 (đã xoá ngay sau khi chọn
  đoạn) — **tất cả đã xoá sau khi viết xong file này**.

## Cách tìm đoạn "lật ngược"
Như video 04: tải khúc 12:00–19:39 (480p), `ffmpeg fps=1/20` + `tile` ra tờ ảnh thưa, đọc bằng mắt, rồi tải đúng khúc 16:40–18:40. Nội dung đoạn đã
đo xác nhận đây là **bước ngoặt cảm xúc**: nhân vật tóc vàng nghe lén cha nói với người khác về "cậu chủ nhà họ Bùi (裴家) bồng bột… vì một thằng
theo hầu không thân phận" và "nghe nói đêm đó bị người từ thư phòng…" → chạy khỏi nhà, bắt taxi → vào phòng tối thấy anh (tóc đen) nằm với lưng
đầy vết thương → băng bó, anh hỏi "ai bắt nạt em", cậu trả lời "là cha tôi" (phụ đề + whisper).

## Phương pháp
Giống 04/05 (cắt `ffmpeg scene`, tờ ảnh, LUFS/LRA/quãng lặng, OpenCV per-shot) + **"nghe bằng số" `tools/audio_listen.py`** (demucs tách nhạc /
giọng, mức nhạc từng giây, nhãn AudioSet 2s/dòng, faster-whisper `--lang zh` chép lời có mốc — khớp phụ đề Trung trên hình). Đã chạy: đoạn 1
giây 0–60 và 60–125; đoạn 2 giây 0–60 (lớp âm tách có 55.5s → **mốc tách + 4.5s = giây file**, đã đối chiếu: whisper "为了个没身份的小跟班" 18.7s
khớp phụ đề shot #6 ở 23.1–25.2s) và 60–120 (mốc tách + 60, đối chiếu: "你怎么来了" 88.3s khớp phụ đề shot #32). Không báo cáo đỉnh.

## Số đo
| Đoạn | Shot | Trung vị | Min–max | Shot/phút | Máy (OpenCV) |
|---|---|---|---|---|---|
| Mở đầu 0:00–3:00 | 61 | 2.60s | 0.4–7.1s | 20.3 | tĩnh 77%, zoom/dolly in 8%, roll 8%, tịnh tiến 5%, thiếu dữ liệu 2% |
| Lật ngược ~16:40 | 43 | 2.97s | 0.33–10.65s | 19.8 | tĩnh 79%, thiếu dữ liệu 12% (các shot 0.33s), zoom in 5%, tịnh tiến 2%, roll 2% |

- Âm thanh: LUFS **−19.0** / **−19.2** (nhỏ hơn rõ các kênh AI drama 9:16: −11…−15), LRA **6.4** / **11.5** LU; quãng lặng (< −35 dB) **0** / **2**
  (87.6–88.6s và 89.8–90.2s — đúng khoảnh khắc gặp lại, xem dưới).
- Nhịp cắt chậm hơn video 01 (trung vị 1.4–2.0s) và 04 (2.0–2.2s), gần DramaBox (07: 2.5–3.7s).

### Nghe bằng số (audio_listen)
- **Nhạc có gần như suốt**: 100% (đoạn 1, 0–125s), 98% và 92% (đoạn 2). Không có chỗ "nhạc tắt giữa các câu" như giả thuyết ở video 01.
- **Đoạn 1 = một bản nhạc vui chạy liên tục 0–125s**: nhãn phụ lặp lại Ding / Jingle, tinkle / Bicycle bell / Beep (0.03–0.14) — [có thể] nhạc
  chuông/celesta kiểu hài nhẹ; tempo đo 136 / 123 BPM, giọng đoán La thứ ở cả hai khúc; mức nhạc −21…−29 dB, dao động đều ~4s/chu kỳ
  ([đoán] vòng lặp 2 ô nhịp). **Nhạc không đổi** cả ở lúc tia điện (#12 37.7s, #25 76.9s) lẫn lúc anh cúi sát mặt (#27–33, 78–96s) — chỉ có tiếng
  "whoosh" (0.05) ở 38–40s trùng tia điện #12.
- **Đoạn 2 = nhạc đổi theo từng nhịp kịch** (mốc giây file):
  | Mốc | Mức nhạc | Nhãn nổi bật | Hình / thoại |
  |---|---|---|---|
  | 4.5–12.5 | rõ (−21…−25) | Guitar, plucked string | #1 cậu ngồi ở nhà (shot 10.65s) |
  | 12.5–24.5 | **nhỏ dưới thoại** (−36…−52) | Speech, footsteps | #2–6 hai người đàn ông bàn chuyện nhà họ Bùi |
  | 24.5–41 | nhỏ/rõ xen kẽ (−34…−40) | Piano (0.03–0.06) | #7–11 nghe lén sau cửa |
  | **41.5 → 58** | **to lên (−26…−30)** | **Cello, Double bass, Bowed string** (0.1–0.22) | #12 (41.8s) CU cậu phản ứng — "nghe nói đêm đó…" |
  | 64–82 | rõ | **Violin** (0.08–0.15) + Car, Skidding | #19–26 chạy, 4 shot 0.33s qua sảnh/cửa xoay, taxi |
  | **84–89** | **tắt** (−48…−59) | Speech, Sigh, "Inside, small room" | #30–32 thấy lưng đầy vết thương, "姜言", "你怎么来了" |
  | 90 → 120 | rõ lại (−26…−31) | Music 0.84 ở 96s; **Piano / Electric piano** từ ~102s | #33 (90.0s, cắt trùng lúc nhạc về) "眼睛怎么红了 / 谁欺负你了"; băng bó, "是我爹" 119.4s |
- Độ tin: mức nhạc và chỗ tắt **khá** (đo trực tiếp trên lớp tách, khớp silencedetect 87.6–90.2s); tên nhạc cụ **có thể** (điểm AST chỉ 0.03–0.22).

## Bảng shot — đoạn 1 (0:00–3:00, 61 shot)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1–3 | 0.0–10.7 | WS/MS 2 người phòng ký túc | ngang mắt | tĩnh | cậu tóc vàng bật dậy trên giường, anh tóc đen đứng; VO nội tâm "某天我突然觉醒了… 陪葬" |
| 4–7 | 10.7–25.0 | WS + CU | ngang mắt | tĩnh | "去不去看新来的转学生 / 主角受"; nhạc chuông vui liên tục |
| 8–13 | 25.0–42.9 | qua vai / CU | ngang mắt | roll×1, zoom in×1, tĩnh×4 | đối đáp bóng bàn "我去 / 你去" 32.9–36.2s (câu 0.6s); #11–12 shot 1.2–1.3s; **#12 tia điện xanh** + whoosh |
| 14–19 | 42.9–59.6 | CU qua vai / WS | ngang mắt | tĩnh | "不去就你不去 / 我自己去就是了 / 等一下 / 你再使坏我试试" |
| 20–26 | 59.6–78.4 | CU anh (#20 zoom in) / WS | ngang mắt | zoom in×1, roll×2, tĩnh×4 | "你耍我"; #25 tia điện ở chân 0.5s |
| 27–33 | 78.4–96.6 | MCU 2 người sát mặt → CU tay nâng cằm | ngang mắt, anh hơi cao hơn | zoom in×2, thiếu dữ liệu×1, tĩnh×4 | anh cúi sát, nắm cổ áo; "刚才我嘴巴臭了… 我陪你去"; nhạc không đổi |
| 34–39 | 96.6–117.6 | WS rời phòng → hành lang, đi về phía máy | chính diện | tịnh tiến×1, roll×1, tĩnh×4 | VO "只要违抗他就会挨电… 我改不了和他一起陪葬的命" |
| 40–48 | 117.6–139.2 | MS/WS đi cùng hành lang; #45 insert tay nắm cổ tay | ngang mắt | roll×1, tịnh tiến×1, zoom in×1, tĩnh×6 | đi và nói |
| 49–54 | 139.2–161.5 | MS 2 người / CU qua vai trong lớp học | ngang mắt | tĩnh | #49 bạn học mới ngồi trong lớp |
| 55–61 | 161.5–180.0 | MS 2 người | ngang mắt | tịnh tiến×1, tĩnh×6 | anh khoác vai cậu (#58, #60) |

## Bảng shot — đoạn 2 (≈16:40, 43 shot; hình từ giây 4.48)
| # | Vào–ra | Cỡ cảnh chủ đạo | Góc | Máy (OpenCV) | Nội dung / âm thanh |
|---|---|---|---|---|---|
| 1 | (4.5)–10.7 | MCU cậu ngồi bàn | ngang mắt | tĩnh | nhạc guitar rõ |
| 2–4 | 10.7–19.9 | WS phòng; MS/WS cậu đi hành lang tối | ngang mắt | tịnh tiến×1, tĩnh×2 | nhạc hạ xuống nền |
| 5–8 | 19.9–30.4 | MS 2 người đàn ông vest / qua vai; #7 CU cậu sau cửa | ngang mắt | tĩnh | "裴家那小少爷也真是冲动 / 为了个没身份的小跟班 / 大少爷想睡就让他睡呗" |
| 9–18 | 30.4–59.5 | xen kẽ CU cậu nghe lén (#9, 12, 15, 18) ↔ MS/qua vai 2 người | ngang mắt | roll×1, tĩnh×9 | #12 (41.8s) cello/bass vào, nhạc to lên; "听说当晚是让人从书房…" |
| 19–26 | 59.5–71.9 | MS chạy; **#20–23 bốn shot 0.33s** (sảnh, cửa xoay); #25 WS phố + taxi; #26 MCU trong taxi | ngang mắt | thiếu dữ liệu×4, tĩnh×4 | violin; tiếng xe |
| 27–30 | 71.9–84.2 | WS phòng ngủ tối; #28 zoom in; **#29 insert lưng đầy vết thương**; #30 CU cậu | ngang mắt, #29 từ trên xuống | zoom in×1, tĩnh×3 | nhạc bắt đầu tắt ở ~84s |
| 31–33 | 84.2–94.0 | MS 2 người → #33 CU qua vai | ngang mắt | zoom in×1 (#32), tĩnh×2 | lặng 84–89s; "你怎么来了" 88.3s; nhạc về đúng cắt #33 (90.0s) "眼睛怎么红了 / 谁欺负你了 / 我就干死他" |
| 34–43 | 94.0–130.0 | MS 2 người trên giường; #41 insert bôi thuốc | ngang mắt | thiếu dữ liệu×1, tĩnh×9 | piano; "一点小伤… 报复人还光明正大… 是我爹" |

## Kỹ thuật đáng học
1. **Tắt nhạc đúng lúc gặp lại, bật lại đúng nhát cắt sang câu hỏi han** (đoạn 2, 84–89s lặng → 90.0s nhạc + cắt #33). Ý đồ **[có thể]**: khoảng lặng
   để người xem "nhìn" vết thương cùng nhân vật; nhạc trở lại đánh dấu chuyển từ sốc sang dịu dàng. Độ tin: khá về số đo, có thể về ý đồ.
2. **Đổi nhạc cụ theo nhịp kịch trong cùng một đoạn** (guitar → nền dưới thoại → cello/bass khi nghe tin → violin khi chạy → lặng → piano khi chăm sóc).
   Ý đồ **[có thể]**: mỗi nhịp một "màu" âm thanh để cảm xúc dẫn đường khi thoại ít (đoạn chạy 59.5–71.9s gần như không thoại). Độ tin: có thể
   (nhãn nhạc cụ điểm thấp, nhưng chuỗi đổi khớp mốc cắt ở 41.8s và 90.0s).
3. **Ngược lại, phần hài mở đầu giữ nguyên một bản nhạc vui 125s**, không đổi cả khi có tia điện hay khoảnh khắc sát mặt. Ý đồ **[có thể]**: giữ tông hài,
   báo cho người xem rằng "bị điện giật" và "bị ép" ở đây là chuyện buồn cười, không phải nguy hiểm. Độ tin: có thể.
4. **Dồn 4 shot 0.33s + 1 shot 0.5s thành một cú "chạy" 1.9s** (62.4–64.3s) giữa các shot 2–5s. Ý đồ **[có thể]**: nén quãng đường nhà → taxi thành một
   nhịp gấp, cho thấy sự vội vã mà không cần thoại. Độ tin: có thể, 1 lần.
5. **Cắt xen nghe lén** (#9–18: 4 CU phản ứng của cậu xen 6 shot hai người nói) — người xem nhận tin cùng lúc với nhân vật; nhạc to lên ở CU phản ứng #12,
   không phải ở câu thoại. Độ tin: có thể.
6. **Đối đáp bóng bàn "我去 / 你去"** mỗi câu ~0.6s (32.9–36.2s) nhưng **không cắt theo từng câu** — cả 6 câu nằm trọn trong shot #10 (32.6–36.5s, hai
   người cùng khung). Ý đồ **[đoán]**: nhịp hài nằm ở thoại, giữ hình để người xem thấy cả hai phản ứng; ngược với video 01 ("1 câu ≈ 1 shot").

## Giới hạn / câu hỏi mở
- Chỉ ~26% phim. Nhãn nhạc cụ từ AST trên lớp nhạc tách bằng demucs (lớp này còn lẫn tiếng xe, cửa…); chưa nghe bằng tai.
- Đoạn 1 giây 125–180 chưa chạy audio_listen (chỉ có RMS/silencedetect: 0 quãng lặng).
- Tên nhân vật trong whisper (姜言, 裴玉, 赫锋) có thể sai chữ đồng âm; nội dung câu đối chiếu với phụ đề trên tờ ảnh.
- OpenCV không track được các shot 0.33s — "thiếu dữ liệu", không phải tĩnh.

## Xoá dữ liệu
Đã xoá `v06_seg1_TB9erIvAiko.webm`, `v06_seg2_TB9erIvAiko.webm`, thư mục `v06_seg*_frames/`, `v06_seg*_listen/` (wav, stem demucs), `v06_seg*_sheet_*.jpg`,
`v06_seg*_spec_*.png` khỏi `scratchpad/s012` sau khi viết xong file này; chỉ giữ `*_result.json`, `*_listen_numbers.json` (mức nhạc / giọng, nhãn — đã bỏ lời chép), `*_table.md`, `*.py`.
