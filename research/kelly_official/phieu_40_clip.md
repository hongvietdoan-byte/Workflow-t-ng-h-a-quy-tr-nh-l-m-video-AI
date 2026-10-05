# Phiếu 40 clip kênh @freefire_kelly_official (S14.32, 05/10/2026)

> Phiếu theo mục 4 `docs/KE_HOACH_PHAN_TICH_KENH_KELLY_2026-10-05.md`. Mã K01–K40 theo thứ tự `data/ref_kelly/list.tsv` (id, giây, view đọc ở đó; video nằm NGOÀI git). Quan sát bằng cách đọc bảng ảnh trong phiên (0 USD API); âm thanh = `tools/audio_listen.py` (đo, chưa nghe tai; lời = whisper đoán, thường là lời hát của nhạc trend). Số shot = bộ cắt tự động ngưỡng 0,30 (bỏ sót cắt khi hậu cảnh giống nhau — ghi 'cắt sót' ở nhãn). Mốc giây trong ghi chú hình ± 1 bước khung. Clip KHÔNG lỗi tải/đọc: 40/40 (không clip nào bị chặn).

### K01 · 7665285092293578005 · 11 s · 625.700 view · user · 1 shot (TB 11.7 s)
- **Định dạng:** tiểu phẩm phản ứng nhóm, 1 cú máy
- **Hook 3 s đầu:** mặt Kelly sốc + thanh máu/đầu lâu hiện ngay giây 0–2
- **Bối cảnh:** văn phòng thật (quầy gỗ vàng, tranh tường FF) — chưa có trong Kho
- **Né thứ khó dựng:** KHÔNG quay màn hình điện thoại: HUD trên đầu (ô số đội + tên + thanh máu + đầu lâu + thẻ SUPER REVIVAL + ô F 0) cho biết ai chết/ai cứu được
- **Nhân vật:** Kelly áo vàng, Alvaro tóc đỏ, Shirou hoodie — 3 người cùng cầm điện thoại, mặt diễn sốc
- **Góc máy:** trung cận, lia ngang liền qua 3 người (pan ~11 s)
- **Lớp phủ:** HUD trên đầu từng người, đổi theo thời gian
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ; 3 s nhạc to lên) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): 'Hmm'
- **Cú chốt:** Shirou há hốc nhìn vào máy, Alvaro quay lại — không CTA
- **Dựng được bằng pipeline?** ⚠ cần: nền văn phòng + 3 nhân vật cùng khung + lớp HUD hoạt hình bám đầu (hậu kỳ); lia ngang 1 cú liền khó cho model video

### K02 · 7577695624548732177 · 18 s · 51.200.000 view · top_view · 3 shot (TB 6.2 s)
- **Định dạng:** tiểu phẩm hài 2 nhân vật (51,2 triệu view)
- **Hook 3 s đầu:** Maxim khoe điện thoại có ảnh mình 0–1,3 s
- **Bối cảnh:** phòng họp có bảng trắng + bản đồ map FF dán tường — chưa có trong Kho
- **Né thứ khó dựng:** màn hình điện thoại chỉ là màn khoá (đồng hồ 9:35) với đường vẽ mở khoá chồng lên — không cần gameplay
- **Nhân vật:** Maxim mũ lưỡi trai tóc bạc, Kelly áo vàng
- **Góc máy:** trung, đẩy vào số hoá tới cận màn hình điện thoại (1,3–15,7 s)
- **Lớp phủ:** đường vẽ trắng trên màn khoá, quả cầu năng lượng xanh trên mũ Maxim (VFX)
- **Âm thanh:** nhạc 89 % thời lượng (0 s nhạc rõ; 16 s nhạc to lên) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): 'What?' · tiếng chuông/beep điện thoại 0–8 s, nhạc to lên ở 16 s; lời thoại thật duy nhất 'What?' 16,9–18,9 s
- **Cú chốt:** Maxim ôm đầu 'quá tải' (VFX)
- **Dựng được bằng pipeline?** ✅ dựng được nếu có nền phòng họp + 2 nhân vật; đường vẽ + VFX làm hậu kỳ

### K03 · 7175123026009214210 · 14 s · 31.400.000 view · top_view · 1 shot (TB 14.1 s)
- **Định dạng:** trend nhạc, 1 take selfie
- **Hook 3 s đầu:** Kelly đập nắm tay vào máy ngay giây 0
- **Bối cảnh:** phòng họp tường xám có sọc đỏ + bảng trắng — chưa có
- **Né thứ khó dựng:** trạng thái rank thể hiện bằng huy hiệu hạng lơ lửng trên đầu (xanh→vàng→đỏ Huyền thoại), không cần màn hình
- **Nhân vật:** Kelly áo vàng; nhân vật tai mèo ngồi hậu cảnh
- **Góc máy:** cận gần như selfie, máy tĩnh 14 s
- **Lớp phủ:** huy hiệu hạng trên đầu
- **Âm thanh:** nhạc 93 % thời lượng (0 s nhạc rõ; 14 s nhạc nhỏ (nền dưới thoại)) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): 'Now somebody anybody everybody scream that girl's got some s'
- **Cú chốt:** đạt hạng cao nhất + Kelly nhìn điện thoại
- **Dựng được bằng pipeline?** ✅ 1 shot cận + huy hiệu overlay; ⚠ lời hát khớp môi theo bài trend

### K04 · 7384704039272860929 · 60 s · 30.300.000 view · top_view · 9 shot (TB 6.7 s)
- **Định dạng:** tiểu phẩm gia đình dài 60 s nhiều cảnh nhà (phản hồi 'câu chuyện nửa năm')
- **Hook 3 s đầu:** Kelly ngủ trong phòng tối, người đàn ông râu mở cửa
- **Bối cảnh:** phòng ngủ, ban công, phòng giặt ven biển, bàn tròn — 4 bối cảnh nhà ở, chưa có trong Kho
- **Né thứ khó dựng:** thẻ TEAM INVITE (Reject/Accept) và huy hiệu Huyền thoại trên đầu thay màn hình điện thoại khi hai người rủ nhau chơi
- **Nhân vật:** Kelly, người đàn ông râu (vest da), nam tóc buộc vệt xám, pet thỏ hồng
- **Góc máy:** trung/trung toàn, máy tĩnh theo cảnh
- **Lớp phủ:** thẻ mời đội, huy hiệu hạng
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): 'I'll give you love, give you my love, everything'
- **Cú chốt:** pet thỏ hồng lộ ra từ máy giặt (gag)
- **Dựng được bằng pipeline?** ⚠ dài 60 s, 4 bối cảnh nhà; bộ cắt tự động bỏ sót cắt (hậu cảnh giống) — dùng làm tham khảo hơn là mẫu

### K05 · 7427399185474882824 · 12 s · 25.100.000 view · top_view · 1 shot (TB 12.5 s)
- **Định dạng:** thử thách chơi nhạc 'Perfect Pitch' (đồ hoạ trên cảnh 3D)
- **Hook 3 s đầu:** Kelly nói vào máy + khối gỗ DO trồi lên
- **Bối cảnh:** phòng sưu tập kệ đồ chơi + đường đua thu nhỏ (cảnh 3D tổng hợp)
- **Né thứ khó dựng:** thử thách game thể hiện bằng đồ vật 3D chồng lên cảnh (khối gỗ nốt nhạc, lựu đạn, tim), không dùng màn hình
- **Nhân vật:** Kelly áo vàng, nhân vật mũ nồi tóc bạc hồng ngồi sau bấm điện thoại
- **Góc máy:** cận, máy tĩnh 12,5 s
- **Lớp phủ:** 3 tim góc phải, thanh năng lượng cầu vồng, khối chữ DO-RE-MI
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ; 4 s nhạc to lên) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): 'ता दार'
- **Cú chốt:** Kelly chơi hết bài
- **Dựng được bằng pipeline?** ⚠ cần đồ hoạ 3D + vật lý; nhân vật nói chuyện — khớp môi

### K06 · 7188083246863895809 · 9 s · 23.000.000 view · top_view · 2 shot (TB 4.8 s)
- **Định dạng:** tiểu phẩm 'nấu ăn' 2 shot
- **Hook 3 s đầu:** Kelly cầm chảo tay kia cầm bánh
- **Bối cảnh:** bếp hiện đại trắng — chưa có
- **Né thứ khó dựng:** 'chơi game' thể hiện bằng người đàn ông vừa nhìn điện thoại (không thấy màn hình) vừa lật bánh nhờ tay phát sáng
- **Nhân vật:** Kelly, người đàn ông râu vest da
- **Góc máy:** trung, máy tĩnh
- **Lớp phủ:** hiệu ứng tay phát sáng cam
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ; 4 s nhạc to lên) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): 'nobody until this ends'
- **Cú chốt:** Kelly bịt miệng nhìn
- **Dựng được bằng pipeline?** ✅ 2 shot tĩnh, nền bếp + 2 nhân vật; hiệu ứng tay hậu kỳ

### K07 · 7327610270883335425 · 63 s · 20.900.000 view · top_view · 30 shot (TB 2.1 s)
- **Định dạng:** tổng kết cuối năm (ghép lại ~30 cảnh cũ)
- **Hook 3 s đầu:** Kelly nói vào máy 'năm vừa rồi'
- **Bối cảnh:** nhiều (bếp, công viên, đường chạy, tivi bản đồ, bụi cây, bàn tiệc)
- **Né thứ khó dựng:** cảnh game: điện thoại thật cầm tay (mua đồ GLOO WALL), thẻ M1887/Xm8 lơ lửng, icon kỹ năng chạy trên đầu
- **Nhân vật:** Kelly + Maxim + nhân vật phụ
- **Góc máy:** đủ cỡ
- **Lớp phủ:** câu hỏi bình chọn 'Which weapon is your favorite?' + 2 thẻ vũ khí
- **Âm thanh:** nhạc 98 % thời lượng (1 s nhạc rõ) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): 'We're going on vacation so where do you wanna go?'
- **Cú chốt:** câu hỏi bình chọn
- **Dựng được bằng pipeline?** ⚠ làm lại từ clip cũ — mẫu cho chữ bình chọn, không phải kịch bản mới

### K08 · 7504969037672221953 · 64 s · 17.800.000 view · top_view · 30 shot (TB 2.2 s)
- **Định dạng:** tổng kết 2025 (ghép lại cảnh cũ)
- **Hook 3 s đầu:** cảnh nhỏ nhanh
- **Bối cảnh:** nhiều
- **Né thứ khó dựng:** thanh máu xanh/đỏ trên đầu 2 người vật tay + icon chibi; chữ 'Dad:' 'Bro:' trên đầu
- **Nhân vật:** Kelly + Maxim + Hayato + người nhà
- **Góc máy:** đa dạng
- **Lớp phủ:** thanh máu đối kháng, nhãn vai
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): '...'
- **Cú chốt:** ghép hết
- **Dựng được bằng pipeline?** ⚠ tổng kết; tham khảo nhãn vai trên đầu

### K09 · 7195895961212751105 · 20 s · 15.300.000 view · top_view · 15 shot (TB 1.4 s)
- **Định dạng:** tiểu phẩm 'đổ cốc' hài + quảng bá điện thoại/skin (15 shot)
- **Hook 3 s đầu:** Kelly đọc giấy, tay chạm cốc nước cạnh điện thoại — người xem biết sắp đổ
- **Bối cảnh:** phòng họp tường xám sọc đỏ + bàn trắng — chưa có
- **Né thứ khó dựng:** CẬN ĐIỆN THOẠI THẬT dính nước: màn hình điện thoại nghiêng cho thấy gameplay/lobby/BOOYAH thật (tư liệu quay màn hình thật), Kelly chỉ phản ứng
- **Nhân vật:** Kelly, chim cánh cụt kính đen (pet)
- **Góc máy:** trung + cận từ trên xuống, tĩnh
- **Lớp phủ:** CONGRATULATIONS/BOOYAH là hình trong game
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): 'No one to hear my praise!'
- **Cú chốt:** pet + Kelly với điện thoại sáng
- **Dựng được bằng pipeline?** ⚠ cần quay màn hình game thật (hoặc đoạn gameplay) + cảnh điện thoại 3D vật thật; không nằm trong khả năng hiện tại

### K10 · 7499044092920302865 · 8 s · 14.900.000 view · top_view · 3 shot (TB 2.8 s)
- **Định dạng:** demo công nghệ 8 s: 3D + người thật quay điện thoại
- **Hook 3 s đầu:** Kelly 3D cầm bút nói với máy
- **Bối cảnh:** bàn gỗ, nền cam ấm (cận người thật)
- **Né thứ khó dựng:** gameplay quay trên điện thoại thật cầm ngang trong tay người thật; bút vẽ lên màn hình
- **Nhân vật:** Kelly 3D bookend
- **Góc máy:** cận → cận điện thoại từ trên → cận Kelly
- **Lớp phủ:** không
- **Âm thanh:** nhạc 67 % thời lượng (0 s nhạc rõ; 4 s nhạc nhỏ (nền dưới thoại); 6 s không nhạc) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): 'Technologia. Technologia. Technologia.' · mẫu nhạc 'Technologia' lặp, nhạc tắt từ 6 s (khoảng lặng trước cú chốt)
- **Cú chốt:** Kelly mỉm cười nhìn máy
- **Dựng được bằng pipeline?** ⚠ cần cảnh quay điện thoại thật (live-action) — ngoài pipeline

### K11 · 7450439544345840904 · 14 s · 13.000.000 view · top_view · 4 shot (TB 3.7 s)
- **Định dạng:** tiểu phẩm 'bỏ rơi đồng đội' công viên
- **Hook 3 s đầu:** icon cuộc gọi xanh lá trên đầu Maxim ngay giây 0
- **Bối cảnh:** công viên cỏ + ghế đá (cảnh 3D photoreal) — chưa có
- **Né thứ khó dựng:** cuộc gọi = icon điện thoại trên đầu; thua trận = HUD '2 Kelly' máu đỏ + chữ DEFEAT ngang đầu; Maxim bỏ đi nghe điện thoại
- **Nhân vật:** Maxim mũ lưỡi trai, Kelly áo vàng
- **Góc máy:** trung toàn tĩnh → cận → qua vai thấy Kelly ngồi xa
- **Lớp phủ:** HUD, icon, chữ DEFEAT
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ) · không có lời
- **Cú chốt:** Kelly cô đơn ngồi xa (không CTA)
- **Dựng được bằng pipeline?** ✅ 4 shot, nền công viên + 2 nhân vật; HUD hậu kỳ

### K12 · 7329471098037292290 · 12 s · 12.400.000 view · top_view · 1 shot (TB 12.5 s)
- **Định dạng:** trend 'My 2024' (6 thanh emoji đầy dần)
- **Hook 3 s đầu:** 6 thanh dọc phía trên đầu Kelly + chữ 'My 2024'
- **Bối cảnh:** tường nhà thật trung tính
- **Né thứ khó dựng:** mọi thành tích năm (tình yêu, học hành, hạng…) thể hiện bằng thanh emoji, không cần cảnh game
- **Nhân vật:** Kelly cận trực diện
- **Góc máy:** cận, tĩnh 12,5 s
- **Lớp phủ:** 6 thanh + emoji + chữ
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): 'And it's just no turning back'
- **Cú chốt:** Kelly áp tay lên má reo
- **Dựng được bằng pipeline?** ✅ rất dễ: 1 shot cận + lớp thanh hoạt hình hậu kỳ (khó nhất: khớp lời)

### K13 · 7554361593941773585 · 15 s · 11.800.000 view · top_view · 16 shot (TB 1.0 s)
- **Định dạng:** tiểu phẩm 'bạn ăn hết' canteen (16 shot, cắt ~1 s)
- **Hook 3 s đầu:** đĩa gà từ trên xuống nhiều tay giành 0–0,8 s
- **Bối cảnh:** căng tin (bàn gỗ, ghế xanh, quầy buffet) — chưa có
- **Né thứ khó dựng:** không có game; gag đồ ăn bằng cận đĩa từ trên xuống (insert tay) + phản ứng mặt
- **Nhân vật:** Kelly, Maxim, Alvaro, pet cánh cụt
- **Góc máy:** trung tĩnh + cận đĩa overhead
- **Lớp phủ:** không
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ; 5 s nhạc to lên; 8 s nhạc to lên) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): 'Dame un dr.'
- **Cú chốt:** Maxim ôm pet, Kelly bịt miệng
- **Dựng được bằng pipeline?** ⚠ 16 shot ngắn, cần đồ ăn 3D + đĩa; nhân vật ≥ 3 cùng khung

### K14 · 7265993607599918338 · 12 s · 11.700.000 view · top_view · 2 shot (TB 6.5 s)
- **Định dạng:** tiểu phẩm 'Ace/quadra' (bảng kill chồng lên khung)
- **Hook 3 s đầu:** bảng đội 4 dòng + X1💀 hiện ngay giây 0
- **Bối cảnh:** bàn tròn đen + tường xám — chưa có
- **Né thứ khó dựng:** quadra thể hiện bằng bảng đội 4 dòng (3 đầu lâu) + bộ đếm X1→X4 trên dòng 'Me'; nhân vật chỉ cầm điện thoại
- **Nhân vật:** nam tóc buộc vệt xám (giáp đỏ), Kelly chắp tay cầu nguyện
- **Góc máy:** trung tĩnh → cận Kelly → cận nam uống sữa
- **Lớp phủ:** bảng đội + bộ đếm kill
- **Âm thanh:** nhạc 92 % thời lượng (0 s nhạc rõ; 8 s nhạc nhỏ (nền dưới thoại)) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): 'First Blood, Double Kill, Triple Kill, Ace!' · giọng thông báo game 'First Blood, Double Kill, Triple Kill, Ace!' 0,1–5,1 s khớp bộ đếm X1→X4 (hiệu ứng game thay thoại)
- **Cú chốt:** nam uống chai sữa (gag 'nhàn')
- **Dựng được bằng pipeline?** ✅ 2–3 shot + overlay bảng kill (rất dễ)

### K15 · 7472277460961201416 · 5 s · 11.400.000 view · top_view · 2 shot (TB 2.5 s)
- **Định dạng:** thử thách 'STOP' 5 s
- **Hook 3 s đầu:** Kelly cận cúi nhìn điện thoại, sprite STOP đã chạy
- **Bối cảnh:** phòng sáng nền mờ
- **Né thứ khó dựng:** thử thách = hai sprite pixel chạy chồng nhau + chữ STOP, không thấy màn hình
- **Nhân vật:** Kelly cận
- **Góc máy:** cận tĩnh
- **Lớp phủ:** sprite + chữ STOP
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ; 3 s nhạc to lên) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): 'When the rhythm starts to play, dance with me'
- **Cú chốt:** Kelly nhìn máy
- **Dựng được bằng pipeline?** ✅ rất dễ: 1–2 shot + overlay

### K16 · 7428879280442068231 · 64 s · 10.400.000 view · top_view · 34 shot (TB 1.9 s)
- **Định dạng:** tổng kết 2024 (ghép cảnh cũ)
- **Hook 3 s đầu:** cận pin 1%, cảnh nhanh
- **Bối cảnh:** nhiều
- **Né thứ khó dựng:** phần trăm (4:4, 50 %, 5 %) và huy hiệu/emoji trên đầu thay màn hình
- **Nhân vật:** Kelly, Maxim, Tatsuya
- **Góc máy:** nhiều
- **Lớp phủ:** điểm số, %, huy hiệu, emoji 🤐
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): 'Shawty's like a melody in the morning that I can't keep out '
- **Cú chốt:** Kelly + cả nhóm
- **Dựng được bằng pipeline?** ⚠ tổng kết

### K17 · 7408843915429678337 · 16 s · 10.300.000 view · top_view · 12 shot (TB 1.4 s)
- **Định dạng:** tiểu phẩm 'Tatsuya chạy nhanh' (12 shot ~1,4 s)
- **Hook 3 s đầu:** thẻ TEAM INVITE + cận pin 1% trong 4 s đầu
- **Bối cảnh:** phòng chờ hồng (ghế dài) + cảnh đường ngoài trời stock thật (flycam đường đèo) — chưa có
- **Né thứ khó dựng:** mời chơi = thẻ TEAM INVITE; sắp hết pin = cận 1%; chạy nhanh = nhoè chuyển động + icon kỹ năng + cảnh stock thật
- **Nhân vật:** Kelly, Tatsuya áo đỏ-trắng, Maxim
- **Góc máy:** cắt nhanh trung/cận/toàn, có shot flycam
- **Lớp phủ:** thẻ mời, icon kỹ năng
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): 'Battle Royale' · nhạc điện tử + tiếng 'Battle Royale' 5–14 s (giọng thông báo/mẫu)
- **Cú chốt:** ba người ngồi lại ghế dài
- **Dựng được bằng pipeline?** ⚠ cần cảnh stock đường + 3 nhân vật + nhoè chuyển động

### K18 · 7334374024476167426 · 63 s · 10.200.000 view · top_view · 33 shot (TB 1.9 s)
- **Định dạng:** tổng kết 2 năm (ghép cảnh cũ)
- **Hook 3 s đầu:** bảng đội + X3
- **Bối cảnh:** nhiều
- **Né thứ khó dựng:** bảng đội, thẻ súng M1887 trên đầu, bảng mic, emoji pizza, chibi trên ngực áo
- **Nhân vật:** Kelly + Maxim + Tatsuya
- **Góc máy:** đa dạng
- **Lớp phủ:** HUD các kiểu
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): '3, 4, 5, 4, 4, 5, 3...2, 1!'
- **Cú chốt:** Kelly cười
- **Dựng được bằng pipeline?** ⚠ tổng kết

### K19 · 7580318907727203601 · 64 s · 9.900.000 view · top_view · 40 shot (TB 1.6 s)
- **Định dạng:** tổng kết 2025 (ghép cảnh cũ)
- **Hook 3 s đầu:** cửa khoá điện tử + người ghi chép
- **Bối cảnh:** nhiều
- **Né thứ khó dựng:** icon bực mình bay lên đầu, thanh trên đầu
- **Nhân vật:** Kelly + Maxim + người nhà
- **Góc máy:** đa dạng
- **Lớp phủ:** icon
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): '¡Voy a dar esta, la sacudura!'
- **Cú chốt:** ghép
- **Dựng được bằng pipeline?** ⚠ tổng kết

### K20 · 7463424831275404552 · 61 s · 9.700.000 view · top_view · 26 shot (TB 2.4 s)
- **Định dạng:** tổng kết (ghép cảnh cũ, có chia đôi màn hình game/nhân vật)
- **Hook 3 s đầu:** TEAM INVITE + huy hiệu Huyền thoại
- **Bối cảnh:** nhiều, xe hơi, công viên
- **Né thứ khó dựng:** CHIA ĐÔI: minimap trên / người trong xe dưới; gameplay thật trên / nhân vật dưới; HUD tên+máu cho 2 người ngồi
- **Nhân vật:** Kelly + Maxim + Shirou + Hayato
- **Góc máy:** nhiều
- **Lớp phủ:** HUD, minimap, ô giá F 400
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): 'We little bumblebee, I know what you want from me'
- **Cú chốt:** Kelly ngồi vắt vẻo
- **Dựng được bằng pipeline?** ⚠ tổng kết; chia đôi màn hình là kỹ thuật dùng lại

### K21 · 7653014707309202706 · 17 s · 9.100.000 view · top_view · 7 shot (TB 2.5 s)
- **Định dạng:** quảng bá sự kiện 9th Anniversary (CTA)
- **Hook 3 s đầu:** bong bóng thoại 'I want a gift!' dày dần quanh Kelly 0–6,8 s
- **Bối cảnh:** cửa hàng quà (kệ đỏ, hộp vàng cam) 3D — chưa có
- **Né thứ khó dựng:** đám đông 'đòi quà' = bong bóng thoại chữ, không cần người đông
- **Nhân vật:** Kelly áo vàng
- **Góc máy:** trung cố định → cận tay POV → poster
- **Lớp phủ:** bong bóng thoại, LIKE & FOLLOW, poster + bảng phần thưởng
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ; 3 s nhạc to lên) · không có lời
- **Cú chốt:** poster '9TH ANNIVERSARY PARTY WITH KELLY' + ngày
- **Dựng được bằng pipeline?** ✅ khung quảng bá dễ: nền cửa hàng + 1 nhân vật + chữ; poster do đội thiết kế

### K22 · 7691960532760333589 · 17 s · 98.900 view · newest · 9 shot (TB 1.9 s)
- **Định dạng:** tiểu phẩm 'không nóng đâu Maxim' (9 shot)
- **Hook 3 s đầu:** Kelly chơi điện thoại, Maxim chỉ tay vào
- **Bối cảnh:** bếp ăn công nghiệp inox — chưa có
- **Né thứ khó dựng:** không có game; gag đồ ăn nóng + phản ứng mặt + bàn tay cận
- **Nhân vật:** Kelly, Maxim, Alvaro
- **Góc máy:** trung/trung cận tĩnh, bát ramen tiền cảnh làm khung
- **Lớp phủ:** không
- **Âm thanh:** nhạc 94 % thời lượng (0 s nhạc rõ; 9 s nhạc to lên; 12 s nhạc to lên) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): 'So I'm looping it'
- **Cú chốt:** hai người đứng cạnh nhau
- **Dựng được bằng pipeline?** ⚠ 3 nhân vật cùng khung, nền bếp + đồ ăn

### K23 · 7691958368008670485 · 10 s · 331.100 view · newest · 5 shot (TB 2.2 s)
- **Định dạng:** tiểu phẩm 'đội bảo vệ' (10,9 s)
- **Hook 3 s đầu:** chữ 'Damage:179 Kill:14' trên Kelly vs 'Damage:6553 Kill:0' trên băng nhóm
- **Bối cảnh:** phố mưa (cảnh thật + 3D) — chưa có
- **Né thứ khó dựng:** so sánh thành tích kiểu hậu trận bằng chữ nổi cạnh đầu, không cần vào trận
- **Nhân vật:** Kelly + băng nhóm (mặt hề xanh, đầu lâu, Hayato) + đội hình 8–9 nhân vật + ngựa + pet
- **Góc máy:** toàn rộng tới cận; cánh tay vươn vào ống kính
- **Lớp phủ:** chữ chỉ số vàng/đỏ, emoji 😂
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ; 6 s nhạc to lên) · không có lời
- **Cú chốt:** đội hình bảo vệ + emoji
- **Dựng được bằng pipeline?** ⚠ cần đội hình nhiều nhân vật (8–9) cùng khung

### K24 · 7690585823615487253 · 14 s · 43.400 view · newest · 4 shot (TB 3.6 s)
- **Định dạng:** trend meme mèo, chia đôi cột
- **Hook 3 s đầu:** Kelly chu môi bên trái, mèo đen thật bên phải
- **Bối cảnh:** nền thật mờ
- **Né thứ khó dựng:** không có game; bắt chước nét mặt
- **Nhân vật:** Kelly, Maxim
- **Góc máy:** cận mặt, tĩnh
- **Lớp phủ:** bố cục 2 cột
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): 'ifier'
- **Cú chốt:** Maxim bắt chước mèo
- **Dựng được bằng pipeline?** ⚠ dùng video mèo thật bên thứ ba — bản quyền; 3D nét mặt cần điều khiển biểu cảm

### K25 · 7690799953974676756 · 19 s · 11.600 view · newest · 6 shot (TB 3.2 s)
- **Định dạng:** hợp tác người thật + Kelly 3D (POV bestfriend)
- **Hook 3 s đầu:** người thật và Kelly cùng chắp tay
- **Bối cảnh:** phòng sống thật, phòng thi đấu eSports
- **Né thứ khó dựng:** không
- **Nhân vật:** người thật + Kelly
- **Góc máy:** trung → selfie
- **Lớp phủ:** khung ngắm camera
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ) · không có lời
- **Cú chốt:** uống nước cùng
- **Dựng được bằng pipeline?** ❌ ngoài pipeline: ghép người thật quay thật

### K26 · 7689306563324022036 · 26 s · 114.700 view · newest · 23 shot (TB 1.2 s)
- **Định dạng:** tiểu phẩm 'lấy lại bóng' (23 shot, nhiều VFX)
- **Hook 3 s đầu:** bóng rổ kẹt cây, Kelly + Maxim nhìn lên
- **Bối cảnh:** sân trường ngoài trời (cảnh thật + nhân vật 3D)
- **Né thứ khó dựng:** không có game; gag bóng/drone/tay cầm game
- **Nhân vật:** Kelly, Maxim
- **Góc máy:** đủ cỡ, nhiều góc thấp/cao
- **Lớp phủ:** không
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc nhỏ (nền dưới thoại); 2 s nhạc rõ; 8 s nhạc to lên) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): 'I put your new fuzzies on the cheek'
- **Cú chốt:** bóng lại kẹt trên cây
- **Dựng được bằng pipeline?** ⚠ 23 shot, cần nền ngoài trời + vật thể 3D (bóng, chảo, drone)

### K27 · 7689305142444723477 · 7 s · 43.000 view · newest · 1 shot (TB 7.8 s)
- **Định dạng:** trend 'Shooting Age Test'
- **Hook 3 s đầu:** ống ngắm + thanh tuổi hiện trên mặt Kelly ngay giây 0
- **Bối cảnh:** phòng mờ
- **Né thứ khó dựng:** 'bắn' = ống ngắm chữ thập chồng lên mặt + hộp đạn đầu lâu rơi + thẻ kết quả, không cảnh gameplay
- **Nhân vật:** Kelly cận
- **Góc máy:** cận 7,8 s, cuối nghiêng/cận nằm
- **Lớp phủ:** chữ thập, thanh 35→18, thẻ AGE 25
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): 'Let's do tonight, at tonight!' · nhạc trend + tiếng súng/nổ khi hộp đạn rơi (hiệu ứng game)
- **Cú chốt:** thẻ kết quả 'ABOVE AVERAGE'
- **Dựng được bằng pipeline?** ✅ 1 shot cận + overlay (dễ)

### K28 · 7686844295956958484 · 27 s · 143.300 view · newest · 23 shot (TB 1.2 s)
- **Định dạng:** trend 'Little wins in life' (23 shot ~1,2 s)
- **Hook 3 s đầu:** chữ cố định 'Little wins in life:' + Kelly vẫy tay tìm điện thoại
- **Bối cảnh:** nhà ở (sofa, bếp, cửa) — chưa có
- **Né thứ khó dựng:** 'chiến thắng game' = cận gameplay thật BOOYAH trên điện thoại; các chiến thắng khác là vật thể 3D gọn
- **Nhân vật:** Kelly
- **Góc máy:** trung/cận nhanh
- **Lớp phủ:** chữ đỉnh khung suốt clip, HUD 48/200
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ; 11 s nhạc to lên; 16 s nhạc to lên) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): 'oh'
- **Cú chốt:** Kelly giơ tay reo
- **Dựng được bằng pipeline?** ⚠ 23 shot, cần nhiều bối cảnh nhà + cảnh game thật

### K29 · 7686780406732950805 · 17 s · 44.300 view · newest · 8 shot (TB 2.2 s)
- **Định dạng:** tiểu phẩm 'hoa hồng của Maxim' (8 shot)
- **Hook 3 s đầu:** Kelly chơi điện thoại sáng mặt vs Maxim ngậm hoa mưa
- **Bối cảnh:** phòng khách / ngoài cửa đêm — chưa có
- **Né thứ khó dựng:** không có game; hai không gian đối lập ấm/lạnh
- **Nhân vật:** Kelly, Maxim, pet cánh cụt
- **Góc máy:** cận, tĩnh
- **Lớp phủ:** VFX mưa + tim lấp lánh
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ; 15 s nhạc to lên) · không có lời
- **Cú chốt:** Maxim nhăn mặt ôm hoa
- **Dựng được bằng pipeline?** ⚠ 2 bối cảnh + VFX mưa/nước

### K30 · 7685702905357192468 · 22 s · 2.600.000 view · newest · 11 shot (TB 2.1 s)
- **Định dạng:** tiểu phẩm 'mua đá' hành động (11 shot)
- **Hook 3 s đầu:** cận Kelly đẫm mồ hôi (giây 0)
- **Bối cảnh:** siêu thị, phố, cầu thang, căn hộ — nhiều bối cảnh ngoài đời
- **Né thứ khó dựng:** không có game
- **Nhân vật:** Kelly, nữ tóc tết tím
- **Góc máy:** theo sau lưng, góc thấp, nhảy parkour
- **Lớp phủ:** khói lạnh
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ; 3 s nhạc to lên) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): 'I'll be suicide.'
- **Cú chốt:** Kelly lau mồ hôi, cười
- **Dựng được bằng pipeline?** ⚠ chuyển động mạnh (chạy, nhảy qua tường) và 4 bối cảnh — dễ lỗi

### K31 · 7684522768712420629 · 10 s · 1.200.000 view · newest · 1 shot (TB 10.0 s)
- **Định dạng:** trend 'Best love for my fans' (danh sách nhãn + gem)
- **Hook 3 s đầu:** 4 nhãn chữ bên trái + Kelly cầm khối gem
- **Bối cảnh:** văn phòng tường xám
- **Né thứ khó dựng:** 'tình yêu dành cho' = khối gem bay đến cạnh từng nhãn
- **Nhân vật:** Kelly
- **Góc máy:** trung, tĩnh 10 s
- **Lớp phủ:** 4 nhãn + 4 khối gem
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): 'I might not be the same, but that's not important.'
- **Cú chốt:** Fans nhận cuối
- **Dựng được bằng pipeline?** ✅ dễ: 1 shot trung + lớp chữ/icon

### K32 · 7289320309457456386 · 9 s · 7.000.000 view · theme:maxim · 3 shot (TB 3.1 s)
- **Định dạng:** tiểu phẩm rượt đuổi 'chạy nhanh' (3 shot)
- **Hook 3 s đầu:** Kelly và Tatsuya bò trên đường
- **Bối cảnh:** đường quê, bầu trời xanh
- **Né thứ khó dựng:** kỹ năng chạy = 2 icon hình thoi trên đầu (giày cánh + người chạy), không cần màn hình
- **Nhân vật:** Kelly, Tatsuya, Maxim, pet cánh cụt
- **Góc máy:** toàn → cận → toàn thấp bám
- **Lớp phủ:** icon kỹ năng, icon bực mình
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): 'No, no, no, no, no, baby, nothing's gonna scuttle some lies'
- **Cú chốt:** Maxim chạy với burger treo trên đầu pet
- **Dựng được bằng pipeline?** ⚠ 3 shot nhưng chạy nhanh + đuổi 4 nhân vật

### K33 · 7232234101292518658 · 8 s · 2.900.000 view · theme:squad · 2 shot (TB 4.2 s)
- **Định dạng:** tiểu phẩm 'họp chiến thuật' (2 shot)
- **Hook 3 s đầu:** Maxim + nữ mũ kính bay ghi chép ở bàn
- **Bối cảnh:** phòng chờ hồng + TV đứng chiếu bản đồ FF — chưa có
- **Né thứ khó dựng:** chiến thuật = chỉ vào bản đồ trên TV
- **Nhân vật:** Maxim, nữ mũ kính bay, Kelly, pet cánh cụt
- **Góc máy:** trung tĩnh
- **Lớp phủ:** không
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): 'I'm so sorry.'
- **Cú chốt:** pet ngồi sau laptop
- **Dựng được bằng pipeline?** ✅ nền phòng + TV bản đồ + ≤ 3 nhân vật

### K34 · 7221842644983385345 · 7 s · 1.200.000 view · theme:pov · 1 shot (TB 8.0 s)
- **Định dạng:** trend 'POV: khi đồng đội chết' (8 s, 1 shot)
- **Hook 3 s đầu:** HUD '1 Me / 2 Teammate' ngay giây 0
- **Bối cảnh:** phòng tường xám sọc
- **Né thứ khó dựng:** đồng đội chết = thanh máu rút đỏ + đầu lâu, hòm loot hiện icon vật phẩm, không cảnh chết
- **Nhân vật:** nhân vật nữ tai mèo
- **Góc máy:** cận → ngước lên
- **Lớp phủ:** HUD, hòm loot, nước mắt hài
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ) · không có lời · AudioSet gắn tiếng súng/hiệu ứng (không lời)
- **Cú chốt:** vỗ tay khóc hài
- **Dựng được bằng pipeline?** ✅ 1 shot cận + HUD hậu kỳ

### K35 · 7419580988151401736 · 14 s · 6.200.000 view · theme:meow · 9 shot (TB 1.6 s)
- **Định dạng:** tiểu phẩm 'giành điện thoại Moco' (9 shot)
- **Hook 3 s đầu:** nữ tóc tím đứng, điện thoại lơ lửng + chỉ báo ▼
- **Bối cảnh:** công viên ngoài trời — chưa có
- **Né thứ khó dựng:** mỗi nhân vật 1 icon kỹ năng trên đầu; điện thoại lơ lửng có chỉ báo = vật cần giành
- **Nhân vật:** Kelly, Tatsuya, nữ đạp xe, nữ tóc tím, mặt nạ đỏ
- **Góc máy:** cận/toàn, bám chuyển động
- **Lớp phủ:** icon kỹ năng hình thoi, chỉ báo ▼
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ; 3 s nhạc to lên; 14 s nhạc nhỏ (nền dưới thoại)) · không có lời
- **Cú chốt:** cả nhóm vồ bụi cây
- **Dựng được bằng pipeline?** ⚠ 5 nhân vật + xe đạp + chuyển động

### K36 · 7382957458920164625 · 15 s · 2.300.000 view · theme:basket · 4 shot (TB 3.8 s)
- **Định dạng:** tiểu phẩm 'ném giấy' (4 shot dài)
- **Hook 3 s đầu:** biển WC nữ rồi Kelly đi vào
- **Bối cảnh:** hành lang văn phòng, lớp học — chưa có
- **Né thứ khó dựng:** không có game
- **Nhân vật:** Kelly, nữ váy hồng, Alvaro
- **Góc máy:** toàn, trung tĩnh
- **Lớp phủ:** không
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ; 8 s nhạc to lên; 11 s nhạc to lên) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): 'Eu não via como lá'
- **Cú chốt:** Kelly khó chịu
- **Dựng được bằng pipeline?** ✅ 4 shot tĩnh

### K37 · 7608930762607332615 · 17 s · 3.700.000 view · theme:kenta · 9 shot (TB 1.9 s)
- **Định dạng:** quảng bá hợp tác nhạc ALOK 'Guess who I just met'
- **Hook 3 s đầu:** cả nhóm xem điện thoại, bài BULLETPROOF phát
- **Bối cảnh:** tường gạch + ghế dài; poster sân khấu DJ
- **Né thứ khó dựng:** nghe nhạc = cận điện thoại thật phát bài; hợp tác = ALOK xuất hiện
- **Nhân vật:** Kelly, Maxim, nữ tai mèo, ALOK (3D photoreal)
- **Góc máy:** trung tĩnh + cận điện thoại, chớp trắng
- **Lớp phủ:** chớp trắng chuyển cảnh
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): 'i'm pulling grooves, i'm pulling grooves'
- **Cú chốt:** poster DJ sân khấu
- **Dựng được bằng pipeline?** ⚠ cần nhân vật khách + poster chuẩn; cận điện thoại thật

### K38 · 7149121058619100443 · 5 s · 319.000 view · theme:dance · 1 shot (TB 5.2 s)
- **Định dạng:** trend nhảy 5 s
- **Hook 3 s đầu:** Hayato khoanh tay trên nền thu
- **Bối cảnh:** nền thu đỏ/đền (cảnh dựng)
- **Né thứ khó dựng:** không
- **Nhân vật:** Hayato
- **Góc máy:** trung cận tĩnh
- **Lớp phủ:** không
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): 'A little honey, of course. A little honey, of course.'
- **Cú chốt:** —
- **Dựng được bằng pipeline?** ✅ 1 shot rất dễ, nhưng cử động nhỏ (trend nhảy)

### K39 · 7152079580948483329 · 18 s · 1.200.000 view · theme:school · 11 shot (TB 1.7 s)
- **Định dạng:** tiểu phẩm 'lớp học' (11 shot)
- **Hook 3 s đầu:** Kelly chống cằm chán
- **Bối cảnh:** lớp học cửa sổ — chưa có
- **Né thứ khó dựng:** 'trong game' = cận điện thoại thật trên đùi; cô giáo người thật
- **Nhân vật:** Kelly + cô giáo người thật
- **Góc máy:** trung/cận tĩnh
- **Lớp phủ:** không
- **Âm thanh:** nhạc 95 % thời lượng (0 s nhạc rõ; 10 s nhạc to lên) · lời (whisper đoán, chủ yếu là lời hát nhạc trend): 'My patience is waning, is this entertaining?'
- **Cú chốt:** Kelly vùi mặt vào tay
- **Dựng được bằng pipeline?** ⚠ cần bảng công thức + giáo viên (người thật) — ngoài pipeline, đổi bằng nhân vật 3D

### K40 · 7392520376967859472 · 8 s · 4.500.000 view · theme:food · 1 shot (TB 8.4 s)
- **Định dạng:** trend 'Screenshot challenge / My rank'
- **Hook 3 s đầu:** chữ 'My rank' + cột 5 huy hiệu hạng bên trái
- **Bối cảnh:** nền mờ
- **Né thứ khó dựng:** chọn hạng = sao vàng chạy dọc cột huy hiệu
- **Nhân vật:** Kelly cận
- **Góc máy:** cận 4:5 tĩnh
- **Lớp phủ:** cột hạng + sao
- **Âm thanh:** nhạc 100 % thời lượng (0 s nhạc rõ) · không có lời
- **Cú chốt:** Kelly đổi nét mặt khi sao dừng
- **Dựng được bằng pipeline?** ✅ 1 shot cận + overlay
