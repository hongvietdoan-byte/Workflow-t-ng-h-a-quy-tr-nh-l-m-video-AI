# Báo cáo phân tích kênh `@freefire_kelly_official` — Đợt 1 (05/10/2026)

> Việc **S14.32**, kế hoạch `docs/KE_HOACH_PHAN_TICH_KENH_KELLY_2026-10-05.md`. Chi phí **0 USD** (không gọi Claude API / dịch vụ trả tiền; gán nhãn trong phiên Claude Code). Chờ người dùng duyệt trước khi đưa luật vào prompt nào.
> Đầu ra: `knowledge/ff_styles/kelly_official.md` (phong cách, luật GỢI Ý) · `knowledge/craft/ne_canh_kho_dung.md` (kỹ thuật né cảnh khó dựng) · `research/kelly_official/phieu_40_clip.md` (phiếu từng clip) · `research/kelly_official/ghi_chu_hinh.md` (ghi chú hình) · `research/kelly_official_records/KELLY_SHOW/*.json` (nhãn từng shot, 33 clip).

## 1. Phạm vi và cách làm
- **40/40 clip đọc xong, không clip nào lỗi / bị chặn.** Mỗi clip: `reference_video.py sheets` (cắt shot + bảng khung) + bảng 6–12 khung đều theo thời gian (vì bộ cắt bỏ sót cắt khi hậu cảnh giống) + `audio_listen.py` (demucs + AudioSet + whisper). Video, khung hình, work_dir ở thư mục tạm ngoài git; repo chỉ giữ chữ + số đo; không cắt ghép / dùng lại hình của kênh.
- 33 clip ngắn (5–27 s) có nhãn từng shot; 7 clip tổng kết ~60 s (K04, K07, K08, K16, K18, K19, K20) chỉ đọc 12 khung đều + số đo âm thanh (bộ cắt bỏ sót nhiều cắt ở đây).
- Giới hạn: MỘT kênh; mốc giây ± 1 bước khung; âm thanh "nghe bằng số", lời whisper phần lớn là lời hát nhạc trend; chưa kiểm khớp môi.

## 2. Số đo chung (33 clip ngắn, 202 shot, 468 s)
- Clip: trung vị **14,3 s** (5,0–27,4 s); **9/33 là một cú máy liền**; clip nhiều shot: shot trung vị **1,5 s**, ≈ 10 % shot ≥ 4 s; 26 shot/phút (cận dưới).
- Cỡ cảnh: trung 36 %, cận 29 %, trung cận 15 %, toàn 15 %. Máy **tĩnh 91 %**, track 4 %. Ngang mắt 79 %.
- Chữ trên hình 21 % shot; HUD/giao diện game 17 % shot (20/33 clip có ít nhất một lần); 15/33 clip có chữ hoặc HUD **ngay shot đầu**.
- Âm thanh: nhạc trend ≥ 90 % thời lượng ở **38/40** clip; thoại gốc của nhân vật gần như không có (chỉ "What?" [K02], "Hmm" [K01]); hiệu ứng game thay thoại [K14 giọng thông báo kill].
- Nhóm view cao (13 clip ngắn): trung vị 3 shot/clip, 10/13 có HUD; nhóm mới nhất (10 clip): 7 shot/clip, 3/10 có HUD, view trung vị ≈ 107 nghìn so với ≈ 13 triệu (không suy ra nhân quả).

## 3. Năm phát hiện chính
1. **"Trong game" luôn được thể hiện bằng lớp thông tin, không bằng cảnh đánh trận:** HUD số đội + tên + thanh máu + đầu lâu trên đầu [K01, K11, K34], bảng đội + bộ đếm kill [K14, K18], icon hạng / kỹ năng [K03, K32, K35], thẻ UI [K17, K20, K34]. Người xem hiểu "sắp chết / thua / quadra" mà không có một khung hình gameplay nào.
2. **Bối cảnh là cảnh đời thường (văn phòng, canteen, bếp, công viên, lớp học…), không phải map FF.** Map chỉ là đạo cụ (TV bản đồ [K33], bản đồ dán tường [K02]).
3. **Định dạng dựng dễ nhất lại chiếm vị trí cao:** 1 shot cận Kelly + đồ hoạ trend (ống ngắm "Shooting Age Test" [K27], "My rank" [K40], STOP [K15], thanh emoji [K12], nhãn + gem [K31]) — 1 nhân vật, 1 nền, 5–12 s.
4. **Gag theo mẫu "tình huống → insert cận vật từ trên xuống → phản ứng mặt"** [K13, K22, K39]; cú chốt là phản ứng, hiếm CTA (2/40: [K21, K37]).
5. **Âm thanh = nhạc trend + hiệu ứng game, không thoại.** Với pipeline: khớp môi gần như không cần cho dạng này; nhạc trend cần giải bài toán bản quyền riêng.

## 4. Định dạng kịch bản "dựng chắc được" (đề xuất đưa vào S14.31 + bộ ý tưởng đo lại S14.22)
| Mức | Định dạng | Mẫu | Điều kiện chắc |
|---|---|---|---|
| Chắc | **A. 1 cận + đồ hoạ trend** (5–12 s) | K12, K27, K15, K40, K31, K34, K05 | 1 nhân vật có ảnh Kho, 1 nền đơn giản, đồ hoạ làm hậu kỳ |
| Chắc | **B. Tiểu phẩm 2–4 shot tĩnh + HUD** (8–15 s) | K01 (lia 1 cú: cần tách 3 shot), K06, K11, K14, K33, K36 | ≤ 2 nhân vật cùng khung, 1 nền đời thường, HUD / bảng kill làm hậu kỳ |
| Khá | **C. Quảng bá sự kiện** (17 s) | K21 | nền cửa hàng + chữ bong bóng + poster do đội thiết kế |
| Vừa | **D. Gag nhiều shot ngắn "insert + phản ứng"** (10–16 shot) | K13, K22, K39 | ≥ 3 nhân vật + đồ vật 3D (đĩa, nồi…) + nhất quán mặt qua nhiều shot — chi phí gen cao |
| Khó | **E. Chuỗi chạy / nhảy / rượt** | K30, K32, K35, K26 | chuyển động mạnh, nhiều nền — dễ lỗi |
| Ngoài pipeline | **F.** hợp tác người thật [K25]; cận điện thoại thật [K09, K10, K28]; tổng kết ghép cảnh cũ [K07…]; video bên thứ ba [K24] | — | cần footage thật / thư viện cảnh |

## 5. Tài nguyên còn thiếu (để dựng A–D)
- **Bối cảnh đời thường nhất quán** (văn phòng sọc đỏ, canteen, bếp, công viên + ghế đá, lớp học, phòng chờ, hành lang): chưa có trong Kho; cần ảnh / 3D từng nơi + câu bố cục.
- **Lớp HUD hoạt hình hậu kỳ:** thanh máu + chip số đội + tên + đầu lâu; bảng đội 4 dòng + bộ đếm kill; icon hạng / kỹ năng; thẻ TEAM INVITE / SUPER REVIVAL / hòm loot; thanh emoji; ống ngắm — cần module hậu kỳ (hiện chưa kiểm công cụ Dựng có hỗ trợ).
- **Tư liệu giao diện chính thức** (huy hiệu hạng, icon kỹ năng, thẻ UI đúng phiên bản) để làm HUD đúng; không có → HUD giản lược, ghi rõ.
- **Nhân vật phụ trong Kho:** Maxim, Alvaro, Shirou, Hayato / Tatsuya, nữ tai mèo, chim cánh cụt kính đen (pet), ALOK; biểu cảm mặt (sốc, bịt miệng, vùi mặt).
- **Đồ vật đời thường 3D:** cốc, đĩa, chảo, hộp quà, bóng rổ, túi đá…
- **Nhạc / hiệu ứng được phép dùng** (giọng thông báo kill, tiếng súng, chuông): hỏi bản quyền trước khi dùng nhạc trend.
→ Việc tạo tài nguyên sau, **hỏi tiền trước**.

## 6. Việc mở
- Người dùng duyệt luật (`kelly_official.md`) và danh mục (`ne_canh_kho_dung.md`) trước khi nạp vào prompt Biên kịch / Đạo diễn (qua cờ TẮT mặc định, như S14.20).
- Bổ sung định dạng A–D vào S14.31, đo lại 5 ý tưởng S14.22 bằng khuôn A/B.
- Đợt 2 (40 clip thêm theo dạng còn thiếu) chỉ khi Đợt 1 có ích; cần cân nhắc vì mẫu "view cao" lệch theo thời gian — nên lấy thêm clip 2026 nhiều view.
- Nghe tai các chỗ "nghe bằng số" (nhạc to lên giây 3–4, khoảng lặng K10).
