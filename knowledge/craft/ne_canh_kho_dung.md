# Kỹ thuật né cảnh không dựng được (S14.32, 05/10/2026)

> **Nguồn:** 40 clip kênh TikTok `@freefire_kelly_official` (Kelly 3D, gần như toàn bộ dựng ngoài đời, không quay màn hình game). Mã K01–K40 theo `data/ref_kelly/list.tsv`; bảng đầy đủ ở `research/kelly_official/phieu_40_clip.md`.
> **Địa vị:** tư liệu cho Biên kịch / Đạo diễn / Quay phim / Dựng. **CHƯA nạp vào prompt nào** (code chưa đọc file này; khi nạp phải qua cờ, TẮT mặc định — như S14.20). Đọc `README.md` (4 nguyên tắc) trước.
> **Đợt 2 (S14.33, 05/10/2026):** thêm 40 clip (mã **E01–E40**, phiếu `research/kelly_official/phieu_dot2_40_clip.md`; mục 12–20 bên dưới). Người dùng nhắc mục đích: mở rộng phong cách làm + dựng và mở rộng Kho tài nguyên FF dùng lại được; mọi mục ở đây chỉ là **GỢI Ý** viết theo kiểu "có thể / khi nào hợp / điều kiện" — không phải cấm hay bắt buộc; Biên kịch / Đạo diễn được trộn, đổi hoặc bỏ.
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

### 12. Huy hiệu hạng / icon trạng thái đổi theo hành động (mở rộng mục 3 — Đợt 2)
- **Có thể dùng khi:** muốn kể "lên hạng / xuống hạng / đang ở trạng thái gì" mà không dựng màn hình. Huy hiệu hoặc cờ hạng lơ lửng trên đầu, đổi đúng lúc nhân vật làm gì đó.
- **Hợp khi:** nhân vật đứng yên hoặc đi chậm; icon đủ lớn đọc trong ~0,5 s; có ảnh huy hiệu rõ nét (đã có mẫu ở Kho, trạng thái CHỜ DUYỆT: "HUD huy hiệu hạng (kênh Kelly)").
- **Ví dụ:** [E14 0–13 s] mỗi người một huy hiệu (bạc → Huyền thoại → Grandmaster) đổi khi đứng cạnh / ôm · [E15 0–5 s] huy hiệu đổi theo món bị cắt (donut → trứng → dứa) · [E17 0–13 s] cờ hạng xanh rồi vàng trên Kelly / Hayato · [E19 ~6–10 s] Grandmaster 3 sao trên mũ Maxim → cờ hạng · [E18 0–5 s] huy hiệu + thẻ số năm lật.
- **Độ tin:** có thể (5 clip, 1 kênh).

### 13. Tỉ số / bộ đếm / dải DEFEAT đặt cạnh đầu hoặc đỉnh khung thay bảng hậu trận (mở rộng mục 1–2)
- **Có thể dùng khi:** cần cho người xem biết thắng / thua / số mạng mà không cần cảnh trận. Số lớn trắng viền tối (0:1 → 6:6 → 102:6), dải trắng DEFEAT, bảng đội 3 hàng xanh–cam (Objective, 00:10), bộ đếm kill đầu lâu + số, ô vũ khí + đếm đạn.
- **Hợp khi:** nhân vật chỉ cần nhìn điện thoại + diễn mặt; đồ hoạ làm hậu kỳ, đổi số theo nhịp nhạc; chừa khoảng trống phía trên đầu hoặc góc trên.
- **Ví dụ:** [E38 0–13 s] DEFEAT + tỉ số 0:1 / 0:6 / 6:6 / 102:6 đè trên đầu · [E40 0–7,5 s] bảng 3 hàng đội đổi 1,2,3 → 3,3,3 · [E12 0–12 s] kill đầu lâu 1,2,3,9,5,15,25 + ô vũ khí M14 / sniper 5/30 / katana / nắm đấm trên từng nhân vật · [E07 0–12 s] đếm đạn 36 → 20 → 4 → 42 "Reload" cho nhân vật nhìn ĐT · [E01 0–12 s] chip số đội + tên + thanh máu + đầu lâu, thẻ REVIVAL 400 / SUPER REVIVAL 600.
- **Độ tin:** có thể (5 clip).

### 14. Quảng bá collab / sự kiện = logo cố định + nhân vật 2D ghép vào cảnh 3D + thẻ kết
- **Có thể dùng khi:** làm nội dung có đối tác (anime, sự kiện). Logo "FREE FIRE × [IP]" cố định góc trên trái + dòng bản quyền nhỏ đáy khung suốt clip; nhân vật anime 2D đứng chung khung với nhân vật 3D FF (Kelly "ngạc nhiên"); chốt bằng thẻ tiêu đề / poster.
- **Hợp khi:** có asset chính thức của đối tác (logo, nhân vật) và được phép dùng; 1 cảnh, 1–2 nhân vật 2D, nền đơn giản (thang cuốn, bàn dài, phòng tập).
- **Ví dụ:** [E21 0–17 s] FF × GINTAMA, 2D (Kagura, Gintoki, Elizabeth) trên thang cuốn 3D, thẻ giấy cuối · [E26 0–14 s] FF × NARUTO, bàn dài + tô ramen, title card "NINE TAILS STRIKES" · [E36 0–17 s] FF × Jujutsu, máy đấm hơi + VFX năng lượng xanh, cắt sang anime 2D · [E02 0–7 s] logo FF × NARUTO + tờ "STREAM PLAN" tiết lộ tin, chốt cắt sang thanh màu test-pattern TV.
- **Độ tin:** có thể (4 clip). Lưu ý: logo / nhân vật của đối tác là tài sản bên thứ ba — chỉ dùng khi có phép riêng; ở Đợt 2 KHÔNG thu logo / hình IP vào Kho.

### 15. Xen cảnh quay màn hình / UI thật giữa các cảnh 3D (mở rộng mục 6)
- **Có thể dùng khi:** cần cho thấy chính xác giao diện game (bản đồ, lobby, phần thưởng) mà dựng lại bằng 3D sẽ sai. Chèn 1–3 s UI thật, quay lại cảnh 3D.
- **Hợp khi:** người dùng có ảnh chụp / clip màn hình chính thức (hoặc dùng ảnh UI đã thu về Kho làm tham chiếu tạo lại); UI đã được duyệt là đúng phiên bản.
- **Ví dụ:** [E32 0–6,8 s] bản đồ FF (Clock Tower, Factory, vòng bo cam, mũi tên 295 m) xen cảnh trong xe jeep 3D · [E39 0–30 s] 3 lớp dọc: Kelly ngồi ghế / gameplay thật / banner KELLY'S GIFT DROP · [E29 0–17 s] màn hình TikTok live + trang đổi mã + thẻ phần thưởng · [E16 ~5–8 s] chế độ chibi (phố nhìn từ trên) xen tiểu phẩm tiệm tóc · [E03 ~11–14 s] cận ĐT hồ sơ người chơi + huy hiệu Heroic 100.
- **Độ tin:** có thể (5 clip). Pipeline hiện chưa có footage; mẫu UI đã vào Kho ở trạng thái CHỜ DUYỆT.

### 16. Đạo cụ lớn / bất ngờ làm tâm điểm cảnh gag
- **Có thể dùng khi:** muốn gag nhanh mà ít nhân vật: một vật đơn quá khổ hoặc đột ngột xuất hiện giữa khung, nhân vật phản ứng.
- **Hợp khi:** vật đơn, nền sạch; vật làm 3D / ảnh riêng rồi ghép; nhân vật chỉ cần nhìn, chạm hoặc đẩy.
- **Ví dụ:** [E27 ~8–16 s] chồng vali nhiều màu cao ngất trên xe đẩy · [E25 ~6–9 s] bánh sinh nhật số 9 + salad xếp chữ 9 · [E26 ~5–10 s] tô ramen khổng lồ giữa bàn · [E24 ~6–9 s] túi xu vàng đầy + thùng rác vàng · [E11 0–10 s] khoai chiên rải bàn + bao lì xì F, burger · [E21 ~4–8 s] cây kem khổng lồ trong tay Kagura.
- **Độ tin:** có thể (6 clip).

### 17. Khuôn "A vs B" chia dọc + nhãn chữ ngắn
- **Có thể dùng khi:** so sánh hai kiểu người (Girl / Boy, Girls / Boys, trai gói đồ / gái gói đồ). Mỗi nửa một nhân vật cùng việc, nhãn chữ trắng ngắn ở đỉnh nửa đó.
- **Hợp khi:** hai nhân vật cùng khung dọc 9:16 xếp trên–dưới, nền gần giống nhau; clip 10–16 s.
- **Ví dụ:** [E07 0–12 s] Girl (Kelly nằm sofa) / Boy (Maxim cận mặt) cùng ô đếm đạn · [E33 0–11 s] Girls: / Boys: ghép 3D vào khán đài bóng chày thật · [E27 0–16 s] "How Boys Pack vs How Girls Pack".
- **Độ tin:** có thể (3 clip).

### 18. Cú chốt bằng glitch RGB / chớp trắng / emoji chồng lên mặt
- **Có thể dùng khi:** cần một cú chốt hoặc chuyển nhanh mà không dựng cảnh: cận mặt nhân vật, màu tách kênh RGB hoặc chớp trắng 0,3–0,6 s, emoji (😂 💀 😮 🤯) trên đỉnh khung hoặc trên đầu.
- **Hợp khi:** làm ở hậu kỳ; emoji lớn, tương phản; hợp clip ngắn có nhạc trend.
- **Ví dụ:** [E01 ~16–18 s] BOOYAH! banner + glitch · [E19 ~12–13 s] cận mặt glitch + 😂 + ngón tay suỵt · [E04 ~8–13 s] khung thành glitch + 😮 · [E17 ~12–13 s] chớp trắng cuối · [E05 0–19 s] 💀 cố định đỉnh khung · [E22 ~13–15 s] 🤯 trên đầu hai nhân vật · [E03 ~7–19 s] 💀 / 😂 trên mặt.
- **Độ tin:** có thể (7 clip).

### 19. Kelly dạng ảnh thật / photoreal + đồ hoạ (người xem khó phân biệt thật hay AI)
- **Có thể dùng khi:** muốn kể chuyện "chơi game / lên hạng" bằng chân dung gần như ảnh thật: cận mặt selfie, một nền thật (xe, cabin, bếp), đồ hoạ chồng lên (thẻ hạng lật, huy hiệu trên đầu, emoji).
- **Hợp khi:** có ảnh Kelly photoreal ổn định mặt; clip 5–19 s; ít chuyển động mạnh.
- **Ví dụ:** [E18 0–5 s] "My rank" thẻ huy hiệu + năm lật, mắt trợn · [E15 0–5 s] cắt donut / trứng / dứa, huy hiệu đổi trên đầu, mặt kéo hoạt hình · [E05 0–19 s] chân bánh xe máy bay (footage bên thứ ba) rồi Kelly trong cabin · [E31 0–14 s] Songkran Bangkok ngoài phố thật (sự kiện thật — ngoài pipeline).
- **Độ tin:** có thể (4 clip).

### 20. Gag nền hành động xa / nhân vật phụ ở xa làm chuyện khác
- **Có thể dùng khi:** muốn một shot dài (10–12 s) tĩnh mà vẫn có kịch tính: nhân vật chính ở tiền cảnh, một người khác ở xa làm chuyện hài hước.
- **Hợp khi:** máy tĩnh, nền công viên rộng, 3–4 nhân vật xếp tầng.
- **Ví dụ:** [E10 0–12,5 s] Alvaro gục đầu trên ghế, Kelly ngồi cạnh, nữ ở xa sơn ghế màu cam · [E20 0–6,9 s] pose đáng yêu trên bãi cỏ, hòm đạn đầu lâu xuất hiện, Kapella vào chung khung · [E13 0–20 s] ĐT rơi, pet chim cánh cụt đỡ, nhiều góc thấp.
- **Độ tin:** thấp (3 clip, ba gag khác nhau — chỉ để thử).

### Cập nhật mục 11 (âm thanh) sau Đợt 2
- **Giọng thông báo kill** thêm ở [E01 4,4–5,7 s "Double kill!", 10,6–11,3 s "Triple kill!"] và [E12 10,3–12,3 s "Unstoppable"] cùng [K14] → 3 clip: **có thể** dùng giọng thông báo đánh dấu số mạng khớp bộ đếm. Ba đoạn đã cắt vào Kho âm thanh (stem giọng, demucs; CHƯA nghe tai nên chưa gắn nhãn "sạch").
- **Nhạc trend:** 40/40 clip Đợt 2 có nhạc (46–100 % thời lượng; E23 46 %, E15 67 %); nhạc "to lên" thường rơi giây 3–4 hoặc 9–12. Thoại / giọng người nghe ra ở vài clip quảng bá: [E02 0,1–2,3 s "The party is starting! Next!"], [E39 0–27 s nhiều câu ngắn, có thể là tiếng stream / game], [E24 0,5–10,5 s câu bình luận ngắn] → thoại gốc VẪN có thể xuất hiện khi clip có nhiệm vụ truyền thông tin (chưa nghe tai nên chưa chắc là Kelly nói). 14 bản nhạc (nguyên mix, kèm lời hát) đã cắt vào Kho âm thanh (nguồn id clip + giây trong `data/ref_kelly/kho_am_thanh/NGUON.tsv`; người dùng xác nhận quyền dùng kênh 05/10/2026).

### Mới thấy ở ≤ 2 clip (Đợt 2, chỉ ghi để thử)
- **Thẻ chọn chế độ (Solo / Duo / BOOYAH / ngón tay chỉ) trên đầu + dấu ✓ ✗ xanh đỏ làm quiz** [E35 0–8,8 s] · **thanh màu test-pattern TV làm cú chốt "bị ngắt"** [E02 ~6–7 s] · **nhãn chữ karaoke nhảy theo lời hát** [E23 0–12 s] · **màu bàn tay đổi bằng VFX** [E06 0–11 s] · **top-down POV tay nhân vật vỗ mũ người khác + icon giày trên đầu** [E08 0–7 s] · **bộ lọc AR camera (TikTok) làm mini-game bóng trên đầu** [E37].

---

## Gợi ý chung khi nạp vào prompt (chờ người dùng duyệt)
1. **Có thể** nạp qua cờ riêng, TẮT mặc định; Biên kịch + Đạo diễn đọc như danh mục gợi ý, không thành bước bắt buộc, không cấm hướng khác.
2. Mục 6 và 15 (cận ĐT / quay màn hình thật) **có thể** để ở dạng "chỉ dùng khi người dùng cung cấp ảnh / footage UI chính thức"; nếu chưa có, có thể thay bằng mục 1–5, 12–13.
3. Mỗi kỹ thuật nên đi kèm chỉ dẫn "làm ở khâu nào" (hậu kỳ / nền / nhân vật) để Đạo diễn không bắt model vẽ HUD.
4. Hình / âm thanh của kênh: người dùng xác nhận quyền dùng (05/10/2026, Đợt 2) → **có thể** thu âm thanh + khung hình sạch vào Kho làm tham chiếu tài nguyên (CHỜ DUYỆT); vẫn không ghép nguyên cảnh của kênh vào video thành phẩm trừ khi người dùng chỉ định.
