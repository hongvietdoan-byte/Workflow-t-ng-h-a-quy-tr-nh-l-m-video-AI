# Phong cách: kênh chính thức Kelly (@freefire_kelly_official) — tiểu phẩm 3D ngắn trên TikTok

> **Địa vị: GỢI Ý theo phong cách**, trộn được, không bắt buộc (luật "phong cách tham khảo là gợi ý", `feedback_reference_styles_are_suggestions`). Mỗi luật có ≥ 3 clip dẫn chứng (mã K + mốc giây); không luật nào khái quát từ 1 clip. **Chưa nạp vào prompt nào.**
> **Mẫu:** 40 clip của MỘT kênh (20 view cao nhất + 10 mới nhất + 9 theo chủ đề + 1 người dùng gửi), phân tích 05/10/2026 bằng đọc bảng ảnh + `tools/audio_listen.py` (0 USD API). 33 clip ngắn (5–27 s) có nhãn từng shot; 7 clip ~60 s là clip tổng kết nên chỉ có số đo chung. Phiếu đầy đủ `research/kelly_official/phieu_40_clip.md`; nhãn shot `research/kelly_official_records/KELLY_SHOW/*.json`; ghi chú hình `research/kelly_official/ghi_chu_hinh.md`.
> **Giới hạn:** một kênh, view cao thiên về clip cũ (mẫu "view cao" lệch theo thời gian); 10 clip mới nhất có view trung vị ≈ 107 nghìn so với ≈ 13 triệu của nhóm view cao (xem luật 10) → đừng coi số đo là "công thức viral".

## Cách dựng (đặc trưng lặp lại)
1. **Clip rất ngắn, ít shot.** 33 clip ngắn: trung vị 14,3 s (5,0–27,4 s); 9/33 là MỘT cú máy liền (K01, K03, K05, K12, K27, K31, K34, K38, K40); clip nhiều shot có shot trung vị 1,5 s, chỉ ≈ 10 % shot ≥ 4 s (20/193). Clip tổng kết dài 60–65 s (K07, K08, K16, K18, K19, K20; K04 là tiểu phẩm dài 60 s).
2. **Cảnh đời thường làm bối cảnh, "game" chỉ hiện như lớp thông tin.** Nơi diễn ra: văn phòng, canteen, bếp, công viên, lớp học, phòng chờ, hành lang, sân trường (K01, K02, K09, K13, K22, K11, K39, K36, K26, K33). Map Free Fire gần như không làm bối cảnh — chỉ là vật trong phòng (bản đồ trên TV [K33 1,5–5,5 s], bản đồ dán tường [K02]). Không có cảnh đang đánh trận bằng 3D.
3. **Trạng thái trận thể hiện bằng HUD / icon / thẻ chồng lên người** (số đội + tên + thanh máu + đầu lâu [K01 0–11,7 s, K11 0–4,5 s, K34 0–8 s]; bảng đội + bộ đếm kill [K14 0–7,8 s, K18 ~0–5 s]; icon hạng / kỹ năng trên đầu [K03 0–14 s, K32 2–9 s, K35 2,5–14,8 s]). Chi tiết kỹ thuật + điều kiện: `knowledge/craft/ne_canh_kho_dung.md`.
4. **Hook bằng lớp đồ hoạ hiện ngay giây 0.** 15/33 clip ngắn có chữ hoặc HUD ngay shot đầu: K01, K03, K05, K11, K12, K14, K15, K17, K21, K23, K27, K28, K31, K34, K40. Không mở bằng lời chào / logo.
5. **Máy gần như tĩnh, chuyển cảnh bằng cắt cứng.** static 91 % shot, track 4 % (chỉ khi nhân vật chạy [K32 2–9 s, K35 2,5–9 s, K30 4–8,6 s]), handheld 2 %, whip 1 % (K17 ~6 s, K13 ~12,4 s). Ngang mắt 79 % shot; góc cao 11 % (đa số là cận vật từ trên xuống).
6. **Cỡ cảnh trung đến cận.** trung 36 %, cận 29 %, trung cận 15 %, toàn 15 %; cận mặt / vật chiếm gần nửa số shot của clip nhiều shot.
7. **Gag theo mẫu "tình huống → insert vật → phản ứng mặt".** Phản ứng chiếm 20 % shot, insert 22 %. Ví dụ: [K13 0–15,2 s] 16 shot xen insert đĩa với phản ứng Alvaro / Kelly / Maxim · [K22 2,1–14,6 s] · [K39 1,3–18,4 s]. Cú chốt thường là mặt sốc / bịt miệng / vùi mặt [K01, K13, K22, K39, K29].
8. **Chữ cố định đỉnh khung làm tiêu đề meme** cho chuỗi cảnh cùng khuôn: [K28 0–27,4 s], [K12 0–12,5 s], [K40 0–8,4 s], [K31 0–10 s].
9. **Đội diễn viên lặp lại:** Kelly (38/40 clip), Maxim (mũ lưỡi trai, tóc bạc) [K02, K11, K13, K22, K26, K29, K24], Alvaro (tóc đỏ kính đỏ) [K01, K13, K22, K36], và **chim cánh cụt kính đen (pet)** làm gag / kết [K09 17–20,5 s, K13 ~4–15 s, K32 0–9 s, K33 6,8–8,3 s, K29 9,6–14,5 s]. Trang phục: Kelly luôn áo khoác vàng (không thấy đổi skin trong 40 clip).
10. **Tổng kết cuối năm ≈ 60–65 s = ghép lại cảnh cũ** (K07, K08, K16, K18, K19, K20 — 9,7–20,9 triệu view; K04 30,3 triệu). Cần thư viện cảnh đã dựng; pipeline chưa có.
11. **Nhóm view cao so với nhóm mới nhất** (số đo, KHÔNG phải nhân quả — thời gian đăng, thuật toán, trend khác nhau): 13 clip ngắn thuộc nhóm view cao có trung vị 3 shot/clip, 10/13 có giao diện game / HUD, 8/13 có chữ-HUD ở shot đầu; 10 clip mới nhất có trung vị 7 shot/clip, 3/10 có HUD, 4/10 chữ-HUD ở shot đầu, và 1/10 là chuỗi chạy / nhảy mạnh nhiều bối cảnh [K30].
12. **CTA hiếm.** Chỉ 2/40 clip có CTA rõ: poster sự kiện [K21 15,9–17,4 s: LIKE & FOLLOW, 9TH ANNIVERSARY PARTY WITH KELLY], poster hợp tác nhạc [K37 14,3–17,2 s]. Phần còn lại kết bằng gag / phản ứng.

## Âm thanh (nghe bằng số, chưa nghe tai)
- **Nhạc trend phủ gần cả clip:** 38/40 clip có nhạc ≥ 90 % thời lượng, nhỏ nhất 67 % [K10]. 16/40 clip nhạc "to lên" một lần; ở giây 3–4 trong [K01 3 s, K05 4 s, K06 4 s, K15 3 s, K21 3 s, K30 3 s] (khả năng cao là điệp khúc của bản trend).
- **Gần như không có thoại gốc của nhân vật:** 32/40 clip whisper nghe ra "lời" nhưng hầu như là lời hát nhạc trend (tiếng Anh, Tây Ban Nha, Bồ Đào Nha, Đức…); thoại thật chỉ thấy "What?" [K02 16,9–18,9 s] và "Hmm" [K01 4,7–6,7 s]. Không có tiếng Việt.
- **Hiệu ứng / giọng thông báo game thay cho cảnh:** [K14 0,1–5,1 s] "First Blood, Double Kill, Triple Kill, Ace!" khớp bộ đếm X1→X4; [K27] tiếng súng khi hộp đạn rơi; [K34] tiếng súng / hiệu ứng; [K02 0–8 s] chuông-beep điện thoại.
- **Khoảng lặng hiếm:** chỉ [K10 6–8,4 s] nhạc tắt trước cú chốt.

## Look
Nhân vật 3D tả thực (da, tóc, vải) ghép vào cảnh ảnh thật / render photoreal; ánh sáng mềm; áo vàng của Kelly là điểm sáng. HUD là phông trắng gọn, chip số đội có màu (1 ngọc, 2 vàng, 3 hồng, 4 tím), thanh máu mảnh; chữ trắng viền tối. Một số clip mới (K30, K26, K25) có chuyển động mạnh và mặt thay đổi nhẹ giữa shot (nhìn như video AI sinh).

## Khi dùng cho AI video (gợi ý)
- **Dễ nhất, nên thử đầu tiên:** 1 shot cận + lớp đồ hoạ trend (mục 5 trong `ne_canh_kho_dung.md`): K12, K27, K15, K40, K31, K34, K05.
- **Tiểu phẩm 2–4 shot tĩnh, 1–2 nhân vật, 1 nền đời thường + HUD** (K01, K06, K11, K14, K33, K36): thiếu nhất là nền đời thường nhất quán và lớp HUD hoạt hình.
- **Khó với khả năng hiện tại (gợi ý: có thể làm nếu người dùng cung cấp tài nguyên / footage):** hợp tác người thật [K25], giáo viên người thật [K39], cận điện thoại thật [K09, K10, K28], tổng kết ghép cảnh cũ [K07…], chuyển động mạnh nhiều nền [K30, K26], video bên thứ ba [K24 mèo thật, K17 flycam stock].
- Giao diện / HUD làm ở hậu kỳ, không bắt model video vẽ (khớp `INGAME.md`).

> Các con số dưới đây là **khoảng tham khảo** đo từ video Free Fire thật, không phải nhịp cố định: độ dài từng shot do kịch bản quyết định.

## Số liệu (Kelly TikTok — 33 clip ngắn có nhãn shot; bộ cắt tự động bỏ sót cắt khi hậu cảnh giống nhau nên số shot là cận dưới)
- **33 video, 202 shot, 468 s** · video dài trung vị 14 s · **26 shot/phút**
- Độ dài shot: phần lớn 1,0–2,5 s (trung vị 1,5 s; 10 % ngắn nhất ≤ 0,6 s, 10 % dài nhất ≥ 5,1 s)
- Độ dài theo vai trò (p25–p75): hành động 1,0–2,4 s; chèn chi tiết 0,8–1,7 s; phản ứng 0,9–1,7 s; mở móc 1,3–8,1 s (gồm các clip 1 cú máy); kết 1,4–3,3 s; thiết lập 1,2–3,4 s
- Vai trò: hành động 26 %, chèn chi tiết 22 %, phản ứng 20 %, mở móc 12 %, kết 11 %, thiết lập 8 %
- Cỡ cảnh: trung 36 %, cận 29 %, trung cận 15 %, toàn 15 %, đồ họa / tiêu đề toàn khung 3 %, toàn rộng 1 %
- Chuyển động máy: tĩnh 91 %, track 4 %, handheld 2 %, whip 1 %, push_in 1 %
- Chữ trên hình 21 % shot · giao diện game / HUD 17 % shot (20/33 clip có HUD ở ít nhất 1 shot) · hiệu ứng 13 %
- Mở bằng: mở móc ×24, thiết lập ×8 · kết bằng: kết ×23, mở móc ×9 (clip 1 shot)

## Đợt 2 (S14.33, 05/10/2026) — 40 clip bổ sung, ưu tiên clip 2026

> **Địa vị:** vẫn là GỢI Ý theo phong cách ("có thể / khi nào hợp / điều kiện"), không áp đặt. Mục đích người dùng: mở rộng phong cách làm + dựng, và mở rộng Kho tài nguyên FF dùng lại được. Mã **E01–E40**, phiếu `research/kelly_official/phieu_dot2_40_clip.md`. Mẫu: 32 clip 2026 nhiều view (top 4,8 triệu → 380 nghìn view + vài clip 214–209 nghìn) + 8 clip chọn theo dạng còn thiếu (collab, bóng đá, quiz…); tổng 519 s, 92,8 MB. Bộ cắt tự động đếm cận dưới: trung vị 4 shot / clip (8/40 clip một cú máy), shot TB ≈ 2,4 s, ≈ 25 shot/phút; clip trung vị 13,0 s (5–30 s). Âm thanh: 40/40 clip có nhạc (46–100 % thời lượng).

### Điều mới so với Đợt 1 (mỗi mục ≥ 3 clip; **có thể** áp dụng, trộn được)
1. **Lớp đồ hoạ trạng thái game vẫn là cách kể "trong trận" chủ đạo ở 2026:** 17/40 clip dùng HUD / icon / thẻ / huy hiệu / tỉ số chồng lên cảnh 3D (E01, E03, E06, E07, E08, E09, E12, E13, E14, E15, E17, E18, E19, E22, E35, E38, E40) và thêm 5/40 xen quay màn hình / UI thật (E16, E29, E32, E37, E39). Cách chọn: HUD khi cần "biết ai sống / thắng", huy hiệu hạng khi kể "lên hạng", thẻ UI (TEAM INVITE) khi kể "rủ chơi".
2. **Tỉ số / bộ đếm đổi theo nhịp là dạng đồ hoạ dễ làm nhất sau chữ cố định:** E38 (0:1 → 102:6 + DEFEAT), E40 (bảng 3 hàng), E12 (kill 1…25), E07 (đạn 36 → 4 → 42), E01 (thanh máu + đầu lâu + thẻ REVIVAL). Có thể làm hậu kỳ, nhân vật chỉ cần nhìn điện thoại.
3. **Bối cảnh vẫn là đời thường, nhưng thêm hai kiểu mới:** (a) nền ngoài trời rộng một cú máy (công viên ghế dài E10, bãi cỏ E20, sân bóng E04 / E14) với đạo cụ lớn làm gag; (b) cảnh nội thất nhiều tầng (canteen E11 / E12 / E38, sofa lounge E28, phòng ngủ E22 / E40). Map FF xuất hiện như HUD (E32), không như cảnh.
4. **Đạo cụ lớn / lệch tỉ lệ làm tâm điểm gag** (E27 vali, E25 bánh số 9 + salad, E26 ramen, E24 túi xu, E11 khoai + bao lì xì, E21 kem): vật đơn ở giữa khung, nhân vật phản ứng.
5. **Quảng bá collab / sự kiện có khuôn riêng** (E02, E21, E25, E26, E29, E36, E37, E39, E31): logo đối tác cố định + dòng bản quyền + nhân vật 2D ghép cảnh 3D + thẻ chốt; trong mẫu 2026 nhóm này tập trung ở nửa view thấp (8/20 clip nửa dưới so với 1/20 ở nửa trên) — số đo, KHÔNG phải nhân quả (thời điểm đăng, nội dung khác nhau). Gợi ý: tiểu phẩm gag nhẹ có thể là điểm xuất phát an toàn hơn clip quảng bá.
6. **Emoji / glitch / chớp trắng làm cú chốt hoặc cảm xúc** (E01, E03, E04, E05, E15, E17, E19, E22 — 8 clip): mặt cận + emoji trên đỉnh khung hoặc trên đầu; thay cho cảnh hậu quả.
7. **Khuôn "A vs B" chia dọc + nhãn ngắn** (E07, E27, E33): mỗi nửa một nhân vật cùng việc.
8. **Kelly dạng ảnh thật / photoreal + đồ hoạ** (E05, E15, E18, E31 — thật hay AI khó phân biệt): cận mặt, một nền thật, thẻ / huy hiệu / emoji chồng lên; phù hợp clip 5–19 s.
9. **Vai phụ và pet lặp lại:** Maxim ở ≥ 10/40 clip (E03, E04, E06, E07, E08, E11, E19, E23, E27, E33, E36), Alvaro (E01, E10, E16), Hayato (E09, E13, E17 — nhận theo ngoại hình, chưa có chữ xác nhận tên), nữ tóc tết xanh–tím (E14, E22), nữ kính bay cam (E04, E28, E32), nữ tai mèo đồng phục (E30), chim cánh cụt (E13), nhân vật hề áo đỏ "Top Criminal" (E16, E24). Trang phục Kelly vẫn áo khoác vàng (ngoại lệ: áo hồng jeans ở sự kiện Songkran E31, trang phục chơi ở E39).
10. **Nhạc "to lên" ở giây 3–4 và 9–12** (E01 4 s, E05 4 s, E08 3 s, E12 4 s + 11 s, E16 3 + 6 + 9 s, E22 5 + 11 s, E27 6 + 16 s, E39 7 + 17 s) — khớp cắt / đổi đồ hoạ vào các điểm này **có thể** làm clip có nhịp; nhạc 46–100 % thời lượng. Thoại gốc hiếm; vài clip quảng bá có câu nói (E02, E39, E24).
11. **Cơ cấu định dạng (các nhóm giao nhau, đếm gần đúng):** tiểu phẩm 3D có lớp đồ hoạ trạng thái 17 clip; một cận / selfie + đồ hoạ 5 (E05, E15, E18, E23, E35); quảng bá collab / sự kiện 9; ghép người thật / chuyển động mạnh 3 (E31, E33, E34) → cơ cấu gần Đợt 1: một cận + đồ hoạ và tiểu phẩm có HUD vẫn là nhóm dễ dựng nhất.

### Tài nguyên thu về Kho (S14.33, CHỜ DUYỆT — người dùng xác nhận quyền dùng kênh 05/10/2026)
- Âm thanh: 14 bản nhạc trend + 3 đoạn giọng thông báo kill vào Kho âm thanh (nguồn id clip + giây ở `data/ref_kelly/kho_am_thanh/NGUON.tsv`).
- Ảnh: 18 mục / 33 ảnh (HUD ô vũ khí, đếm đạn, kill, thẻ REVIVAL, BOOYAH, Solo / Duo, TEAM INVITE, huy hiệu hạng, pin yếu, UI hồ sơ + phần thưởng, bản đồ + vòng bo, bảng điểm + DEFEAT; nền bãi cỏ + hòm đạn, khung thành; lựu đạn, máy đấm hơi BOOYAH; nhân vật Top Criminal; biểu cảm Kelly / Maxim) ở trạng thái CHỜ DUYỆT; chưa chỗ nào trong pipeline tự dùng.

## Nguồn đã phân tích (40 clip Đợt 1 + 40 clip Đợt 2, `data/ref_kelly/`, ngoài git)
Mã K01–K40 theo thứ tự `list.tsv`; id đầy đủ + tiêu đề + view trong `research/kelly_official/phieu_40_clip.md`.
