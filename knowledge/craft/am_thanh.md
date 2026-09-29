# Âm thanh (S0.11 lượt 2, 2026-09-29)

> Đọc `README.md` trước. Luật pipeline: editing.md E2–E4, E8; Đạo diễn Đ9 (`sound`: cut / in / breath / sfx). Nghề nhạc phim (spotting, brief
> nhạc, nhạc theo thể loại) ở S0.15: `research/craft/draft/nhac_*.md` — kho này chỉ ghi kỹ thuật âm thanh đã thấy ở mẫu.
> **Giới hạn đo:** "nghe bằng số" (`tools/audio_listen.py`: demucs tách lớp, nhãn AudioSet cửa sổ 2 s → khớp mốc ±1 s, whisper) — **chưa nghe
> tai**; lớp "nhạc" lẫn tiếng động (14); đỉnh âm trên file nén không tin được. Danh sách chỗ cần người nghe: `TONG_HOP.md` mục Tồn đọng.

### Thiết kế âm thanh từ lúc viết cảnh (Randy Thom)
- **Cách làm:** quyết vai trò của âm (dẫn dắt / minh hoạ / im lặng) khi chia cảnh, không "thêm sau". Thom [C2]: cảnh âm thanh mạnh nhất thường là
  lúc người xem nghe **theo điểm nhìn một nhân vật** (âm cho biết họ là ai, cảm thấy gì); **âm ngoài khung**; hình **giấu bớt** thông tin (tối,
  góc cực đoan, ống dài) mời người xem dùng tai và tưởng tượng; thoại kín từ đầu tới cuối bóp chết chỗ cho âm thanh.
- **Có thể phục vụ:** để âm dẫn trước hình · cho cảnh ít thoại / ít cắt vì âm đã gánh cảm xúc · biện minh cho âm chủ quan (Thom: *The
  Conversation* dùng ống dài để âm thanh chủ quan hợp lý).
- **Ví dụ:** [09 0–158s] 2:38 không thoại — tiếng gió, thở, bàn tay đập lên mép đá (nhãn Whip 0,72 ở 6 s) kể sự cô độc · [18 đ2 +71–98s] đêm gần đen,
  đèn pin là nguồn sáng duy nhất, nhạc tăng đều −37 → −24 dB trong 30 s thay cho cú giật mình · [16] phim về người mù–điếc: nền nhạc −44…−48 dB,
  LRA 26 LU, chữ thay lời.
- **Với video AI:** ghi `sound` của từng shot (Đ9) **trước** khi sinh; model video tự thêm nhạc / âm nền — tắt tiếng gốc khi có kế hoạch riêng.
- **Nguồn:** Thom [C2] (đọc trọn). **Độ tin:** chắc (nguồn); ví dụ: khá.

### Tắt nhạc dưới khoảnh khắc then chốt, cho nhạc về ở (gần) một điểm cắt
- **Cách làm:** nhạc rút xuống / tắt (thoại vẫn chạy) dưới một câu hoặc một khoảnh khắc, rồi trở lại — thường đúng nhát cắt sang phản ứng.
- **Có thể phục vụ (đã thấy — ý nghĩa do ngữ cảnh):** câu lật thế cờ nghe "trơ trọi" (lật mặt) · punchline hài · thú nhận / nội tâm then chốt ·
  khoảnh khắc "thắng" được cho thở · để người xem "nhìn" vết thương cùng nhân vật · nghỉ giữa trận để nâng cược · ký ức bị xoá = âm bị xoá.
- **Khi hợp / khi không:** chỉ "nghe" được khi trước đó có nhạc; dùng dày sẽ mất tác dụng; nhạc có thể về **dần** chứ không nhất thiết đúng cắt (23).
- **Ví dụ:** [06 đ2 +84–89s] lặng lúc gặp lại → nhạc + cắt 90,0 s · [07 đ2 +33–40s] nhạc < −50 dB dưới câu sỉ nhục → về ~40 s kèm timpani · [10 đ3
  +42–57s] → cắt 57,9 · [11 đ2 +90.7–92.9s] dưới câu chốt cãi yêu → nhạc về ở cắt 93,4 (hài) · [12 đ2 +79.1–80.6s] lặng ↔ cắt 80,2 → nhạc trồi −11 dB
  84 s · [15 36–42s, 47–53s] dưới câu nội tâm; [15 đ3 +60–70s] dưới "It was a mistake" · [16 đ2 +60.8–67.5s] → nhạc −16 dB khi xe buýt tới · [19 đ2
  +94–118s] nhạc tụt + gong + lặng ~17 s trên CU ↔ CU · [23 đ2 +34.4s] −60 dB, về dần 12 s.
- **Với video AI:** Đ9 `sound.cut` / `sound.in` + `core/sound_intent.py` (cờ `sound_intent`); editing.md E4 "khoảng lặng trước cú ngoặt" (D6).
- **Nguồn:** mẫu hình 5 `TONG_HOP.md` (10 video). **Độ tin:** chắc về hình thức (số đo khớp cắt 0,1–0,5 s ở 06, 10, 11, 12); ý đồ: có thể.

### Im lặng có chủ đích — chuyển thời gian, nín thở, chờ
- **Cách làm:** rút hết âm (kể cả nền) vài giây.
- **Có thể phục vụ:** (a) báo đổi thời gian / thực tại (xem `chuyen_canh.md`) · (b) "nín thở" trước một cú âm lớn · (c) hồi hộp chờ tin bằng im lặng
  thay nhạc căng.
- **Ví dụ:** (a) [10 14.2–23.2s] lặng hoàn toàn đúng cắt 14,2 · [11 28.6–29.3s] ↔ cắt 28,4 · [14 115.4–117.2s, 123.8–125.6s] quanh trọng sinh · (b)
  [07 đ2 +73.0–77.5s] lặng tuyệt đối dưới ECU mắt rồng 15,8 s → tiếng gầm ~76–78 s · (c) [14 đ2 +146.5–154.5s] lặng 8 s dưới cảnh chờ tin nhắn.
- **Khi hợp / khi không:** ở video gộp, lặng sau thẻ "còn tiếp" có thể chỉ là chỗ nối tập (07) — không phải ý đồ.
- **Với video AI:** tắt tiếng clip + tắt nhạc ở khâu trộn; im lặng hoàn toàn quá lâu nghe như lỗi (E3 ví dụ ✘) → cân nhắc giữ nền không khí.
- **Nguồn:** mẫu hình 8 `TONG_HOP.md`; Thom [C2]. **Độ tin:** khá (a: 3 mẫu, đo khớp 0,1–0,2 s; b, c: mỗi ý 1 mẫu — có thể).

### Âm nhấn (đập / nổ / vút) trùng điểm cắt
- **Cách làm:** đặt một tiếng đập, nổ, cửa sập, vút đúng nhát cắt.
- **Có thể phục vụ:** biến lời cãi vã thành "cú đánh" · đánh dấu lộ bài · mở tập / mở cảnh bằng một cú · chấm câu cho chuỗi CU tĩnh.
- **Ví dụ:** [07 138–154s] 5/6 cửa sổ có nhãn đập đều có cắt trong ±0,5 s (Slam 139,3; Explosion 139,9, 145,9…) · [10 đ3 +68.7s] Bang ở cắt "Is this a
  joke?" · [11 đ2 +66.6s] Explosion ở cắt (đầu lâu, mở tập) · [12 đ2 +80.2s] Clang / Whoosh · [14 37.9s] Slap ở cắt, Explosion 0,59 ở cắt 28,2 ·
  [15 2s] Explosion 0,81 cảnh mở.
- **Với video AI:** `core/sfx_plan.py` đặt điểm nhấn + âm Đạo diễn ghi ở `sound.sfx` (E3).
- **Nguồn:** mẫu hình 6 `TONG_HOP.md` (8 video). **Độ tin:** khá (nhãn AST điểm thấp 0,1–0,4, khớp ±1 s).

### Tiếng tim đập dưới câu lật bài / thú nhận
- **Cách làm:** lớp tim đập nhỏ dưới câu then chốt, thường khi nhạc đã rút.
- **Có thể phục vụ:** báo "đây là khoảnh khắc quan trọng" bằng âm cơ thể thay vì tăng nhạc · đặt người xem vào ngực nhân vật đang sốc.
- **Ví dụ:** [07 156–160s] dưới "This is Grayson's baby too"; [07 đ2 +10–14s] dưới câu cha · [10 đ3 +70s, +78s] · [12 đ2 +84s] · [15 10s] (cảnh mở),
  [15 đ3 +40s, +46s].
- **Nguồn:** mẫu hình 6 `TONG_HOP.md`. **Độ tin:** khá (4 video, đều AI drama — chưa thấy ở phim quay thật).

### Nhạc nền: liền một khối hay thưa bật / tắt — lựa chọn của kênh, có khi đổi theo cảnh
- **Cách làm:** (A) nền liên tục dưới thoại (97–100% thời gian) · (B) nhạc thưa, bật / tắt theo câu hoặc chỉ như cú nhấn 1–2 s.
- **Có thể phục vụ:** A — giữ áp lực liên tục cho người xem lướt, giữ tông (hài) · B — để thoại / tiếng thở / tiếng động mang cảm xúc, câu "nổi"
  lên · đổi A ↔ B trong một phim như một đường cong kịch.
- **Khi hợp / khi không:** không có luật "AI drama = có / không có nhạc". Độ to tổng cũng theo kênh: AI drama −9,8…−19 LUFS, phim ngắn quay thật
  −22,5…−27,9 LUFS (số đo, không phải chuẩn — chuẩn xuất bản ở E8).
- **Ví dụ:** A: [12] 100%, 0 quãng lặng, −10,3 LUFS · [13] 100% phẳng ±3 dB · [11] 97–98% · B: [01 0–90s] 20% · [10] 14–32% (cú nhấn 27 / 32 / 36 s
  trong cuộc gọi bắt cóc) · [15] 57–69%, 57–68 quãng lặng / 3 phút · đổi theo cảnh: [17] đoạn mở 48 quãng lặng ↔ cao trào 100%, 1 quãng lặng ·
  [10] bi kịch ↔ tiệc.
- **Với video AI:** kiểu A dễ làm (một bài dài + hạ nhạc 8–12 dB dưới giọng, E4); kiểu B cần kế hoạch `sound` từng shot.
- **Nguồn:** mẫu hình 4 `TONG_HOP.md` (14 video, tách lớp demucs). **Độ tin:** khá.

### Màu nhạc theo nhịp kịch — hoặc giữ một màu để giữ tông
- **Cách làm:** đổi nhạc cụ / bản nhạc theo từng nhịp; hoặc cố ý giữ một bản suốt cảnh dù có "nguy hiểm".
- **Có thể phục vụ:** cho cảm xúc dẫn đường khi ít thoại · báo cho người xem rằng chuyện "nguy hiểm" ở đây là chuyện buồn cười (giữ tông hài).
- **Ví dụ:** [06 đ2] guitar → nền dưới thoại → cello / bass khi nghe tin (41,8 s) → violin khi chạy → lặng → piano khi chăm sóc (90,0 s) · ngược lại
  [06 0–125s] một bản vui suốt cảnh hài bị điện giật · [11] marimba / accordion cả trong cảnh "nhà ma" · [12 50–80s] dây kéo lên dưới chuỗi sỉ nhục.
- **Với video AI:** brief nhạc theo đoạn (composition plan của Eleven Music [NGUON #38]) — xem S0.15.
- **Nguồn:** mẫu 06, 11, 12 (nhãn nhạc cụ AST điểm thấp); NPR — Theodore Shapiro về nhạc hài "giữ mặt nghiêm" [NGUON #43]. **Độ tin:** có thể.

### Nhạc vào / trồi ở shot mở không gian — hoặc tắt đúng lúc đó (phản ví dụ)
- **Cách làm:** mức nhạc đổi mạnh đúng shot nhân vật "thoát ra" / không gian mở.
- **Có thể phục vụ:** phóng to khoảnh khắc thắng / thoát · **ngược lại**: nhạc lên đỉnh **trước** khi thoát rồi tụt gần câm để người xem "thở ra"
  cùng nhân vật bằng tiếng gió / chuông.
- **Ví dụ:** [12 đ2 +84s] cửa sáng cháy, nhạc −11 dB sau nhịp lặng · [16 đ2 +71s] nhạc −16 dB cùng tiếng xe buýt · [09 30.1s] toàn cảnh vách đá, nhạc
  lên · [09 đ2 +71.5s] nhạc lên ở cắt sang đám mây khổng lồ · phản ví dụ [25 116–124s] nhạc −19 dB → −67 dB khi khu vườn mái mở ra (121,2 s).
- **Khi hợp / khi không:** ở drama thường đi **sau một nhịp lặng** (12, 16). Cùng loại khoảnh khắc, hai cách ngược nhau → là "một cách làm",
  không phải quy luật.
- **Nguồn:** mẫu hình 7 `TONG_HOP.md` + 25. **Độ tin:** khá cho hình thức; ý đồ: có thể.

### Đoạn thiết lập không nhạc / nhạc nhỏ, nhạc vào ở chữ tên phim hoặc khi truyện bắt đầu
- **Cách làm:** 16–52 s đầu chỉ có âm nền / nhạc rất nhỏ; nhạc chính vào đúng chữ tên phim hoặc lúc "luật chơi" đã rõ.
- **Có thể phục vụ:** dựng luật chơi trước để phần nhạc / lời sau được hiểu theo truyện · đánh dấu cấu trúc (hết mở màn → vào truyện) thay lời.
- **Ví dụ:** [23 0–52s] ký giấy, phòng chờ, nền −38 dB, nhịp tim → bài hát từ 52 s · [18 0–18s] 6 khung báo trước không nhạc → nhạc vào ở chữ tên
  phim · [09 58s] nhạc lên ở tên phim (0–29 s nhạc −38…−46 dB dưới tiếng gió) · [16 4–42s] nhạc lên rất chậm −49 → −20 dB dưới shot đi bộ.
- **Nguồn:** `TONG_HOP.md` (ứng viên mẫu hình mới, 3–4 video). **Độ tin:** khá.

### Âm ngoài khung / cầu âm giữa hai shot (J / L)
- **Cách làm:** âm của shot sau vào trước hình (J), hoặc âm shot trước kéo sang hình sau (L); nguồn âm không thấy trong khung.
- **Có thể phục vụ:** báo trước điều sắp vào khung · mở rộng thế giới ra ngoài khung · kéo người xem qua chỗ cắt (tiếng gọi → cắt sang người được gọi).
- **Ví dụ:** [12 85.9s → 86.6s] tiếng gọi "老爷" rồi mới cắt sang vườn (cầu âm kiểu J, ~0,7 s) · [16 đ2 +65.5–71s] tiếng xe buýt tới cùng lúc nhạc trồi,
  quanh cắt 65,5 (chưa rõ tiếng vào trước hay sau hình). Thom [C2]: nhân vật ở góc tối quán bar được "định vị" bằng tiếng chai lăn và giọng trước khi thấy.
- **Với video AI:** J-cut giọng lồng 0,25 s (cờ `j_cut`, editing.md E1); cầu âm hiệu ứng phải đặt tay ở khâu trộn — model sinh từng clip riêng.
- **Nguồn:** Thom [C2]; [E3]; mẫu 12, 16. **Độ tin:** có thể (mốc cần soi lại bằng tai).

### Giọng nội tâm / giọng kể trên cận mặt không mở miệng
- **Cách làm:** giọng nhân vật (nội tâm hoặc kể) phủ lên CU phản ứng / cảnh minh hoạ, miệng không nói.
- **Có thể phục vụ:** cho người xem vào đầu nhân vật · kể quá khứ trên cảnh hiện tại · để hành động làm minh hoạ cho lời · [suy luận] với AI:
  tránh bài toán khớp môi.
- **Ví dụ:** [15 14.3–57s] nội tâm "crush… best friend" trên CU câm · [14 0–28.7s] giọng kể "40 năm hôn nhân" trên cảnh đám tang · [09 27.8–48.4s] giọng
  kể liên tục trên hồi tưởng hành động, rồi giọng tắt 2 s trên ECU mắt (44–46 s) trong khi nhạc vẫn chạy.
- **Nguồn:** mẫu hình 15 `TONG_HOP.md` + 09. **Độ tin:** khá (3 mẫu).

### Motif âm gieo chủ đề (giả thuyết)
- **Cách làm:** một âm lặp lại sớm (tích tắc, tiếng đòn) báo trước chủ đề / cú chính về sau.
- **Ví dụ:** [17 0–90s] nhãn Tick-tock 0,13–0,36 ở 8 cửa sổ + insert đồng hồ (#12) — chủ đề vòng lặp thời gian · [19] tiếng đòn trên cọc gỗ khi tập,
  cùng họ nhãn "Slam" với trận chính.
- **Nguồn:** mẫu 17, 19 — nhãn AST điểm thấp, **chưa nghe tai**. **Độ tin:** giả thuyết (đoán) — cần người nghe 17 đoạn 0–90 s.
