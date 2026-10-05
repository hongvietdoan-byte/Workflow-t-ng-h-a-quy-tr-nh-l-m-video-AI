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
- **Tránh (ngoài khả năng hiện tại):** hợp tác người thật [K25], giáo viên người thật [K39], cận điện thoại thật [K09, K10, K28], tổng kết ghép cảnh cũ [K07…], chuyển động mạnh nhiều nền [K30, K26], video bên thứ ba [K24 mèo thật, K17 flycam stock].
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

## Nguồn đã phân tích (40 clip, `data/ref_kelly/`, ngoài git)
Mã K01–K40 theo thứ tự `list.tsv`; id đầy đủ + tiêu đề + view trong `research/kelly_official/phieu_40_clip.md`.
