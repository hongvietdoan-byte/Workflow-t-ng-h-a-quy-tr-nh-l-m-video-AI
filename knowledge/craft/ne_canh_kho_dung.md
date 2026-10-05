# Kỹ thuật né cảnh không dựng được (S14.32, 05/10/2026)

> **Nguồn:** 40 clip kênh TikTok `@freefire_kelly_official` (Kelly 3D, gần như toàn bộ dựng ngoài đời, không quay màn hình game). Mã K01–K40 theo `data/ref_kelly/list.tsv`; bảng đầy đủ ở `research/kelly_official/phieu_40_clip.md`.
> **Địa vị:** tư liệu cho Biên kịch / Đạo diễn / Quay phim / Dựng. **CHƯA nạp vào prompt nào** (code chưa đọc file này; khi nạp phải qua cờ, TẮT mặc định — như S14.20). Đọc `README.md` (4 nguyên tắc) trước.
> **Cách đọc:** "né" = khi cảnh gốc (trận đấu, màn hình điện thoại, đám đông, map) khó hoặc không dựng được bằng model, kênh thể hiện nó bằng **lớp thông tin / vật thể nhỏ / phản ứng** thay vì dựng cảnh đó. Kỹ thuật không có nghĩa cố định; mỗi mục ghi "ở clip nào, giây nào, để làm gì".
> **Giới hạn của mẫu:** MỘT kênh, 40 clip (20 view cao + 10 mới + 9 chủ đề + 1 người dùng gửi). Mọi mục có ≥ 3 clip nhưng cùng kênh → độ tin tối đa "có thể" (README: "khá" cần ≥ 2 mẫu **khác kênh**). Mốc giây ± 1 bước khung (≈ 1,3–2,3 s; clip 60 s ± 5 s).

---

### 1. HUD trên / cạnh đầu thay "màn hình điện thoại trong trận"
- **Cách làm:** nhân vật ngồi ngoài đời, cầm điện thoại nhưng KHÔNG thấy màn hình; trên đầu hiện ô **số thứ tự đội (màu) + tên + thanh máu**; khi "chết" hiện **đầu lâu đỏ** cạnh thanh máu; có thể thêm thẻ vật phẩm (SUPER REVIVAL 600F, ô F 0), chữ DEFEAT.
- **Thay cho:** cảnh trong trận / màn hình game (khó dựng đúng giao diện, đúng HUD).
- **Điều kiện dùng:** người xem đã biết giao diện FF (HUD là chữ viết tắt cảm xúc); nhân vật phải **nhìn xuống điện thoại + diễn mặt** (sốc, hả hê); mỗi người một HUD để đếm "ai còn sống"; làm bằng **lớp hậu kỳ**, không bắt model video vẽ HUD (`knowledge/ff_styles/INGAME.md` đã dặn).
- **Ví dụ:** [K01 0–11,7 s] một cú lia qua 3 người, Kelly đầu lâu ~2 s, Alvaro đầu lâu ~8 s, thẻ SUPER REVIVAL ~5,8–8 s, ô F 0 ~10 s · [K11 0–4,5 s] icon cuộc gọi trên đầu Maxim, "2 Kelly" máu đỏ có nút "+", chữ DEFEAT ~4 s · [K34 0–8 s] "1 Me / 2 Teammate" máu rút, đỏ + đầu lâu ~2,5 s · [K23 0–6 s] chữ "Damage:179 Kill:14" vs "Damage:6553 Kill:0" cạnh đầu (thay bảng hậu trận) · [K20 ~36–39 s] "Maxim / Kelly" thanh máu trên đầu khi ngồi ghế đá.
- **Với video AI:** viết trong kịch bản "HUD: [số][tên][thanh máu] trên đầu X, giây a–b, đầu lâu ở giây c" thành **chỉ dẫn hậu kỳ**; ảnh/clip nhân vật gửi model phải để khoảng trống phía trên đầu (khung chặt đầu làm mất chỗ HUD).
- **Độ tin:** có thể (5 clip, 1 kênh).

### 2. Bảng đội + bộ đếm hạ gục chồng lên cảnh
- **Cách làm:** góc trên trái khung có bảng 4 dòng (1 Teammate, 2, 3 có đầu lâu = chết; "Me" thanh cyan) và bộ đếm "X1 → X3 → X4 💀" chạy trên dòng "Me"; nhân vật chỉ cầm điện thoại, người bên cạnh phản ứng (chắp tay cầu nguyện).
- **Thay cho:** cảnh bắn hạ 4 địch (quadra).
- **Điều kiện dùng:** đủ khoảng trống góc trên trái; có **âm thanh thông báo game** đi kèm (xem mục 11); gag ở cú chốt (người "ghi 4 mạng" uống sữa nhàn nhã).
- **Ví dụ:** [K14 0–7,8 s] bảng 4 dòng + X1→X3→X4, giọng thông báo "First Blood … Ace!" 0,1–5,1 s · [K18 ~0–5 s] bảng đội + "X3" · [K34 0–2 s] bảng 2 dòng.
- **Với video AI:** bảng và bộ đếm làm hậu kỳ (card/hoạt hình chữ), ghép với track âm thanh game.
- **Độ tin:** có thể (3 clip).

### 3. Icon / huy hiệu lơ lửng trên đầu = trạng thái, hạng, kỹ năng, cuộc gọi, cảm xúc
- **Cách làm:** một icon nhỏ (huy hiệu hạng, icon kỹ năng hình thoi, biểu tượng điện thoại, emoji) lơ lửng trên đầu nhân vật, đổi theo thời gian.
- **Thay cho:** màn hình lên hạng; hiệu ứng kỹ năng; cuộc gọi; cảm xúc khó diễn.
- **Điều kiện dùng:** mỗi nhân vật chỉ 1 icon tại một thời điểm; icon cần **đọc được trong 0,5 s** (đủ lớn, tương phản); dùng khi nhân vật chính đứng yên hoặc chạy theo đường thẳng (icon bám đầu).
- **Ví dụ:** [K03 0–14 s] huy hiệu hạng đổi xanh → vàng → đỏ Huyền thoại khi Kelly chơi · [K32 2–9 s] hai icon kỹ năng (giày cánh, người chạy) trên đầu khi chạy · [K35 2,5–14,8 s] mỗi nhân vật một icon thoi (giày cánh, chạy, vòng xoắn, mặt quỷ) · [K11 0–2 s] icon cuộc gọi · [K16 ~12–16 s] huy hiệu hạng + emoji 🤐 trên đầu · [K12 0–12,5 s] 6 thanh dọc emoji trên đầu đầy dần.
- **Với video AI:** ghi icon ở khâu hậu kỳ; trong prompt cảnh KHÔNG yêu cầu model vẽ icon.
- **Độ tin:** có thể (6 clip).

### 4. Thẻ giao diện game "dán" lên cảnh đời thường
- **Cách làm:** thẻ UI thật (TEAM INVITE: Kelly, BR-RANKED Random Map – Squad, nút Reject/Accept; thẻ SUPER REVIVAL; hòm loot đầu lâu + icon vật phẩm; thẻ vũ khí M1887) hiện như vật thể trong không khí cạnh nhân vật.
- **Thay cho:** cảnh "mở menu / nhận lời mời / nhặt đồ" trong game.
- **Điều kiện dùng:** có ảnh giao diện chính thức (đúng phiên bản); thẻ ngắn (0,5–3 s) và đứng yên khi nhân vật đứng yên.
- **Ví dụ:** [K17 0–2,5 s] TEAM INVITE · [K04 ~28–40 s] TEAM INVITE + huy hiệu · [K20 ~0–2 s] TEAM INVITE · [K34 ~5–8 s] hòm loot bay lên góc trái với icon Gloo Wall, áo giáp, M1887 · [K18 ~16–18 s] thẻ M1887 trên đầu Kelly khi đọc giấy.
- **Với video AI:** cần tư liệu giao diện chính thức; không có thì làm thẻ giản lược và ghi rõ "thẻ giản lược".
- **Độ tin:** có thể (5 clip).

### 5. Đồ hoạ trend phủ lên mặt cận (ống ngắm, thanh tuổi, cột hạng, sprite STOP, nhãn + gem)
- **Cách làm:** MỘT shot cận mặt Kelly 5–12 s; toàn bộ "trò chơi" nằm ở lớp đồ hoạ chồng lên (ống ngắm chữ thập + thanh Shooting Age Test + hộp đạn đầu lâu rơi + thẻ kết quả; cột 5 huy hiệu hạng + sao vàng chạy; sprite pixel + chữ STOP; danh sách Dad/Friends/Teammates/Fans + khối gem; khối gỗ DO-RE-MI).
- **Thay cho:** thử thách / mini-game / bắn súng / chọn hạng.
- **Điều kiện dùng:** khuôn mặt giữ ổn định cả clip (không đổi góc mạnh); đồ hoạ làm hậu kỳ theo nhịp nhạc; hợp với clip ≤ 12 s.
- **Ví dụ:** [K27 0–7,8 s] ống ngắm + thanh tuổi → AGE 25 ABOVE AVERAGE · [K40 0–8,4 s] "My rank" + cột huy hiệu + sao · [K15 0–5 s] sprite + STOP · [K31 0–10 s] 4 nhãn + 4 gem · [K05 0–12,5 s] khối gỗ nốt nhạc + tim + thanh năng lượng · [K12 0–12,5 s] 6 thanh emoji.
- **Với video AI:** đây là định dạng dễ dựng nhất (1 shot, 1 nhân vật, 1 nền): chi phí gen thấp, rủi ro nhất quán thấp.
- **Độ tin:** có thể (6 clip).

### 6. Cận điện thoại thật khi buộc phải cho thấy "màn hình game"
- **Cách làm:** chèn 1–3 s cận một chiếc điện thoại THẬT (người thật cầm hoặc đặt trên bàn) có màn hình gameplay / lobby / BOOYAH / CONGRATULATIONS, giữa các cảnh 3D.
- **Thay cho:** dựng lại giao diện game bằng 3D.
- **Điều kiện dùng:** cần clip quay màn hình thật hoặc ảnh chụp màn hình; **kênh làm bằng quay thật** → pipeline hiện KHÔNG làm được trực tiếp (không có footage). Tư liệu gameplay chỉ để AI hiểu, không ghép (`decision_gameplay_refs_reference_only`).
- **Ví dụ:** [K09 ~4,4–17,2 s] 7 cận điện thoại dính nước: lobby, concert, gameplay, BOOYAH/CONGRATULATIONS, nhận thưởng · [K10 1,1–7,1 s] điện thoại cầm ngang, bút vẽ lên màn hình, VICTORY · [K28 ~22–25,7 s] HUD 48/200 + BOOYAH · [K37 1,7–3,1 s] app nhạc phát BULLETPROOF · [K39 ~3,9–4,9 s] cửa hàng game trong tay.
- **Với video AI:** thay bằng mục 1–5; chỉ dùng khi người dùng cung cấp footage và đồng ý (không tự quay/ghép).
- **Độ tin:** có thể (5 clip) — nhưng **ngoài khả năng pipeline**.

### 7. Insert cận vật nhỏ nhìn từ trên xuống (đĩa, tay, điện thoại, nồi)
- **Cách làm:** chèn 0,5–1,5 s cận từ trên xuống một vật + bàn tay; không cần thấy mặt.
- **Thay cho:** cảnh hành động có nhiều nhân vật tương tác phức tạp (giành đồ ăn, đổ nước).
- **Điều kiện dùng:** vật đơn giản, nền sạch (mặt bàn gỗ, đĩa trắng); xen giữa các shot trung có nhân vật phản ứng; giữ hướng bàn tay nhất quán.
- **Ví dụ:** [K13 0–0,8; 2,8–3,7; 5,4–6,3; 10–10,5; 12,4–12,9 s] 5 insert đĩa từ trên xuống (gà, tay quệt, chai tương, hộp thức ăn pet) · [K09 1,3–2,1; 3,2–4,4 s] cốc / điện thoại dính nước · [K28 1,2–1,6; 2,1–2,6; 3,8–5,4 s] điện thoại kẹt sofa, nồi nước sôi · [K22 2,1–2,9 s] tay chỉ · [K17 ~9,3–10,2 s] flycam đường đèo.
- **Với video AI:** shot rất ngắn → clip 2–3 s; gen một lần, dùng nhiều cắt; nhớ tránh "tay thừa ngón".
- **Độ tin:** có thể (5 clip).

### 8. Phản ứng mặt cận thay cảnh hậu quả
- **Cách làm:** thay vì cho thấy điều xảy ra, cắt sang cận mặt nhân vật sốc / bịt miệng / vùi mặt vào tay / khoanh tay quay đi.
- **Thay cho:** cảnh va chạm, đổ vỡ, thất bại.
- **Điều kiện dùng:** người xem đã biết nguyên nhân (HUD, insert); phản ứng 0,5–2 s; mặt diễn rõ.
- **Ví dụ:** [K01 ~9,8–11,7 s] Shirou há hốc, Alvaro quay lại · [K13 ~10–12; 15 s] Alvaro ôm đầu, Kelly bịt miệng · [K22 5,8–10,3; 13,4–14,6 s] Kelly há miệng, khoanh tay · [K39 ~15,7–18,4 s] Kelly vùi mặt vào tay · [K09 ~6,6–7,5 s] Kelly tay lên ngực · [K29 14,5–16,7 s] Maxim nhăn mặt.
- **Với video AI:** shot cận mặt là thứ model làm tốt nhất; cho biểu cảm trong `why`.
- **Độ tin:** có thể (6 clip).

### 9. Chữ cố định ở đỉnh khung làm "tiêu đề meme" cho cả clip
- **Cách làm:** một dòng chữ (Little wins in life: / My 2024 / My rank) giữ nguyên suốt clip, mọi cảnh bên dưới là ví dụ minh hoạ.
- **Thay cho:** lời dẫn / bối cảnh cần giải thích.
- **Điều kiện dùng:** chuỗi cảnh cùng một khuôn (danh sách, so sánh); chữ không che mặt.
- **Ví dụ:** [K28 0–27,4 s] "Little wins in life:" suốt 23 shot · [K12 0–12,5 s] "My 2024" · [K40 0–8,4 s] "My rank" · [K31 0–10 s] nhãn trái.
- **Với video AI:** làm bằng lớp chữ hậu kỳ; chừa phần trên khung dọc 9:16.
- **Độ tin:** có thể (4 clip).

### 10. Vật thể game lơ lửng trong cảnh đời thường (điện thoại bay, hòm loot, lựu đạn, khối gỗ)
- **Cách làm:** một vật "của trận" (điện thoại lơ lửng có chỉ báo ▼ xanh, hòm đầu lâu, lựu đạn, thẻ vũ khí) nằm giữa không khí như cái đang bị tranh giành.
- **Thay cho:** cảnh nhặt đồ / giành đồ trong trận.
- **Điều kiện dùng:** vật đơn, tương phản mạnh với nền; chuyển động của nhân vật chỉ là "với tay / vồ về phía vật".
- **Ví dụ:** [K35 1,2–2,5; 8,5–9,1 s] điện thoại lơ lửng + chỉ báo ▼ · [K34 ~5–8 s] hòm loot · [K05 2–12 s] lựu đạn bay quanh Kelly · [K18 ~16–18 s] thẻ M1887.
- **Độ tin:** có thể (4 clip).

### Mới thấy ở ≤ 2 clip (chưa đủ làm luật — chỉ ghi để thử)
- **Chia đôi màn hình:** minimap trên / người trong xe dưới [K20 ~10–18 s]; gameplay thật trên / nhân vật 3D dưới [K20 ~46–50 s]; hai cột Kelly | mèo thật [K24 0–14,2 s].
- **Bong bóng thoại chữ thay đám đông:** [K21 0–6,8 s] "I want a gift!" dày dần quanh Kelly.
- **Chớp trắng chuyển sang "sự kiện":** [K37 ~3,1; ~14,3 s].
- **Poster tĩnh làm cú chốt kèm CTA:** [K21 15,9–17,4 s], [K37 14,3–17,2 s].
- **Chữ nổi cạnh đầu thay bảng điểm hậu trận:** [K23 0–6 s] (cũng đã nằm trong mục 1).

### 11. Âm thanh game / nhạc trend thay lời kể (kỹ thuật âm thanh của cùng khuôn)
- **Cách làm:** không có thoại gốc của nhân vật; nhạc trend phủ gần hết clip, **giọng thông báo / hiệu ứng game** (First Blood … Ace!, tiếng súng, chuông điện thoại) đánh dấu sự kiện thay cho cảnh.
- **Ví dụ:** [K14 0,1–5,1 s] giọng thông báo khớp bộ đếm kill · [K27 ~3,5 s] tiếng súng khi hộp đạn rơi · [K34] tiếng súng/hiệu ứng (AudioSet) · [K02 0–8 s] chuông/beep điện thoại · số đo chung: 38/40 clip nhạc ≥ 90 % thời lượng; 32/40 whisper nghe ra "lời" nhưng gần như toàn là lời hát nhạc trend; thoại gốc rất hiếm (chỉ thấy "What?" ở [K02 16,9–18,9 s]).
- **Điều kiện dùng:** có nguồn nhạc / hiệu ứng được phép dùng (bản quyền); khớp hiệu ứng vào đúng khung của HUD.
- **Độ tin:** có thể (nghe bằng số, chưa nghe tai).

---

## Điều kiện chung khi nạp vào prompt (đề xuất, chờ người dùng duyệt)
1. Chỉ nạp qua cờ riêng, TẮT mặc định; Biên kịch + Đạo diễn đọc, **không** thành bước bắt buộc.
2. Mục 6 (cận điện thoại thật) KHÔNG nạp cho Biên kịch (pipeline không có footage); chỉ ghi "ngoài khả năng".
3. Mỗi kỹ thuật đi kèm chỉ dẫn "làm ở khâu nào" (hậu kỳ / nền / nhân vật) để Đạo diễn không bắt model vẽ HUD.
4. Không ghép / dùng lại hình của kênh (`docs/KE_HOACH_PHAN_TICH_KENH_KELLY_2026-10-05.md` mục 6).
